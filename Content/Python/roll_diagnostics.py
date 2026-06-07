"""roll_diagnostics.py - show what the generator generates.

Two tools, both registered under Tools > (see init_unreal.py):

  diagnose_last_roll()
      Walks the live ShuffleLab's AHexShuffleGenerator.LastNetwork, buckets every
      frontier cell by canonical (min-rotation) road mask, prints a histogram to
      the Output Log. Run after any Randomize.

  run_roll_sweep(n=200, base_seed=0)
      Calls UHexMapGrowthLibrary.GrowRoadNetwork N times (pure C++, no mesh
      placement) using the live actor's Growth params + core. Per necklace,
      reports mean / std / min / max / p50 / p95 / p99 and a recommended pool
      size (ceil(p95)). Writes a CSV under Design/Rolls/ for spreadsheet analysis.

Either tool can also run from the Output Log:
  import roll_diagnostics, importlib; importlib.reload(roll_diagnostics)
  roll_diagnostics.diagnose_last_roll()
  roll_diagnostics.run_roll_sweep(n=500, base_seed=42)
"""

import datetime
import math
import os

import unreal

# ---------------------------------------------------------------------------
# Necklace table - the 14 canonical (rotation-minimum) 6-bit road masks.
# Burnside count for binary necklaces of length 6 = 14, matches the catalog.
# Map: canonical mask -> (name, edge_count). Names match the tile catalog
# (T_street_<name>) so the histogram lines up with what the kit ships.
# ---------------------------------------------------------------------------

NECKLACE_NAMES = {
    0b000000: ("blank",    0),
    0b000001: ("deadend",  1),
    0b000011: ("bend",     2),   # adjacent edges
    0b000101: ("curve",    2),   # one-apart
    0b001001: ("straight", 2),   # opposite
    0b000111: ("tee",      3),   # 3 consecutive
    0b001011: ("tee_a",    3),
    0b001101: ("tee_b",    3),
    0b010101: ("tee_c",    3),   # Y / triradial (max symmetric)
    0b001111: ("quad",     4),
    0b010111: ("quad_b",   4),
    0b011011: ("quad_c",   4),
    0b011111: ("penta",    5),
    0b111111: ("junction", 6),
}

# Stable display order: by edge count, then name.
NECKLACE_ORDER = sorted(
    NECKLACE_NAMES.keys(),
    key=lambda m: (NECKLACE_NAMES[m][1], NECKLACE_NAMES[m][0]),
)


# ---------------------------------------------------------------------------
# Hex / mask helpers (Python mirror of HexCoordinates.h)
# ---------------------------------------------------------------------------

def _rotate_mask_6(mask, r):
    r %= 6
    return ((mask << r) | (mask >> (6 - r))) & 0x3F


def _canonical_mask(mask):
    best = mask & 0x3F
    for r in range(1, 6):
        rot = _rotate_mask_6(mask, r)
        if rot < best:
            best = rot
    return best


def _hex_distance(q, r):
    # cube y = -q - r; distance = (|x|+|y|+|z|) / 2
    return (abs(q) + abs(-q - r) + abs(r)) // 2


# ---------------------------------------------------------------------------
# Locate the live generator
# ---------------------------------------------------------------------------

def _sf(struct_val, name):
    """Get a field from a UE struct robustly. UE 5.x normally exposes struct fields
    via attribute access (`struct.field_name`), but some bindings only expose them
    via `get_editor_property("FieldName")`. Try attribute access first, then fall
    back; raise AttributeError if neither path works so the caller sees a clear error."""
    val = getattr(struct_val, name, None)
    if val is not None:
        return val
    try:
        return struct_val.get_editor_property(name)
    except Exception:
        pass
    # Some UE versions camelCase the property name in get_editor_property
    camel = "".join(w.capitalize() if i else w for i, w in enumerate(name.split("_")))
    try:
        return struct_val.get_editor_property(camel)
    except Exception as exc:
        raise AttributeError(
            "could not read struct field '%s' (also tried '%s'): %s"
            % (name, camel, exc)
        )


def _find_shuffle_generator():
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if sub is None:
        unreal.log_warning("[RollDiag] EditorActorSubsystem unavailable")
        return None
    for a in sub.get_all_level_actors():
        if a.get_class().get_name() == "HexShuffleGenerator":
            return a
    return None


def _build_core_cells(actor):
    """Mirror HexShuffleGenerator.cpp: use the assigned CoreLayout if any,
    otherwise the placeholder core. Returns a TArray-castable Python list."""
    core_layout = actor.get_editor_property("core_layout")
    cells = []
    if core_layout is not None:
        layout_cells = core_layout.get_editor_property("cells")
        if layout_cells is not None and len(layout_cells) > 0:
            for cc in layout_cells:
                r = unreal.HexCellResult()
                r.set_editor_property("axial", _sf(cc, "axial"))
                r.set_editor_property("road_mask", _sf(cc, "road_mask"))
                cells.append(r)
            return cells
    growth = actor.get_editor_property("growth")
    placeholder = unreal.HexMapGrowthLibrary.make_placeholder_core(growth)
    # Convert the returned TArray into a plain Python list so we can pass it back.
    return [c for c in placeholder]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def _percentile(sorted_vals, p):
    """Linear interpolation between order statistics (NIST type 7 / numpy default)."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * (p / 100.0)
    lo = int(math.floor(k))
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return float(sorted_vals[lo]) * (1.0 - frac) + float(sorted_vals[hi]) * frac


def _summarise(samples):
    if not samples:
        return {"mean": 0.0, "std": 0.0, "min": 0, "max": 0,
                "p50": 0.0, "p95": 0.0, "p99": 0.0}
    n = len(samples)
    mean = sum(samples) / n
    # Sample variance (n-1); we're sampling a generator distribution, not measuring
    # the full population. With n=200 the bias is sub-percent either way.
    var = sum((x - mean) ** 2 for x in samples) / (n - 1) if n > 1 else 0.0
    std = var ** 0.5
    s = sorted(samples)
    return {
        "mean": mean,
        "std": std,
        "min": s[0],
        "max": s[-1],
        "p50": _percentile(s, 50.0),
        "p95": _percentile(s, 95.0),
        "p99": _percentile(s, 99.0),
    }


# ---------------------------------------------------------------------------
# Tool A: single-roll histogram
# ---------------------------------------------------------------------------

def diagnose_last_roll():
    gen = _find_shuffle_generator()
    if gen is None:
        unreal.log_warning("[RollDiag] no HexShuffleGenerator in the open level")
        return

    # Re-grow the network from the actor's current Seed + Growth + CoreLayout.
    # We deliberately do NOT read `LastNetwork` directly — that UPROPERTY is Transient
    # without a Blueprint visibility modifier, so Python reflection can't see it. A
    # fresh deterministic grow with the same inputs reproduces the exact network the
    # actor just placed for any Randomize-style roll. (Edge case: after LoadRoll() the
    # actor's LastNetwork comes from JSON, not from grow — in that case re-growing with
    # the seed shown here may differ. Once LastNetwork is exposed for reflection we'll
    # read it directly and the edge case goes away — see HexShuffleGenerator.h.)
    growth = gen.get_editor_property("growth")
    core_r = _sf(growth, "core_radius")
    seed = gen.get_editor_property("seed")
    core_cells = _build_core_cells(gen)
    net = unreal.HexMapGrowthLibrary.grow_road_network(growth, core_cells, seed)
    cells = list(_sf(net, "cells")) if net is not None else []
    if not cells:
        unreal.log_warning(
            "[RollDiag] grow returned no cells - check the generator's Growth params (Radius=%d)"
            % _sf(growth, "radius")
        )
        return

    core_count = 0
    frontier_buckets = {m: 0 for m in NECKLACE_NAMES}
    unknown_buckets = {}

    for cell in cells:
        ax = _sf(cell, "axial")
        q, r = ax.x, ax.y
        if _hex_distance(q, r) <= core_r:
            core_count += 1
            continue
        canon = _canonical_mask(_sf(cell, "road_mask"))
        if canon in frontier_buckets:
            frontier_buckets[canon] += 1
        else:
            unknown_buckets[canon] = unknown_buckets.get(canon, 0) + 1

    frontier_total = sum(frontier_buckets.values()) + sum(unknown_buckets.values())

    unreal.log(
        "[RollDiag] Frontier mask histogram (seed=%d, %d frontier cells, %d core):"
        % (seed, frontier_total, core_count)
    )
    for mask in NECKLACE_ORDER:
        name, deg = NECKLACE_NAMES[mask]
        n = frontier_buckets[mask]
        pct = (100.0 * n / frontier_total) if frontier_total else 0.0
        unreal.log(
            "  {:<10s} ({:d}-edge, mask=0b{:06b})  {:>4d}  ({:>5.1f}%)".format(
                name, deg, mask, n, pct
            )
        )
    if unknown_buckets:
        unreal.log_warning(
            "[RollDiag] masks outside the 14-necklace catalog (should not happen):"
        )
        for m, n in sorted(unknown_buckets.items()):
            unreal.log_warning("    0b{:06b}  {:d}".format(m, n))


# ---------------------------------------------------------------------------
# Tool B: multi-roll sweep
# ---------------------------------------------------------------------------

def run_roll_sweep(n=200, base_seed=0):
    gen = _find_shuffle_generator()
    if gen is None:
        unreal.log_warning(
            "[RollDiag] no HexShuffleGenerator in the open level "
            "(the sweep reads its Growth params + CoreLayout)"
        )
        return None
    if n <= 0:
        unreal.log_warning("[RollDiag] n must be > 0")
        return None

    growth = gen.get_editor_property("growth")
    core_cells = _build_core_cells(gen)
    core_axials = set()
    for c in core_cells:
        ax = _sf(c, "axial")
        core_axials.add((ax.x, ax.y))

    unreal.log(
        "[RollDiag] sweep starting: %d rolls from seed %d (%d core cells pinned)"
        % (n, base_seed, len(core_axials))
    )

    per_necklace = {m: [] for m in NECKLACE_NAMES}
    per_roll_frontier_totals = []
    per_roll_unknown = []

    for i in range(n):
        seed = base_seed + i
        net = unreal.HexMapGrowthLibrary.grow_road_network(growth, core_cells, seed)
        roll_buckets = {m: 0 for m in NECKLACE_NAMES}
        unknown = 0
        frontier_total = 0
        for cell in _sf(net, "cells"):
            ax = _sf(cell, "axial")
            if (ax.x, ax.y) in core_axials:
                continue
            frontier_total += 1
            canon = _canonical_mask(_sf(cell, "road_mask"))
            if canon in roll_buckets:
                roll_buckets[canon] += 1
            else:
                unknown += 1
        for m in NECKLACE_NAMES:
            per_necklace[m].append(roll_buckets[m])
        per_roll_frontier_totals.append(frontier_total)
        per_roll_unknown.append(unknown)

    # Aggregate
    rows = []
    for mask in NECKLACE_ORDER:
        name, deg = NECKLACE_NAMES[mask]
        s = _summarise(per_necklace[mask])
        pool = int(math.ceil(s["p95"]))
        rows.append({
            "name": name,
            "edges": deg,
            "mask_bin": "0b{:06b}".format(mask),
            "mean": s["mean"],
            "std": s["std"],
            "min": s["min"],
            "max": s["max"],
            "p50": s["p50"],
            "p95": s["p95"],
            "p99": s["p99"],
            "pool_p95": pool,
        })

    mean_frontier = sum(per_roll_frontier_totals) / float(n)
    mean_unknown = sum(per_roll_unknown) / float(n)
    total_pool = sum(r["pool_p95"] for r in rows)
    total_mean = sum(r["mean"] for r in rows)

    unreal.log(
        "[RollDiag] sweep done: %d rolls, mean frontier cells %.1f, mean unresolved %.2f"
        % (n, mean_frontier, mean_unknown)
    )
    unreal.log("[RollDiag] per-necklace stats (recommended pool size = ceil(p95)):")
    unreal.log(
        "  {:<10s} {:>3s} {:>7s} {:>6s} {:>4s} {:>4s} {:>6s} {:>6s} {:>6s} {:>5s}".format(
            "name", "deg", "mean", "std", "min", "max", "p50", "p95", "p99", "pool"
        )
    )
    for r in rows:
        unreal.log(
            "  {name:<10s} {edges:>3d} {mean:>7.2f} {std:>6.2f} {min:>4d} {max:>4d}"
            " {p50:>6.1f} {p95:>6.1f} {p99:>6.1f} {pool_p95:>5d}".format(**r)
        )
    unreal.log(
        "[RollDiag] sum(mean)=%.1f  sum(pool_p95)=%d  (frontier budget target: ~120)"
        % (total_mean, total_pool)
    )

    # CSV
    out_dir = os.path.join(unreal.Paths.project_dir(), "Design", "Rolls")
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception as exc:
        unreal.log_warning("[RollDiag] could not create %s: %s" % (out_dir, exc))
        return None
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    csv_path = os.path.join(
        out_dir, "Sweep_seed{}_n{}_{}.csv".format(base_seed, n, ts)
    )
    try:
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("name,edges,mask_bin,mean,std,min,max,p50,p95,p99,pool_p95\n")
            for r in rows:
                f.write(
                    "{name},{edges},{mask_bin},{mean:.4f},{std:.4f},{min},{max},"
                    "{p50:.4f},{p95:.4f},{p99:.4f},{pool_p95}\n".format(**r)
                )
            f.write("\n# Sweep totals\n")
            f.write("# rolls,{}\n".format(n))
            f.write("# base_seed,{}\n".format(base_seed))
            f.write("# mean_frontier_cells,{:.4f}\n".format(mean_frontier))
            f.write("# mean_unresolved,{:.4f}\n".format(mean_unknown))
            f.write("# sum_mean,{:.4f}\n".format(total_mean))
            f.write("# sum_pool_p95,{}\n".format(total_pool))
            # Provenance: the growth knobs that produced this distribution.
            try:
                f.write("\n# Growth params (provenance)\n")
                f.write("# radius,{}\n".format(_sf(growth, "radius")))
                f.write("# core_radius,{}\n".format(_sf(growth, "core_radius")))
                f.write("# num_arteries,{}\n".format(growth.get_editor_property("num_arteries")))
                f.write("# road_budget,{}\n".format(growth.get_editor_property("road_budget")))
                f.write("# branch_chance,{:.4f}\n".format(growth.get_editor_property("branch_chance")))
                f.write("# straight_bias,{:.4f}\n".format(growth.get_editor_property("straight_bias")))
                f.write("# straight_decay,{:.4f}\n".format(growth.get_editor_property("straight_decay")))
                f.write("# max_straight_run,{}\n".format(growth.get_editor_property("max_straight_run")))
                f.write("# artery_straight_radius,{}\n".format(growth.get_editor_property("artery_straight_radius")))
                f.write("# artery_kink_chance,{:.4f}\n".format(growth.get_editor_property("artery_kink_chance")))
                f.write("# artery_fork_chance,{:.4f}\n".format(growth.get_editor_property("artery_fork_chance")))
            except Exception as exc:
                f.write("# (growth provenance footer error: {})\n".format(exc))
    except Exception as exc:
        unreal.log_warning("[RollDiag] CSV write failed: %s" % exc)
        return None

    unreal.log("[RollDiag] wrote %s" % csv_path)
    return csv_path


if __name__ == "__main__":
    diagnose_last_roll()
