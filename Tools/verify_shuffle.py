# verify_shuffle.py — the post-change smoke test. Opens ShuffleLab, forces a fresh
# calibration + a roll, then exercises the diagnostics stack end-to-end:
#   * Recalibrate + Randomize  -> C++ logs measured masks + built/unresolved/souls
#   * diagnose_last_roll       -> reads the placed LastNetwork (not a re-grow)
#   * constrained_randomize    -> BuildFromSeed path + placed-roll re-verification
# Run (GUI editor, one-shot — gotcha #15):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/verify_shuffle.py"
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = None
for a in eas.get_all_level_actors():
    if a.get_class().get_name() == "HexShuffleGenerator":
        gen = a
        break

if gen:
    gen.recalibrate()   # forces MeasureCalibration -> logs per-tile measured masks
    gen.randomize()     # builds with the resolved tiles -> logs built/unresolved/souls
    unreal.log_warning("verify_shuffle: souls=%d (expect 120 at Radius=6/CoreRadius=1)"
                       % gen.get_editor_property("souls"))

    import roll_diagnostics
    roll_diagnostics.diagnose_last_roll()
    seed = roll_diagnostics.constrained_randomize("default", max_attempts=100,
                                                  verbose=False)
    unreal.log_warning("verify_shuffle: constrained_randomize -> seed=%s" % seed)
    roll_diagnostics.diagnose_last_roll()
    unreal.log_warning("=== verify_shuffle: done ===")
else:
    unreal.log_error("verify_shuffle: no HexShuffleGenerator in ShuffleLab")
