# CLAUDE.md — context & resume on-ramp

> Read this first when resuming **ModularHexMap** cold. This file is deliberately lean:
> it says what the project is, how to run it, and where everything else lives. Don't
> grow a diary here — that's the worklog's job.

## The four-doc system

| Doc | Role | Read it when |
| --- | --- | --- |
| **CLAUDE.md** (this) | *Context* — identity, commands, file map | resuming cold |
| [Docs/Roadmap.md](Docs/Roadmap.md) | *Direction* — locked decisions, execution queue, ToDos | deciding what's next |
| [Docs/Worklog.md](Docs/Worklog.md) | *Memory* — dated session records | "what happened / when / why" |
| [Docs/Resistance.md](Docs/Resistance.md) | *Resistance* — 31 gotchas with diagnostics + fixes | **before** fighting glTF/Blender/UE-Python/git/build |

Deeper references: [Docs/Design.md](Docs/Design.md) (the vision + resolved design law),
[Docs/Pipeline.md](Docs/Pipeline.md) (Blender→UE flow), [Docs/Buildings.md](Docs/Buildings.md)
(building-tile pipeline), [Docs/Rivers.md](Docs/Rivers.md) (the water layer),
[Docs/Testing.md](Docs/Testing.md) (**the user testing script** — run it instead of
intuition; exact steps + expected values for every feature),
[Source_Art/README.md](Source_Art/README.md) (the tile contract),
[Docs/Audit_2026-06-10.md](Docs/Audit_2026-06-10.md) (full external audit).

## What this is

A modular **hex map town hub** for UE 5.7 (C++) — the surface counterpart to underground
dungeon crawling: come up, **tour, meet locals, shop**, go back down. **Pop One spine:**
a radius-6 hex town = 127 tiles; the center 7 are the Pit (the permanent scar / dungeon
mouth at (0,0)); the **120 frontier tiles are one soul each** — `120 + you = Pop 121`.
The town is the player's trophy case. Aesthetic: dense turn-of-the-century London,
**style over fidelity**. Tiles are flat-top hexes (R = 10 m); roads on edges are the
assembly grammar; the `HexMapGenerator` plugin grows road networks and places real tiles
with **geometry-measured rotation**. The dungeon game lives in a **separate project** —
never plan its features here.

## Resume — quickstart

Engine: launcher **UE 5.7** at `C:\Program Files\Epic Games\UE_5.7`. Blender **5.1** at
`C:\Program Files\Blender Foundation\Blender 5.1`. Repo path differs per machine — all
commands below run from the **repo root** and stay machine-neutral.

```powershell
# Build C++ (editor must be CLOSED — DLL lock). The ONLY sanctioned compile path;
# NEVER the VS Build menu (Resistance #29).
.\Tools\Build.ps1

# Launch the editor (startup map = /Game/_project/Maps/ShuffleLab)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" "$PWD\ModularHexMap.uproject"

# Bake the tile kits from the master (idempotent; never saves the master; manifest-aware)
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background `
  ".\Source_Art\Blender\HexBase.blend" --python ".\Tools\blender\gen_curved_tiles.py"   # 14 street tiles
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background `
  ".\Source_Art\Blender\HexBase.blend" --python ".\Tools\blender\gen_pit_core.py"       # 7 core tiles
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background `
  ".\Source_Art\Blender\HexBase.blend" --python ".\Tools\blender\gen_buildings.py"      # 12 building tiles

# Post-change smoke test (one-shot GUI editor: calibrate, roll, histogram, constrained+assert)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" `
  "$PWD\ModularHexMap.uproject" -ExecutePythonScript="$PWD\Tools\verify_shuffle.py"
```

**Fresh clone note:** `Content/_project/HexTiles/Source/` (.glb staging) is gitignored —
on a new machine it doesn't exist until you bake (the in-engine `.uasset`s are committed
and work regardless; only **Tools ▸ Reimport Hex Tiles** needs the staging files).

**Roll the randomizer:** open `ShuffleLab` → select **`HexShuffleGenerator`** → Details →
**Randomize** (reroll) / **Save Roll** / **Load Roll**. Tools menu: **Reimport Hex Tiles /
Diagnose Last Roll / Hex Roll Sweep / Constrained Randomize**. `Recalibrate` after
reimporting tiles. Day-to-day tile authoring runs through the **"Hex Tiles" Blender
addon** (`Tools/blender/tile_pipeline.py`) — see Docs/Pipeline.md.

## Status snapshot (2026-06-11)

Works end-to-end, all gates green: **127 cells / core=7 / 0 unresolved / souls=120**.
The town is a playable loop in `ShuffleLab` (saved with **restoration mode ON**):
Randomize rolls a **destiny** — streets + buildings + the **River** (core-anchored
through-flow past the wound, player-chosen `RiverOutflowDir`, oxbow meander at the
0.22 default, ~2.5 bridges clustered near the center, Left/Right Banks via `GetBank`)
— rendered as a **ghost silhouette at Pop 1**; `RestoreNext`/`RestoreCell` heal it one
soul at a time toward **Pop 121** (bridges gate the far bank); rolls save/load as the
complete town save (`FHexRoll` + `Restored`). Catalog = 21 tiles (14 street + 3 river +
4 census-complete bridges); `RoadBudget` is an honest density dial (wave reseeding) and
`SideBridgeChance` the bridge-scarcity dial. Run [Docs/Testing.md](Docs/Testing.md)
T0–T11 to verify everything; **next:** blank-max clamp (director's eyeball) + the
garden-square blank variants — full queue in Roadmap.md.

## Architecture & file map

| Path | Role |
| ---- | ---- |
| `Source/ModularHexMap/` | primary game module (scaffold, ~empty) |
| `Source/TP_ThirdPerson/` | ported Epic Third Person template module |
| `Plugins/HexMapGenerator/Source/HexMapGenerator/` | the randomizer engine (runtime module): |
| &nbsp;&nbsp;`Public/HexCoordinates.h` | cube/axial hex math; flat-top axial→world; mask rotate; diegetic addressing (Main/1st/Arapahoe) |
| &nbsp;&nbsp;`Public/HexTileTypes.h` | `EHexEdgeSocket`, `FHexTileDef` (mesh + BuildingMesh + 6 edges), `FHexNecklaceConstraint` (RollConstraints row) |
| &nbsp;&nbsp;`HexTileSet.{h,cpp}` | `UHexTileSet` catalog + mask→tile/rotation lookup; `UHexCoreLayout` (authored fixed core) |
| &nbsp;&nbsp;`HexMapGrowthLibrary.{h,cpp}` | pure seeded `GrowRoadNetwork` (pinned core + arteries + branching + stub prune); `FHexRoll` |
| &nbsp;&nbsp;`HexShuffleGenerator.{h,cpp}` | the actor: measure-calibrate, grow, place street+building ISMs, `Souls` count; `Randomize`/`BuildFromSeed`/`Recalibrate`/`Clear`/`SaveRoll`/`LoadRoll`; `RollConstraints` DataTable |
| `Source_Art/Blender/HexBase.blend` | master base (Hex_Base + anchors + 3 materials) — **keep byte-identical (~101.5 KB; Resistance #30); scripts never save it** |
| `Source_Art/Blender/Tiles/` | bespoke per-tile `.blend`s (hand-owned). `T_core_pit.blend` = the first |
| `Tools/Build.ps1` | THE build command (UBT direct; dodges the MSBuild SetEnv trap) |
| `Tools/blender/gen_curved_tiles.py` | canonical street-kit generator (spline-curved; edit `EDGE_SETS`; manifest-aware) |
| `Tools/blender/gen_pit_core.py` | pit-core generator (7-tile radial star; manifest-aware; writes `core_layout.json`) |
| `Tools/blender/gen_buildings.py` | building-tile generator (walls/roof/interior/doors; manifest-aware) — see Docs/Buildings.md |
| `Tools/blender/tile_pipeline.py` | the "Hex Tiles" Blender addon (export toggles, preview, Promote to Bespoke) |
| `Tools/blender/tile_registry.py` / `tile_common.py` | single tile list pulled from the generators / shared paths+export+manifest plumbing |
| `Tools/blender/tile_manifest.json` | git-tracked per-tile state: `enabled` + `bespoke` + `blend` |
| `Tools/blender/_wip_building_facades.py` | iteration workbench: streets + buildings together for visual review |
| `Tools/setup_shuffle_lab.py` → `wire_core_into_shufflelab.py` → `setup_buildings.py` | rebuild-from-scratch chain (GUI editor one-shots; bake .glbs first) |
| `Tools/setup_pit_core.py` | (GUI editor) import core tiles + build walkable `PitCoreLab` |
| `Tools/verify_shuffle.py` / `Tools/_verify_buildings.py` | post-change smoke test / building-ISM sanity check |
| `Content/Python/reimport_hextiles.py` | **Tools ▸ Reimport Hex Tiles** — reimport all tiles + Complex-As-Simple + material self-heal |
| `Content/Python/roll_diagnostics.py` | Diagnose Last Roll / Hex Roll Sweep / Constrained Randomize (BuildFromSeed + placed-roll re-verify) |
| `Content/Python/hexmap_menus.py` / `init_unreal.py` | Tools-menu registration (uniquely-named module; Resistance #22) |
| `Content/Python/hextile_materials.py` | `consolidate_to_masters()` (Resistance #19) |
| `Design/Rolls/` | saved roll JSONs — curated layout history; the future save-game town format |
| `Design/RollConstraints/` | JSON fallback constraint presets (DataTable preferred) |
| `/Game/_project/Data/` | `DA_HexTileSet_Streets`, `DA_HexCoreLayout`, `DT_RollConstraints_*` |
| `/Game/_project/HexTiles/` | imported tile meshes (streets, `Core/`, `Buildings/`) + the 4 material masters |
| `/Game/_project/Maps/` | `ShuffleLab` (startup) + `PitCoreLab` |

## Invariants (the short list)

- **1 tile = 1 soul** — the pipeline's law (Design.md). No occupancy sums anywhere.
- **Edge anchor contract** — roads cross edge midpoints perpendicular (Source_Art/README).
- **Procedural vs bespoke = file ownership** via `tile_manifest.json` (Resistance #18/#30).
- **Never place an imported tile at a hardcoded yaw** — measure-and-rotate (Resistance #16).
- **Build only via `Tools/Build.ps1`** (Resistance #29); editor closed for C++ (#4/#24).
- The master `HexBase.blend` stays canonical: 9 objects, 3 materials, ~101.5 KB (#30).
