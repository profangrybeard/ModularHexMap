# set_occupancy.py — seed each catalog tile's Occupancy with the default rule
# (6 - roadEdges) * 2, then roll once so the vacancies tally is logged.
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/set_occupancy.py"
import unreal

DA = "/Game/Data/DA_HexTileSet_Streets"
CONFIGS = {
    "blank": [], "deadend": [0], "bend": [0, 1], "curve": [0, 2], "straight": [0, 3],
    "tee": [0, 2, 4], "tee_a": [0, 1, 2], "tee_b": [0, 1, 3], "tee_c": [0, 1, 4],
    "quad": [0, 1, 2, 3], "quad_b": [0, 2, 3, 4], "quad_c": [0, 1, 3, 4],
    "penta": [0, 1, 2, 3, 4], "junction": [0, 1, 2, 3, 4, 5],
}

asset = unreal.load_asset(DA)
tiles = asset.get_editor_property("tiles")
for i in range(len(tiles)):
    e = tiles[i]                                  # copy
    name = str(e.get_editor_property("name"))
    occ = (6 - len(CONFIGS.get(name, []))) * 2
    e.set_editor_property("occupancy", occ)
    tiles[i] = e                                  # write the copy back into the array
asset.set_editor_property("tiles", tiles)
unreal.EditorAssetLibrary.save_loaded_asset(asset)

# read back from the asset to confirm it persisted
for d in asset.get_editor_property("tiles"):
    unreal.log_warning("READBACK %s occ=%d" % (str(d.get_editor_property("name")), d.get_editor_property("occupancy")))
unreal.log_warning("=== occupancy seeded ===")

# roll once so EstimatedVacancies / the label / the log get populated
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/Maps/ShuffleLab")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.HexShuffleGenerator):
        a.recalibrate()
        a.randomize()
        break
unreal.log_warning("=== set_occupancy: done ===")
