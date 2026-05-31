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

- **Unreal Engine 5.7.4** built from source. See Epic's
  [Building Unreal Engine from Source](https://dev.epicgames.com/documentation/en-us/unreal-engine/downloading-unreal-engine-source-code)
  guide.
- **Visual Studio 2022** (17.8+) with the *Game development with C++* workload and
  the *Unreal Engine installer* component.
- **Blender 4.x** with the MCP connector add-on enabled.
- **Git LFS** installed system-wide (`git lfs install`).

## First-time setup

```powershell
# 1. Clone (LFS pulls binary assets automatically once installed system-wide).
git clone https://github.com/profangrybeard/ModularHexMap.git
cd ModularHexMap

# 2. Associate the .uproject with your source-built engine.
#    Right-click ModularHexMap.uproject → "Switch Unreal Engine version"
#    and pick your 5.7.4 source build. This stamps EngineAssociation in the file.

# 3. Generate IDE project files.
#    Right-click ModularHexMap.uproject → "Generate Visual Studio project files"
#    (or invoke UnrealBuildTool's GenerateProjectFiles directly).

# 4. Open ModularHexMap.sln in Visual Studio, set the solution config to
#    "Development Editor" / "Win64", and Build.

# 5. Launch the editor (F5 or the built UnrealEditor.exe with the .uproject).
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

When 5.8 ships stable (Epic's window: **June–August 2026**):

1. Bump `EngineAssociation` in `ModularHexMap.uproject` to the 5.8 source build.
2. Regenerate project files.
3. Fix any compile breaks (typically minimal across `.x` releases).
4. Bump `EngineVersion` in `Plugins/HexMapGenerator/HexMapGenerator.uplugin`.

We are intentionally **not** adopting 5.7-only experimental APIs, so this should
stay cheap.
