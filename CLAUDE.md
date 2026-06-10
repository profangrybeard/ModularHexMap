# CLAUDE.md — project memory & resume guide

> Read this first. It's the on-ramp for resuming **ModularHexMap** cold — for a fresh
> Claude session or a solo dev. Design intent lives in [Docs/Design.md](Docs/Design.md);
> the tile contract in [Source_Art/README.md](Source_Art/README.md); the pipeline in
> [Docs/Pipeline.md](Docs/Pipeline.md).

## What this is
A modular **hex map town hub** for Unreal Engine 5.7 (C++). The surface counterpart to
underground dungeon crawling: you come up to **tour, meet locals, shop**, then go back
down. **Not** combat/parkour. The town is a **record of the player's achievements**, and its
size *is* the rescue count (tiles house the people you save). Aesthetic: **dense
turn-of-the-century London**. Flat-top hex tiles assembled into streets; roads on the edges
govern how tiles connect.

Tiles are authored in **Blender** (via the Blender MCP), exported to **glTF**, imported into
UE. The **`HexMapGenerator`** plugin is a **working in-engine randomizer**: road-driven
growth + geometry-validated tile rotation, dropping real tiles under real light, with a live
population/vacancy metric. Reusable + runtime-callable (the same engine is the future
autofill / brainstorm / act-2 "rearrange the town" beat).

## Resume — quickstart
Repo root `C:\SCAD\_projects\ModularHexMap`. Engine: launcher **UE 5.7** at
`C:\Program Files\Epic Games\UE_5.7`. Blender **5.1** at `C:\Program Files\Blender Foundation\Blender 5.1`.

```powershell
# Build the editor target (after any C++ change; needs the editor CLOSED — DLL lock).
# This is the ONLY sanctioned compile path. NEVER use the VS 2022 Build menu on this
# project — it dies on $(IncludePath) > 32 KB (gotcha #29). The script wraps Build.bat
# so future-you doesn't have to remember the engine path / args.
.\Tools\Build.ps1

# Launch the editor (startup map = /Game/_project/Maps/ShuffleLab)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" `
  "C:\SCAD\_projects\ModularHexMap\ModularHexMap.uproject"

# Regenerate the curved street kit + pit core from the master (idempotent; never saves master)
# Both generators are now MANIFEST-AWARE: they skip tiles marked `bespoke` in
# Tools/blender/tile_manifest.json so a headless run can't clobber hand-authored tiles.
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background `
  "C:\SCAD\_projects\ModularHexMap\Source_Art\Blender\HexBase.blend" `
  --python "C:\SCAD\_projects\ModularHexMap\Tools\blender\gen_curved_tiles.py"   # 14 street tiles
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background `
  "C:\SCAD\_projects\ModularHexMap\Source_Art\Blender\HexBase.blend" `
  --python "C:\SCAD\_projects\ModularHexMap\Tools\blender\gen_pit_core.py"       # 7 core tiles
```

**Tile authoring pipeline (canonical — the "Hex Tiles" Blender addon).** Day-to-day tile work
runs through **`Tools/blender/tile_pipeline.py`** (install via Preferences ▸ Add-ons, or Run it
from the Text Editor). Open `HexBase.blend`, find the **Hex Tiles** sidebar tab:
- **Build Enabled → Preview & Export** lays the enabled *procedural* tiles out in a grid (transient
  preview, never saves the master) and writes their `.glb`.
- Each tile has an **export ☑** (persists to `tile_manifest.json`, git-tracked).
- **Promote to Bespoke** spins a tile into its own editable `.blend` under `Source_Art/Blender/Tiles/`
  (materials + a reference hex **linked** from the master; mesh is local), toggles it OFF for
  procedural export, and opens it. **Open Bespoke** reopens it; **Export This Tile** / **Return to
  Master** are the in-bespoke buttons. Leaving the master **never auto-saves** it (gotcha #2/#18).
- The registry (`tile_registry.py`) pulls the tile list straight from the generators, so there's no
  second list to maintain. `T_core_pit` is the **first bespoke tile** (`Source_Art/Blender/Tiles/
  T_core_pit.blend`).

**Roll the randomizer:** open `ShuffleLab` → select **`HexShuffleGenerator`** in the Outliner →
Details → **Randomize**. Tune under **Growth** (`NumArteries`, `RoadBudget`, `BranchChance`,
`StraightBias`); read **`Estimated Vacancies`**. Shuffled tiles are **transient** (re-roll each
session). **`Recalibrate`** if you re-import tiles.

**Rebuild the lab from scratch** (re-import 14 tiles + catalog + lit level), in a GUI editor:
`UnrealEditor.exe <uproject> -ExecutePythonScript="Tools\setup_shuffle_lab.py"`.
⚠️ **`setup_shuffle_lab.py` / `setup_pit_core.py` predate the `_project` reorg** — they import to the
old `/Game/HexTiles` paths. Update their destination paths to `/Game/_project/...` before re-running,
or just refresh existing assets via **Tools ▸ Reimport Hex Tiles** instead.

## Current status (works end-to-end)
> **★ TODAY (2026-06-07 late) — buildings SHIPPED in engine.** Single-story walk-in shop fronts
> tracing the splined road centerlines, baked from `Tools/blender/gen_buildings.py`, placed by
> a parallel ISM in `AHexShuffleGenerator::Build()` at every road-bearing frontier cell. Full
> pipeline (Blender → glTF → UE → ShuffleLab) is documented in **[Docs/Buildings.md](Docs/Buildings.md)**
> — read that first for any building work; this section is the high-level resume note.
> - **`gen_buildings.py`** (production, manifest-aware) → 12 `T_bldg_*.glb` in
>   `Content/_project/HexTiles/Source/`. Skips `blank` (user playground) and `junction`
>   (no buildable area). Same Shapely `hex - corridor` footprints the WIP used, now with
>   the production trimmings: orient(CCW) for normals, per-run arc-length door rule, interior
>   walls, door frames + thresholds, angle-limited bevel, smooth shading.
> - **5 material slots per tile**: `M_Building` / `M_BuildingBack` / `M_BuildingRoof` /
>   `M_BuildingInterior` / `M_DoorFrame`. `M_BuildingBack` is the engine seam for the future
>   per-edge "inset on blank-side" alley behaviour.
> - **C++ `FHexTileDef::BuildingMesh`** (`TSoftObjectPtr<UStaticMesh>`) + parallel
>   `BISM->AddInstance` in `AHexShuffleGenerator::Build()`'s frontier branch. Core (pit) cells
>   skip building placement.
> - **Door rule** is per-RUN arc length (per-segment was wrong — Shapely tessellates curves
>   into many short sub-segments and per-segment fits failed): `<3m=0, <7m=1, <25m=2, >=25m=3`.
>   Multi-frontage buildings get this per run, so every road frontage gets ≥1 door.
> - **Corner gardens** are now classified by TOPOLOGY (piece contains a bend vertex) and
>   emit ZERO geometry — that's the user's playground. The inner-bend disc subtraction grows
>   each corner to ~9 m² so there's room to author.
> - **Setup script** `Tools/setup_buildings.py` (one-shot, GUI editor) does first-time import +
>   DA wiring + force-saves. **Subsequent rebakes** go through the existing **Tools ▸ Reimport
>   Hex Tiles** menu (reimport_hextiles.py walks `/Game/_project/HexTiles` recursively, so
>   `Buildings/` is picked up automatically).
> - **Verified end-to-end**: 127 cells / 0 unresolved / building ISM count == road-bearing
>   frontier cell count (1:1 pairing).
> - **Bonus fix**: `Tools/save_occupancy.py` had a stale `/Game/Data/...` path from before the
>   `_project` reorg, so `EstimatedVacancies` had silently been 0 for weeks. Repointed +
>   re-seeded via commandlet — vacancies now flow through.
>
> **Session 2026-06-06 — curved roads + 2× scale + Pit center, all landed.** The whole map now
> reads as one consistent system, validated in `ShuffleLab` (127 cells, core=7, 0 unresolved):
> - **Per-tile spline-smoothed roads** (the [PerTileSplineRoads.md](Docs/PerTileSplineRoads.md)
>   pivot): `bend`/`curve` are now circular arcs anchored at the edge midpoints (C1-smooth across
>   tiles); junctions were radial *then* — **later splined too** (see Latest below). New generator
>   **`Tools/blender/gen_curved_tiles.py`** (faceted `gen_street_tiles.py` superseded). All 14 configs.
> - **2× tile scale** (R=5→**R=10**) holding the street/walk cross-section absolute (3 m road, ~1 m
>   walk) → parkable block depth. Engine side: `HexCircumradiusUU = 1000` on the generator.
> - **Tile-border lips** (`M_TileBorder`, near-black) outline every cell — a metric/debug aid.
> - **The Pit center caught up** — `gen_pit_core.py` → 7-tile **radial star** (Pit void + 6 spokes),
>   hardwired via `DA_HexCoreLayout`. Roads **break at the Pit rim**. (Dropped the cogwheel alley
>   ring + valley tiles.)
> - **Growth cleanup:** a **dangling-stub prune** in `GrowRoadNetwork` (a road edge survives only
>   if its neighbour carries the return road) → no more off-map cut-offs or block-butting stubs.
> - **Core rotation fix:** core tiles now **measure-and-rotate** like the frontier (they were
>   placed at a fixed yaw and came out mirrored — see gotcha #16).
>
> **★ TODAY (2026-06-07) — roll diagnostics + constraints DataTable.** First analytical pass over
> the rolls themselves, plus a way to bias them. All Python (no C++ rebuild for the diagnostics
> themselves; the constraint *struct* is C++).
> - **Tools ▸ Diagnose Last Roll** — per-necklace histogram of the *current* live roll (counts +
>   %) so a single click answers "what did this roll actually contain?"
> - **Tools ▸ Hex Roll Sweep** — **200 rolls** at the live settings → mean/std/p95 per necklace +
>   a CSV at **`Design/Rolls/Sweep_*.csv`**. First sweep landed: **24 k cell samples, 0 unresolved
>   across all 200 rolls**; **Σ(mean) = 120.0 exact** (matches the design target). Asset budget
>   anchored at **~40 unique meshes** total — well under the 120-tile worry.
> - **Volatility flag (acted on, not fixed):** `blank` has **σ/μ ≈ 0.43** → the open-ground share
>   swings **8 %–72 %** between rolls. Tuneable later with growth knobs or rejection sampling.
> - **Constraint system (the bias knob).** New C++ struct **`FHexNecklaceConstraint`** (USTRUCT,
>   `TableRowBase`, in `HexTileTypes.h`) + new **`UDataTable* RollConstraints`** UPROPERTY on
>   `AHexShuffleGenerator` (category *Hex Shuffle | Constraints*). **Tools ▸ Constrained Randomize**
>   reads the assigned DataTable (preferred) and falls back to `Design/RollConstraints/<name>.json`
>   when none is assigned. Two presets shipped: **`DT_RollConstraints_Default`** (`junction ≥ 1`,
>   `tee_c ≥ 1` — auto-created by `roll_diagnostics.create_default_constraints_table()`) +
>   **`DT_RollConstraints_reqJunction`**.
> - **Retry-with-log failure mode** — on exhaustion the tool prints the **"biggest bouncer"** (the
>   constraint that rejected the most attempts) and the **"closest miss"** (observed vs target),
>   so a failure is actionable rather than just "no roll found".
> - **Python path silent-failure fixed** — editor Python moved **`Content/_project/Python/` →
>   `Content/Python/`** (UE-canonical; on `sys.path` by default). The broken
>   `+AdditionalPaths=(Path="Content/_project/Python")` line in `DefaultEngine.ini` is gone. The
>   previous Reimport menu entry had been a ghost since the `_project` reorg — see gotcha #22.
>
> **★ LATEST — LANDED + LKG** (2026-06-06, tag **`lkg`** @ `6b746a3`, pushed to `origin/main`;
> the `tile-pipeline-reorg` branch is kept as a safety net). All validated in-engine — `ShuffleLab`
> generates and renders against the shared masters:
> - **Iterative tile pipeline** — the **"Hex Tiles" Blender addon** (`tile_pipeline.py` +
>   `tile_registry`/`tile_common`/`tile_manifest.json`): per-tile export toggles, Build-Enabled
>   preview/export, **Promote to Bespoke** (a tile graduates to its own `.blend` linking the master).
>   Both generators are **manifest-aware** (skip bespoke). **Pit = first bespoke tile**
>   (`Source_Art/Blender/Tiles/T_core_pit.blend`) with a **30° descent ramp + floor-normal fix**.
> - **Spline-fanned junctions** — `gen_curved_tiles.py` junctions are no longer radial spikes: a
>   central road **hub** + cubic-bezier arms bowing toward the road-mouth centroid + a tangential
>   **swirl** so even symmetric junctions curve (knobs `JUNCTION_HUB_R`/`JUNCTION_BOW`/
>   `JUNCTION_SWIRL`). Perpendicular-at-edge anchor preserved → tiles still tile.
> - **Material masters** — collapsed ~130 per-mesh glTF dupes into **4 shared masters** in
>   `/Game/_project/HexTiles/Materials/`, now parented to an opaque **`M_HexTile_Master`**; reimport
>   self-heals the sprawl (gotcha #19). UE reimport tooling: **Tools ▸ Reimport Hex Tiles** + prompted
>   auto-reimport on the tile `.glb`s.
> - **Content reorg DONE** — our work lives under **`/Game/_project/`** (`HexTiles`/`Data`/`Maps`).
>   **Python tooling lives at `Content/Python/`** (the UE-canonical location; on `sys.path` by default —
>   see gotcha #22 for why `_project/Python/` doesn't work). Config startup/default maps + auto-reimport
>   wildcard + all script path constants repointed.
>
> **Pending propagation (deferred, not yet done):** scale R=10 into the master `HexBase.blend` +
> `Source_Art/README.md` contract; delete orphaned `T_valley_*` meshes; asymmetric Pit rim
> (irregular slumped edges) + the deeper descent geometry. See Next steps.

- ✅ UE 5.7 C++ builds & opens. **Third-person Manny/Quinn** plays (ported `TP_ThirdPerson` module).
- ✅ Pipeline: Blender → `.glb` → UE, walkable. **Hex base LOCKED**: flat-top R=5 / 10 m across,
  origin bottom-center, edge 0 = +Y CCW.
- ✅ **14-config street kit** (all road-edge necklaces: blank/deadend/bend/curve/straight/
  tee[/_a/_b/_c]/quad[/_b/_c]/penta/junction), generated by `gen_curved_tiles.py` (canonical;
  `gen_street_tiles.py` superseded). London cross-section: cobble carriageway 3 m + raised
  flagstone pavements 1 m + 0.15 m curb.
- ✅ **`HexMapGenerator` randomizer (in-engine, working):** road-driven **growth** (cube coords;
  **cardinal arteries** run center→map-edge along each hex axis, then secondary streets branch
  off) → connected by construction; **geometry-measured rotation** (reads each tile's real
  `M_Road` verts so placement is immune to glTF orientation); ISM placement under real light in
  `ShuffleLab`. Verified: 61 cells, 0 unresolved.
- ✅ **Population metric:** per-tile `Occupancy` in the catalog (rule `(6 − roadEdges) × 2`),
  summed live into **`Estimated Vacancies`** + a floating label. Core tiles (`Distance ≤
  CoreRadius`) are **excluded** from the tally — only the frontier counts.
- ✅ **Pit anchor in the generator:** `GrowRoadNetwork` grows the frontier *around* a pinned
  fixed core (`CoreRadius`, default 1); arteries seed from the core boundary. Diegetic
  addressing helper (Main / 1st / Arapahoe axes; ring = restoration ring).
- ✅ **Roll save/load:** `HexShuffleGenerator` **Save Roll** / **Load Roll** → JSON in
  `Design/Rolls/` (the durable record = the resolved cell masks; reloads verbatim regardless of
  later generator edits). See `Design/Rolls/README.md`.
- ✅ **Pit-core blockout (intact, pre-destruction):** `gen_pit_core.py` parametrically builds the
  7 fixed-core tiles (hub + 6 ring) **+ 6 perimeter "valley" tiles** — a 6-way 3 m hub junction
  (the portal all roads drain to), 3 m spokes, and a closed 2 m boundary alley loop. Correct
  London cross-section (carriageway 0.5 / flagstone pavement 0.65 / 0.15 curb). Imported via
  `setup_pit_core.py` (collision complex-as-simple) and **walkable in `/Game/_project/Maps/PitCoreLab`**.
- ⬜ **Boolean sinkhole carve = TODO (phase 2)** — the intact streets are signed off; carving the
  zig-zag void + hardwiring the core into `HexShuffleGenerator` come next.
- ⬜ Frontier placement is **transient** (not yet baked).
  The reusable generator isn't yet wired to gameplay (autofill / rearrange).
- ✅ **Building tiles SHIPPED in engine (2026-06-07).** `gen_buildings.py` bakes 12
  `T_bldg_*.glb`; `FHexTileDef::BuildingMesh` + parallel ISM in
  `AHexShuffleGenerator::Build()` places one per road-bearing frontier cell at the same
  world transform as its street tile. Single-story walls, flat roof, interior surfaces,
  door frames + thresholds, bevel modifier. See [Docs/Buildings.md](Docs/Buildings.md) for
  the full pipeline. Corner pieces (bend-vertex topology) emit zero geometry — user's
  authoring playground.

## Architecture & file map
| Path | Role |
| ---- | ---- |
| `Source/ModularHexMap/` | primary game module (scaffold, ~empty) |
| `Source/TP_ThirdPerson/` | **ported** Epic Third Person template module (non-primary) |
| `Plugins/HexMapGenerator/Source/HexMapGenerator/` | the randomizer engine (runtime module): |
| &nbsp;&nbsp;`Public/HexCoordinates.h` | cube/axial hex math; flat-top axial→world; mask rotate |
| &nbsp;&nbsp;`Public/HexTileTypes.h` | `EHexEdgeSocket`, `FHexTileDef` (mesh + 6 edges + Occupancy), **`FHexNecklaceConstraint`** (row struct for `RollConstraints` DataTable; min/max/exact) |
| &nbsp;&nbsp;`HexTileSet.{h,cpp}` | `UHexTileSet` catalog + mask→tile/rotation lookup |
| &nbsp;&nbsp;`HexCoordinates.h` | …also `ArteryName`/`Address` (Main/1st/Arapahoe diegetic addressing) |
| &nbsp;&nbsp;`HexMapGrowthLibrary.{h,cpp}` | pure seeded `GrowRoadNetwork` (pinned core + arteries + branching); `MakePlaceholderCore`; `FHexGrowthParams.CoreRadius`; `FHexRoll` |
| &nbsp;&nbsp;`HexShuffleGenerator.{h,cpp}` | `AHexShuffleGenerator` actor: measure-calibrate, grow, place, tally vacancies; `Randomize`/`Recalibrate`/`Clear`/`SaveRoll`/`LoadRoll` CallInEditor; **`RollConstraints` UPROPERTY** (`UDataTable*`, read by Python's `constrained_randomize`) |
| `Source_Art/Blender/HexBase.blend` | master base (Hex_Base + anchors + materials, fake-user) — **keep byte-identical; scripts never save it** |
| `Tools/blender/gen_curved_tiles.py` | **canonical** street-kit generator (spline-curved roads; edit `EDGE_SETS`; `build_tile_obj` = build-only entry; **manifest-aware** — skips bespoke) |
| `Tools/blender/gen_street_tiles.py` | superseded faceted street generator (kept for reference; don't regenerate from it) |
| `Tools/blender/gen_pit_core.py` | pit-core generator (7-tile radial star; 30° descent ramp; **manifest-aware**; keeps every tile in `core_layout.json` but skips bespoke `.glb`) |
| `Tools/blender/tile_pipeline.py` | **the "Hex Tiles" Blender addon** — per-tile export toggles, Build-Enabled preview/export, Promote/Open bespoke, save-prompts |
| `Tools/blender/tile_registry.py` | unified tile list (name → build-callable) pulled from both generators — single source of "what tiles exist" |
| `Tools/blender/tile_common.py` | shared plumbing: paths, the ONE canonical glTF export, manifest I/O, `bespoke_tile_names`, preview layout |
| `Tools/blender/_make_bespoke.py` | headless creator of a bespoke per-tile `.blend` (linked master mats + reference hex + local mesh; spawned by Promote) |
| `Tools/blender/tile_manifest.json` | git-tracked per-tile state: `enabled` (export on/off) + `bespoke` (owned by a `.blend`) + `blend` path |
| `Source_Art/Blender/Tiles/` | **bespoke per-tile `.blend`s** (hand-owned; link the master). `T_core_pit.blend` = the first |
| `Content/Python/hextile_materials.py` | `consolidate_to_masters()` — fold per-mesh material dupes into the 4 shared masters (gotcha #19) |
| `Content/Python/reimport_hextiles.py` | one-click **Tools ▸ Reimport Hex Tiles** — reimport all `/Game/_project/HexTiles` from `.glb`, re-assert Complex-As-Simple, self-heal materials |
| `Content/Python/init_unreal.py` | startup hook: registers the Reimport Hex Tiles menu entry |
| `Content/Python/roll_diagnostics.py` | **Tools ▸ Diagnose Last Roll / Hex Roll Sweep / Constrained Randomize** — per-necklace histograms, 200-roll empirical distribution + CSV, and seed-retry that finds a roll satisfying `RollConstraints` (DataTable preferred, JSON fallback) |
| `Content/Python/hexmap_menus.py` | the four Tools-menu entries (kept in a separately-named module so `import init_unreal` collisions with other plugins can't break registration — gotcha #22) |
| `Design/RollConstraints/` | JSON fallback presets when no DataTable assigned; see its `README.md` |
| `/Game/_project/Data/DT_RollConstraints_*` | in-engine **roll-constraints DataTables** (rows of `FHexNecklaceConstraint`, keyed by necklace name). Clone for alternate town flavours; assign to the generator's `RollConstraints` property to swap |
| `Content/Python/_run_consolidate.py` | explicit commandlet entry for the one-time material consolidation |
| `Tools/setup_shuffle_lab.py` | (GUI editor) import 14 tiles + build catalog + lit lab |
| `Tools/setup_pit_core.py` | (GUI editor) import 13 core tiles + build walkable `PitCoreLab` (reads `core_layout.json`) |
| `Tools/setup_buildings.py` | (GUI editor) one-shot first-time import of `T_bldg_*.glb` + wires `BuildingMesh` on each `DA_HexTileSet_Streets` row + force-save (gotcha #11). After this, use **Tools ▸ Reimport Hex Tiles** for subsequent rebakes. |
| `Tools/_verify_buildings.py` | (GUI editor) loads ShuffleLab + Randomize + dumps ISM counts (street vs building) — sanity check after any change to FHexTileDef or AHexShuffleGenerator |
| `Tools/save_occupancy.py` | (commandlet) seed catalog `Occupancy` + **force-save**. **Post-`_project` reorg:** path repointed to `/Game/_project/Data/...` (2026-06-07); pre-fix it had been silently 0 since the reorg |
| `Tools/blender/gen_buildings.py` | **building-tile generator** (manifest-aware) — single-story walls + flat roof + interior surfaces + door frames + thresholds + bevel modifier; exports `T_bldg_*.glb` to `Content/_project/HexTiles/Source/`. See [Docs/Buildings.md](Docs/Buildings.md). |
| `Tools/blender/_wip_building_facades.py` | iteration workbench — lays road tiles + buildings together for visual review (with road context); production `gen_buildings.py` is buildings-only |
| `Tools/verify_shuffle.py` | (GUI editor) headless roll + log for self-checks |
| `Design/Rolls/` | saved roll JSONs — curated layout history (+ `README.md`) |
| `/Game/_project/Data/DA_HexTileSet_Streets` | the tile catalog asset (now carries `BuildingMesh` per row) |
| `/Game/_project/HexTiles/Core/` | imported pit-core blockout tile meshes (13) |
| `/Game/_project/HexTiles/Buildings/` | **imported building meshes (12 `T_bldg_*`)** — paired by name to street tiles via DA |
| `/Game/_project/HexTiles/Materials/` | the **4 shared master materials** (every tile mesh slot points here — gotcha #19) |
| `/Game/_project/Maps/ShuffleLab` | lit lab containing the generator actor (startup map) |
| `/Game/_project/Maps/PitCoreLab` | lit lab — the intact 13-tile core blockout, walkable |

## Records of resistance (gotchas — don't relearn these)
1. **Headless glTF import crashes on Slate** (`-run=pythonscript` commandlet, no Slate, asserts
   in the Interchange→ContentBrowser sync). → Import in a **GUI editor** (`-ExecutePythonScript`).
   Level *assembly* and *asset edits* (no import) are headless/commandlet-safe.
2. **Blender drops unused materials on save** → `material.use_fake_user = True` on shared mats.
3. **Migrated BPs needed the FULL `TP_ThirdPerson` module (~30 classes).** Copied the engine
   template module verbatim, `IMPLEMENT_PRIMARY_GAME_MODULE`→`IMPLEMENT_GAME_MODULE`, registered
   in both `*.Target.cs` + `.uproject`, enabled **StateTree + GameplayStateTree**. Names match
   `/Script/TP_ThirdPerson.*` so BPs resolve natively.
4. **New `UCLASS` types need a full editor restart + `Build.bat`** (Live Coding can't hot-add;
   editor locks the DLLs — close it first).
5. **Imported meshes aren't walkable until** Collision Complexity = **Use Complex As Simple**.
6. **glTF imports at true scale** (1 m → 100 uu).
7. **Hexes carry √3 between axes** — can't round both. **R=10** now (was 5; 2× scale 2026-06-06);
   the generator places tiles so 17.3 m is never hand-typed. `HexCircumradiusUU` must match
   (=`R×100`=1000). Neighbor offsets in `Source_Art/README.md` (still listed at the old R=5).
8. **UE launch wrapper exits 0 instantly** (editor reparents). Confirm with `Get-Process UnrealEditor`; real logs in `Saved/Logs/`.
9. **Blender close-range perspective fakes tall walls** — verify with vertex Z or **orthographic**.
10. **glTF import re-orients meshes (handedness + offset).** Never trust the abstract Blender
    edge layout for in-engine placement. The generator **measures** each tile's true road edges
    from geometry (reads the `M_Road` section verts near each edge midpoint) and resolves
    rotation against that. **Physics line-traces were useless** in the editor (the spawned body
    isn't ready the same frame) — read **render-data vertices** instead.
11. **UE-Python `set_editor_property` on a nested struct array does NOT dirty the package**, so
    `EditorAssetLibrary.save_loaded_asset` silently no-ops (returns `True`, writes nothing). →
    save with **`only_if_is_dirty=False`**, edit struct arrays by **index** (`a[i]=e`, not
    mutating the loop var), and **verify the `.uasset` size/mtime actually changed**. Also: never
    `Stop-Process -Force` the editor right after a save — it eats the flush. Use a clean
    **commandlet** (`-run=pythonscript`) for asset edits/saves (exits cleanly, flushes).
12. **UE yaw convention:** world_angle = local_angle + yaw (positive yaw = +1 edge / rotate mask
    left). The generator's default is correct for our import; `bInvertYawShift` is the escape
    hatch if a future kit imports mirrored.
13. **Export tiles CENTERED, or UE double-offsets them.** An object's world location bakes into
    the glTF node transform, then UE bakes that into the mesh — so placing the actor at the same
    coord doubles the offset (tiles spread at 2× spacing with gaps). Set `object.location = 0`
    before export; position **only** via the actor/generator. (Mesh data stays bottom-center.)
14. **Self-intersecting boolean cutter eats the WHOLE target.** Overlapping carriageway arms (a
    junction cutter where arms meet at center) make the EXACT solver mis-evaluate and delete *all*
    the pavement, not just the channel. Fix: `modifier.use_self = True` + `use_hole_tolerant =
    True`. ⚠️ **This bug is also in `gen_street_tiles.py`** — the street kit's raised curbs have
    been getting eaten on every generate. Fix + regenerate the 14-tile kit (pending).
15. **`-ExecutePythonScript` is one-shot:** the GUI editor runs the script and **exits** (a build
    step, like `setup_shuffle_lab.py`/`setup_pit_core.py`). The work persists; relaunch the editor
    normally (optionally `UnrealEditor.exe <uproject> /Game/Maps/<Map>`) to use the result.
16. **glTF import MIRRORS each tile across the X-axis** (edges 0↔3, 1↔2, 4↔5) — the concrete form
    of gotcha #10's "re-orientation." The frontier resolver absorbs it (matches measured→target
    mask by rotation; road geometry is per-edge symmetric). **Anything placed verbatim must do the
    same** — the Pit-core tiles were placed at a fixed yaw and came out mis-rotated (rings off the
    mirror axis wrong, *every roll*). Fix: `Build()` measures each core mesh's real mask and rotates
    it onto the authored `CC.RoadMask`. ⇒ **Never place an imported tile at a hardcoded yaw; always
    measure-and-rotate.** (Chiral *art* would also need authoring that accounts for the mirror.)
17. **glTF reimport (`replace_existing`) doesn't reliably update MATERIAL factors** — a colour/param
    change baked in Blender may not take on reimport. Force it in UE after import via
    `MaterialEditingLibrary.set_material_instance_vector_parameter_value(MIC, "baseColorFactor", …)`
    (glTF mats import as `MaterialInstanceConstant`; param is `baseColorFactor`). See
    `Tools/fix_and_roll.py` / `wire_core_into_shufflelab.py`.
18. **Procedural vs bespoke is FILE ownership, enforced by the manifest.** A tile is either
    generator-owned (rebuilt from code) or hand-owned (a `.blend` under `Source_Art/Blender/Tiles/`)
    — never both, or a regenerate clobbers hand work. `tile_manifest.json` is the contract; the
    generators skip `bespoke` tiles (verified: `gen_pit_core.py` skips `T_core_pit`, keeps it in
    `core_layout.json`, leaves its `.glb` untouched). ⚠️ **Don't hand-edit a tile inside the master
    `HexBase.blend` and Ctrl+S** — that bakes it into the master (we hit this: `PitProto` polluted
    the master; fix was capture-to-bespoke then `git checkout HexBase.blend`). Use the **Hex Tiles**
    panel's **Promote to Bespoke** instead; leaving the master via the panel never auto-saves it.
19. **glTF import mints per-mesh material dupes — consolidate to shared masters.** Each `.glb`
    import gives every tile its own `Materials/` folder, so ~30 tiles scattered **~130 copies** of
    really **4** materials (`M_Road`/`M_Pavement`/`M_HexGround`/`M_TileBorder`). Canonical masters
    live in **`/Game/_project/HexTiles/Materials/`**; `Content/Python/hextile_materials.py` consolidates.
    Headless quirks learned the hard way: `EditorAssetLibrary.consolidate_assets` **replaces
    references but leaves the copies as `ObjectRedirector`s**; `delete_asset` **does not remove
    redirectors** headless and `AssetTools.fixup_referencers` **doesn't exist in 5.7 Python**. The
    working recipe: **force-rebind every static-mesh slot to the master path + save** (so no mesh
    depends on a redirector), then **delete the redirector `.uasset` files on disk** (editor
    closed; UE rescans on launch). `reimport_hextiles.py` calls `consolidate_to_masters()` after
    every reimport so the sprawl never comes back. Run the one-time cleanup headless:
    `UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="Content/Python/_run_consolidate.py"`
    (⚠️ UE's pythonscript commandlet does **not** reliably run a file's `if __name__=="__main__"`
    block — use an explicit entry script that calls the function at top level).
20. **Close the UE editor before any git op that MOVES/DELETES `.uasset` files** (branch switch,
    merge, `checkout -f`, reset). The open editor **locks** the package files, so git can't unlink
    them → "unable to unlink … Invalid argument" and a **half-completed branch switch** (tracked
    text files flip to the target branch while locked assets stay behind). Recovery is clean once
    closed: `git checkout -f <branch>` restores the tree, then merge. (Same family as gotcha #4's
    DLL lock for C++ builds.) The work is never lost — it's in the commits; only the working tree
    gets stuck. *(Hit during the `_project` reorg merge to `main`; recovered, then merged + tagged.)*
21. **A live Blender session caches imported pipeline modules.** After editing `tile_common.py` /
    the generators / the addon on disk, the **open** session keeps the OLD code (e.g. a stale
    `source_glb_dir`), so "Export This Tile" can silently write to the **pre-edit path**. Fix:
    reload (`importlib.reload(tile_common)` …) or just **restart Blender** (it re-reads fresh).
    *(Hit right after the reorg: the pit re-exported to the old `Content/HexTiles/Source` and UE,
    now pointing at `_project`, didn't see it.)*
22. **`PythonScriptPlugin.AdditionalPaths` silently no-ops on relative paths.** A line like
    `+AdditionalPaths=(Path="Content/_project/Python")` is resolved against
    `Engine/Binaries/Win64/`, not the project root — so it points at a nonexistent dir, gets
    dropped without warning, and the directory never lands on `sys.path`. Symptoms: any module
    living there throws `ModuleNotFoundError`, and any `init_unreal.py` in there never runs (UE
    only auto-runs init scripts in dirs already on `sys.path`, so this becomes a silent
    chicken-and-egg). Fix: **keep editor Python under `Content/Python/`** — UE hard-codes that
    onto `sys.path` for every project. (`Content/_project/HexTiles`, `/Game/_project/Maps`, etc.
    are still fine; the `_project` convention applies to everything *except* Python tooling.)
    *(Hit when the new Tools-menu entries didn't appear; turned out the old Reimport entry was
    also silently broken since the `_project` reorg — nobody had clicked it to notice.)*
23. **`BlueprintReadOnly` / `BlueprintReadWrite` is REJECTED on `private` UPROPERTYs by default.**
    Symptom: header compile fails with `BlueprintReadOnly should not be used on private members`
    the moment you try to expose a private field to BP/Python. Fix: add **`meta =
    (AllowPrivateAccess = "true")`** to the UPROPERTY — keeps the field C++-private but opts past
    UE's BP-visibility gate. Example in-repo: `AHexShuffleGenerator::LastNetwork`, which Python's
    roll diagnostics need to read. Without the meta even a syntactically clean header refuses to
    compile. *(Hit while exposing `LastNetwork` for `Diagnose Last Roll`.)*
24. **Live Coding (Ctrl+Alt+F11 / editor "Compile") CANNOT add new `UPROPERTY`/`UCLASS`/`USTRUCT`
    reflection.** It hot-patches *function* bodies; new reflected members look like they compiled
    but never reach the engine. Symptom: source has the new property, Live-Coding console says
    succeeded, but the **Details panel never shows the field**, the UBT log is untouched, and only
    `*.patch_*.dll/exe` files were written. **Diagnostic:** compare mtimes —
    `Plugins/<plugin>/Binaries/Win64/UnrealEditor-<plugin>.dll` older than your `.h` edit ⇒ Live
    Coding ran but didn't compile anything reflection-visible. **Fix:** close the editor (DLLs are
    locked open — gotcha #4) and run the full build:
    `Build.bat ModularHexMapEditor Win64 Development -Project="..." -WaitMutex`. (This is the
    *Live-Coding-specific* tell for the same family as #4, which covers new UCLASS; #24 covers new
    UPROPERTY/USTRUCT too.) *(Hit adding `RollConstraints` + `FHexNecklaceConstraint`.)*
25. **Shapely returns CW polygons after `hex.difference(corridor).buffer(...)`** — verified empirically
    against every config in `gen_buildings.py`. With CW polygons, the standard
    `add_quad([v00,v10,v11,v01])` winding produces INWARD normals (every wall flips, every face
    paints red in Blender's Face Orientation overlay, walls render as backfaces in UE). Shapely
    doesn't promise any orientation on output; the OGC convention is CCW for exteriors but
    `difference`/`buffer` operations don't preserve or enforce it. **Fix:** call
    `shapely.geometry.polygon.orient(pc, sign=1.0)` before extracting `.exterior.coords` in every
    builder function (walls, roofs, gardens). *(Hit twice in `gen_buildings.py`: first when I
    removed `recalc_face_normals` thinking my winding was correct, second when I tried `orient`
    plus `recalc` together; the working combo is `orient` ALONE — see #26.)*
26. **`bmesh.ops.recalc_face_normals` flips alternating panels on disconnected per-segment quads.**
    The walls in `gen_buildings.py::build_walls` create a fresh vertex set per quad (no sharing /
    no welding), so adjacent segments share neither edges nor vertices — recalc has no
    neighbour-consistency anchor and ends up flipping every other face in any door-split run
    (verified: Panel 1, Lintel 1, Panel 2... alternate outward/inward). **Fix:** with `orient(CCW)`
    (gotcha #25) the explicit `add_quad` winding is already correct on every segment; do NOT call
    recalc on the wall mesh. *(Recalc on a CLOSED solid like the roof slab is fine — it has shared
    edges to anchor against.)*
27. **Blender 5.1's `bpy.ops.object.shade_smooth_by_angle()` no longer adds the Smooth-by-Angle
    GN modifier.** In Blender 4.1 that operator added a geometry-nodes group that produced split
    normals; in 5.1 it only marks `mesh.edges[i].use_edge_sharp` flags. Without the GN modifier
    (or a manual `mesh.normals_split_custom_set_*` call), sharp-edge marks have **no visual effect**
    — smooth shading just averages all incident face normals at each vertex regardless of marks.
    **Diagnostic:** after calling the operator, `len(obj.modifiers)` is unchanged. **Fix:** set
    `use_smooth = True` on every polygon and let the bevel modifier (with `limit_method='ANGLE'`
    and `angle_limit = SHARP_ANGLE_DEG`) provide the visible hard-corner treatment by adding actual
    chamfer geometry, not split-normal tricks. *(Hit while trying to give curves smooth shading
    AND keep wall corners crisp.)*
28. **Per-segment door placement is wrong for tessellated curves.** Shapely's `LineString.buffer`
    tessellates an arc into many short sub-segments (~1.3 m each on a curve at R=10), so any
    per-segment "does this segment fit a door?" check fails on curves (curve and bend ended up
    with ZERO doors) while a single-segment straight facade got too many (`ceil(17/8) = 3`).
    **Fix:** classify doors by **combined front-run arc length** (`doors_for_run` in
    `gen_buildings.py`): walk the polygon's exterior, group contiguous front segments into runs,
    pick `N = 0/1/2/3` by total run length, distribute door spans evenly along the run, and map
    each span back to whichever segments it overlaps. A door whose width crosses multiple sub-segments
    produces a lintel quad on each overlapped segment — the "banana lintel" follows the curve.
29. **NEVER use VS 2022 Build menu on this UE project — it trips MSBuild's `SetEnv` task before
    any compile starts.** Line 116 of `Microsoft.Cpp.Current.targets` runs
    `<SetEnv Name="INCLUDE" Value="$(IncludePath)" Prefix="false" />`, and `$(IncludePath)` on a
    UE 5.7 project with engine modules + plugins exceeds **32 767 chars** (the per-variable
    Windows env-var ceiling that .NET's `Environment.SetEnvironmentVariable` enforces). MSBuild
    throws `MSB4018: System.ArgumentException: Environment variable name or value is too long`
    and dies. Nothing about the machine env is wrong — a clean install with `PATH` at 1 074 chars
    and *zero* other env vars over 1 000 chars still hits this. **Fix:** always compile via
    `Tools/Build.ps1` (or the underlying `Build.bat ModularHexMapEditor Win64 Development -Project=... -WaitMutex`).
    That path goes through UnrealBuildTool → `cl.exe` directly, passing include paths as
    command-line `/I "..."` args instead of stuffing them into a Windows env var. Same compiler,
    same SDK, just not via MSBuild's SetEnv. Editor's "rebuild outdated modules?" prompt also
    works (it calls UBT internally). Edit C++ in whatever IDE you like; only ever build through
    `Tools/Build.ps1`. *(Hit on the secondary dev machine when picking up the building-tile work
    fresh; cost an evening.)*

## Next steps
0. **Building footprints (pivot — the next big rock).** Roll diagnostics ✅ and the constraints
   DataTable ✅ closed the loop on the *street* side: we can now measure a roll and bias it. The
   open question is no longer "what tiles?" but **"what fits on the blocks the streets leave?"**
   Per the auto-memory note, **per-hex buildings don't fit** the dense-London read — footprints
   should be **multi-hex BLOCKS** authored on the blocks the road graph carves out. Shapely-based
   inset/boolean pipeline already prototyped (and already taught us not to crash Blender at 32 GB
   — see auto-memory). This subsumes the old standalone *"first bespoke building tile"* step:
   the bespoke tile is a deliverable of the footprint phase, not a prerequisite to it.
1. **Anchor the map on the Pit (0,0)** (current focus — supersedes rivers for now). Generator
   side ✅ (`CoreRadius`, pinned core, boundary-seeded arteries, vacancy exclusion, addressing).
   Intact **pre-destruction blockout** ✅ (`gen_pit_core.py` → `PitCoreLab`, walkable). **Still
   TODO:**
   - **(a) Hardwire the core into `HexShuffleGenerator`** ✅✅ — `DA_HexCoreLayout` assigned to the
     **live `ShuffleLab` generator** (was `CoreGenLab` only); **radial star** (`gen_pit_core.py`,
     7 tiles, 2× scale), placed with **measured rotation** (gotcha #16). 127 cells, core=7, 0
     unresolved. Rebuild via `Tools/wire_core_into_shufflelab.py`.
   - **(b) Pit void + roads-break-at-rim** ✅ — clean recessed hex void representation. **Still
     TODO:** the **asymmetric collapsed-building rim** (irregular slumped edges, not a clean hex)
     and the deeper zig-zag −3 m carve (`ZZ_*`/`PIT_DEPTH` staged in `gen_pit_core.py`).
   - **(c) Level-transition gameplay** on the Pit (descend prompt → `OpenLevel`).
   - **(d)** `gen_curved_tiles.py` uses the curb-bug fix (gotcha #14); `gen_street_tiles.py` is
     superseded (don't regenerate from it). Delete orphaned `T_valley_*` meshes.
   See Docs/Design.md "The Pit & the fixed core" + "Coordinate & address system".
2. **Splined streets, junctions, pipeline, materials, reorg** ✅ **DONE (LKG `6b746a3`)** —
   `bend`/`curve` circular arcs **and** fanned spline junctions (hub + bezier + swirl) in the
   canonical `gen_curved_tiles.py`; the Hex Tiles pipeline + manifest; 4 material masters under
   `M_HexTile_Master`; content under `/Game/_project`. **Still pending:** propagate `R=10` into the
   master `HexBase.blend` + `Source_Art/README.md` contract (the generators build at R=10 already;
   only the master base + the written contract still say R=5). An explicit raised-walk strip can
   come with building tiles.
3. **Open up building real estate** — *feeder into #0.* Constraints DataTable ✅ landed today and
   gives us a *bias knob* (e.g. force `junction ≥ 1`). Sweep showed density is *measurable* now
   (Σ=120 exact, blank σ/μ ≈ 0.43). Rule tweaks already in: **artery kink/fork**
   (`ArteryStraightRadius`/`ArteryKinkChance`/`ArteryForkChance`) + **side-street straight-decay**
   (`StraightDecay`/`MaxStraightRun`). Still: tune `RoadBudget`/`BranchChance`/`ArteryForkChance`
   DOWN, and/or add a **minimum-block-size rule** (refuse a road that shrinks a block below N
   tiles) — both directly serve the footprint pivot, since footprints need predictable blocks.
4. **Rivers & bridges** — **water as a foundation layer generated BEFORE roads**. Low-branch,
   edge-to-edge river that roads must *bridge*; new water edge-socket + bridge tiles. See
   Docs/Design.md "Rivers & bridges".
5. **Boolean sinkhole carve** of the Pit core (next-steps 1a) once the street geometry direction
   is settled.
6. **Bake/persist** a chosen shuffle to a saved level (placement is currently transient).
7. Wire the reusable generator to **gameplay** (autofill, the act-2 rearrange).
