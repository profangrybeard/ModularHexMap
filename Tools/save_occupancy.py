# save_occupancy.py — seed catalog Occupancy and SAVE it, as a clean commandlet so the
# package actually flushes to disk:
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<repo>/Tools/save_occupancy.py" -unattended -nosplash
import unreal

DA = "/Game/_project/Data/DA_HexTileSet_Streets"   # post-`_project` reorg (was /Game/Data/...)
CONFIGS = {
    "blank": [], "deadend": [0], "bend": [0, 1], "curve": [0, 2], "straight": [0, 3],
    "tee": [0, 2, 4], "tee_a": [0, 1, 2], "tee_b": [0, 1, 3], "tee_c": [0, 1, 4],
    "quad": [0, 1, 2, 3], "quad_b": [0, 2, 3, 4], "quad_c": [0, 1, 3, 4],
    "penta": [0, 1, 2, 3, 4], "junction": [0, 1, 2, 3, 4, 5],
}

asset = unreal.load_asset(DA)
tiles = asset.get_editor_property("tiles")
for i in range(len(tiles)):
    e = tiles[i]
    name = str(e.get_editor_property("name"))
    e.set_editor_property("occupancy", (6 - len(CONFIGS.get(name, []))) * 2)
    tiles[i] = e
asset.set_editor_property("tiles", tiles)
ok = unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
unreal.log_warning("SAVE_OCCUPANCY result=%s" % ok)

# prove it from disk by reloading
for d in unreal.load_asset(DA).get_editor_property("tiles"):
    unreal.log_warning("READBACK %s=%d" % (str(d.get_editor_property("name")), d.get_editor_property("occupancy")))
unreal.log_warning("=== save_occupancy done ===")
