# setup_spline_test.py — prove the spline-mesh road render.
# Run INSIDE the GUI editor (Slate available, glTF import is GUI-only):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_spline_test.py"
#
# Imports SM_RoadSeg (collision = complex-as-simple), then builds a lit /Game/Maps/SplineLab
# with one ASplineRoad bent into an S-curve so we can confirm a smooth London street follows
# the spline (and walk it). Requires the C++ ASplineRoad to be COMPILED first (Build.bat).

import unreal

REPO = r"C:/SCAD/_projects/ModularHexMap"
SRC  = REPO + "/Content/HexTiles/Source"
DEST = "/Game/HexTiles"
MAP  = "/Game/Maps/SplineLab"

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
tools = unreal.AssetToolsHelpers.get_asset_tools()


def import_seg():
    t = unreal.AssetImportTask()
    t.filename = SRC + "/SM_RoadSeg.glb"
    t.destination_path = DEST
    t.automated = True
    t.replace_existing = True
    t.save = True
    tools.import_asset_tasks([t])
    for p in unreal.EditorAssetLibrary.list_assets(DEST, recursive=True):
        a = unreal.EditorAssetLibrary.load_asset(p)
        if isinstance(a, unreal.StaticMesh) and a.get_name() == "SM_RoadSeg":
            bs = a.get_editor_property("body_setup")
            if bs:
                bs.set_editor_property("collision_trace_flag",
                                       unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            unreal.EditorAssetLibrary.save_loaded_asset(a)
            log("import_seg: SM_RoadSeg imported (complex-as-simple)")
            return a
    err("import_seg: SM_RoadSeg not found after import")
    return None


def build_lab(mesh):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
    les.new_level(MAP)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    def spawn(cls, loc, rot=(0, 0, 0)):
        return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))

    sun = spawn(unreal.DirectionalLight, (0.0, 0.0, 800.0), (-45.0, -45.0, 0.0))
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property(
        "mobility", unreal.ComponentMobility.MOVABLE)
    spawn(unreal.SkyAtmosphere, (0.0, 0.0, 0.0))
    spawn(unreal.ExponentialHeightFog, (0.0, 0.0, 0.0))
    sky = spawn(unreal.SkyLight, (0.0, 0.0, 400.0))
    slc = sky.get_component_by_class(unreal.SkyLightComponent)
    slc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    slc.set_editor_property("real_time_capture", True)

    spawn(unreal.PlayerStart, (0.0, 0.0, 200.0))

    road = spawn(unreal.SplineRoad, (0.0, 0.0, 0.0))
    road.set_editor_property("road_segment_mesh", mesh)
    sp = road.spline
    sp.clear_spline_points(False)
    # points ~13 m apart (>= 2 pieces) -> gentle curve, even tiling
    pts = [unreal.Vector(0, 0, 50), unreal.Vector(1200, 600, 50),
           unreal.Vector(2600, -300, 50), unreal.Vector(4000, 500, 50),
           unreal.Vector(5200, 0, 50)]
    for p in pts:
        sp.add_spline_point(p, unreal.SplineCoordinateSpace.LOCAL, False)
    sp.update_spline()
    road.rebuild()
    les.save_current_level()
    log("build_lab: SplineLab built, SplineRoad with %d points" % len(pts))


def main():
    log("=== setup_spline_test: start ===")
    mesh = None
    try:
        mesh = import_seg()
    except Exception as e:
        err("import_seg failed: " + str(e))
    if mesh:
        try:
            build_lab(mesh)
        except Exception as e:
            err("build_lab failed: " + str(e))
    warn("=== setup_spline_test: DONE (mesh=%s) ===" % ("ok" if mesh else "FAILED"))


main()
