# build_test_map.py
# Headless UE automation: import the Blender-authored hex base, give it walkable
# collision, and assemble a lit Test Map with a PlayerStart so we can stand on it.
#
# Run (editor MUST be closed) via:
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript ^
#       -script="<repo>/Tools/build_test_map.py" -unattended -nosplash -nopause
#
# The Third Person character + GameMode are added by the user in-editor afterwards.

import traceback
import unreal

GLB        = r"C:/SCAD/_projects/ModularHexMap/Content/HexTiles/Source/HexBase.glb"
DEST_PATH  = "/Game/HexTiles"
MAP_PATH   = "/Game/Maps/TestMap"
TARGET_WIDTH_UU = 1000.0   # 10 m point-to-point (5 m radius) in UE units (cm)

log  = unreal.log
warn = unreal.log_warning
err  = unreal.log_error


def find_hex_mesh():
    """Return the already-imported HexBase StaticMesh, scanning if needed.

    NOTE: the glTF Interchange importer syncs the Content Browser, which asserts
    in a Slate-less commandlet. The import was completed in a prior run, so we
    load the existing asset rather than re-importing here.
    """
    for p in unreal.EditorAssetLibrary.list_assets(DEST_PATH, recursive=True):
        a = unreal.EditorAssetLibrary.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            log("Found StaticMesh: {}".format(a.get_path_name()))
            return a
    raise RuntimeError(
        "No StaticMesh under {} — import HexBase.glb in the GUI editor first.".format(DEST_PATH)
    )


def set_walkable_collision(sm):
    """Use complex-as-simple so the exact top face is collidable."""
    bs = sm.get_editor_property("body_setup")
    if bs is None:
        # Force a body setup via the editor subsystem, then refetch.
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        sub.set_convex_decomposition_collisions(sm, 1, 8, 0)
        bs = sm.get_editor_property("body_setup")
    bs.set_editor_property(
        "collision_trace_flag",
        unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
    )
    unreal.EditorAssetLibrary.save_loaded_asset(sm)
    log("Collision set to UseComplexAsSimple.")


def measure_scale(sm):
    """Return the uniform actor scale needed to hit TARGET_WIDTH_UU."""
    b = sm.get_bounds()                      # BoxSphereBounds
    ext = b.box_extent                       # half-extents
    width_x = 2.0 * ext.x
    scale = TARGET_WIDTH_UU / width_x if width_x > 0.01 else 1.0
    log("Imported mesh width X = {:.2f} uu -> actor scale {:.4f}".format(width_x, scale))
    return scale, width_x


def spawn(cls, loc, rot=None):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return eas.spawn_actor_from_class(
        cls,
        unreal.Vector(*loc),
        unreal.Rotator(*(rot or (0.0, 0.0, 0.0))),
    )


def build_map(sm, scale):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    # A prior aborted run may have left an empty TestMap; replace it cleanly.
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.EditorAssetLibrary.delete_asset(MAP_PATH)
        warn("Deleted pre-existing {}".format(MAP_PATH))
    if not les.new_level(MAP_PATH):
        raise RuntimeError("new_level failed for {}".format(MAP_PATH))

    # Hex tile at origin.
    hex_actor = spawn(unreal.StaticMeshActor, (0.0, 0.0, 0.0))
    hex_actor.set_actor_label("HexBase")
    smc = hex_actor.static_mesh_component
    smc.set_static_mesh(sm)
    smc.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    if abs(scale - 1.0) > 0.01:
        hex_actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))

    # Slab is 0.5 m thick; uniform footprint correction keeps it 0.5 m -> 50 uu top.
    top_z = 50.0

    # Lighting / sky.
    sun = spawn(unreal.DirectionalLight, (0.0, 0.0, 600.0), (-45.0, -45.0, 0.0))
    dlc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    dlc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    dlc.set_editor_property("atmosphere_sun_light", True)
    dlc.set_editor_property("intensity", 6.0)

    spawn(unreal.SkyAtmosphere, (0.0, 0.0, 0.0))
    spawn(unreal.ExponentialHeightFog, (0.0, 0.0, 0.0))

    skylight = spawn(unreal.SkyLight, (0.0, 0.0, 300.0))
    slc = skylight.get_component_by_class(unreal.SkyLightComponent)
    slc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    slc.set_editor_property("real_time_capture", True)

    # PlayerStart above the tile center so the character drops onto the top face.
    ps = spawn(unreal.PlayerStart, (0.0, 0.0, top_z + 200.0))
    ps.set_actor_label("PlayerStart")

    les.save_current_level()
    unreal.EditorAssetLibrary.save_directory("/Game/HexTiles", False, True)
    unreal.EditorAssetLibrary.save_directory("/Game/Maps", False, True)
    log("Saved level {} and assets.".format(MAP_PATH))


def main():
    log("=== build_test_map: start ===")
    sm = find_hex_mesh()
    set_walkable_collision(sm)
    scale, width = measure_scale(sm)
    build_map(sm, scale)
    warn("=== build_test_map: DONE (mesh width {:.1f} uu, actor scale {:.3f}) ===".format(width, scale))


try:
    main()
except Exception:
    err("build_test_map FAILED:\n" + traceback.format_exc())
    raise
