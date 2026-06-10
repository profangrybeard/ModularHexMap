# Worklog — session memory, newest first

> The **memory** doc: dated session records of what landed and why. CLAUDE.md stays a
> lean on-ramp; the diary lives here. Direction (queue/ToDos) is [Roadmap.md](Roadmap.md);
> gotchas are [Resistance.md](Resistance.md).

## 2026-06-10 — Audit, master fix, platform hardening, graveyard sweep

Full external audit ([Audit_2026-06-10.md](Audit_2026-06-10.md)) + director feedback
session locked the direction (see Roadmap "Locked direction"), then two execution phases:

- **Master hygiene (`e63eb75`)** — `HexBase.blend` at HEAD contained three committed
  generator-output stowaways (`T_bldg_penta/straight/tee_a` + 7 on-demand materials,
  baked in during the buildings session, `8e7b862`). Purged via the live Blender MCP
  session; master back to canonical at ~101.5 KB. New gotchas #30 (LFS-size tell, guard
  ToDo) + #31 (`bpy.data.*.remove()` doesn't set `is_dirty`).
- **Phase 0 platform (`f6e9c87`)** — all five audit bugs fixed, verified in-engine
  (127 cells / core=7 / 0 unresolved / **souls=120**; constrained roll satisfied at
  seed=23 and the *placed* roll re-verified):
  - **`BuildFromSeed(int32)`** — grow+build exactly that seed. Kills the constrained-
    randomize off-by-one (`Randomize()` pre-increments). `Randomize()` ≡
    `BuildFromSeed(Seed+1)`.
  - **Occupancy nuked** per the 1-tile-=-1-soul law: `Occupancy`, `EstimatedVacancies`,
    `FHexRoll.Vacancies`, seeding scripts — gone. New `Souls` property + label.
  - **Spline-road system deleted outright** (ASplineRoad, 4 actor props, auto-draw,
    SM_RoadSeg/SM_GroundHex) — per-tile baked curves made it dead weight.
  - `roll_diagnostics`: DataTable constraints **actually load now** (UE 5.7 Python can't
    call the wildcard get-row nodes — read columns-as-strings zipped with row names);
    `diagnose_last_roll` reads the placed `last_network`; both unknown-necklace warning
    paths un-crashed; closest-miss tracks distance-to-satisfaction; placed-roll
    re-verification guards the BuildFromSeed contract.
  - Blessed ShuffleLab growth tuning promoted to `FHexGrowthParams` defaults;
    `MeasureTileMask` tolerance made absolute (250 uu).
- **Phase 1 heal (`1240f0b` + doc restructure)** — 13 dead scripts deleted; keepers
  machine-neutral (`__file__`-derived repo, `_project` paths, R=10); in-editor purge of
  `T_valley_0..5`, `SM_RoadSeg`, `SM_GroundHex`, and maps CoreGenLab / SplineLab /
  TestMap / Z_Houses (director-approved); ShuffleLab + PitCoreLab re-saved clean; doc
  drift reconciled; **CLAUDE.md split into context (CLAUDE.md) / direction (Roadmap.md
  + Design.md) / memory (this file) / resistance (Resistance.md)**.
- **Phase 2 rivers plan delivered + ruled** ([Rivers.md](Rivers.md)) — design brief from
  the director's Richmond/James weekend (river = divider of business/culture AND the
  thing that puts everyone on one team). Core insight: the two-bank divide is *emergent*
  (far bank only receives roads through bridges). Rulings same day: river/bridge cells
  house souls (souls = 120 holds); name = "River" (vanilla by choice); channel = 5 m
  one-cell. R1 (growth-side implementation) unblocked; restoration loop remains next in
  the build queue per the locked order.

## 2026-06-07 (late) — Buildings SHIPPED in engine

Single-story walk-in shop fronts tracing the splined road centerlines, baked from
`Tools/blender/gen_buildings.py`, placed by a parallel ISM in
`AHexShuffleGenerator::Build()` at every road-bearing frontier cell. Full pipeline in
[Buildings.md](Buildings.md).
- **`gen_buildings.py`** (production, manifest-aware) → 12 `T_bldg_*.glb`. Skips `blank`
  (user playground) and `junction` (no buildable area). Shapely `hex - corridor`
  footprints with orient(CCW), per-run arc-length door rule, interior walls, door
  frames + thresholds, angle-limited bevel, smooth shading.
- **5 material slots per tile** (`M_Building` / `M_BuildingBack` / `M_BuildingRoof` /
  `M_BuildingInterior` / `M_DoorFrame`); `M_BuildingBack` is the engine seam for future
  per-edge "inset on blank-side" alley behaviour.
- **`FHexTileDef::BuildingMesh`** + parallel `BISM->AddInstance` in `Build()`'s frontier
  branch; core cells skip buildings.
- **Door rule** is per-RUN arc length (per-segment failed on tessellated curves).
- **Corner gardens** classified by topology (bend-vertex) emit ZERO geometry — the
  user's authoring playground (~9 m² per corner via the inner-bend disc subtraction).
- Verified: 127 cells / 0 unresolved / building ISM count == road-bearing frontier count.
- Bonus fix: `save_occupancy.py`'s stale path (vacancies had silently been 0 since the
  reorg). *(Whole metric retired 2026-06-10.)*

## 2026-06-07 — Roll diagnostics + constraints DataTable

First analytical pass over the rolls + a bias knob:
- **Tools ▸ Diagnose Last Roll** — per-necklace histogram of the live roll.
- **Tools ▸ Hex Roll Sweep** — 200 rolls → mean/std/p95 per necklace + CSV under
  `Design/Rolls/`. First sweep: 24k cell samples, 0 unresolved, **Σ(mean) = 120.0
  exact**. Asset budget anchored at ~40 unique meshes.
- **Volatility flag:** `blank` σ/μ ≈ 0.43 (8%–72% open-ground swing) — min-block-size
  rule is the durable fix (Roadmap).
- **`FHexNecklaceConstraint`** row struct + **`RollConstraints` DataTable** UPROPERTY;
  **Tools ▸ Constrained Randomize** with retry-with-log (biggest bouncer / closest miss).
  Presets `DT_RollConstraints_Default` + `DT_RollConstraints_reqJunction`.
- **Python path silent-failure fixed** — editor Python moved to `Content/Python/`
  (UE-canonical; gotcha #22).

## 2026-06-06 — LKG tag `lkg` @ `6b746a3`: tile pipeline, spline junctions, masters, reorg

- **Iterative tile pipeline** — the "Hex Tiles" Blender addon (`tile_pipeline.py` +
  `tile_registry`/`tile_common`/`tile_manifest.json`): per-tile export toggles,
  Build-Enabled preview/export, **Promote to Bespoke**. Both generators manifest-aware.
  **Pit = first bespoke tile** (`Source_Art/Blender/Tiles/T_core_pit.blend`) with a 30°
  descent ramp + floor-normal fix.
- **Spline-fanned junctions** — central hub + cubic-bezier arms + tangential swirl
  (knobs `JUNCTION_HUB_R`/`JUNCTION_BOW`/`JUNCTION_SWIRL`); perpendicular-at-edge anchor
  preserved → tiles still tile.
- **Material masters** — ~130 per-mesh glTF dupes collapsed into 4 shared masters under
  `M_HexTile_Master`; reimport self-heals (gotcha #19).
- **Content reorg** → `/Game/_project/` (HexTiles/Data/Maps); editor Python at
  `Content/Python/`.

## 2026-06-06 — Curved roads + 2× scale + Pit center

- **Per-tile spline-smoothed roads** ([PerTileSplineRoads.md](PerTileSplineRoads.md)
  pivot): `bend`/`curve` are circular arcs anchored at edge midpoints (C1-smooth across
  tiles); junctions splined later the same day. Canonical generator
  `gen_curved_tiles.py`. All 14 configs.
- **2× tile scale** (R=5→**R=10**) holding the street/walk cross-section absolute →
  parkable block depth. Engine: `HexCircumradiusUU = 1000`.
- **Tile-border lips** (`M_TileBorder`) outline every cell — metric/debug aid.
- **Pit center radial star** — `gen_pit_core.py` → 7 tiles (Pit void + 6 spokes),
  hardwired via `DA_HexCoreLayout`; roads break at the Pit rim. (Cogwheel alley ring +
  valley tiles dropped; valley meshes finally deleted 2026-06-10.)
- **Dangling-stub prune** in `GrowRoadNetwork` + **core measure-and-rotate** fix
  (gotcha #16). Verified: 127 cells, core=7, 0 unresolved.

## Earlier milestones (compressed)

- **Randomizer engine** (`9db82fc`): cube coords, road-driven growth (pinned core +
  cardinal arteries + branching), geometry-measured rotation, ISM placement, ShuffleLab.
- **Pit-core blockout** (`fff0831`): intact pre-destruction 13-tile core, walkable
  PitCoreLab. **Rivers & bridges intent** captured (`510d6b2`).
- **14-config street kit + ShuffleLab tooling** (`6559e23`, `79e22d4`).
- **Spline-road runtime experiments** (`667a5bb`…`53cd6ed`) — proven, then rejected for
  per-tile baked curves; fully deleted 2026-06-10.
- **Foundation**: UE 5.7 C++ project + ported `TP_ThirdPerson` module + Blender master
  base + pipeline docs (`82d035e`…`e841282`).
