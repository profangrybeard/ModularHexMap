# Worklog — session memory, newest first

## 2026-06-11 (evening) — Full test pass, red-herring pruning, the meander ruling

- **Director ran Testing.md end-to-end: every step passed.**
- **Tweakables audit** (director: "avoid red herrings"): every Growth field is live
  except `bCardinalArteries` (≡ `NumArteries=0`) — removed. Calibration was the real
  nest: `bAutoCalibrate` removed (OFF silently ignored the glTF mirror — foot-gun;
  always-on now, distrust-fallback retained), `ExtraYawDeg` removed (relic),
  `bInvertYawShift` → AdvancedDisplay (the Resistance #12 escape hatch, demoted).
- **Aesthetic ruling: `RiverStraightBias` 0.8 → 0.22 default** — the director tuned
  live and called the oxbow meander gorgeous. Census at 0.22: river mean 16.7 cells,
  74.5% curve necklaces; same 3 bridge pairs (dominant: straight-over-curve).
  **Prediction tested + wrong:** meander did NOT fix the bridge drought (0.41 → 0.47);
  options stay parked. `Baseline.csv` re-anchored to the 0.22 default.
- **`Roll_seed17.json` committed** — the reference-beauty roll (seed 17 @ bias 0.216).

## 2026-06-11 (later) — Rivers R4: core-anchored river, player heading, banks

Director design evolution mid-R4: the river is **designed into the core** — it passes
the wound (water sloshing/pouring into the Pit, his bespoke art pass), giving the river
a required start location, and **players grow it in a direction they prefer**. Rulings
(asked + answered): through-flow past the wound; direction chosen at destiny-roll time.
- **Growth:** ring-1 water route injected on two adjacent story tiles (gates at
  `RiverOutflowDir` and +1; the art replaces the visuals later — interim ring-1 gap
  accepted); two arms grow outward from the gates to the boundary; arteries whose gate
  cell is water yield their avenue to the river.
- **`FHexGrowthParams.RiverOutflowDir`** (−1 = rolled, 0–5 = the player's roll-time
  choice, permanent after).
- **Banks (R4):** flow-relative **Left Bank / Right Bank** via nearest-segment side of
  the river centerline — `GetBank` / `GetBankName` (BlueprintCallable). The geometry
  gift: adjacent gates force a 60° bend past the Pit, carving a small wedge district
  hugged by the river on two sides (seed 6: L=15 / R=95) — a pocket-quarter identity
  for free.
- **The wound unites the banks:** ring-1 water is core, the core propagates healing —
  restoration rounds the Pit between banks from the start; bridges stay the scarce
  mid-frontier connectors.
- **Gates:** verify_river_r4 ALL PASS (gates carry water, outflow at chosen heading,
  arms reach boundary, 0 unresolved, souls=120, banks populated, water/core = −1);
  restoration regression ALL PASS; census unchanged in KIND (same 3 bridge pairs, no
  new authoring) but **bridges mean fell 1.52 → 0.41** (radial arms parallel the
  arteries) — flagged as a tuning knob (meander up, or side-street bridging, or a
  min-bridge constraint).

## 2026-06-11 — Restoration loop: the first playable

The queue returned to Phase 3 after the rivers pivot. Landed + gated in one pass:
- **Engine API** (`AHexShuffleGenerator`): `bRestorationMode`, `GhostMaterial`,
  `RestoredCells`; `RestoreNext` / `RestoreAll` / `ResetRestoration` /
  `RestoreCell(Axial)` / `GetRestorationCandidates()`. Candidates = unrestored cells
  adjacent to the core or a restored *propagating* cell — land and bridges propagate,
  open water never does (the far bank waits for its bridge, per Rivers.md §1); a plain
  adjacency fallback keeps bridge-less destinies fully reachable. Deterministic
  ring-outward ordering.
- **Presentation:** ghost twin ISMs (same meshes, `M_GhostTile` translucent unlit on
  every slot, no collision) render the unrestored destiny; buildings only materialize
  with their soul; label switches to `Pop <restored+1> / 121`.
- **Save format:** `FHexRoll.Restored` — a roll JSON is now the complete town save
  (destiny + progress). Old rolls load as fresh Pop 1.
- **Gate ALL PASS** (`verify_restoration.py`, seed 6): Pop 1 start, 12 candidates at
  ring 2, RestoreNext advances, Save/Load round-trips progress, RestoreAll = 120/120
  with 0 candidates left, reset clean. Mid-heal proof shot (Pop 46) in Docs/Images.
- Tooling: `setup_ghost_material.py` (creates M_GhostTile, wires + saves ShuffleLab
  with restoration mode ON), `verify_restoration.py` (the gate), `_restore_shot.py`.

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
  one-cell.
- **Rivers R1–R3 IMPLEMENTED + verified in-engine** (director pivot: "trust the river
  before we design much more"; rivers jumped ahead of the restoration loop):
  - **R1 growth:** `FHexCellResult.WaterMask`, `GrowRiver` (seeded momentum walk,
    boundary→boundary, frontier-only, no self-touch, 24-attempt retry), water-as-wall
    `MarkRoad`, **artery-only one-deck bridging** (landing confirmed before writing —
    the first census caught failed crossings leaving roads diving into water, and
    arteries marching *along* the channel; both fixed, census re-run clean).
  - **Census discipline paid off:** exactly **3 bridge pairs exist** in 200 rolls
    (straight×straight 120° 45.7%, 60° 43.8%, straight×curve 10.5%) → the complete
    bridge kit is 3 parametric meshes. River mean 10.6 cells; bridges mean 1.52.
  - **R2 kit:** `gen_river_tiles.py` (channel 5 m, water at −0.9, banks in-tile,
    census-driven `BRIDGE_SETS`, writes `river_kit.json`); `setup_river.py` imports +
    wires the catalog (20 rows).
  - **R3 resolution:** material-keyed two-layer `MeasureTileMask` + joint-rotation
    `FindPlacement`; **20-tile calibration OK on both layers; 127 cells / 0 unresolved
    / souls=120 with the river through town and both bridge types placed (seed 6).**
  - Python-formatting gotcha caught live: `%`-formatting has no binary conversion
    (`%06b` → ValueError); and `AutomationLibrary.take_high_res_screenshot` silently
    no-ops outside the automation framework — console `HighResShot` is the working
    editor capture path.

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
