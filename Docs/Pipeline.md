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
Claude exports the tile to glTF 2.0 (`.glb`) into the UE staging folder
`Content/_project/HexTiles/Source/`. glTF is preferred over FBX for
deterministic transforms and open-standard materials.

### 3. Import into UE
The export lands under `Content/_project/` so UE auto-detects it. Imported
assets live under `/Game/_project/HexTiles/`. Standard UE import settings
apply (Static Mesh, **Use Complex As Simple** collision — gotcha #5). A
**Tools ▸ Reimport Hex Tiles** menu entry runs the full reimport + material
self-heal in one click (`Content/Python/reimport_hextiles.py`).

### 4. Catalog registration
Imported tiles are entered into the `UHexTileSet` data asset at
`/Game/_project/Data/DA_HexTileSet_Streets` (mesh + 6 edge sockets +
`Occupancy`). The catalog is the runtime's mask→tile/rotation lookup.

### 5. Map assembly
`AHexShuffleGenerator` (in `ShuffleLab`) grows a road network (pinned core +
arteries + branching), measures each tile's real road edges from geometry,
and resolves rotation to drop tiles as ISMs under real light. Reusable +
runtime-callable.

## Tile authoring tracks

Two tracks share **one** canonical base — `Source_Art/Blender/HexBase.blend`
(`Hex_Base` + `RoadAnchor_0..5` + materials `M_HexGround`/`M_Road`/`M_Pavement`):

1. **Procedural tiles (roads/streets)** — generated, never hand-modeled. The canonical
   generator is `Tools/blender/gen_curved_tiles.py` (per-tile spline-smoothed roads:
   circular-arc `bend`/`curve` + fanned spline junctions = hub + cubic-bezier + swirl).
   It is a table of `name → connected-edge list`. (The earlier faceted
   `gen_street_tiles.py` was superseded and deleted 2026-06-10; git history has it.)
   Run against the master to (re)build + export every `T_street_*.glb`:

   ```
   blender --background Source_Art/Blender/HexBase.blend \
           --python Tools/blender/gen_curved_tiles.py
   ```

   Add a tile type by adding a row to `EDGE_SETS`. Change the master base/materials once and
   every tile inherits it on the next run. The script never saves the master, and is
   **manifest-aware** — tiles flagged `bespoke` in `tile_manifest.json` are skipped.

2. **Bespoke tiles (buildings, the Pit)** — hand-authored, one `.blend` per tile under
   `Source_Art/Blender/Tiles/`, each **linking** the `HexBase` collection so they share the
   exact base geometry/materials. `T_core_pit.blend` is the first. Exported to the same
   staging folder.

Both write glbs to `Content/_project/HexTiles/Source/` for UE import.

### The "Hex Tiles" Blender addon
Day-to-day tile work runs through `Tools/blender/tile_pipeline.py` (the **Hex Tiles**
N-panel). Per-tile **export ☑** toggles persist to `tile_manifest.json` (git-tracked:
`enabled` + `bespoke` + `blend` path). **Build Enabled → Preview & Export** lays the
enabled procedural tiles out in a transient preview grid and writes their `.glb`.
**Promote to Bespoke** spins a tile into its own `.blend` (materials + reference hex
**linked** from the master; mesh local), flips it OFF in the manifest, and opens it.
Leaving the master never auto-saves it (gotcha #2/#18).

### Material masters
The 4 shared masters (`M_Road` / `M_Pavement` / `M_HexGround` / `M_TileBorder`) live in
`/Game/_project/HexTiles/Materials/`, all parented to **`M_HexTile_Master`**. Reimport
self-heals the per-mesh dupes glTF mints on import (`hextile_materials.consolidate_to_masters`,
gotcha #19).

## What's built today vs. what's next

| Stage                                       | Status        |
| ------------------------------------------- | ------------- |
| Repo + LFS + scaffold                       | ✅ done        |
| Plugin modules compile                      | ✅ scaffolded  |
| Third-person character (UE)                 | ✅ done        |
| Blender authoring conventions               | ✅ locked      |
| Procedural street set + curved generator    | ✅ done        |
| "Hex Tiles" addon + `tile_manifest.json`    | ✅ done        |
| Content reorg → `/Game/_project/`           | ✅ done        |
| `UHexTileSet` catalog (`DA_HexTileSet_Streets`) | ✅ done    |
| `AHexShuffleGenerator` (runtime randomizer) | ✅ done        |
| 4 shared material masters (`M_HexTile_Master`) | ✅ done     |
| First bespoke tile (`T_core_pit`)           | ✅ done        |
| Bespoke building tiles (per-file)           | ⏭️ next        |
| Editor placement tool                       | ⏭️ later       |
