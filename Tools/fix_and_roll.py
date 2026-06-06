# fix_and_roll.py  (GUI editor one-shot)
# Force the M_TileBorder material to the bold near-black ink colour (glTF reimport doesn't
# reliably update material factors), then recalibrate + roll ShuffleLab and save.
import unreal

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
TARGET = unreal.LinearColor(0.015, 0.015, 0.02, 1.0)

# --- recolour every M_TileBorder material under the tiles ---
mats = [eal.load_asset(p) for p in eal.list_assets("/Game/HexTiles", recursive=True)
        if "TileBorder" in p]
mats = [m for m in mats if m]
for m in mats:
    cls = m.get_class().get_name()
    if isinstance(m, unreal.MaterialInstanceConstant):
        before = None
        for pname in ("baseColorFactor", "BaseColorFactor", "Base Color", "baseColor"):
            try:
                ok, val = m.get_vector_parameter_value(unreal.Name(pname)), None
            except Exception:
                ok = None
            try:
                mel.set_material_instance_vector_parameter_value(m, pname, TARGET)
            except Exception:
                pass
        eal.save_loaded_asset(m, only_if_is_dirty=False)
        unreal.log_warning("border MIC recoloured: %s" % m.get_path_name())
    elif isinstance(m, unreal.Material):
        try:
            node = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector)
            node.set_editor_property("constant", TARGET)
            mel.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)
            mel.recompile_material(m)
            eal.save_loaded_asset(m, only_if_is_dirty=False)
            unreal.log_warning("border Material recoloured: %s" % m.get_path_name())
        except Exception as e:
            unreal.log_error("border Material recolour failed: %s" % e)
    else:
        unreal.log_warning("border asset (unhandled class %s): %s" % (cls, m.get_path_name()))
unreal.log_warning("fix_and_roll: %d border material(s) processed" % len(mats))

# --- recalibrate + roll + save ---
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/Maps/ShuffleLab")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = next((a for a in eas.get_all_level_actors()
            if isinstance(a, unreal.HexShuffleGenerator)), None)
if gen:
    gen.set_editor_property("road_segment_mesh", None)
    gen.set_editor_property("ground_only", False)
    gen.set_editor_property("hex_circumradius_uu", 1000.0)  # R=10 m -> 1000 uu (2x scale)
    gen.recalibrate()
    gen.randomize()
    les.save_current_level()
    unreal.log_warning("=== fix_and_roll: done ===")
else:
    unreal.log_error("fix_and_roll: no HexShuffleGenerator")
