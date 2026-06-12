# setup_scenery.py — one-shot UE wiring for the off-grid bowl scenery (GUI editor;
# glTF import asserts headless — Resistance #1):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_scenery.py"
#
# Imports T_waterway + T_range_a/b/c to /Game/_project/HexTiles/Scenery, then
# spawns them in ShuffleLab as tagged StaticMeshActors: the waterway ONCE at the
# origin (the ring is destiny-independent — river mouths open into it wherever
# they land), the Range as ~9 instances around the bowl at varied yaw/radius/
# scale (deterministic table, no RNG). Idempotent: previously-tagged actors are
# destroyed first. Saves the level.
import math
import os
import unreal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = REPO + "/Content/_project/HexTiles/Source"
DEST = "/Game/_project/HexTiles/Scenery"
TAG  = "RimScenery"

log, warn = unreal.log, unreal.log_warning
eal = unreal.EditorAssetLibrary

NAMES = ["T_waterway", "T_range_a", "T_range_b", "T_range_c"]

# 1) import
tools = unreal.AssetToolsHelpers.get_asset_tools()
tasks = []
for n in NAMES:
    glb = os.path.join(SRC, n + ".glb")
    if not os.path.exists(glb):
        warn("[Scenery] missing glb: " + glb)
        continue
    t = unreal.AssetImportTask()
    t.filename = glb
    t.destination_path = DEST
    t.automated = True
    t.replace_existing = True
    t.save = True
    tasks.append(t)
tools.import_asset_tasks(tasks)
log("[Scenery] imported %d meshes" % len(tasks))

meshes = {}
for p in eal.list_assets(DEST, recursive=True, include_folder=False):
    a = eal.load_asset(p)
    if isinstance(a, unreal.StaticMesh) and a.get_name() in NAMES:
        meshes[a.get_name()] = a

# 2) place in ShuffleLab (replace tagged)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
killed = 0
for a in list(eas.get_all_level_actors()):
    if TAG in [str(t) for t in a.tags]:
        eas.destroy_actor(a)
        killed += 1
log("[Scenery] removed %d previous scenery actors" % killed)

def spawn(mesh_name, loc, yaw_deg, scale):
    m = meshes.get(mesh_name)
    if m is None:
        warn("[Scenery] no mesh %s" % mesh_name)
        return
    a = eas.spawn_actor_from_object(m, loc, unreal.Rotator(0.0, 0.0, yaw_deg))
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    a.tags = [unreal.Name(TAG)]
    a.set_actor_label("Scenery_%s_%d" % (mesh_name, int(yaw_deg)))

# The waterway ring: authored in world meters around the origin -> uu scale 100.
spawn("T_waterway", unreal.Vector(0, 0, 0), 0.0, 100.0)

# The Range: deterministic placement table (radius uu, heading deg, ridge, scale).
# Radii 300-400 m; scales push apparent peaks ~50-120 m; headings stagger so
# silhouettes overlap (the parallax read) with two deliberate gaps (B3 notch
# alignment claims them for the sun path).
RANGE_TABLE = [
    ("T_range_a", 33500.0,   8.0, 100.0),
    ("T_range_b", 36800.0,  52.0, 138.0),
    ("T_range_c", 31800.0,  97.0,  92.0),
    ("T_range_a", 39500.0, 141.0, 156.0),
    ("T_range_c", 34200.0, 188.0, 112.0),
    ("T_range_b", 32400.0, 232.0,  96.0),
    ("T_range_a", 37600.0, 274.0, 144.0),
    ("T_range_b", 40500.0, 318.0, 168.0),
    ("T_range_c", 33900.0, 347.0, 104.0),
]
for mesh_name, radius, heading, scale in RANGE_TABLE:
    rad = math.radians(heading)
    loc = unreal.Vector(radius * math.cos(rad), radius * math.sin(rad), 0.0)
    spawn(mesh_name, loc, heading + 90.0, scale)

les.save_current_level()
log("[Scenery] placed 1 waterway + %d range instances; ShuffleLab saved" % len(RANGE_TABLE))
warn("=== setup_scenery: done — the sandwich has its layers ===")
