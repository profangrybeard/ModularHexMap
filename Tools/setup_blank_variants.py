# setup_blank_variants.py — one-shot UE wiring for the blank-variant kit (GUI editor;
# glTF import asserts headless — Resistance #1):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_blank_variants.py"
#
# Reads blank_kit.json (written by gen_blank_variants.py), imports T_blank_* to
# /Game/_project/HexTiles/Blanks with Complex-As-Simple collision (Resistance #5),
# then adds/updates DA_HexTileSet_Streets rows: all-Pavement edges, WaterMask 0,
# BuildingMesh untouched (null — the garden IS the content), and the kit's Weight
# (the resolver's variant dial; plain T_street_blank keeps the C++ default 1.0).
# Idempotent (update-by-name); rows edited by index + force-saved (Resistance #11).
# Run Recalibrate (or Tools ▸ Reimport Hex Tiles) afterwards so the new meshes get
# measured; then Randomize and walk a garden.
import os
import json
import unreal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # machine-neutral
SRC  = REPO + "/Content/_project/HexTiles/Source"
DEST = "/Game/_project/HexTiles/Blanks"
DA   = "/Game/_project/Data/DA_HexTileSet_Streets"

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
eal = unreal.EditorAssetLibrary

with open(os.path.join(SRC, "blank_kit.json")) as f:
    kit = json.load(f)["tiles"]

# 1) import the .glbs
tools = unreal.AssetToolsHelpers.get_asset_tools()
tasks = []
for tile in kit:
    glb = os.path.join(SRC, tile + ".glb")
    if not os.path.exists(glb):
        warn("[Blanks] missing glb: " + glb)
        continue
    t = unreal.AssetImportTask()
    t.filename = glb
    t.destination_path = DEST
    t.automated = True
    t.replace_existing = True
    t.save = True
    tasks.append(t)
tools.import_asset_tasks(tasks)
log("[Blanks] imported %d tiles" % len(tasks))

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
log("[Blanks] meshes found %d/%d" % (len(meshes), len(kit)))

# 3) catalog rows (update-or-append by name; index assignment — Resistance #11)
asset = unreal.load_asset(DA)
tiles = list(asset.get_editor_property("tiles"))
by_name = {str(t.get_editor_property("name")): i for i, t in enumerate(tiles)}
added = updated = 0
for tile, spec in kit.items():
    row_name = tile[2:]                       # T_blank_garden -> blank_garden
    mesh = meshes.get(tile)
    if mesh is None:
        warn("[Blanks] no mesh for %s; row skipped" % tile)
        continue
    existing = row_name in by_name
    d = tiles[by_name[row_name]] if existing else unreal.HexTileDef()
    d.set_editor_property("name", row_name)
    d.set_editor_property("mesh", mesh)
    d.set_editor_property("edges", [unreal.HexEdgeSocket.PAVEMENT] * 6)
    d.set_editor_property("water_mask", int(spec["water_mask"]))
    d.set_editor_property("weight", float(spec.get("weight", 1.0)))
    if existing:
        tiles[by_name[row_name]] = d
        updated += 1
    else:
        tiles.append(d)
        by_name[row_name] = len(tiles) - 1
        added += 1
asset.set_editor_property("tiles", tiles)
ok = eal.save_loaded_asset(asset, only_if_is_dirty=False)
log("[Blanks] DA rows: %d added, %d updated, %d total (save=%s)"
    % (added, updated, len(tiles), ok))
warn("=== setup_blank_variants: done — Recalibrate, then Randomize ===")
