# show_curved_tiles.py
# Configure ShuffleLab to display the BAKED curved tiles cleanly (retire the runtime
# spline overlay from the 2026-06-06 pivot) and roll once. GUI editor one-shot:
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/show_curved_tiles.py"
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/Maps/ShuffleLab")

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = next((a for a in eas.get_all_level_actors()
            if isinstance(a, unreal.HexShuffleGenerator)), None)
if not gen:
    unreal.log_error("show_curved_tiles: no HexShuffleGenerator in ShuffleLab")
else:
    gen.set_editor_property("road_segment_mesh", None)  # disable retired runtime spline overlay
    gen.set_editor_property("ground_only", False)       # place the real (curved) road tiles
    gen.recalibrate()                                   # re-measure the curved geometry
    gen.randomize()                                     # place the baked curved tiles
    les.save_current_level()
    unreal.log_warning("=== show_curved_tiles: done (overlay off, curved tiles placed) ===")
