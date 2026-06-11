# _restore_shot.py — tick-driven proof shot of the restoration loop mid-heal.
# Launch (NOT one-shot — needs frames to render + capture, then self-quits):
#   UnrealEditor.exe <uproject> -ExecCmds="py <repo>/Tools/_restore_shot.py"
# Rolls the destiny (seed 6), restores 45 souls (BFS from the wound), frames the town,
# one console HighResShot, quits. Pop label should read "Pop 46 / 121".
import unreal

S = {"t": 0, "h": None}
RESTORE_N = 45


def _tick(_dt):
    S["t"] += 1
    t = S["t"]
    try:
        if t == 60:
            eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            gen = next((a for a in eas.get_all_level_actors()
                        if a.get_class().get_name() == "HexShuffleGenerator"), None)
            if gen is None:
                unreal.log_error("[RestoreShot] no generator")
                S["t"] = 10000
                return
            gen.set_editor_property("restoration_mode", True)
            gen.recalibrate()
            gen.build_from_seed(6)
            for _ in range(RESTORE_N):
                gen.restore_next()
            unreal.log("[RestoreShot] restored=%d souls=%d"
                       % (len(list(gen.get_editor_property("restored_cells"))),
                          gen.get_editor_property("souls")))
        if t == 140:
            ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            ues.set_level_viewport_camera_info(
                unreal.Vector(0.0, -17500.0, 12500.0),
                unreal.Rotator(roll=0.0, pitch=-40.0, yaw=90.0))
        if t == 240:
            unreal.SystemLibrary.execute_console_command(None, "HighResShot 2400x1350")
        if t >= 460:
            if S["h"] is not None:
                unreal.unregister_slate_post_tick_callback(S["h"])
                S["h"] = None
            unreal.SystemLibrary.quit_editor()
    except Exception as e:
        unreal.log_error("[RestoreShot] tick error: %s" % e)
        if S["h"] is not None:
            unreal.unregister_slate_post_tick_callback(S["h"])
            S["h"] = None
        unreal.SystemLibrary.quit_editor()


S["h"] = unreal.register_slate_post_tick_callback(_tick)
unreal.log("[RestoreShot] armed")
