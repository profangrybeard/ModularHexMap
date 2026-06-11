# Worklog — session memory, newest first

## 2026-06-11 (close) — The landing: curated clamp wired, proven, shipped

Director's picks arrived as a screenshot (junction 2/2, tee_c 2/2, blank 2/4) —
two clarifications turned them into the blessed set:
- **"blank 2–4" meant plain VOID lots**, not dry cells (dry never rolls below 6).
  That's the **Weight dial, not a census row**: plain `T_street_blank` Weight
  **0.4** vs the three gardens at 1.0 → ~12% of dry cells stay void (~3/town,
  deterministic per destiny). The census row became **blank 2–40** (≥2 dry so
  gardens always exist; ≤40 culls the strangled tail).
- **Exact-2s loosened to 1–3** (junction, tee_c): same scarce-landmark read,
  jointly ~1-in-18 instead of ~1-in-500.
`_land_constraints.py` (one-shot) rewrote the table via CSV-fill (NB: 5.7 returns
a bool, not an error list — caught live), set the Weight, and **proved the loop**:
constrained satisfied at **seed 65, attempt 4/300**, placed-roll re-verify PASS,
dressing census **voids=4, gardens 9/10/6, dry 29**. Mirror committed as
`Design/RollConstraints/curated.json`. The "too much nothing" plan is **complete**
— L1 growth (wave reseeding), L2 clamp (this), L3 gardens (the variants).

## 2026-06-11 (cont.) — StraightDecay 0.33: the canyon-killer ruling

Director walked the gardens (look approved: "this looks great"), then ruled on the
**stacking turn pressure**: `StraightDecay` 0.8 → **0.33** — kills multi-tile
straight runs walled by buildings on both sides (2nd straight ~24%, 3rd ~8% at the
0.72 base bias). Promoted to the C++ default (the 0.22-meander precedent: the
spoken round number is the ruling; the Details drag had left 0.3464 slider noise —
`_normalize_decay.py` pinned the instance to exactly 0.33 and saved ShuffleLab, so
**instance = default = baseline**). Chain re-run (build 15 s → sweep): **Baseline
re-anchored at decay 0.33**:
- straights 11.3 → **8.9** (−21%, the intent); bends/curves up; junction 6.5;
  tee_c 0.69 (p50 still 0).
- **Cost surfaced: dry blank mean 23.4 → 27.8** (p50 23, p95 69) — wiggle wastes
  reach, the budget covers less ground. Accepted trade: blanks are tended ground
  now (the gardens absorb it); the blank-Max clamp guidance moved to ~35–40.
- Bridges 2.2; **bridge-pair census still census-complete** — same 3 authored
  kinds in 200 rolls (the rare straight×bend 4th kind absent, as documented), so
  the wiggle ruling required NO new bridge authoring.
- sum(mean) = 120.0 exact; 0 unresolved. Gates hold.

Also this stretch: a false "we died" alarm — the editor session had simply never
run the sweep (zero RollDiag lines); the director's level save at 21:29 was what
persisted the decay edit. Diagnosis path: log forensics over guessing.

## 2026-06-11 (later night) — Water is water, blank is blank; the gardens are staged

Two rulings landed and got built in one pass:

**1. Dry-blank semantics (census + constraints).** Resuming the layer-2 clamp, the
labels didn't add up: the staged reference rolls' "blank 30/45/60" decomposed as
**dry 15/24/36 + pure river cells 15/21/24** — the census bucketed by ROAD mask only,
so the river counted as blank, and a `blank Max` clamp would have culled the long
meanders preferentially. Director ruled: *water is water (hosts a water soul), blank
is blank (hosts a soul whose efforts live in that blank).* Fix in
`roll_diagnostics.py` (Python-only; menu auto-reload means no restart):
- `blank` = road 0 AND water 0 everywhere (histogram / sweep / CSV / constraints);
  pure-water cells get a `water` pseudo-bucket (sentinel 0x40) — so `sum(mean)` still
  accounts for all 120 souls, and `water` is now a legal constraint row (a
  river-length clamp, free). Bridges stay under their road necklace.
- Verified offline by executing the module with a stubbed `unreal` against the three
  reference rolls: dry counts exact, totals 120, `blank max 5` fails at 36 while a
  `water` row resolves. Testing.md T6 + oddities #2/#3 trued; RollConstraints README
  documents the semantics; **Baseline.csv re-anchor pending** (one sweep click — old
  census numbers don't compare raw).
- **The Max=5 finding:** `DT_RollConstraints_junction_mxBlank` (committed at the
  previous session close; rows lowercase-correct) can never pass at census Max 5
  (floor was 12 — the river alone exceeds 5), and Constrained Randomize on
  exhaustion returns None and leaves the level unchanged — so the "good results"
  were unconstrained Layer-1 rolls. Re-pick N from the dry re-anchored sweep
  (workable band likely ≈ 25–35 dry); the Details-panel Max edit was unsaved.

**2. Layer 3 staged: open ground is occupied ground.** Engine + kit + wiring written,
two gates left (build + editor pass):
- **Engine (built same session — 21 s clean):**
  `FHexTileDef.Weight` returns with its consumer. Both resolvers collect ALL
  mask-matching tiles and pick Weight-proportionally from a per-cell
  `FRandomStream(VariantSeedFor(Seed, Axial))` (spatial-hash primes, engine-stable);
  mask-0 cells also roll a free heading so gardens don't stamp. Deterministic per
  destiny — LoadRoll re-places identical variants (Seed restored before Build);
  healing/ghosts consistent (RefreshPresentation funnels through Build);
  `FHexRoll` unchanged. Single-candidate masks behave exactly as before.
- **Kit:** `gen_blank_variants.py` → `T_blank_garden` (railed circular green, two
  gate gaps at edges 0/3, centre monument, shrubs), `T_blank_green` (off-centre
  lawn, bezier desire-line, one tree, mound lenses), `T_blank_allotment` (5 raised
  timber beds, shed standing on the sixth plot, compost). Street-kit canvas
  imported from `gen_curved_tiles` (can't drift); new `M_Green` master (no
  'Road'/'Water' in any name — tiles measure 0/0); baked + verified via the new
  **`render_contact.py`** (the contact-sheet ToDo, now a keeper tool;
  `Docs/Images/ContactSheets/`). Registry + manifest entries live.
- **Wiring:** `setup_blank_variants.py` (one-shot GUI editor; `blank_kit.json` →
  catalog rows incl. Weight). **ORDER MATTERS: run only after the C++ build** —
  `weight` doesn't exist in the old binaries' reflection. Plain blank stays in the
  pool at Weight 1.0 (the void:tended ratio = catalog dial).
- **Materials rider:** `M_Water` + `M_Green` added to `hextile_materials.CANON` —
  the river-dupes ToDo closes on the next Reimport (then Recalibrate).

**The chain ran same session (editor closed, all green):** `Build.ps1` (21 s) →
`setup_blank_variants` one-shot (3 imported, **24 catalog rows**, saved) →
consolidate commandlet (**masters `M_Water` + `M_Green` created; 32 slots rebound,
44 dupes deleted, 10 folders pruned** — river-dupe ToDo closed) → `verify_shuffle`
(calibration OK **24 tiles**, 127 cells / 0 unresolved / souls=120, dry histogram
live) → 200-roll sweep → **Baseline.csv re-anchored dry**: blank mean 23.4 / p50 19
/ p95 64 / max 87; water mean 14.3; river 16.9 / bridges 2.52; sum(mean) = 120.0
exact; 0 unresolved.

**Verify also decoded the committed constraints table** (`junction_mxBlank`):
junction **Max 2**, tee_c **Min 1**, blank **Max 5** — all three infeasible-to-rare
against the post-Layer-1 distribution (junction mean 7.3 since densification;
tee_c p50 = 0; blank dry min 7). Constrained Randomize bounced 100/100 on blank.
**Director's picks outstanding:** blank Max (dry terms — the layer-2 N), junction
Max (or accept that 6-way scarcity is a growth/landmark pass, not a constraint),
tee_c Min. Then SAVE the table + mirror a JSON preset.

## 2026-06-11 (night) — The "too much nothing" hunt: three diagnoses, one real cause

Director ruled: congestion fine, blanks kill it, no player layout agency ever
(min-block-size struck as vestigial). Layer-1 fix became a census-driven hunt —
two plausible mechanisms were real but SMALL; the third was the cause:

| Stage | blank mean | bridges mean |
| --- | --- | --- |
| 0.22 meander baseline (strangled avenues) | 83.7 | 0.47 |
| + **bridge-at-the-gate** (avenues cross transverse arms at their gate; the river's own two axes stay properly dead) | 81.0 | 0.77 |
| + **daring lanes** (`SideBridgeChance` 0.35 — blocked side-street tips may throw a one-deck transverse crossing) | 80.0 | 1.11 |
| + **wave reseeding** (between waves every street may sprout a fresh tip until RoadBudget spends or the map saturates) | **36.5** | **2.54** |

The dominant cause was **subcritical growth stranding the budget**: tips die against
water walls and decay, the pool drains, and growth used to halt with ~150 of 174
budget unspent — the town starved with money in the bank. Wave reseeding makes
`RoadBudget` the actual density contract (the director's one honest dial). Bridges
landed back at the original 2–3 design read, clustered near the center (London-style),
without bending any character knobs. Gates ALL PASS throughout; 0 unresolved over
every 200-roll census. Densified streets surfaced a 4th bridge pair
(straight × bend-water, 0.4%) — authored per kit discipline (`T_bridge_09_06`),
catalog now 21 tiles. Remaining tail (blank p95 = 68, max 107 = geography-strangled
rolls) is layer 2's clamp — the director picks N from reference rolls. Layer 3
(garden-square blank variants) queued.

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
