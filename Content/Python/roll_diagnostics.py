"""roll_diagnostics.py - show what the generator generates.

Three tools, all registered under Tools > (see hexmap_menus.py):

  diagnose_last_roll()
      Re-grows the live ShuffleLab's network from its Seed + Growth + CoreLayout
      and buckets every frontier cell by canonical (min-rotation) road mask.
      Prints a histogram to the Output Log. Run after any Randomize.

  run_roll_sweep(n=200, base_seed=0)
      Calls UHexMapGrowthLibrary.GrowRoadNetwork N times (pure C++, no mesh
      placement) using the live actor's Growth params + core. Per necklace,
      reports mean / std / min / max / p50 / p95 / p99 and a recommended pool
      size (ceil(p95)). Writes a CSV under Design/Rolls/ for spreadsheet analysis.

  constrained_randomize(constraints_name="default", max_attempts=200, verbose=True)
      Loads constraints from Design/RollConstraints/<name>.json. Grows with
      seed, seed+1, seed+2, ... until a roll satisfies every constraint, then
      sets the actor's Seed and triggers Randomize() so the satisfying network
      lands in the level. Prints per-attempt failures so you can see why rolls
      are bouncing.

All tools can also run from the Output Log:
  import roll_diagnostics, importlib; importlib.reload(roll_diagnostics)
  roll_diagnostics.diagnose_last_roll()
  roll_diagnostics.run_roll_sweep(n=500, base_seed=42)
  roll_diagnostics.constrained_randomize("default")
"""

import datetime
import json
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


# ---------------------------------------------------------------------------
# Tool C: constrained randomize - retry until a roll satisfies declared rules
# ---------------------------------------------------------------------------

# Keys in a constraint file that aren't necklace constraints (skipped on load).
_CONSTRAINT_RESERVED_KEYS = frozenset({"schema_version", "description"})


def _constraints_path(name):
    """Resolve a constraints name (e.g. 'default') to an absolute .json path."""
    proj = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    return os.path.join(proj, "Design", "RollConstraints", name + ".json")


def _necklace_name_to_canon():
    """Build a {name_string: canonical_mask} lookup so we can map DataTable row
    names (which are FNames like 'junction') to canonical mask values.
    NECKLACE_NAMES values are (name, edge_count) tuples — take the [0]."""
    return {v[0]: k for k, v in NECKLACE_NAMES.items()}


def _load_constraints_from_datatable(data_table):
    """Read a UDataTable of FHexNecklaceConstraint rows. Returns the same shape
    as _load_constraints_from_json: {canonical_mask_int: {min, max, exact}}."""
    if data_table is None:
        return {}
    name_to_mask = _necklace_name_to_canon()
    out = {}
    row_names = data_table.get_row_names() if hasattr(data_table, "get_row_names") else []
    if not row_names:
        # Fallback for older bindings — `get_data_table_row_names` is the alt API.
        try:
            row_names = unreal.DataTableFunctionLibrary.get_data_table_row_names(data_table)
        except Exception:
            row_names = []
    for row_name in row_names:
        key = str(row_name)
        if key not in name_to_mask:
            unreal.log_warning(
                "[RollDiag] DataTable row '%s' is not a known necklace; skipping. "
                "Valid names: %s" % (key, ", ".join(sorted(NECKLACE_NAMES.values())))
            )
            continue
        # Read the struct row. UE 5.x exposes `DataTableFunctionLibrary.get_data_table_row`.
        try:
            found, row = unreal.DataTableFunctionLibrary.get_data_table_row_from_name(
                data_table, row_name
            )
            if not found or row is None:
                continue
        except Exception:
            # Older API variant
            try:
                row = unreal.DataTableFunctionLibrary.get_data_table_row(data_table, row_name)
            except Exception:
                unreal.log_warning(
                    "[RollDiag] couldn't read DataTable row '%s' via either API" % key
                )
                continue
        canon = name_to_mask[key]
        out[canon] = {
            "min": int(_sf(row, "min")) if int(_sf(row, "min")) > 0 else None,
            "max": int(_sf(row, "max")) if int(_sf(row, "max")) >= 0 else None,
            "exact": int(_sf(row, "exact")) if int(_sf(row, "exact")) >= 0 else None,
        }
    return out


def _load_constraints_from_json(name):
    """Load a JSON constraints file. Returns {canonical_mask_int: {min, max, exact}}."""
    p = _constraints_path(name)
    if not os.path.isfile(p):
        unreal.log_warning(
            "[RollDiag] constraints file not found: %s (running unconstrained)" % p
        )
        return {}
    with open(p, "r", encoding="utf-8") as f:
        raw = json.load(f)
    name_to_mask = _necklace_name_to_canon()
    out = {}
    for key, val in raw.items():
        if key.startswith("_") or key in _CONSTRAINT_RESERVED_KEYS:
            continue
        if key not in name_to_mask:
            unreal.log_warning(
                "[RollDiag] constraint key '%s' is not a known necklace; skipping. "
                "Valid names: %s" % (key, ", ".join(sorted(NECKLACE_NAMES.values())))
            )
            continue
        canon = name_to_mask[key]
        if isinstance(val, bool):
            unreal.log_warning("[RollDiag] constraint '%s' is a bool; skipping" % key)
            continue
        if isinstance(val, int):
            out[canon] = {"min": val, "max": None, "exact": None}
        elif isinstance(val, dict):
            out[canon] = {
                "min": val.get("min"),
                "max": val.get("max"),
                "exact": val.get("exact"),
            }
        else:
            unreal.log_warning(
                "[RollDiag] constraint '%s' has unsupported value type %s; skipping"
                % (key, type(val).__name__)
            )
    return out


def _load_constraints(actor, name):
    """Load constraints, preferring the actor's assigned DataTable over the JSON file.

    Returns: (source_string, {canonical_mask: {min, max, exact}})
      source_string is a short tag like 'DataTable:DA_HexRollConstraints' or
      'JSON:default' that the log can print so you can see which source won.
    """
    data_table = None
    try:
        data_table = actor.get_editor_property("roll_constraints")
    except Exception:
        # Property doesn't exist yet (pre-rebuild) — fall through to JSON.
        data_table = None

    if data_table is not None:
        loaded = _load_constraints_from_datatable(data_table)
        return ("DataTable:%s" % data_table.get_name(), loaded)

    loaded = _load_constraints_from_json(name)
    return ("JSON:%s" % name, loaded)


def _check_constraints(buckets, constraints):
    """Return list of (mask_int, name_str, observed, requirement_str) for failed
    constraints. Empty list means all constraints satisfied. Both buckets and
    constraints are keyed by canonical mask int — we look up the name only for
    the human-facing failure tuple."""
    failures = []
    for mask, c in constraints.items():
        observed = buckets.get(mask, 0)
        name = NECKLACE_NAMES.get(mask, (str(mask), -1))[0]
        if c.get("exact") is not None:
            if observed != c["exact"]:
                failures.append((mask, name, observed, "exact %d" % c["exact"]))
            continue
        if c.get("min") is not None and observed < c["min"]:
            failures.append((mask, name, observed, "min %d" % c["min"]))
        if c.get("max") is not None and observed > c["max"]:
            failures.append((mask, name, observed, "max %d" % c["max"]))
    return failures


def _grow_and_bucket(growth, core_cells, core_radius, seed):
    """Grow with the given seed, return per-necklace frontier bucket counts."""
    net = unreal.HexMapGrowthLibrary.grow_road_network(growth, core_cells, seed)
    buckets = {m: 0 for m in NECKLACE_NAMES}
    if net is None:
        return buckets
    for cell in _sf(net, "cells"):
        ax = _sf(cell, "axial")
        if _hex_distance(ax.x, ax.y) <= core_radius:
            continue
        canon = _canonical_mask(_sf(cell, "road_mask"))
        if canon in buckets:
            buckets[canon] += 1
    return buckets


def _format_constraint(c):
    """Render {min, max, exact} as a compact human string for logs."""
    if c.get("exact") is not None:
        return "exact %d" % c["exact"]
    parts = []
    if c.get("min") is not None:
        parts.append("min %d" % c["min"])
    if c.get("max") is not None:
        parts.append("max %d" % c["max"])
    return ", ".join(parts) if parts else "(no bounds)"


def constrained_randomize(constraints_name="default", max_attempts=200,
                          base_seed=None, verbose=True):
    """Find a seed whose grown roll satisfies the constraints, then apply it.

    Steps deterministically through seed, seed+1, seed+2, ... so re-running with
    the same starting seed always finds the same satisfying seed. On success:
    sets the actor's Seed property to the winning seed, calls actor.randomize()
    to place the network in the level. On exhaustion: logs a warning naming the
    constraint that bounced the most rolls and the closest miss.

    Args:
      constraints_name: name under Design/RollConstraints/ (no .json suffix).
      max_attempts: cap on retries before giving up.
      base_seed: starting seed for the search; None = use the actor's current Seed.
      verbose: print per-failed-attempt info (recommended while tuning).
    """
    gen = _find_shuffle_generator()
    if gen is None:
        unreal.log_warning("[RollDiag] no HexShuffleGenerator in the open level")
        return None

    source, constraints = _load_constraints(gen, constraints_name)
    if not constraints:
        unreal.log(
            "[RollDiag] no constraints loaded (%s) - calling Randomize() unconstrained"
            % source
        )
        gen.randomize()
        return gen.get_editor_property("seed")

    growth = gen.get_editor_property("growth")
    core_radius = _sf(growth, "core_radius")
    core_cells = _build_core_cells(gen)

    start_seed = gen.get_editor_property("seed") if base_seed is None else int(base_seed)

    unreal.log(
        "[RollDiag] constrained randomize (source=%s) from seed %d (max %d attempts):"
        % (source, start_seed, max_attempts)
    )
    for mask, c in constraints.items():
        unreal.log("  %-9s %s" % (NECKLACE_NAMES[mask][0], _format_constraint(c)))

    # Track which constraint blocked the most rolls + the closest miss per
    # constraint so the failure summary is actionable. Both keyed by mask int.
    bounce_count = {mask: 0 for mask in constraints}
    closest_miss = {}  # mask -> (observed, requirement_str) closest to passing

    for attempt in range(max_attempts):
        try_seed = start_seed + attempt
        buckets = _grow_and_bucket(growth, core_cells, core_radius, try_seed)
        failures = _check_constraints(buckets, constraints)

        if not failures:
            unreal.log(
                "[RollDiag] satisfied at seed=%d (attempt %d/%d):"
                % (try_seed, attempt + 1, max_attempts)
            )
            for mask in constraints:
                unreal.log(
                    "  %-9s got %d  (%s)"
                    % (NECKLACE_NAMES[mask][0],
                       buckets.get(mask, 0),
                       _format_constraint(constraints[mask]))
                )
            gen.set_editor_property("seed", try_seed)
            gen.randomize()
            return try_seed

        for mask, name, observed, req in failures:
            bounce_count[mask] = bounce_count.get(mask, 0) + 1
            # "closest" = smallest distance to satisfaction
            prev = closest_miss.get(mask)
            if prev is None or abs(observed - prev[0]) > 0:
                closest_miss[mask] = (observed, req)

        if verbose:
            unreal.log(
                "[RollDiag] seed=%d FAIL: %s"
                % (try_seed,
                   "; ".join("%s=%d (%s)" % (name, obs, req)
                             for _m, name, obs, req in failures))
            )

    # Exhausted. Tell them which constraint hurt the most + closest miss.
    worst_mask, worst_count = max(bounce_count.items(), key=lambda kv: kv[1])
    unreal.log_warning(
        "[RollDiag] exhausted %d attempts from seed %d without satisfying %s."
        % (max_attempts, start_seed, source)
    )
    unreal.log_warning(
        "[RollDiag]   biggest bouncer: '%s' (%d/%d attempts failed it)"
        % (NECKLACE_NAMES[worst_mask][0], worst_count, max_attempts)
    )
    for mask, (obs, req) in closest_miss.items():
        unreal.log_warning(
            "[RollDiag]   closest miss '%s': observed %d, needed %s"
            % (NECKLACE_NAMES[mask][0], obs, req)
        )
    unreal.log_warning(
        "[RollDiag]   try: loosen constraints, raise max_attempts, "
        "or re-run run_roll_sweep() to check feasibility against this Growth tuning."
    )
    return None


# ---------------------------------------------------------------------------
# One-shot setup: create the default DT_RollConstraints_Default asset
# ---------------------------------------------------------------------------

_CONSTRAINTS_ASSET_DIR = "/Game/_project/Data"
_CONSTRAINTS_ASSET_NAME = "DT_RollConstraints_Default"
_CONSTRAINTS_STRUCT_PATH = "/Script/HexMapGenerator.HexNecklaceConstraint"


def create_default_constraints_table(assign_to_actor=True):
    """One-shot: create /Game/_project/Data/DT_RollConstraints_Default as a
    UDataTable of FHexNecklaceConstraint rows, populated with the same defaults
    as Design/RollConstraints/default.json (junction min 1, tee_c min 1).

    Run once after the C++ rebuild that introduces FHexNecklaceConstraint.
    Idempotent: if the asset already exists, just (re)populates rows and saves.

    Args:
      assign_to_actor: if True, also assigns the table to the live
        HexShuffleGenerator's RollConstraints property.

    Returns the created/loaded UDataTable, or None on failure.
    """
    full_path = "%s/%s" % (_CONSTRAINTS_ASSET_DIR, _CONSTRAINTS_ASSET_NAME)

    table = None
    if unreal.EditorAssetLibrary.does_asset_exist(full_path):
        table = unreal.EditorAssetLibrary.load_asset(full_path)
        unreal.log("[RollDiag] loaded existing %s" % full_path)
    else:
        struct = unreal.load_object(None, _CONSTRAINTS_STRUCT_PATH)
        if struct is None:
            unreal.log_error(
                "[RollDiag] couldn't find FHexNecklaceConstraint at '%s'. "
                "Did the C++ rebuild succeed and include the HexMapGenerator plugin? "
                "Check Plugins/HexMapGenerator/Binaries/Win64/UnrealEditor-HexMapGenerator.dll mtime."
                % _CONSTRAINTS_STRUCT_PATH
            )
            return None

        # Create the asset. DataTableFactory takes the row struct via either
        # `struct` or `data_table_struct` depending on UE version — try both.
        factory = unreal.DataTableFactory()
        for prop in ("struct", "data_table_struct"):
            try:
                factory.set_editor_property(prop, struct)
                break
            except Exception:
                continue
        else:
            unreal.log_warning(
                "[RollDiag] DataTableFactory didn't accept 'struct' or "
                "'data_table_struct'; create will probably fall through to defaults"
            )

        tools = unreal.AssetToolsHelpers.get_asset_tools()
        table = tools.create_asset(
            _CONSTRAINTS_ASSET_NAME,
            _CONSTRAINTS_ASSET_DIR,
            unreal.DataTable,
            factory,
        )
        if table is None:
            unreal.log_error("[RollDiag] failed to create %s" % full_path)
            return None
        unreal.log("[RollDiag] created %s" % full_path)

    # Populate via CSV. UE's DataTable CSV import expects the first column
    # header to be "---" (representing the row name); subsequent columns are
    # struct field names.
    csv = (
        "---,Min,Max,Exact\n"
        "junction,1,-1,-1\n"
        "tee_c,1,-1,-1\n"
    )
    try:
        errs = unreal.DataTableFunctionLibrary.fill_data_table_from_csv_string(table, csv)
        if errs:
            unreal.log_warning("[RollDiag] CSV import warnings: %s" % errs)
    except Exception as exc:
        unreal.log_warning(
            "[RollDiag] CSV import failed (%s) — add rows manually in the DT editor "
            "(junction min=1, tee_c min=1)" % exc
        )

    unreal.EditorAssetLibrary.save_asset(full_path)
    unreal.log("[RollDiag] saved %s" % full_path)

    if assign_to_actor:
        gen = _find_shuffle_generator()
        if gen is None:
            unreal.log_warning(
                "[RollDiag] no HexShuffleGenerator in level; assign %s manually "
                "via Details > Hex Shuffle | Constraints > Roll Constraints" % full_path
            )
        else:
            try:
                gen.set_editor_property("roll_constraints", table)
                unreal.log(
                    "[RollDiag] assigned %s to the live HexShuffleGenerator. "
                    "Save the level (Ctrl+S) to persist the assignment." % full_path
                )
            except Exception as exc:
                unreal.log_warning(
                    "[RollDiag] failed to assign DataTable to actor: %s. "
                    "Did the C++ rebuild include the RollConstraints UPROPERTY?" % exc
                )

    return table


if __name__ == "__main__":
    diagnose_last_roll()
