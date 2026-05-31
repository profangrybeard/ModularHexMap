# Pipeline: Claude → Blender → Unreal

End-to-end flow for authoring and integrating a hex tile.

## Roles

| Component         | Responsibility                                                 |
| ----------------- | -------------------------------------------------------------- |
| **Claude Code**   | Orchestrator. Drives Blender via MCP, validates outputs, edits the plugin. |
| **Blender + MCP** | Authoring environment. Creates and standardizes tile geometry. |
| **Unreal 5.7.4**  | Runtime + editor. Imports tiles, the HexMapGenerator plugin assembles them. |

## Flow

```
┌──────────────┐    1. drive    ┌──────────────┐   2. export    ┌──────────────┐
│ Claude Code  │ ─────────────▶ │   Blender    │ ─────────────▶ │ Content/     │
│ (this repo)  │                │  (MCP add-on)│   .glb / .fbx  │  HexTiles/   │
└──────────────┘                └──────────────┘                └──────────────┘
        │                                                                │
        │                                                                │ 3. UE import
        │              5. validate + register                            ▼
        │           ┌────────────────────────────────────────────────────┐
        └──────────▶│ HexMapGenerator plugin (Editor module)             │
                    │  - cataloging                                      │
                    │  - tile contract validation                        │
                    │  - hex grid assembly (edit-time & runtime)         │
                    └────────────────────────────────────────────────────┘
```

## Step-by-step (per tile)

### 1. Author in Blender
Claude opens Blender via the MCP connector and either creates a new tile or
edits an existing one in `Source_Art/Blender/Tiles/`. Conventions
(orientation, scale, pivot, naming) are enforced as the tile is built. See
[Source_Art/README.md](../Source_Art/README.md).

### 2. Export
Claude exports the tile to glTF 2.0 (`.glb`) into a UE staging folder
(`Content/HexTiles/Source/` — name TBD). glTF is preferred over FBX for
deterministic transforms and open-standard materials.

### 3. Import into UE
The export lands in `Content/` so UE auto-detects it. Standard UE import
settings apply (Static Mesh, collision generation per project default).

### 4. Plugin discovery
The HexMapGenerator **editor module** scans `Content/HexTiles/` for newly
imported tiles, validates them against the contract (bounds, pivot, naming),
and registers each as an entry in a `UHexTileDataAsset`.

### 5. Map assembly
At edit time, the plugin's tool window lets the designer place tiles on a hex
grid. At runtime, the plugin's **runtime module** exposes a deterministic
generator that materializes the grid into `AHexMapActor` instances given a
seed and a ruleset.

## What's built today vs. what's next

| Stage                          | Status        |
| ------------------------------ | ------------- |
| Repo + LFS + scaffold          | ✅ done        |
| Plugin modules compile         | ✅ scaffolded  |
| Blender authoring conventions  | 📝 drafted    |
| Tile validator (editor module) | ⏭️ next        |
| `UHexTileDataAsset`            | ⏭️ next        |
| Editor tool window             | ⏭️ next        |
| Runtime generator              | ⏭️ later       |
