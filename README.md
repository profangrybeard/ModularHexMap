# ModularHexMap

A modular hex map system for Unreal Engine. Hex tiles are authored in **Blender**,
exported through a **Claude-driven pipeline**, and assembled at runtime/edit-time by
the **HexMapGenerator** Unreal plugin.

> **Status:** Foundation only — no gameplay yet. The repo, project scaffold, and
> plugin module skeletons are in place; tile authoring and the generator's runtime
> behavior come next.

---

## Stack

| Layer                | Tool                                    |
| -------------------- | --------------------------------------- |
| Tile authoring       | Blender (via Blender MCP connector)     |
| Pipeline orchestrator| Claude Code                             |
| Engine               | Unreal Engine 5.7.4 (source build)      |
| Project type         | C++                                     |
| Plugin               | `Plugins/HexMapGenerator` (Editor + Runtime) |
| Asset storage        | Git LFS                                 |

## Repository layout

```
ModularHexMap/
├── ModularHexMap.uproject       UE project manifest
├── Source/                      Game C++ module + build targets
├── Config/                      Default*.ini stubs
├── Content/                     UE assets (LFS-tracked)
├── Plugins/
│   └── HexMapGenerator/         Custom plugin (Runtime + Editor modules)
├── Source_Art/
│   └── Blender/Tiles/           Authoritative .blend tile sources
└── Docs/
    └── Pipeline.md              Claude → Blender → Unreal flow
```

## Prerequisites

- **Unreal Engine 5.7.x** installed via the Epic Games Launcher
  (`EngineAssociation: "5.7"` in the `.uproject` resolves to whatever 5.7.x is
  installed).
- **Visual Studio 2022** (17.8+) with the *Game development with C++* workload.
  Install components by importing the committed `.vsconfig` in the VS Installer.
- **Blender 4.x** with the MCP connector add-on enabled.
- **Git LFS** installed system-wide (`git lfs install`).

## First-time setup

```powershell
# 1. Clone (LFS pulls binary assets automatically once installed system-wide).
git clone https://github.com/profangrybeard/ModularHexMap.git
cd ModularHexMap

# 2. Generate IDE project files.
#    Right-click ModularHexMap.uproject → "Generate Visual Studio project files".
#    EngineAssociation is "5.7" — the Epic Games Launcher install handler picks
#    your installed 5.7.x automatically.

# 3. Open ModularHexMap.sln in Visual Studio, set the solution config to
#    "Development Editor" / "Win64", and Build. Or run from a shell:
#       "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" `
#         ModularHexMapEditor Win64 Development `
#         -Project="<abs path>\ModularHexMap.uproject" -WaitMutex

# 4. Launch by double-clicking ModularHexMap.uproject (or F5 from VS).
```

## The pipeline (high level)

1. **Author** a hex tile in Blender (Source_Art/Blender/Tiles/).
2. **Claude** drives Blender via the MCP connector to standardize tile bounds,
   pivot, scale, and naming conventions.
3. **Export** to FBX/glTF into a staging area under `Content/`.
4. **Import** into UE; the HexMapGenerator plugin's editor tool catalogs the tile
   and registers it as a hex variant.
5. **Generate** maps at edit time or runtime using the plugin's procedural API.

See [Docs/Pipeline.md](Docs/Pipeline.md) for the detailed flow.

## Migrating to UE 5.8

UE 5.8.0 is now available as a launcher install (`C:\Program Files\Epic Games\UE_5.8`).
When ready to move:

1. Change `EngineAssociation` in `ModularHexMap.uproject` from `"5.7"` to `"5.8"`.
2. Regenerate project files.
3. Fix any compile breaks (typically minimal across `.x` releases).
4. Bump `EngineVersion` in `Plugins/HexMapGenerator/HexMapGenerator.uplugin`.

We are intentionally **not** adopting 5.7-only experimental APIs, so this should
stay cheap.

## License

Copyright (c) 2026 Tim Lindsey. All rights reserved.

The code is public to read. It is not licensed for reuse.
