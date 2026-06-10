# setup_pit_core.py
# Run INSIDE the GUI editor (Slate available) so the glTF import doesn't hit the
# headless-commandlet Slate assert (see CLAUDE.md gotcha #1):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_pit_core.py"
#
# Imports the 7 fixed-core tiles (the Pit + 6 ring spokes, per core_layout.json),
# collision = complex-as-simple, then builds a lit PitCoreLab with each tile placed at
# its exact generator coordinate (WorldXY) and a PlayerStart, so you can PIE and WALK
# the core. (The 6 perimeter "valley" tiles were dropped 2026-06-06.)

import os
import json
import math
import unreal

REPO     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # machine-neutral
SRC      = REPO + "/Content/_project/HexTiles/Source"
DEST     = "/Game/_project/HexTiles/Core"
MAP_PATH = "/Game/_project/Maps/PitCoreLab"
MANIFEST = SRC + "/core_layout.json"

CIRC = 1000.0                      # hex circumradius in uu (R = 10 m), matches the generator
INR  = CIRC * math.cos(math.radians(30))

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
tools = unreal.AssetToolsHelpers.get_asset_tools()


def axial_to_world_uu(q, r):
    """Flat-top axial (q, r) -> world XY in uu, matching HexGrid::WorldXY at R=500."""
    return (1.5 * CIRC * q, INR * q + 2.0 * INR * r)


def load_layout():
    """Return {tile_name: (q, r)}. gen_pit_core.py writes {"q":, "r":, "mask":} dicts
    (the mask feeds DA_HexCoreLayout via wire_core_into_shufflelab.py); the original
    [q, r] list shape is still accepted for old manifests."""
    with open(MANIFEST) as f:
        data = json.load(f)
    out = {}
    for name, spec in data["tiles"].items():
        if isinstance(spec, dict):
            out[name] = (spec["q"], spec["r"])
        else:
            out[name] = (spec[0], spec[1])
    return out


def import_tiles(names):
    tasks = []
    for name in names:
        glb = "%s/%s.glb" % (SRC, name)
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


def find_meshes(names):
    found = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST, recursive=True):
        a = unreal.EditorAssetLibrary.load_asset(p)
        if isinstance(a, unreal.StaticMesh) and a.get_name() in names:
            found[a.get_name()] = a
    log("find_meshes: %d / %d" % (len(found), len(names)))
    return found


def set_collision(meshes):
    for m in meshes.values():
        bs = m.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag",
                                   unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        unreal.EditorAssetLibrary.save_loaded_asset(m)
    log("set_collision: complex-as-simple on %d meshes" % len(meshes))


def make_lab(meshes, layout):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.EditorAssetLibrary.delete_asset(MAP_PATH)
    les.new_level(MAP_PATH)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    def spawn(cls, loc, rot=(0, 0, 0)):
        return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))

    # lighting (mirrors setup_shuffle_lab)
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

    # place each tile at its generator coordinate
    placed = 0
    for name, (q, r) in layout.items():
        mesh = meshes.get(name)
        if not mesh:
            warn("no mesh for " + name)
            continue
        x, y = axial_to_world_uu(q, r)
        actor = spawn(unreal.StaticMeshActor, (x, y, 0.0))
        smc = actor.get_component_by_class(unreal.StaticMeshComponent)
        smc.set_static_mesh(mesh)
        actor.set_actor_label(name)
        placed += 1

    # drop-in point above the hub so PIE lands you on the center tile
    spawn(unreal.PlayerStart, (0.0, 0.0, 300.0))
    les.save_current_level()
    log("make_lab: PitCoreLab built, placed %d tiles" % placed)


def main():
    log("=== setup_pit_core: start ===")
    layout = {}
    try:
        layout = load_layout()
    except Exception as e:
        err("load_layout failed: " + str(e)); return
    names = list(layout.keys())
    try:
        import_tiles(names)
    except Exception as e:
        err("import_tiles failed: " + str(e))
    meshes = {}
    try:
        meshes = find_meshes(names)
        set_collision(meshes)
    except Exception as e:
        err("mesh phase failed: " + str(e))
    try:
        make_lab(meshes, layout)
    except Exception as e:
        err("make_lab failed: " + str(e))
    warn("=== setup_pit_core: DONE (meshes=%d/%d) ===" % (len(meshes), len(names)))


main()
