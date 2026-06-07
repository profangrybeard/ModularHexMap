"""init_unreal.py - auto-runs at editor startup (Content/Python is on UE's sys.path by default).

Heads-up: every UE plugin can ship its own `init_unreal.py` and they all live under
the same module name. `import init_unreal` from the Python console will resolve to
whichever wins on `sys.path` (often *not* ours). For that reason, all real work
lives in uniquely-named modules — this file just routes startup into them.

Defensive: any failure here is logged and swallowed so it can never block startup.
If the LevelEditor Tools menu isn't ready when Python initialises (the usual cause
of "my entries aren't showing up"), we retry every slate tick until it appears.

To re-register the menu by hand without restarting Unreal:
  import hexmap_menus, importlib; importlib.reload(hexmap_menus); hexmap_menus.register()

Output Log fallbacks (always work, no menu needed):
  import roll_diagnostics;  roll_diagnostics.diagnose_last_roll()
  import roll_diagnostics;  roll_diagnostics.run_roll_sweep(n=200, base_seed=0)
"""
import unreal

# Slate-tick retry state — cap so we don't tick forever if registration is broken.
_TICK_HANDLE = None
_TICK_COUNT = 0
_MAX_TICKS = 600  # ~10 s at 60 fps


def _try_register():
    try:
        import hexmap_menus  # uniquely-named — no plugin collision
        return hexmap_menus.register()
    except Exception as exc:
        unreal.log_warning("[HexTiles] hexmap_menus.register() raised: %s" % exc)
        return False


def _on_tick(_delta_seconds):
    global _TICK_HANDLE, _TICK_COUNT
    _TICK_COUNT += 1
    succeeded = _try_register()
    if succeeded or _TICK_COUNT >= _MAX_TICKS:
        if _TICK_HANDLE is not None:
            unreal.unregister_slate_post_tick_callback(_TICK_HANDLE)
            _TICK_HANDLE = None
        if not succeeded and _TICK_COUNT >= _MAX_TICKS:
            unreal.log_warning(
                "[HexTiles] gave up waiting for Tools menu after %d ticks. "
                "Output Log fallback: import roll_diagnostics; "
                "roll_diagnostics.diagnose_last_roll()" % _TICK_COUNT
            )


try:
    if not _try_register():
        # Tools menu not ready yet — common when Python startup races the
        # LevelEditor module load. Subscribe to slate ticks and retry each frame.
        _TICK_HANDLE = unreal.register_slate_post_tick_callback(_on_tick)
        unreal.log(
            "[HexTiles] Tools menu not ready at startup; retrying on slate tick."
        )
except Exception as exc:
    unreal.log_warning(
        "[HexTiles] startup hook failed: %s "
        "(fallback: import roll_diagnostics; roll_diagnostics.diagnose_last_roll())" % exc
    )
