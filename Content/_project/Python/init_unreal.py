"""init_unreal.py — auto-runs at editor startup (Content/Python is on the Python path).

Registers a one-click "Reimport Hex Tiles" entry under the main Tools menu that batch-reimports
/Game/HexTiles from the exported .glb sources. Fully defensive: any failure here is logged and
swallowed so it can never block editor startup. If the menu doesn't appear, the reliable fallback
is the Output Log:  import reimport_hextiles; reimport_hextiles.run()
"""
import unreal

_PY = "import reimport_hextiles, importlib; importlib.reload(reimport_hextiles); reimport_hextiles.run()"


def _register_reimport_menu():
    menus = unreal.ToolMenus.get()
    tools_menu = menus.find_menu("LevelEditor.MainMenu.Tools")
    if tools_menu is None:
        unreal.log_warning("[HexTiles] Tools menu not found yet; use the Output Log fallback "
                           "(import reimport_hextiles; reimport_hextiles.run())")
        return
    entry = unreal.ToolMenuEntry(name="ReimportHexTiles",
                                 type=unreal.MultiBlockType.MENU_ENTRY)
    entry.set_label("Reimport Hex Tiles")
    entry.set_tool_tip("Reimport every /Game/HexTiles static mesh from its .glb source "
                       "and re-assert Complex-As-Simple collision")
    entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, "", _PY)
    tools_menu.add_menu_entry("HexMap", entry)
    menus.refresh_all_widgets()
    unreal.log("[HexTiles] registered Tools > Reimport Hex Tiles")


try:
    _register_reimport_menu()
except Exception as exc:
    unreal.log_warning("[HexTiles] menu registration skipped: %s "
                       "(use: import reimport_hextiles; reimport_hextiles.run())" % exc)
