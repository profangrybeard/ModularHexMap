# CLAUDE.md — project memory & resume guide

> Read this first. It's the on-ramp for resuming **ModularHexMap** cold — for a fresh
> Claude session or a solo dev. Design intent lives in [Docs/Design.md](Docs/Design.md);
> the tile contract in [Source_Art/README.md](Source_Art/README.md); the pipeline in
> [Docs/Pipeline.md](Docs/Pipeline.md).

## What this is
A modular **hex map town hub** for Unreal Engine 5.7 (C++). The surface counterpart to
underground dungeon crawling: you come up to **tour, meet locals, shop**, then go back
down. **Not** combat/parkour. The town is a **record of the player's achievements** — it
fills in as they progress. Aesthetic: **dense turn-of-the-century London**. Tiles are
flat-top hexes assembled into streets; roads on the edges govern how they connect.

Tiles are authored in **Blender**, driven via the **Blender MCP** connector, exported to
**glTF**, imported into UE. The custom **`HexMapGenerator`** plugin (currently empty stubs)
is the intended tile catalog + placement/generation system.

## Resume tomorrow — quickstart
All commands from the repo root `C:\SCAD\_projects\ModularHexMap` unless noted. Engine:
launcher **UE 5.7** at `C:\Program Files\Epic Games\UE_5.7`. Blender **5.1** at
`C:\Program Files\Blender Foundation\Blender 5.1`.

```powershell
# Build the editor (after any C++ change; needs the editor CLOSED — DLL lock)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" `
  ModularHexMapEditor Win64 Development `
  -Project="C:\SCAD\_projects\ModularHexMap\ModularHexMap.uproject" -WaitMutex

# Launch the editor (opens to /Game/Maps/TestMap; press Play to walk as Manny/Quinn)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" `
  "C:\SCAD\_projects\ModularHexMap\ModularHexMap.uproject"

# Regenerate the whole street-tile set from the master base (idempotent; never saves master)
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background `
  "C:\SCAD\_projects\ModularHexMap\Source_Art\Blender\HexBase.blend" `
  --python "C:\SCAD\_projects\ModularHexMap\Tools\blender\gen_street_tiles.py"
```

## Current status (what works end-to-end)
- ✅ UE 5.7 C++ project **builds & opens**; `TestMap` is the startup map.
- ✅ **Third-person character** (Manny/Quinn) works — full Epic Third Person template
  ported as the `TP_ThirdPerson` game module. Play → walk/jump on tiles.
- ✅ **Pipeline proven**: Blender → `.glb` → UE import, **walkable** (collision below).
- ✅ **Hex base LOCKED**: flat-top, **R=5 / 10 m across**, 0.5 m slab, origin bottom-center,
  6 `RoadAnchor` empties at edge midpoints (edge 0 = +Y, CCW).
- ✅ **London street set** generated procedurally: `blank, deadend, straight, curve, tee,
  junction` → `Content/HexTiles/Source/T_street_*.glb`. Cross-section = recessed cobble
  carriageway (3 m) + raised flagstone pavements (1 m) + 0.15 m curb.
- ✅ **Master `HexBase.blend` is clean**; the generator is the single source of truth for
  road tiles. Bespoke building tiles (per-file `.blend` linking the master) = not started.
- ⬜ `HexMapGenerator` plugin = empty module stubs (next big build).
- ⬜ No auto-placement yet — tiles have only been placed/walked by hand.

## Architecture & file map
| Path | Role |
| ---- | ---- |
| `Source/ModularHexMap/` | primary game module (scaffold, ~empty) |
| `Source/TP_ThirdPerson/` | **ported** Epic Third Person template module (character/controller/gamemode + Combat/Platforming/SideScrolling variants). Non-primary (`IMPLEMENT_GAME_MODULE`). |
| `Plugins/HexMapGenerator/` | Runtime + Editor modules — **empty stubs**; the future catalog + placement system |
| `Source_Art/Blender/HexBase.blend` | **master base** (Hex_Base + anchors + M_HexGround/M_Road/M_Pavement) |
| `Tools/blender/gen_street_tiles.py` | **street generator** (edit `EDGE_SETS`, run it) |
| `Tools/build_test_map.py` | UE headless map assembly (import + lights + PlayerStart) |
| `Content/HexTiles/Source/` | glTF staging (**gitignored**, regenerable) |
| `Docs/Design.md` `Docs/Pipeline.md` `Source_Art/README.md` | vision / pipeline / tile contract |

## Records of resistance (gotchas that fought us — don't relearn these)
1. **Headless glTF import crashes on Slate.** `UnrealEditor-Cmd -run=pythonscript` is a
   commandlet with **no Slate**; the Interchange importer syncs the Content Browser and
   asserts (`CurrentApplication.IsValid()`). → Import glTF **in the GUI editor**, or note the
   asset still *saves to disk* before the crash. Level *assembly* (no import) is headless-safe.
2. **Blender drops unused materials on save.** `M_Road`/`M_Pavement` vanished from the saved
   master because nothing used them. → `material.use_fake_user = True` on shared materials.
3. **Migrated BPs needed the FULL `TP_ThirdPerson` module (~30 classes)**, not the 3 vanilla
   files first shared. The content came from Epic's modern Third Person template (Combat/
   Platforming/SideScrolling variants). → Copied the engine template module
   (`UE_5.7/Templates/TP_ThirdPerson/...`) **verbatim**, changed `IMPLEMENT_PRIMARY_GAME_MODULE`
   → `IMPLEMENT_GAME_MODULE`, registered it in both `*.Target.cs` + the `.uproject`, and
   enabled the **StateTree + GameplayStateTree** plugins. Class names match `/Script/TP_ThirdPerson.*`
   so BPs resolve natively (no redirects).
4. **New `UCLASS` types need a full editor restart + `Build.bat`.** Live Coding can't hot-add
   classes; the editor holds the DLLs locked, so **close it first**.
5. **Imported tile meshes aren't walkable until** Collision Complexity = **Use Complex
   Collision As Simple** (Static Mesh editor). Then the curb/walls/floor all block.
6. **glTF imports at true real-world scale** (1 m → 100 uu) via Interchange — no scale fudge.
7. **Hexes carry a √3 between axes** — you can't round both. We keep **R=5** (edge 5 m,
   width 10 m; flat-to-flat = 8.66 m) and let the generator/plugin place tiles, so 8.66 is
   never hand-typed. Neighbor offsets are in `Source_Art/README.md`.
8. **UE launch wrapper exits 0 instantly** because the editor reparents to its own process —
   not a failure. Confirm with `Get-Process UnrealEditor`; real logs are in `Saved/Logs/`.
9. **Blender close-range perspective makes flat tiles look like tall walls.** Verify with
   vertex Z extents or an **orthographic** view before believing a screenshot.

## Next steps
1. **`HexMapGenerator` plugin MVP** — a tile catalog (`UHexTileDataAsset`: type + connected
   edges) + an **editor placement tool** so tiles auto-snap on the hex grid (no hand-placing).
   Goal: get to *playing with placed streets* ASAP. (Planning this next — want a minimal,
   metric-defined scope.)
2. First **bespoke building tile** (`.blend` linking master; walk-in on-tile interior).
3. Batch-import the street set into UE with collision (extend `Tools/build_test_map.py`).
