# wire_core_into_shufflelab.py  (GUI editor one-shot)
# Import the 13 (2x, pit-void) core tiles, rebuild DA_HexCoreLayout, recolor their borders,
# assign the core to the EXISTING ShuffleLab generator (was None), and roll.
#   UnrealEditor.exe <uproject> -ExecutePythonScript="Tools/wire_core_into_shufflelab.py"
import os, json, unreal

REPO      = r"C:/SCAD/_projects/ModularHexMap"
SRC       = REPO + "/Content/HexTiles/Source"
CORE_DEST = "/Game/HexTiles/Core"
DATA_DIR  = "/Game/Data"
CORE_DA   = "DA_HexCoreLayout"
MAP_PATH  = "/Game/Maps/ShuffleLab"
MANIFEST  = SRC + "/core_layout.json"
BORDER    = unreal.LinearColor(0.015, 0.015, 0.02, 1.0)

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal, mel = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary

layout = json.load(open(MANIFEST))["tiles"]
names = list(layout.keys())

# 1) import core tiles (replace in place, save)
tasks = []
for name in names:
    glb = "%s/%s.glb" % (SRC, name)
    if not os.path.exists(glb):
        warn("missing glb: " + glb); continue
    t = unreal.AssetImportTask()
    t.filename = glb; t.destination_path = CORE_DEST
    t.automated = True; t.replace_existing = True; t.save = True
    tasks.append(t)
tools.import_asset_tasks(tasks)
log("imported %d core tiles" % len(tasks))

# 2) collision + border recolor on the core assets
meshes = {}
for p in eal.list_assets(CORE_DEST, recursive=True):
    a = eal.load_asset(p)
    if isinstance(a, unreal.StaticMesh) and a.get_name() in names:
        bs = a.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag",
                                   unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_loaded_asset(a, only_if_is_dirty=False)
        meshes[a.get_name()] = a
    elif isinstance(a, unreal.MaterialInstanceConstant) and "TileBorder" in p:
        for pn in ("baseColorFactor", "BaseColorFactor", "Base Color", "baseColor"):
            try: mel.set_material_instance_vector_parameter_value(a, pn, BORDER)
            except Exception: pass
        eal.save_loaded_asset(a, only_if_is_dirty=False)
log("core meshes=%d/%d" % (len(meshes), len(names)))

# 3) (re)build DA_HexCoreLayout — update in place if it already exists
full = DATA_DIR + "/" + CORE_DA
core_da = eal.load_asset(full) if eal.does_asset_exist(full) else None
if core_da is None:
    fac = unreal.DataAssetFactory()
    try: fac.set_editor_property("data_asset_class", unreal.HexCoreLayout)
    except Exception: pass
    core_da = tools.create_asset(CORE_DA, DATA_DIR, unreal.HexCoreLayout, fac)
cells = []
for name, d in layout.items():
    c = unreal.HexCoreCell()
    c.set_editor_property("axial", unreal.IntPoint(int(d["q"]), int(d["r"])))
    if name in meshes: c.set_editor_property("mesh", meshes[name])
    c.set_editor_property("road_mask", int(d["mask"]))
    cells.append(c)
core_da.set_editor_property("cells", cells)
eal.save_loaded_asset(core_da, only_if_is_dirty=False)
log("DA_HexCoreLayout: %d cells" % len(cells))

# 4) assign to ShuffleLab generator + roll
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level(MAP_PATH)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = next((a for a in eas.get_all_level_actors()
            if isinstance(a, unreal.HexShuffleGenerator)), None)
if not gen:
    err("no HexShuffleGenerator in ShuffleLab")
else:
    gen.set_editor_property("core_layout", core_da)
    gen.set_editor_property("hex_circumradius_uu", 1000.0)
    gen.recalibrate()
    gen.randomize()
    les.save_current_level()
    warn("=== wire_core_into_shufflelab: done (core assigned, rolled) ===")
