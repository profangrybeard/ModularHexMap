# _census_run.py — one-shot (GUI editor): run the 200-roll sweep with the river on,
# printing the water-necklace + bridge-pair census that sets the river kit's authoring
# budget (Docs/Rivers.md R1 gate).
import unreal
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")
import roll_diagnostics
roll_diagnostics.run_roll_sweep(n=200, base_seed=0)
unreal.log_warning("=== census run done ===")
