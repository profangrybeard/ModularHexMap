# reimport_tiles.py
# Re-import the 14 street tiles in place (replace_existing) and restore collision.
# Run INSIDE the GUI editor (Slate available; glTF import asserts headless -- gotcha #1):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/reimport_tiles.py"
#
# The DA_HexTileSet_Streets catalog references these StaticMesh assets by object, so
# replacing the meshes in place swaps in the new (curved) geometry with no catalog edit.
# This is one-shot (the editor runs it and exits -- gotcha #15); relaunch to roll, then
# select HexShuffleGenerator -> Recalibrate (re-measures the new road geometry) -> Randomize.

import os
import unreal

REPO = r"C:/SCAD/_projects/ModularHexMap"
SRC  = REPO + "/Content/HexTiles/Source"
DEST = "/Game/HexTiles"
NAMES = ["blank", "deadend", "bend", "curve", "straight", "tee", "tee_a", "tee_b",
         "tee_c", "quad", "quad_b", "quad_c", "penta", "junction"]

log, warn = unreal.log, unreal.log_warning
tools = unreal.AssetToolsHelpers.get_asset_tools()

tasks = []
for name in NAMES:
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
log("reimport_tiles: submitted %d tasks" % len(tasks))

# restore collision = complex-as-simple (reimport resets it -- gotcha #5)
n = 0
for p in unreal.EditorAssetLibrary.list_assets(DEST, recursive=True):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if isinstance(a, unreal.StaticMesh) and a.get_name().startswith("T_street_"):
        bs = a.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag",
                                   unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        unreal.EditorAssetLibrary.save_loaded_asset(a)
        n += 1
warn("=== reimport_tiles: DONE (%d meshes re-imported + collision set) ===" % n)
