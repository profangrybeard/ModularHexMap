"""hexmap_menus.py — ModularHexMap project Tools menu registration.

Owns the registration of three Tools menu entries:
  - Reimport Hex Tiles
  - Diagnose Last Roll
  - Hex Roll Sweep (200 rolls)

Lives in its own module (not in `init_unreal.py`) so it can be reloaded by name
without colliding with the *other* `init_unreal.py` files UE auto-loads from
every plugin's `Content/Python` dir (e.g. IKRig's, which shadows ours on `import
init_unreal`).

To re-register after the editor is fully up:
  import hexmap_menus, importlib; importlib.reload(hexmap_menus); hexmap_menus.register()

Output Log fallbacks (always work, no menu needed):
  import reimport_hextiles;   reimport_hextiles.run()
  import roll_diagnostics;    roll_diagnostics.diagnose_last_roll()
  import roll_diagnostics;    roll_diagnostics.run_roll_sweep(n=200, base_seed=0)
"""
import unreal

_REIMPORT_PY = (
    "import reimport_hextiles, importlib; "
    "importlib.reload(reimport_hextiles); reimport_hextiles.run()"
)
_DIAG_PY = (
    "import roll_diagnostics, importlib; "
    "importlib.reload(roll_diagnostics); roll_diagnostics.diagnose_last_roll()"
)
_SWEEP_PY = (
    "import roll_diagnostics, importlib; "
    "importlib.reload(roll_diagnostics); roll_diagnostics.run_roll_sweep()"
)


def _add_entry(tools_menu, name, label, tooltip, command):
    entry = unreal.ToolMenuEntry(name=name, type=unreal.MultiBlockType.MENU_ENTRY)
    entry.set_label(label)
    entry.set_tool_tip(tooltip)
    entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, "", command)
    tools_menu.add_menu_entry("HexMap", entry)


def register():
    """Register the three Tools menu entries. Returns True on success, False if the
    LevelEditor Tools menu isn't ready yet (caller can retry on tick)."""
    menus = unreal.ToolMenus.get()
    tools_menu = menus.find_menu("LevelEditor.MainMenu.Tools")
    if tools_menu is None:
        return False

    _add_entry(
        tools_menu,
        "ReimportHexTiles",
        "Reimport Hex Tiles",
        "Reimport every /Game/_project/HexTiles static mesh from its .glb source "
        "and re-assert Complex-As-Simple collision.",
        _REIMPORT_PY,
    )
    _add_entry(
        tools_menu,
        "DiagnoseLastRoll",
        "Diagnose Last Roll",
        "Bucket the live HexShuffleGenerator's LastNetwork by canonical road mask "
        "and print a per-necklace histogram to the Output Log.",
        _DIAG_PY,
    )
    _add_entry(
        tools_menu,
        "HexRollSweep",
        "Hex Roll Sweep (200 rolls)",
        "Run 200 pure GrowRoadNetwork rolls using the live generator's Growth params; "
        "print per-necklace stats (mean/std/p95) and write a CSV under Design/Rolls/. "
        "Output Log: roll_diagnostics.run_roll_sweep(n=500, base_seed=42)",
        _SWEEP_PY,
    )

    menus.refresh_all_widgets()
    unreal.log(
        "[HexTiles] registered Tools > Reimport Hex Tiles / Diagnose Last Roll / Hex Roll Sweep"
    )
    return True
