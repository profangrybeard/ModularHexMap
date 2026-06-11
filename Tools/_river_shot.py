# _river_shot.py — tick-driven proof shot (Docs/Rivers.md "see it in engine").
# Launch (NOT one-shot — the script needs frames to render + capture, then self-quits):
#   UnrealEditor.exe <uproject> -ExecCmds="py <repo>/Tools/_river_shot.py"
#
# Picks a seed whose roll has 2-4 bridges and ONLY census-authored bridge pairs,
# builds it via BuildFromSeed (the validated-seed contract), frames the town, takes
# two HighRes screenshots (Saved/Screenshots/WindowsEditor/), and quits the editor.
import json
import os
import unreal

import roll_diagnostics as rd

REPO = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
KIT = os.path.join(REPO, "Content", "_project", "HexTiles", "Source", "river_kit.json")

_authored = set()
try:
    with open(KIT) as f:
        for t, m in json.load(f)["tiles"].items():
            if m["road_mask"]:
                _authored.add(rd._joint_canonical(m["road_mask"], m["water_mask"]))
except Exception as e:
    unreal.log_warning("[Shot] kit read failed (%s) — pair filter disabled" % e)

S = {"t": 0, "h": None, "seed": None}


def _pick_seed(gen):
    growth = gen.get_editor_property("growth")
    core = rd._build_core_cells(gen)
    axials = rd._core_axial_set(core)
    for seed in range(1, 400):
        net = unreal.HexMapGrowthLibrary.grow_road_network(growth, core, seed)
        cells = list(rd._sf(net, "cells"))
        _wb, bp, wc, bc = rd._water_census(cells, axials)
        if not (1 <= bc <= 4):
            continue
        if _authored and any(p not in _authored for p in bp):
            continue
        unreal.log("[Shot] seed %d: %d river cells, %d bridges, all pairs authored"
                   % (seed, wc, bc))
        return seed
    unreal.log_warning("[Shot] no seed matched the filter; using 1")
    return 1


def _tick(_dt):
    S["t"] += 1
    t = S["t"]
    try:
        if t == 60:
            eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            gen = next((a for a in eas.get_all_level_actors()
                        if a.get_class().get_name() == "HexShuffleGenerator"), None)
            if gen is None:
                unreal.log_error("[Shot] no HexShuffleGenerator in the startup map")
                S["t"] = 10000
                return
            growth = gen.get_editor_property("growth")
            growth.set_editor_property("river_outflow_dir", 4)   # "the player chose west-ish"
            gen.set_editor_property("growth", growth)
            gen.set_editor_property("restoration_mode", False)   # solid dev view for the proof
            gen.recalibrate()
            S["seed"] = _pick_seed(gen)
            gen.build_from_seed(S["seed"])
            unreal.log("[Shot] built seed %s, souls=%d"
                       % (S["seed"], gen.get_editor_property("souls")))
            rd.diagnose_last_roll()
        if t == 140:
            # ONE shot per session is the reliable pattern. Mode by env-ish flag file:
            # default = wide; if Saved/shot_closeup exists -> bridge close-up instead.
            import math
            closeup = os.path.exists(os.path.join(REPO, "Saved", "shot_closeup"))
            ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            if not closeup:
                ues.set_level_viewport_camera_info(
                    unreal.Vector(0.0, -17500.0, 12500.0),
                    unreal.Rotator(roll=0.0, pitch=-40.0, yaw=90.0))
            else:
                eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
                gen = next((a for a in eas.get_all_level_actors()
                            if a.get_class().get_name() == "HexShuffleGenerator"), None)
                net = gen.get_editor_property("last_network")
                circ = float(gen.get_editor_property("hex_circumradius_uu"))
                inr = circ * 0.8660254
                focus = None
                for cell in rd._sf(net, "cells"):
                    if int(rd._sf(cell, "road_mask")) and int(rd._sf(cell, "water_mask")):
                        ax = rd._sf(cell, "axial")
                        focus = (1.5 * circ * ax.x, inr * ax.x + 2.0 * inr * ax.y)
                        break
                if focus:
                    cx, cy = focus
                    px, py, pz = cx - 2400.0, cy - 4000.0, 2600.0
                    yaw = math.degrees(math.atan2(cy - py, cx - px))
                    dist = math.hypot(cx - px, cy - py)
                    pitch = -math.degrees(math.atan2(pz - 150.0, dist))
                    ues.set_level_viewport_camera_info(
                        unreal.Vector(px, py, pz),
                        unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))
                    unreal.log("[Shot] bridge close-up at (%.0f, %.0f)" % (cx, cy))
        if t == 240:
            # Console HighResShot writes Saved/Screenshots/WindowsEditor/HighresScreenshot*.png
            # next frame; AutomationLibrary.take_high_res_screenshot silently no-ops outside
            # the automation framework (verified live).
            unreal.SystemLibrary.execute_console_command(None, "HighResShot 2400x1350")
        if t >= 460:
            unreal.log("[Shot] done; quitting")
            if S["h"] is not None:
                unreal.unregister_slate_post_tick_callback(S["h"])
                S["h"] = None
            unreal.SystemLibrary.quit_editor()
    except Exception as e:
        unreal.log_error("[Shot] tick error: %s" % e)
        if S["h"] is not None:
            unreal.unregister_slate_post_tick_callback(S["h"])
            S["h"] = None
        unreal.SystemLibrary.quit_editor()


S["h"] = unreal.register_slate_post_tick_callback(_tick)
unreal.log("[Shot] armed — rolling at tick 60, shots at 220/400, quit at 520")
