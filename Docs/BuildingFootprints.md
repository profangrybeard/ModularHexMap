# Building Footprints — research & process (PAUSED 2026-06-05, RESUMED + SHIPPED 2026-06-07)

> **Status update (2026-06-07):** the building system is **shipped in engine**. See
> [Buildings.md](Buildings.md) for the production pipeline (gen_buildings.py + setup_buildings.py
> + FHexTileDef::BuildingMesh + parallel ISM in HexShuffleGenerator). What follows below is the
> original research history — kept for context on the OBB-gable approach we DIDN'T ship, the
> Shapely-based footprint pipeline that we DID, and the crash gotchas. Do NOT use this doc to
> drive new work; it predates the gable -> flat-roof, area -> topology classification, and
> per-segment -> per-run door rule changes that landed in production.

---

> Original research-status text (preserved): **paused, removed from the kit.** The footprint
> *machinery* works end-to-end; what's unsolved is the *placement design* (see "Why paused" +
> "Open problems"). This doc is the resume point so we don't redo the research. Working
> reference implementation lives in
> [`Tools/blender/_wip_building_blockout.py`](../Tools/blender/_wip_building_blockout.py).

## Goal
Walk-in building footprints for the modular hex town: dense turn-of-century London lots that
follow the road outline, sized so the player can stand inside. The surface counterpart to the
dungeon — you come up to tour/shop. Buildings are eventually the "record of rescues" (occupancy).

## Spatial budget — the "do I have room?" answer (CONFIRMED)
From the locked contract (R=5 flat-top, apothem 4.33 m, 5 m edges, carriageway 3 m, walk 1 m):

| measure | value |
| --- | --- |
| carriageway edge (curb), from street centreline | 1.50 m |
| building face (1 m walk behind curb) | **2.50 m** |
| hex vertex (deepest a lot reaches) | 5.00 m |

**Buildable depth perpendicular to a street scales with road count:**
- `straight` (worst lining case): **2.5 m deep** at street mid, tapering to ~1 m, 0 at corners. ~10 m²/strip.
- `deadend` (1 road): ~⅚ of the hex — generous.
- `tee`/`quad` (3–4 roads): small wedges.
- `junction` (6 roads): **none** — all road.

A 1.8 m player capsule fits standing in a 2.5 m-deep lot with a 0.9×2.1 m doorway — cramped, as
intended. **So yes, there is room.** Confirmed in Blender with a human-scale reference.

## Locked design decisions (this session)
- **Building face = 1 m behind the curb** → 2.5 m from street centreline (`KEEP_HW = HW+WALK = 1.5+1.0`).
  The 1 m flagstone strip between curb and wall IS the walk.
- **Footprint = hex MINUS center→edge road corridors** (arms `t = -0.8 .. 6.0`, half-width `KEEP_HW`),
  so the footprint extends to the non-road hex edges and neighbours **meet at corners** (flatiron
  tips at street corners are fine).
- **Slivers removed by morphological opening** — Shapely `buffer(-0.2).buffer(+0.2)` with
  `join_style=mitre`, erasing every feature thinner than 0.4 m (kills the flatiron blades cleanly).
- **Hollow walk-in shell** — 0.25 m walls, inner void = `footprint.buffer(-0.25)`, a doorway
  box-cut (0.9 × 2.1 m) onto every street frontage.
- **Wall (eaves) height** 6 m default, a couple of tiles at 9 m for variety.
- **Roof = OBB-gable** — oriented bounding box → ridge axis → triangular "tent" prism (two planar
  slopes) **INTERSECTED** with the footprint volume so slopes clip exactly to plan. Pitch 35°.
  Crisp ridges + gable ends; chosen over lumpy `inset_region` hips.
- **3 materials per tile**, slot order: `M_Road` (carriageway), `M_Walk` (base+pavement),
  `M_Building_<name>` (per-tile, recolourable). glTF drops unused slots, so `junction` had no
  building slot and `blank` had no road slot.

## Pipeline (low-memory, crash-free)
1. Compute footprint as a 2-D **Shapely** polygon: `hexpoly().difference(union(corridors))`, then open.
2. Extrude clean polygon(s) to a prism; hollow with a simple boolean (`buffer(-0.25)` void).
3. Doorways: box cutters. Roof: OBB-gable tent ∩ footprint prism.
4. Every EXACT boolean runs on **simple solids only** — never through inset-collapse geometry.

**Shapely is required** in Blender's Python (installed 2026-06-05):
```
"C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe" -m pip install shapely
```

## Gotchas / crash lessons (hard-won — cost a Blender crash on a 32 GB box)
1. `bmesh.ops.inset_region(use_even_offset=True)` looped on **concave** footprints (e.g. the
   deadend street notch) balloons vertex counts.
2. Running an **EXACT boolean AFTER** such an inset (solving through self-intersecting roof
   geometry) spikes RAM until the OS dies. → **booleans-first, mesh-shaping-last**; never boolean
   through inset-collapse output. The OBB-gable roof avoids this entirely (two simple solids).
3. glTF export **drops unused materials** — slot counts vary per tile by what's actually present.
4. Generator places **one tile per cell** (`HexShuffleGenerator::Build`); a roadless cell
   (`RoadMask = 0`) resolves to the `blank` tile. There is **no doubling**.

## Why paused
The footprint generator did exactly what was asked, but the *design* wasn't a solution for the
goal. Concretely: making the `blank` (roadless) tile a full-hex building flooded the map —
with a sparse road network **most cells are roadless**, so most of the town became isolated
per-hex gable buildings ("tents"), reading as a mess. The buildings also don't merge into
continuous city blocks across cells. These are **placement/design** problems, not generation bugs.

## Open problems to solve before resuming
- **Non-road (`blank`) cell treatment.** Options floated: empty lot (flat) / solid flat-roofed
  block / something smarter. Undecided.
- **Continuous blocks vs per-hex isolation.** Per-tile buildings each carry their own roof, so a
  field of them reads as repeating tents, not a London block. Need a strategy: buildings that span
  multiple cells, shared roofs, or a different unit than the hex tile.
- **Which configs carry buildings, and how big.** Footprints currently fill the hex out to the
  edges (assuming neighbours' buildings meet) — but neighbours are usually `blank`, so the
  oversized building exposes its back/sides.
- **Relationship to road growth.** Where do buildings actually make sense given the topology?
- These depend on first settling **streets, walks, and the road-growth/block-sizing rules**
  (the reason we backed up).

## How to resume
1. The full working generator is preserved in
   [`Tools/blender/_wip_building_blockout.py`](../Tools/blender/_wip_building_blockout.py) (runnable
   blockout) and in git history (the building-bearing `gen_street_tiles.py`, commit before the revert).
2. Re-fold the building layer into `gen_street_tiles.py` once the open problems above are decided.
3. Ensure Shapely is installed in Blender's Python (command above).
