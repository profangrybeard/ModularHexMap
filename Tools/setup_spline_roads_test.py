# setup_spline_roads_test.py — drive ground-only spline-road review on ShuffleLab.
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_spline_roads_test.py"
#
# Imports SM_RoadSeg + SM_GroundHex, puts the generator in GROUND-ONLY mode (plain hex per cell,
# no building/road tiles), applies a parkable-blocks Growth starting set, rolls, and builds the
# curved spline roads from it. Requires the C++ (BuildSplineRoads + bGroundOnly) COMPILED first.
# Tune the Growth params live in the editor afterwards (Randomize -> Build Spline Roads).

import unreal

MAP  = "/Game/Maps/ShuffleLab"
SRC  = r"C:/SCAD/_projects/ModularHexMap/Content/HexTiles/Source"
DEST = "/Game/HexTiles"

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
tools = unreal.AssetToolsHelpers.get_asset_tools()


def import_mesh(name):
    t = unreal.AssetImportTask()
    t.filename = "%s/%s.glb" % (SRC, name)
    t.destination_path = DEST
    t.automated = True
    t.replace_existing = True
    t.save = True
    tools.import_asset_tasks([t])
    for p in unreal.EditorAssetLibrary.list_assets(DEST, recursive=True):
        a = unreal.EditorAssetLibrary.load_asset(p)
        if isinstance(a, unreal.StaticMesh) and a.get_name() == name:
            return a
    return None


def main():
    log("=== setup_spline_roads_test: start ===")
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.load_level(MAP)

    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    gen = None
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.HexShuffleGenerator):
            gen = a
            break
    if not gen:
        err("no HexShuffleGenerator in ShuffleLab")
        return

    road = import_mesh("SM_RoadSeg")
    ground = import_mesh("SM_GroundHex")
    if not road or not ground:
        err("missing SM_RoadSeg or SM_GroundHex")
        return
    gen.set_editor_property("road_segment_mesh", road)
    gen.set_editor_property("ground_mesh", ground)
    gen.set_editor_property("ground_only", True)

    # Parkable-blocks starting set (tune live from here).
    g = gen.get_editor_property("growth")
    g.set_editor_property("road_budget", 22)
    g.set_editor_property("branch_chance", 0.10)
    g.set_editor_property("artery_fork_chance", 0.12)
    g.set_editor_property("straight_bias", 0.72)
    g.set_editor_property("straight_decay", 0.8)
    gen.set_editor_property("growth", g)

    try:
        gen.recalibrate()
        gen.randomize()
        gen.build_spline_roads()
    except Exception as e:
        err("drive failed: " + str(e))
        return

    les.save_current_level()
    warn("=== setup_spline_roads_test: done ===")


main()
