# Buildings — production pipeline (LANDED 2026-06-07)

> Single-story walk-in shop fronts that trace the splined road centerlines, with
> interior surfaces, door frames + thresholds, and a small bevel on every hard edge.
> Generated procedurally per road config, baked to glTF, placed in-engine as a parallel
> ISM next to the matching street tile.
>
> For the research history (paused-then-resumed) see [BuildingFootprints.md](BuildingFootprints.md).

## The 30-second tour

```
gen_buildings.py  -->  T_bldg_*.glb  -->  /Game/_project/HexTiles/Buildings/  -->  ISM in ShuffleLab
   (Blender)         (12 files)         (UE StaticMesh assets)                  (parallel to street tile)
```

- **Blender**: `Tools/blender/gen_buildings.py` headless-bakes one `.glb` per road config
  (`straight`, `bend`, `curve`, `deadend`, `tee`/`tee_a/b/c`, `quad`/`b/c`, `penta`).
  Skips `blank` (user playground) and `junction` (no buildable area).
- **glTF**: `Content/_project/HexTiles/Source/T_bldg_<name>.glb` — exported with
  `export_apply=True` so modifiers (bevel) bake into the mesh at write-time.
- **Unreal**: `Tools/setup_buildings.py` first-time-imports → `/Game/_project/HexTiles/Buildings/`,
  sets collision to Complex-As-Simple, and wires `BuildingMesh` on each `DA_HexTileSet_Streets`
  row by name (`T_street_<x>` → `T_bldg_<x>`).
- **Engine**: `AHexShuffleGenerator::Build()` places a parallel ISM at every road-bearing
  frontier cell — same world transform as the street tile, keyed on `BuildingMesh`.

## Per-tile geometry

Each `T_bldg_<name>.glb` is **walls + roof + door frames + threshold** for every building
piece inside the polygon `hex - corridor`. Corner pieces (any pair of adjacent road edges
sharing a hex vertex) are classified as **gardens** and emit **NO geometry** — the user
authors custom content into those plots later. The inner-bend disc subtraction grows the
corner plot to ~9 m² so there's room for that future authoring.

### Material slots (5 per tile)

| Slot | Material | What it covers |
| --- | --- | --- |
| 0 | `M_Building` | Exterior facade walls (front, road-facing) |
| 1 | `M_BuildingBack` | Exterior back/side walls (along the hex perimeter) |
| 2 | `M_BuildingRoof` | Roof top + vertical sides |
| 3 | `M_BuildingInterior` | Inside face of every wall + ceiling (roof underside) |
| 4 | `M_DoorFrame` | Jambs + header + threshold at every door |

`M_BuildingBack` is the **engine seam** for the future "inset on blank-side" alley
behaviour — the engine can later hide / replace per-edge sections of slot 1 based on
neighbour type (road tile vs blank), without re-baking from Blender.

### Wall details

- **Single-story** — 3.5 m eaves (`WALL_H`), flat roof slab (`ROOF_T = 0.2 m`). No
  gables — verified that per-hex gables read as a "field of tents" on a hex grid.
- **Facade tracks the road** — for each piece, the polygon's road-facing perimeter is
  the offset of the splined road centerline by `KEEP_HW = HW + WALK = 2.5 m` (1.5 m
  carriageway half-width + 1 m sidewalk). C1-smooth at edge midpoints, matches the
  modular contract used by `gen_curved_tiles.py`.
- **Interior walls** — for every exterior wall quad we emit a coincident inward-facing
  duplicate, offset 5 mm into the building (`INTERIOR_EPS`) to avoid z-fight. Same
  door splits propagate; lintels become two-sided automatically.
- **Door frames** — per door: 2 jambs (vertical posts, `FRAME_W = 12 cm` wide,
  `FRAME_D = 20 cm` deep, projects 10 cm into the room + 10 cm out to mask the
  thin wall edge), 1 header (cap above the lintel, `HEADER_T = 12 cm` tall),
  1 threshold (sill at the door bottom, `THRESHOLD_H = 5 cm` step,
  `THRESHOLD_D = 40 cm` deep).
- **Bevel** — angle-limited (30°) modifier with `BEVEL_WIDTH = 3 cm` chamfers every
  hard corner. Applied at export, bakes into the .glb.
- **Smooth shading** — `use_smooth = True` on every polygon. With Shapely orient(CCW)
  guaranteeing CCW exterior, welded vertex normals on curved facades interpolate
  cleanly. (Blender 5.1 caveat: `shade_smooth_by_angle` no longer adds the
  Smooth-by-Angle GN modifier — per-edge sharp marking has no visual effect without
  it; we just smooth everything and let the bevel hold the hard corners.)

### Door count rule

Doors are placed by **combined front-run arc length**, not per-segment (per-segment
was wrong: Shapely's `LineString.buffer(arc)` tessellates a curve into many short
segments, each of which fails a per-segment door-fit check — curves ended up with no
doors, straight got too many).

```python
def doors_for_run(L):
    if L < 1.3:  return 0     # no room for a 0.9 m door
    if L < 7.0:  return 1     # small shop
    if L < 25.0: return 2     # default
    return 3                  # long facade
```

Doors are evenly distributed along the run's arc length. A door whose width spans
multiple curved sub-segments produces a **lintel quad on each overlapped segment** —
the lintel follows the curve (a "banana lintel"). Multi-frontage buildings (a building
with two separate non-adjacent road faces) get the rule per-run, so every road
frontage gets at least one door automatically.

## Engine wiring

### C++ change

`Plugins/HexMapGenerator/Source/HexMapGenerator/Public/HexTileTypes.h` adds one
field to `FHexTileDef`:

```cpp
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile")
TSoftObjectPtr<UStaticMesh> BuildingMesh;
```

`Private/HexShuffleGenerator.cpp::Build()` — frontier-cell branch — after placing
the street tile's ISM, place the building too at the same world transform:

```cpp
if (UStaticMesh* BMesh = TileSet->Tiles[TileIdx].BuildingMesh.LoadSynchronous())
{
    if (UInstancedStaticMeshComponent* BISM = GetOrCreateISM(BMesh))
    {
        BISM->AddInstance(X, /*bWorldSpace=*/false);
    }
}
```

Core (pit) cells skip the building placement — the destroyed heart of the town
isn't residential.

### Data wiring

`DA_HexTileSet_Streets` rows now point each `T_street_<name>` at the matching
`T_bldg_<name>`. `Tools/setup_buildings.py` does both first-time import + DA
population in one `-ExecutePythonScript` pass. Subsequent geometry changes go
through `Content/Python/reimport_hextiles.py` (the existing **Tools → Reimport
Hex Tiles** menu) — `Buildings/` is under `TILE_ROOT` so it picks the new tiles
up automatically.

## Commands

```powershell
# 1. Bake the .glb (headless, Blender; never saves the master)
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background `
  "C:\SCAD\_projects\ModularHexMap\Source_Art\Blender\HexBase.blend" `
  --python "C:\SCAD\_projects\ModularHexMap\Tools\blender\gen_buildings.py"

# 2. First-time UE import + DA wiring (GUI editor, one-shot Python; required only ONCE)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" `
  "C:\SCAD\_projects\ModularHexMap\ModularHexMap.uproject" `
  -ExecutePythonScript="C:\SCAD\_projects\ModularHexMap\Tools\setup_buildings.py"

# 3. Subsequent geometry changes: just reimport (refreshes both streets + buildings)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" `
  "C:\SCAD\_projects\ModularHexMap\ModularHexMap.uproject" `
  -ExecutePythonScript="C:\SCAD\_projects\ModularHexMap\Content\Python\reimport_hextiles.py"

# 4. Verify in-engine (loads ShuffleLab, Randomizes, dumps ISM counts)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" `
  "C:\SCAD\_projects\ModularHexMap\ModularHexMap.uproject" `
  -ExecutePythonScript="C:\SCAD\_projects\ModularHexMap\Tools\_verify_buildings.py"
```

## Tuning knobs

All in `gen_buildings.py` — re-bake + reimport after changing.

| Constant | Default | Effect |
| --- | --- | --- |
| `WALL_H` | 3.5 | Wall (eaves) height in metres |
| `ROOF_T` | 0.20 | Flat roof slab thickness |
| `DOOR_W` / `DOOR_H` | 0.9 / 2.1 | Doorway dimensions |
| `FRAME_W` / `FRAME_D` / `HEADER_T` | 0.12 / 0.20 / 0.12 | Jamb width / depth / header thickness |
| `THRESHOLD_H` / `THRESHOLD_D` | 0.05 / 0.40 | Sill step height / cross-wall depth |
| `INTERIOR_EPS` | 0.005 | Interior-wall inward offset (z-fight prevention) |
| `BEVEL_WIDTH` / `BEVEL_SEGMENTS` | 0.03 / 1 | Chamfer size / smoothness |
| `SHARP_ANGLE_DEG` | 30.0 | Bevel angle threshold (only corners > this are beveled) |
| `INNER_KEEP_HW` | 1.5 | Corridor inner extent at bend vertices (smaller = bigger corner gardens) |
| `KEEP_HW` (= `HW + WALK`) | 2.5 | Building face offset from road centerline |

## Open / deferred

1. **Custom corner content.** Bend / tee_a / quad_b/c / penta corners are tagged
   `garden` by `classify_pieces` and emit no geometry. The inner-bend disc subtraction
   gives each corner a usable ~9 m² plot. **User authors per-corner content.**
2. **Engine-side per-edge back-wall split** for the "inset on blank-side" alley
   behaviour. `M_BuildingBack` is the seam — the engine can later hide / replace
   per-edge sections without a re-bake.
3. **`blank` cell treatment** — also user playground. Generator skips it entirely;
   custom geometry drops in there.
4. **Materials are placeholder colours.** A textured pass + per-tile material variation
   are downstream from style/lighting decisions (see `style-over-fidelity` memory).

## Gotchas (hard-won — read before "improving" the generator)

1. **Shapely returns CW polygons after `hex.difference(corridor).buffer(...)`.** Verified
   empirically against every config. With CW polygons, `add_quad`'s
   `[v00,v10,v11,v01]` winding produces INWARD normals — every wall faces backwards
   in UE (Face Orientation overlay paints them red). **Fix:** always call
   `shapely.geometry.polygon.orient(pc, sign=1.0)` before extracting coords in
   `build_walls` and `build_roof_slab`.

2. **`bmesh.ops.recalc_face_normals` on disconnected per-segment quads FLIPS
   alternating panels** in any door-split run — half the facade ends up backwards.
   The per-segment quads share no edges (each `add_quad` creates fresh verts),
   so recalc has nothing to anchor consistency to and ends up flipping. **Fix:** do
   NOT call recalc in `build_walls`. With `orient(CCW)` above, the explicit winding
   is already correct.

3. **Blender 5.1's `shade_smooth_by_angle` no longer adds the Smooth-by-Angle GN
   modifier** — it just marks edges sharp on the mesh. Without the GN modifier (or
   custom split normals), sharp-edge marks have no visual effect on smooth shading.
   **Fix:** set `use_smooth = True` on every polygon and let the bevel modifier
   provide the visible hard-corner treatment.

4. **Per-segment door placement is wrong for tessellated curves.** Shapely's
   `LineString.buffer(arc)` returns many short sub-segments (~1.3 m each) along a
   curved facade — each one fails the `seg_len ≥ DOOR_W + 0.4` fit test, so curves
   get zero doors while straight gets too many (`ceil(17/8) = 3`). **Fix:** classify
   doors by combined front-run arc length (`doors_for_run`) and map each door's span
   to whichever segments it overlaps (multi-segment "banana lintel" handles curves
   correctly).

5. **5 material slots → 5 ISMs per tile in UE.** Each new slot adds an ISM to
   `AHexShuffleGenerator`'s `MeshToISM` map. Manageable but accounts for the bulk of
   the post-Randomize component count.
