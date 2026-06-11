# setup_ghost_material.py — one-shot (GUI editor): create M_GhostTile (translucent,
# unlit, pale) for the restoration loop's unrestored-destiny silhouette, assign it to
# the ShuffleLab generator's GhostMaterial, flip bRestorationMode ON, save the level.
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/setup_ghost_material.py"
import unreal

log, warn = unreal.log, unreal.log_warning
eal = unreal.EditorAssetLibrary
MAT_DIR = "/Game/_project/HexTiles/Materials"
MAT_PATH = MAT_DIR + "/M_GhostTile"

if eal.does_asset_exist(MAT_PATH):
    mat = eal.load_asset(MAT_PATH)
    log("[Ghost] loaded existing M_GhostTile")
else:
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset("M_GhostTile", MAT_DIR, unreal.Material,
                             unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mel = unreal.MaterialEditingLibrary
    col = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -450, 0)
    col.set_editor_property("constant", unreal.LinearColor(0.32, 0.42, 0.52, 1.0))
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -450, 220)
    op.set_editor_property("r", 0.12)
    mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    eal.save_asset(MAT_PATH)
    log("[Ghost] created M_GhostTile (translucent unlit, 12%)")

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = next((a for a in eas.get_all_level_actors()
            if a.get_class().get_name() == "HexShuffleGenerator"), None)
if gen is None:
    unreal.log_error("[Ghost] no HexShuffleGenerator in ShuffleLab")
else:
    gen.set_editor_property("ghost_material", mat)
    gen.set_editor_property("restoration_mode", True)
    les.save_current_level()
    log("[Ghost] generator wired: GhostMaterial set, bRestorationMode ON, level saved")
warn("=== setup_ghost_material: done ===")
