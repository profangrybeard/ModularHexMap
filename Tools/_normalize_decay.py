# _normalize_decay.py — one-shot (GUI editor): pin ShuffleLab's StraightDecay to the
# ruled 0.33 exactly (the Details-panel drag left 0.3464 slider noise), save the map,
# then run the 200-roll sweep so the Baseline anchor == the instance == the C++
# default. Precedent: the 0.216 walk became the 0.22 RiverStraightBias ruling.
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = None
for a in eas.get_all_level_actors():
    if a.get_class().get_name() == "HexShuffleGenerator":
        gen = a
        break
if gen is None:
    unreal.log_error("[NormalizeDecay] no HexShuffleGenerator in ShuffleLab")
else:
    growth = gen.get_editor_property("growth")
    old = growth.get_editor_property("straight_decay")
    growth.set_editor_property("straight_decay", 0.33)
    gen.set_editor_property("growth", growth)
    unreal.log_warning("[NormalizeDecay] straight_decay %.4f -> 0.33" % old)
    les.save_current_level()
    unreal.log_warning("[NormalizeDecay] ShuffleLab saved")

    import roll_diagnostics
    roll_diagnostics.run_roll_sweep(n=200, base_seed=0)
    unreal.log_warning("=== normalize_decay: done ===")
