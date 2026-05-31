# Source_Art

Authoritative source files for art assets. **The files here are the source of
truth** — anything in `Content/` is downstream of these and can be regenerated.

## Layout

```
Source_Art/
└── Blender/
    └── Tiles/         hex tile .blend files (one tile per file)
```

## Conventions for hex tiles

These are working assumptions for the foundation — refine as we go.

| Property        | Value                                                  |
| --------------- | ------------------------------------------------------ |
| Orientation     | Flat-top (vertices at top/bottom of hex)               |
| Hex radius      | 1.0 m (Blender units = meters; UE scales on import)    |
| Pivot           | World origin (0, 0, 0), at the base of the tile        |
| Up axis         | +Z                                                     |
| Forward axis    | +Y                                                     |
| Naming          | `T_<biome>_<variant>.blend` e.g. `T_grassland_a.blend` |
| Export format   | glTF 2.0 (`.glb`) — preserves transforms, materials    |
| Export path     | `Content/HexTiles/Source/` (staged, not committed)     |

The Blender MCP connector (driven by Claude) is responsible for enforcing these
conventions on author and on export. The plugin's editor module will validate
imported tiles against this contract.
