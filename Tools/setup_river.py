# setup_river.py — one-shot UE wiring for the river kit (GUI editor; glTF import
# asserts headless — Resistance #1):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_river.py"
#
# Reads river_kit.json (written by gen_river_tiles.py — the single source for the kit's
# masks), imports T_river_* / T_bridge_* to /Game/_project/HexTiles/River with
# Complex-As-Simple collision (Resistance #5), then adds/updates DA_HexTileSet_Streets
# rows: road edges as sockets + the authored WaterMask. Idempotent (update-by-name);
# rows edited by index + force-saved (Resistance #11).
import os
import json
import unreal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # machine-neutral
SRC  = REPO + "/Content/_project/HexTiles/Source"
DEST = "/Game/_project/HexTiles/River"
DA   = "/Game/_project/Data/DA_HexTileSet_Streets"

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
eal = unreal.EditorAssetLibrary

with open(os.path.join(SRC, "river_kit.json")) as f:
    kit = json.load(f)["tiles"]

# 1) import the .glbs
tools = unreal.AssetToolsHelpers.get_asset_tools()
tasks = []
for tile in kit:
    glb = os.path.join(SRC, tile + ".glb")
    if not os.path.exists(glb):
        warn("[River] missing glb: " + glb)
        continue
    t = unreal.AssetImportTask()
    t.filename = glb
    t.destination_path = DEST
    t.automated = True
    t.replace_existing = True
    t.save = True
    tasks.append(t)
tools.import_asset_tasks(tasks)
log("[River] imported %d tiles" % len(tasks))

# 2) find meshes + assert collision
meshes = {}
for p in eal.list_assets(DEST, recursive=True, include_folder=False):
    a = eal.load_asset(p)
    if isinstance(a, unreal.StaticMesh) and a.get_name() in kit:
        bs = a.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag",
                                   unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_loaded_asset(a)
        meshes[a.get_name()] = a
log("[River] meshes found %d/%d" % (len(meshes), len(kit)))

# 3) catalog rows (update-or-append by name; index assignment — Resistance #11)
asset = unreal.load_asset(DA)
tiles = list(asset.get_editor_property("tiles"))
by_name = {str(t.get_editor_property("name")): i for i, t in enumerate(tiles)}
added = updated = 0
for tile, masks in kit.items():
    row_name = tile[2:]                       # T_river_straight -> river_straight
    mesh = meshes.get(tile)
    if mesh is None:
        warn("[River] no mesh for %s; row skipped" % tile)
        continue
    existing = row_name in by_name
    d = tiles[by_name[row_name]] if existing else unreal.HexTileDef()
    d.set_editor_property("name", row_name)
    d.set_editor_property("mesh", mesh)
    rm = int(masks["road_mask"])
    socks = [unreal.HexEdgeSocket.ROAD if (rm >> i) & 1 else unreal.HexEdgeSocket.PAVEMENT
             for i in range(6)]
    d.set_editor_property("edges", socks)
    d.set_editor_property("water_mask", int(masks["water_mask"]))
    if existing:
        tiles[by_name[row_name]] = d
        updated += 1
    else:
        tiles.append(d)
        by_name[row_name] = len(tiles) - 1
        added += 1
asset.set_editor_property("tiles", tiles)
ok = eal.save_loaded_asset(asset, only_if_is_dirty=False)
log("[River] DA rows: %d added, %d updated, %d total (save=%s)"
    % (added, updated, len(tiles), ok))
warn("=== setup_river: done ===")
