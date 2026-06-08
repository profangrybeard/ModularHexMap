# setup_buildings.py -- one-shot UE wiring for the building-tile family.
# Run inside a GUI editor (Slate available -- glTF import asserts headless, gotcha #1):
#
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_buildings.py"
#
# What it does (in order):
#   1. Imports 12 T_bldg_*.glb from Content/_project/HexTiles/Source/ to
#      /Game/_project/HexTiles/Buildings/ (collision = complex-as-simple, gotcha #5).
#      The glTF importer creates per-tile subfolders -- we discover by recursive walk
#      so naming pattern shifts (e.g. /StaticMeshes/<name>) don't break us.
#   2. Iterates DA_HexTileSet_Streets, populating each row's BuildingMesh with the
#      matching T_bldg_<row.name>. Row names are bare suffixes ('bend', 'tee_c'), so
#      we match by appending to 'T_bldg_'. Skips 'blank' and 'junction'.
#   3. Force-saves the DA with only_if_is_dirty=False (gotcha #11: nested struct array
#      edits don't dirty the package). Verifies the .uasset mtime changed.
#
# After this lands, open ShuffleLab and hit Randomize -- the parallel ISM in
# AHexShuffleGenerator::Build() places the matching building at every road-bearing
# frontier cell at the same world transform as the street tile.

import os
import time
import unreal

REPO     = r"C:/SCAD/_projects/ModularHexMap"
SRC      = REPO + "/Content/_project/HexTiles/Source"
DEST     = "/Game/_project/HexTiles/Buildings"
DA_PATH  = "/Game/_project/Data/DA_HexTileSet_Streets"
DA_FILE  = REPO + "/Content/_project/Data/DA_HexTileSet_Streets.uasset"

TILE_NAMES = [
    "T_bldg_straight", "T_bldg_bend", "T_bldg_curve", "T_bldg_deadend",
    "T_bldg_tee", "T_bldg_tee_a", "T_bldg_tee_b", "T_bldg_tee_c",
    "T_bldg_quad", "T_bldg_quad_b", "T_bldg_quad_c", "T_bldg_penta",
]
SKIP_ROWS = {"blank", "junction"}             # no buildable area / user playground

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal   = unreal.EditorAssetLibrary


# ---- step 1: import + collision ----
def import_tiles(names):
    tasks = []
    for name in names:
        glb = "%s/%s.glb" % (SRC, name)
        if not os.path.exists(glb):
            warn("missing glb: " + glb); continue
        t = unreal.AssetImportTask()
        t.filename         = glb
        t.destination_path = DEST
        t.destination_name = name
        t.automated        = True
        t.replace_existing = True
        t.save             = True
        tasks.append(t)
    tools.import_asset_tasks(tasks)
    log("import_tiles: submitted %d tasks -> %s" % (len(tasks), DEST))


def discover_building_meshes():
    """Walk DEST recursively. The glTF importer drops StaticMeshes under
    T_bldg_<name>/StaticMeshes/T_bldg_<name> -- we don't depend on the exact path."""
    out = {}
    for p in eal.list_assets(DEST, recursive=True, include_folder=False):
        obj = eal.load_asset(p)
        if isinstance(obj, unreal.StaticMesh) and obj.get_name().startswith("T_bldg_"):
            out[obj.get_name()] = obj
    return out


def set_collision(meshes):
    fixed = 0
    for name, sm in meshes.items():
        bs = sm.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag",
                                   unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            eal.save_loaded_asset(sm, only_if_is_dirty=False)
            fixed += 1
    log("set_collision: complex-as-simple on %d / %d meshes" % (fixed, len(meshes)))


# ---- step 2: wire BuildingMesh into DA_HexTileSet_Streets ----
def _coerce_building_mesh(row, asset):
    """TSoftObjectPtr<UStaticMesh> in UE Python: assigning the loaded asset usually works,
    but some bindings want a SoftObjectPath. Try the asset first, fall back to the path."""
    try:
        row.set_editor_property("building_mesh", asset)
        return
    except Exception:
        sop = unreal.SoftObjectPath(asset.get_path_name())
        row.set_editor_property("building_mesh", sop)


def wire_buildings_into_da(meshes):
    ts = eal.load_asset(DA_PATH)
    if ts is None:
        err("DA not found: " + DA_PATH); return False
    tiles = ts.get_editor_property("tiles")
    if tiles is None:
        err("DA has no 'tiles' array"); return False

    new_tiles = list(tiles)                   # mutate-by-index then set_editor_property back (gotcha #11)
    wired, skipped, missing = 0, [], []
    for i, row in enumerate(new_tiles):
        nm = str(row.get_editor_property("name"))
        if nm in SKIP_ROWS:
            skipped.append(nm); continue
        bldg_name = "T_bldg_%s" % nm
        bldg = meshes.get(bldg_name)
        if bldg is None:
            missing.append(bldg_name); continue
        _coerce_building_mesh(row, bldg)
        new_tiles[i] = row
        wired += 1
    ts.set_editor_property("tiles", new_tiles)
    log("wire: wired=%d skipped=%s missing=%s" % (wired, skipped, missing))

    before = os.path.getmtime(DA_FILE) if os.path.exists(DA_FILE) else 0
    eal.save_loaded_asset(ts, only_if_is_dirty=False)
    time.sleep(0.5)
    after = os.path.getmtime(DA_FILE) if os.path.exists(DA_FILE) else 0
    size  = os.path.getsize(DA_FILE)  if os.path.exists(DA_FILE) else 0
    if after > before:
        log("DA saved OK: size=%d mtime=%s" % (size, time.ctime(after)))
        return True
    err("DA mtime DID NOT CHANGE -- save was a no-op."); return False


def main():
    if not eal.does_directory_exist(DEST):
        eal.make_directory(DEST)
    import_tiles(TILE_NAMES)
    meshes = discover_building_meshes()
    log("discover_building_meshes: found %d" % len(meshes))
    set_collision(meshes)
    wire_buildings_into_da(meshes)
    log("setup_buildings: done.")


if __name__ == "__main__":
    main()
