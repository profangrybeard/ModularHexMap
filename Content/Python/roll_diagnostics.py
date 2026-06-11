"""roll_diagnostics.py - show what the generator generates.

Three tools, all registered under Tools > (see hexmap_menus.py):

  diagnose_last_roll()
      Reads the live ShuffleLab generator's LastNetwork (the cells it actually
      placed — valid after Randomize, BuildFromSeed, or LoadRoll alike) and
      buckets every frontier cell by canonical (min-rotation) road mask.
      Prints a histogram to the Output Log.

  run_roll_sweep(n=200, base_seed=0)
      Calls UHexMapGrowthLibrary.GrowRoadNetwork N times (pure C++, no mesh
      placement) using the live actor's Growth params + core. Per necklace,
      reports mean / std / min / max / p50 / p95 / p99 and a recommended pool
      size (ceil(p95)). Writes a CSV under Design/Rolls/ for spreadsheet analysis.

  constrained_randomize(constraints_name="default", max_attempts=200, verbose=True)
      Loads constraints (the actor's RollConstraints DataTable if assigned, else
      Design/RollConstraints/<name>.json). Grows with seed, seed+1, seed+2, ...
      until a roll satisfies every constraint, then calls BuildFromSeed(seed) so
      the EXACT validated network lands in the level (Randomize() pre-increments
      and would place the next, unvalidated seed), and re-checks the placed
      LastNetwork as a belt-and-suspenders assertion. Prints per-attempt
      failures so you can see why rolls are bouncing.

Bucket semantics (director's ruling 2026-06-11): 'blank' counts DRY open ground
only (road mask 0 AND water mask 0). Pure-water cells bucket as 'water' (also a
legal constraint row = river-length clamp); bridges count under their road
necklace. Every frontier cell lands in exactly one bucket, so sum(mean) over the
14 necklaces + water still accounts for all 120 souls.

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

# Pseudo-bucket: frontier cells that are NOT street necklaces. Director's ruling
# (2026-06-11): water is water (hosts a water soul); blank is dry ground (hosts a
# soul whose work lives in that blank). A road-mask-0 cell carrying water is a
# RIVER cell, never a "blank" — it must not trip blank-max curation or pad the
# open-ground stats. Bridges (road != 0, water != 0) keep their road necklace:
# they carry streets. The sentinel key lives outside 6-bit mask space so the
# water bucket can share the necklace dict (keeping sum(mean) = 120 exact) and
# the constraints namespace (a 'water' row = river-length clamp) without ever
# colliding with a canonical road mask.
WATER_PSEUDO_MASK = 0x40
PSEUDO_NAMES = {WATER_PSEUDO_MASK: ("water", 0)}
ALL_BUCKET_NAMES = {**NECKLACE_NAMES, **PSEUDO_NAMES}


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

def _core_axial_set(core_cells):
    """The pinned core as a set of (q, r) tuples — membership, not radius, so an
    irregular authored core is excluded correctly everywhere."""
    out = set()
    for c in core_cells:
        ax = _sf(c, "axial")
        out.add((ax.x, ax.y))
    return out


def _bucket_cells(cells, core_axials):
    """Bucket cells by canonical road mask, excluding core cells (axial membership).
    Pure-water cells (road mask 0, water mask != 0) are river, not blank — they
    land in the WATER_PSEUDO_MASK ('water') bucket; bridges keep their road
    necklace. 'blank' therefore means DRY open ground (road 0 AND water 0).
    Returns (frontier_buckets, core_count, unknown_buckets)."""
    buckets = {m: 0 for m in ALL_BUCKET_NAMES}
    unknown = {}
    core_count = 0
    for cell in cells:
        ax = _sf(cell, "axial")
        if (ax.x, ax.y) in core_axials:
            core_count += 1
            continue
        road = int(_sf(cell, "road_mask"))
        if road == 0 and int(_sf(cell, "water_mask")) != 0:
            buckets[WATER_PSEUDO_MASK] += 1
            continue
        canon = _canonical_mask(road)
        if canon in buckets:
            buckets[canon] += 1
        else:
            unknown[canon] = unknown.get(canon, 0) + 1
    return buckets, core_count, unknown


def _joint_canonical(road, water):
    """Canonicalize a (road, water) mask PAIR under JOINT rotation — both layers rotate
    by the same k, because a bridge's identity is the relative road/water geometry."""
    best = None
    for r in range(6):
        key = (_rotate_mask_6(road, r) << 6) | _rotate_mask_6(water, r)
        if best is None or key < best:
            best = key
    return ((best >> 6) & 0x3F, best & 0x3F)


def _pair_name(pair):
    rd, wt = pair
    rn = NECKLACE_NAMES.get(_canonical_mask(rd), ("0b{:06b}".format(rd),))[0]
    wn = NECKLACE_NAMES.get(_canonical_mask(wt), ("0b{:06b}".format(wt),))[0]
    # NB: %-formatting has no binary conversion — use str.format for the masks.
    return "road:{} x water:{} [0b{:06b}|0b{:06b}]".format(rn, wn, rd, wt)


def _water_census(cells, core_axials):
    """Water-layer stats over placed/grown cells (frontier only).
    Returns (water_buckets{canon: n}, bridge_pairs{(road,water) joint-canon: n},
             water_cell_count, bridge_count)."""
    water_buckets, bridge_pairs = {}, {}
    water_cells = bridges = 0
    for cell in cells:
        ax = _sf(cell, "axial")
        if (ax.x, ax.y) in core_axials:
            continue
        w = int(_sf(cell, "water_mask"))
        if w == 0:
            continue
        water_cells += 1
        wc = _canonical_mask(w)
        water_buckets[wc] = water_buckets.get(wc, 0) + 1
        rd = int(_sf(cell, "road_mask"))
        if rd != 0:
            bridges += 1
            pair = _joint_canonical(rd, w)
            bridge_pairs[pair] = bridge_pairs.get(pair, 0) + 1
    return water_buckets, bridge_pairs, water_cells, bridges


def diagnose_last_roll():
    gen = _find_shuffle_generator()
    if gen is None:
        unreal.log_warning("[RollDiag] no HexShuffleGenerator in the open level")
        return

    # Read the network the actor ACTUALLY placed. LastNetwork is exposed to reflection
    # (BlueprintReadOnly + AllowPrivateAccess — see HexShuffleGenerator.h) precisely so
    # this tool reports the truth for Randomize, BuildFromSeed, and LoadRoll alike:
    # no re-grow, no "loaded rolls aren't reproducible" edge case.
    net = gen.get_editor_property("last_network")
    cells = list(_sf(net, "cells")) if net is not None else []
    if not cells:
        unreal.log_warning("[RollDiag] no roll placed yet — Randomize (or Load Roll) first")
        return

    seed = gen.get_editor_property("seed")
    core_axials = _core_axial_set(_build_core_cells(gen))
    frontier_buckets, core_count, unknown_buckets = _bucket_cells(cells, core_axials)
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
    n_water = frontier_buckets[WATER_PSEUDO_MASK]
    pct = (100.0 * n_water / frontier_total) if frontier_total else 0.0
    unreal.log(
        "  {:<10s} (river: road 0 + water)  {:>4d}  ({:>5.1f}%)".format(
            "water", n_water, pct
        )
    )
    if unknown_buckets:
        unreal.log_warning(
            "[RollDiag] masks outside the 14-necklace catalog (should not happen):"
        )
        for m, n in sorted(unknown_buckets.items()):
            unreal.log_warning("    0b{:06b}  {:d}".format(m, n))

    # Water layer: river cells + bridge pairs (Docs/Rivers.md census).
    wb, bp, wcount, bcount = _water_census(cells, core_axials)
    unreal.log("[RollDiag] water: %d river cells, %d bridges" % (wcount, bcount))
    for m, n in sorted(wb.items()):
        nm = NECKLACE_NAMES.get(m, ("0b{:06b}".format(m),))[0]
        unreal.log("  water {:<10s} {:>3d}".format(nm, n))
    for pair, n in sorted(bp.items(), key=lambda kv: -kv[1]):
        unreal.log("  bridge %-46s %3d" % (_pair_name(pair), n))


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
    core_axials = _core_axial_set(core_cells)

    unreal.log(
        "[RollDiag] sweep starting: %d rolls from seed %d (%d core cells pinned)"
        % (n, base_seed, len(core_axials))
    )

    per_necklace = {m: [] for m in ALL_BUCKET_NAMES}
    per_roll_frontier_totals = []
    per_roll_unknown = []

    agg_water, agg_pairs = {}, {}
    per_roll_water, per_roll_bridges = [], []

    for i in range(n):
        seed = base_seed + i
        net = unreal.HexMapGrowthLibrary.grow_road_network(growth, core_cells, seed)
        cells = list(_sf(net, "cells")) if net is not None else []
        roll_buckets, _core, unknown_buckets = _bucket_cells(cells, core_axials)
        for m in ALL_BUCKET_NAMES:
            per_necklace[m].append(roll_buckets[m])
        per_roll_frontier_totals.append(
            sum(roll_buckets.values()) + sum(unknown_buckets.values()))
        per_roll_unknown.append(sum(unknown_buckets.values()))
        wb, bp, wcount, bcount = _water_census(cells, core_axials)
        per_roll_water.append(wcount)
        per_roll_bridges.append(bcount)
        for m, c in wb.items():
            agg_water[m] = agg_water.get(m, 0) + c
        for pair, c in bp.items():
            agg_pairs[pair] = agg_pairs.get(pair, 0) + c

    # Aggregate. The water pseudo-bucket rides along as a normal row (mask_bin
    # label 'water') so sum(mean) still accounts for every frontier cell = 120.
    rows = []
    for mask in NECKLACE_ORDER + [WATER_PSEUDO_MASK]:
        name, deg = ALL_BUCKET_NAMES[mask]
        s = _summarise(per_necklace[mask])
        pool = int(math.ceil(s["p95"]))
        rows.append({
            "name": name,
            "edges": deg,
            "mask_bin": ("water" if mask == WATER_PSEUDO_MASK
                         else "0b{:06b}".format(mask)),
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

    # Water census (Docs/Rivers.md): the empirical authoring budget for the river kit.
    ws = _summarise(per_roll_water)
    bs = _summarise(per_roll_bridges)
    unreal.log(
        "[RollDiag] WATER: river cells mean %.1f (min %d max %d) | bridges mean %.2f "
        "(min %d max %d)" % (ws["mean"], ws["min"], ws["max"],
                             bs["mean"], bs["min"], bs["max"])
    )
    total_w = sum(agg_water.values()) or 1
    for m, c in sorted(agg_water.items()):
        nm = NECKLACE_NAMES.get(m, ("0b{:06b}".format(m),))[0]
        unreal.log("  water  {:<10s} {:>6d}  ({:>5.1f}%)".format(nm, c, 100.0 * c / total_w))
    unreal.log("[RollDiag] bridge pairs (joint-canonical; author these, most-common first):")
    total_b = sum(agg_pairs.values()) or 1
    for pair, c in sorted(agg_pairs.items(), key=lambda kv: -kv[1]):
        unreal.log("  bridge %-46s %6d  (%5.1f%%)" % (_pair_name(pair), c, 100.0 * c / total_b))

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
            f.write("\n# Water census (aggregate over all rolls)\n")
            f.write("# mean_river_cells,{:.4f}\n".format(ws["mean"]))
            f.write("# mean_bridges,{:.4f}\n".format(bs["mean"]))
            for m, c in sorted(agg_water.items()):
                nm = NECKLACE_NAMES.get(m, ("0b{:06b}".format(m),))[0]
                f.write("# water_{},{}\n".format(nm, c))
            for pair, c in sorted(agg_pairs.items(), key=lambda kv: -kv[1]):
                f.write("# bridge_0b{:06b}x0b{:06b},{}\n".format(pair[0], pair[1], c))
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
    names (which are FNames like 'junction') to canonical mask values. Includes
    the 'water' pseudo-bucket — constraining it bounds river length (pure-water
    cells; bridges count under their road necklace, blank stays dry-only)."""
    return {v[0]: k for k, v in ALL_BUCKET_NAMES.items()}


def _load_constraints_from_datatable(data_table):
    """Read a UDataTable of FHexNecklaceConstraint rows. Returns the same shape
    as _load_constraints_from_json: {canonical_mask_int: {min, max, exact}},
    or None when the table can't be read at all (caller falls back to JSON).

    UE 5.7's Python can't call the wildcard get-row Blueprint nodes on arbitrary
    row structs (verified live: both get_data_table_row_from_name and
    get_data_table_row raise) — so read whole COLUMNS as strings and zip them
    with the row names. get_data_table_column_as_string is a plain
    BlueprintCallable that works everywhere, and both it and
    get_data_table_row_names iterate the table's row map in the same order."""
    if data_table is None:
        return {}
    name_to_mask = _necklace_name_to_canon()
    dtl = unreal.DataTableFunctionLibrary
    try:
        row_names = [str(n) for n in dtl.get_data_table_row_names(data_table)]
        col_min   = list(dtl.get_data_table_column_as_string(data_table, "Min"))
        col_max   = list(dtl.get_data_table_column_as_string(data_table, "Max"))
        col_exact = list(dtl.get_data_table_column_as_string(data_table, "Exact"))
    except Exception as exc:
        unreal.log_warning(
            "[RollDiag] DataTable '%s' column read failed (%s) — falling back to JSON"
            % (data_table.get_name(), exc)
        )
        return None

    def _num(col, i, default):
        try:
            return int(float(col[i]))
        except (IndexError, ValueError, TypeError):
            return default

    out = {}
    for i, key in enumerate(row_names):
        if key not in name_to_mask:
            unreal.log_warning(
                "[RollDiag] DataTable row '%s' is not a known necklace; skipping. "
                "Valid names: %s" % (key, ", ".join(sorted(v[0] for v in ALL_BUCKET_NAMES.values())))
            )
            continue
        mn = _num(col_min, i, 0)
        mx = _num(col_max, i, -1)
        ex = _num(col_exact, i, -1)
        out[name_to_mask[key]] = {
            "min": mn if mn > 0 else None,
            "max": mx if mx >= 0 else None,
            "exact": ex if ex >= 0 else None,
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
                "Valid names: %s" % (key, ", ".join(sorted(v[0] for v in ALL_BUCKET_NAMES.values())))
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
        if loaded is not None:   # None = unreadable table -> fall through to JSON
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
        name = ALL_BUCKET_NAMES.get(mask, (str(mask), -1))[0]
        if c.get("exact") is not None:
            if observed != c["exact"]:
                failures.append((mask, name, observed, "exact %d" % c["exact"]))
            continue
        if c.get("min") is not None and observed < c["min"]:
            failures.append((mask, name, observed, "min %d" % c["min"]))
        if c.get("max") is not None and observed > c["max"]:
            failures.append((mask, name, observed, "max %d" % c["max"]))
    return failures


def _grow_and_bucket(growth, core_cells, core_axials, seed):
    """Grow with the given seed, return per-necklace frontier bucket counts."""
    net = unreal.HexMapGrowthLibrary.grow_road_network(growth, core_cells, seed)
    if net is None:
        return {m: 0 for m in ALL_BUCKET_NAMES}
    buckets, _core, _unknown = _bucket_cells(list(_sf(net, "cells")), core_axials)
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
    core_cells = _build_core_cells(gen)
    core_axials = _core_axial_set(core_cells)

    start_seed = gen.get_editor_property("seed") if base_seed is None else int(base_seed)

    unreal.log(
        "[RollDiag] constrained randomize (source=%s) from seed %d (max %d attempts):"
        % (source, start_seed, max_attempts)
    )
    for mask, c in constraints.items():
        unreal.log("  %-9s %s" % (ALL_BUCKET_NAMES[mask][0], _format_constraint(c)))

    # Track which constraint blocked the most rolls + the closest miss per
    # constraint so the failure summary is actionable. Both keyed by mask int.
    bounce_count = {mask: 0 for mask in constraints}
    closest_miss = {}  # mask -> (observed, requirement_str, distance_to_satisfaction)

    def _miss_distance(c, observed):
        """How far an observation is from satisfying constraint c (0 = satisfied)."""
        if c.get("exact") is not None:
            return abs(observed - c["exact"])
        if c.get("min") is not None and observed < c["min"]:
            return c["min"] - observed
        if c.get("max") is not None and observed > c["max"]:
            return observed - c["max"]
        return 0

    for attempt in range(max_attempts):
        try_seed = start_seed + attempt
        buckets = _grow_and_bucket(growth, core_cells, core_axials, try_seed)
        failures = _check_constraints(buckets, constraints)

        if not failures:
            unreal.log(
                "[RollDiag] satisfied at seed=%d (attempt %d/%d):"
                % (try_seed, attempt + 1, max_attempts)
            )
            for mask in constraints:
                unreal.log(
                    "  %-9s got %d  (%s)"
                    % (ALL_BUCKET_NAMES[mask][0],
                       buckets.get(mask, 0),
                       _format_constraint(constraints[mask]))
                )
            # BuildFromSeed places EXACTLY the validated seed. Randomize() would
            # pre-increment and place the unvalidated seed+1 — never fall back to it.
            if not hasattr(gen, "build_from_seed"):
                unreal.log_error(
                    "[RollDiag] generator has no BuildFromSeed — stale binaries? "
                    "Rebuild via Tools/Build.ps1. Refusing the Randomize() fallback: "
                    "it would place unvalidated seed %d." % (try_seed + 1)
                )
                return None
            gen.build_from_seed(try_seed)
            # Belt-and-suspenders: re-bucket what the actor ACTUALLY placed
            # (LastNetwork) and re-check — guards the BuildFromSeed contract itself.
            net = gen.get_editor_property("last_network")
            placed = list(_sf(net, "cells")) if net is not None else []
            placed_buckets, _c, _u = _bucket_cells(placed, core_axials)
            placed_failures = _check_constraints(placed_buckets, constraints)
            if placed_failures:
                unreal.log_error(
                    "[RollDiag] PLACED roll violates the validated constraints — "
                    "BuildFromSeed contract broken: %s"
                    % "; ".join("%s=%d (%s)" % (nm, ob, rq)
                                for _m, nm, ob, rq in placed_failures)
                )
            else:
                unreal.log(
                    "[RollDiag] placed roll re-verified against constraints (seed=%d)"
                    % try_seed
                )
            return try_seed

        for mask, name, observed, req in failures:
            bounce_count[mask] = bounce_count.get(mask, 0) + 1
            dist = _miss_distance(constraints[mask], observed)
            prev = closest_miss.get(mask)
            if prev is None or dist < prev[2]:
                closest_miss[mask] = (observed, req, dist)

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
        % (ALL_BUCKET_NAMES[worst_mask][0], worst_count, max_attempts)
    )
    for mask, (obs, req, _dist) in closest_miss.items():
        unreal.log_warning(
            "[RollDiag]   closest miss '%s': observed %d, needed %s"
            % (ALL_BUCKET_NAMES[mask][0], obs, req)
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
