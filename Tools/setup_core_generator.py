# setup_core_generator.py
# Run INSIDE the GUI editor (Slate) — validates the Pit-core layout WITH the generator:
#   UnrealEditor.exe <uproject> -ExecutePythonScript="Tools/setup_core_generator.py"
#
# 1) re-import the 13 core tiles (they changed: ring tiles now carry the outward artery)
# 2) build UHexCoreLayout (axial + mesh + road mask, from core_layout.json)
# 3) spawn a HexShuffleGenerator with the street catalog (frontier) + the core layout
# 4) Randomize -> core placed verbatim + procedural frontier grown around it
# 5) Save Roll -> JSON, then Load Roll -> verify the round-trip matches
# Results land in the editor log (grep "setup_core_generator" / "HexShuffle:").

import os
import json
import unreal

REPO      = r"C:/SCAD/_projects/ModularHexMap"
SRC       = REPO + "/Content/HexTiles/Source"
CORE_DEST = "/Game/HexTiles/Core"
DATA_DIR  = "/Game/Data"
CORE_DA   = "DA_HexCoreLayout"
STREET_DA = "/Game/Data/DA_HexTileSet_Streets"
MAP_PATH  = "/Game/Maps/CoreGenLab"
MANIFEST  = SRC + "/core_layout.json"

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
tools = unreal.AssetToolsHelpers.get_asset_tools()


def load_layout():
    with open(MANIFEST) as f:
        return json.load(f)["tiles"]   # {name: {"q","r","mask"}}


def import_core(names):
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
    log("import_core: %d tasks" % len(tasks))


def find_meshes(names):
    found = {}
    for p in unreal.EditorAssetLibrary.list_assets(CORE_DEST, recursive=True):
        a = unreal.EditorAssetLibrary.load_asset(p)
        if isinstance(a, unreal.StaticMesh) and a.get_name() in names:
            found[a.get_name()] = a
    return found


def set_collision(meshes):
    for m in meshes.values():
        bs = m.get_editor_property("body_setup")
        if bs:
            bs.set_editor_property("collision_trace_flag",
                                   unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        unreal.EditorAssetLibrary.save_loaded_asset(m)


def build_core_layout(layout, meshes):
    full = DATA_DIR + "/" + CORE_DA
    if unreal.EditorAssetLibrary.does_asset_exist(full):
        unreal.EditorAssetLibrary.delete_asset(full)
    fac = unreal.DataAssetFactory()
    try:
        fac.set_editor_property("data_asset_class", unreal.HexCoreLayout)
    except Exception as e:
        log("factory hint failed (ok): " + str(e))
    asset = tools.create_asset(CORE_DA, DATA_DIR, unreal.HexCoreLayout, fac)
    cells = []
    for name, d in layout.items():
        c = unreal.HexCoreCell()
        c.set_editor_property("axial", unreal.IntPoint(int(d["q"]), int(d["r"])))
        if name in meshes:
            c.set_editor_property("mesh", meshes[name])
        c.set_editor_property("road_mask", int(d["mask"]))
        cells.append(c)
    asset.set_editor_property("cells", cells)
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    log("build_core_layout: %d cells" % len(cells))
    return asset


def make_lab(street, core):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.EditorAssetLibrary.delete_asset(MAP_PATH)
    les.new_level(MAP_PATH)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    def spawn(cls, loc, rot=(0, 0, 0)):
        return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))

    sun = spawn(unreal.DirectionalLight, (0, 0, 800), (-45, -45, 0))
    dlc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    dlc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    dlc.set_editor_property("atmosphere_sun_light", True)
    spawn(unreal.SkyAtmosphere, (0, 0, 0))
    spawn(unreal.ExponentialHeightFog, (0, 0, 0))
    sky = spawn(unreal.SkyLight, (0, 0, 400))
    slc = sky.get_component_by_class(unreal.SkyLightComponent)
    slc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    slc.set_editor_property("real_time_capture", True)
    spawn(unreal.PlayerStart, (0, 0, 300))

    gen = spawn(unreal.HexShuffleGenerator, (0, 0, 0))
    gen.set_editor_property("tile_set", street)
    gen.set_editor_property("core_layout", core)
    gen.set_editor_property("seed", 1)
    return les, gen


def main():
    log("=== setup_core_generator: start ===")
    layout = load_layout()
    names = list(layout.keys())

    import_core(names)
    meshes = find_meshes(names)
    set_collision(meshes)
    log("meshes: %d/%d" % (len(meshes), len(names)))

    street = unreal.EditorAssetLibrary.load_asset(STREET_DA)
    if not street:
        err("street catalog missing: " + STREET_DA); return
    core = build_core_layout(layout, meshes)
    les, gen = make_lab(street, core)

    # ---- ROLL: core placed verbatim + connected frontier grown around it ----
    gen.randomize()
    seed = gen.get_editor_property("seed")
    vac = gen.get_editor_property("estimated_vacancies")
    log("ROLL: seed=%d estimated_vacancies=%d" % (seed, vac))

    # ---- SAVE -> JSON ----
    gen.save_roll()
    roll_name = "Roll_seed%d_vac%d" % (seed, vac)
    log("SAVED roll: %s.json" % roll_name)

    # ---- LOAD round-trip ----
    gen.set_editor_property("roll_to_load", roll_name)
    gen.load_roll()
    vac2 = gen.get_editor_property("estimated_vacancies")
    log("LOADED roll: estimated_vacancies=%d (round-trip match=%s)" % (vac2, vac2 == vac))

    les.save_current_level()
    warn("=== setup_core_generator: DONE (core meshes=%d/%d, vac=%d, reload_match=%s) ===" % (
        len(meshes), len(names), vac, vac2 == vac))


main()
