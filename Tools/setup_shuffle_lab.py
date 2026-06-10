# setup_shuffle_lab.py
# Run INSIDE the GUI editor (Slate available) so the glTF import doesn't hit the
# headless-commandlet Slate assert:
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_shuffle_lab.py"
#
# Imports the 14 street tiles (collision = complex-as-simple), builds the
# DA_HexTileSet_Streets catalog with each tile's edge sockets, and assembles a lit
# ShuffleLab with an AHexShuffleGenerator ready to Randomize. Each phase is guarded
# so a failure in one is logged and the rest still run.
#
# Rebuild-from-scratch order: this script -> Tools/wire_core_into_shufflelab.py (core
# layout + roll) -> Tools/setup_buildings.py (BuildingMesh wiring). The .glb sources
# must exist first (bake via gen_curved_tiles.py — the staging dir is gitignored).

import os
import unreal

REPO     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # machine-neutral
SRC      = REPO + "/Content/_project/HexTiles/Source"
DEST     = "/Game/_project/HexTiles"
DATA_DIR = "/Game/_project/Data"
DA_NAME  = "DA_HexTileSet_Streets"
MAP_PATH = "/Game/_project/Maps/ShuffleLab"

# Must match Tools/blender/gen_curved_tiles.py EDGE_SETS.
CONFIGS = {
    "blank": [], "deadend": [0], "bend": [0, 1], "curve": [0, 2], "straight": [0, 3],
    "tee": [0, 2, 4], "tee_a": [0, 1, 2], "tee_b": [0, 1, 3], "tee_c": [0, 1, 4],
    "quad": [0, 1, 2, 3], "quad_b": [0, 2, 3, 4], "quad_c": [0, 1, 3, 4],
    "penta": [0, 1, 2, 3, 4], "junction": [0, 1, 2, 3, 4, 5],
}

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
tools = unreal.AssetToolsHelpers.get_asset_tools()


def import_tiles():
    tasks = []
    for name in CONFIGS:
        glb = "%s/T_street_%s.glb" % (SRC, name)
        if not os.path.exists(glb):
            warn("missing glb: " + glb)
            continue
        t = unreal.AssetImportTask()
        t.filename = glb
        t.destination_path = DEST
        t.automated = True
        t.replace_existing = True
        t.save = True
        tasks.append(t)
    tools.import_asset_tasks(tasks)
    log("import_tiles: submitted %d tasks" % len(tasks))


def find_meshes():
    found = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST, recursive=True):
        a = unreal.EditorAssetLibrary.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            an = a.get_name()
            for name in CONFIGS:
                if an == "T_street_" + name:
                    found[name] = a
    log("find_meshes: %d / %d (%s)" % (len(found), len(CONFIGS), sorted(found.keys())))
    return found


def set_collision(meshes):
    for m in meshes.values():
        bs = m.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag",
                                   unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        unreal.EditorAssetLibrary.save_loaded_asset(m)
    log("set_collision: complex-as-simple on %d meshes" % len(meshes))


def make_catalog(meshes):
    full = DATA_DIR + "/" + DA_NAME
    if unreal.EditorAssetLibrary.does_asset_exist(full):
        unreal.EditorAssetLibrary.delete_asset(full)
    fac = unreal.DataAssetFactory()
    try:
        fac.set_editor_property("data_asset_class", unreal.HexTileSet)
    except Exception as e:
        log("DataAssetFactory class hint failed (ok): " + str(e))
    asset = tools.create_asset(DA_NAME, DATA_DIR, unreal.HexTileSet, fac)
    tiles = []
    for name, edges in CONFIGS.items():
        d = unreal.HexTileDef()
        d.set_editor_property("name", name)
        if name in meshes:
            d.set_editor_property("mesh", meshes[name])
        socks = [unreal.HexEdgeSocket.ROAD if i in edges else unreal.HexEdgeSocket.PAVEMENT
                 for i in range(6)]
        d.set_editor_property("edges", socks)
        tiles.append(d)
    asset.set_editor_property("tiles", tiles)
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    log("make_catalog: %d tiles" % len(tiles))
    return asset


def make_lab(asset):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.EditorAssetLibrary.delete_asset(MAP_PATH)
    les.new_level(MAP_PATH)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    def spawn(cls, loc, rot=(0, 0, 0)):
        return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))

    sun = spawn(unreal.DirectionalLight, (0.0, 0.0, 800.0), (-45.0, -45.0, 0.0))
    dlc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    dlc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    dlc.set_editor_property("atmosphere_sun_light", True)
    spawn(unreal.SkyAtmosphere, (0.0, 0.0, 0.0))
    spawn(unreal.ExponentialHeightFog, (0.0, 0.0, 0.0))
    sky = spawn(unreal.SkyLight, (0.0, 0.0, 400.0))
    slc = sky.get_component_by_class(unreal.SkyLightComponent)
    slc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    slc.set_editor_property("real_time_capture", True)

    gen = spawn(unreal.HexShuffleGenerator, (0.0, 0.0, 0.0))
    gen.set_editor_property("tile_set", asset)
    gen.set_editor_property("seed", 1)
    gen.set_editor_property("hex_circumradius_uu", 1000.0)   # R = 10 m contract
    les.save_current_level()
    log("make_lab: ShuffleLab built with generator")


def main():
    log("=== setup_shuffle_lab: start ===")
    try:
        import_tiles()
    except Exception as e:
        err("import_tiles failed: " + str(e))
    meshes = {}
    try:
        meshes = find_meshes()
        set_collision(meshes)
    except Exception as e:
        err("mesh phase failed: " + str(e))
    asset = None
    try:
        asset = make_catalog(meshes)
    except Exception as e:
        err("make_catalog failed: " + str(e))
    try:
        if asset:
            make_lab(asset)
    except Exception as e:
        err("make_lab failed: " + str(e))
    warn("=== setup_shuffle_lab: DONE (meshes=%d, catalog=%s) ===" % (
        len(meshes), "ok" if asset else "FAILED"))


main()
