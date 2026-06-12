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
import json
import math
import os
import unreal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = REPO + "/Content/_project/HexTiles/Source"
DEST = "/Game/_project/HexTiles/Scenery"
TAG  = "RimScenery"

log, warn = unreal.log, unreal.log_warning
eal = unreal.EditorAssetLibrary

NAMES = ["T_range_a", "T_range_b", "T_range_c"]   # the water lives in the rim tiles now

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

# All transforms come from Tools/scenery_table.json — the ONE source of truth
# shared with the eye-height gate (render_eyeline.py). Table units: METERS and
# unitless scale. The glTF importer already converted Blender meters to UE
# centimeters (every street tile proves it: scale 1.0 = a perfect 10 m hex), so
# scale passes through UNTOUCHED — positions alone convert m -> uu (x100).
# (2026-06-12 units bug: an extra x100 on scale made 17 km ridges. Never again.)
with open(os.path.join(REPO, "Tools", "scenery_table.json")) as f:
    table = json.load(f)

for row in table["range"]:
    rad = math.radians(float(row["heading_deg"]))
    radius_uu = float(row["radius_m"]) * 100.0
    loc = unreal.Vector(radius_uu * math.cos(rad), radius_uu * math.sin(rad), 0.0)
    spawn(row["mesh"], loc, float(row["heading_deg"]) + 90.0, float(row["scale"]))
RANGE_TABLE = table["range"]   # for the count in the log line below

# The retired waterway-loop asset leaves with its actor (Ringwater ruling:
# the water lives in the rim tiles now).
old_ww = DEST + "/T_waterway"
if eal.does_directory_exist(old_ww):
    if eal.delete_directory(old_ww):
        log("[Scenery] deleted retired %s" % old_ww)

les.save_current_level()
log("[Scenery] placed %d range instances; ShuffleLab saved" % len(RANGE_TABLE))
warn("=== setup_scenery: done — the Range stands ===")
