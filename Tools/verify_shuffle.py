# verify_shuffle.py — open ShuffleLab, force a fresh calibration + a roll, and let the
# C++ log every measured tile mask so we can confirm the fix from the log.
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/verify_shuffle.py"
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/Maps/ShuffleLab")

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = None
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.HexShuffleGenerator):
        gen = a
        break

if gen:
    gen.recalibrate()   # forces MeasureCalibration -> logs per-tile measured masks
    gen.randomize()     # builds with the resolved tiles -> logs built/unresolved
    unreal.log_warning("=== verify_shuffle: done ===")
else:
    unreal.log_error("verify_shuffle: no HexShuffleGenerator in ShuffleLab")
