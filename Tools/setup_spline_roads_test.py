# setup_spline_roads_test.py — drive the new BuildSplineRoads on ShuffleLab.
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_spline_roads_test.py"
#
# Assigns SM_RoadSeg to the generator, rolls a network, then builds curved spline roads from it
# (one ASplineRoad per traced chain) so the grown network renders as curved London streets over
# the faceted tiles. Requires the new C++ (AHexShuffleGenerator::BuildSplineRoads) COMPILED first.

import unreal

MAP  = "/Game/Maps/ShuffleLab"
SEG  = "/Game/HexTiles/SM_RoadSeg/StaticMeshes/SM_RoadSeg"

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error


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

    mesh = unreal.EditorAssetLibrary.load_asset(SEG)
    if not mesh:
        err("SM_RoadSeg not found at " + SEG)
        return
    gen.set_editor_property("road_segment_mesh", mesh)

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
