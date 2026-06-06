# roll_and_save.py (GUI editor one-shot) — roll ShuffleLab with the current build, write the
# roll JSON (for analysis) and save the level.
import unreal
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/Maps/ShuffleLab")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = next((a for a in eas.get_all_level_actors()
            if isinstance(a, unreal.HexShuffleGenerator)), None)
if gen:
    gen.set_editor_property("road_segment_mesh", None)
    gen.set_editor_property("ground_only", False)
    gen.recalibrate()
    gen.randomize()
    gen.save_roll()
    seed = gen.get_editor_property("seed")
    unreal.log_warning("=== roll_and_save: done seed=%d ===" % seed)
    les.save_current_level()
else:
    unreal.log_error("roll_and_save: no generator")
