# _make_reference_rolls.py — one-shot (GUI editor): find seeds whose destinies land
# nearest blank ≈ 30 / 45 / 60 and SaveRoll each, so the director can walk them and
# pick the blank-max clamp (Rivers/"too much nothing" layer 2). Logs the mapping.
import unreal
import roll_diagnostics as rd

TARGETS = [30, 45, 60]

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = next((a for a in eas.get_all_level_actors()
            if a.get_class().get_name() == "HexShuffleGenerator"), None)
if gen is None:
    unreal.log_error("[RefRolls] no HexShuffleGenerator")
    raise SystemExit

growth = gen.get_editor_property("growth")
core = rd._build_core_cells(gen)
axials = rd._core_axial_set(core)

best = {t: (None, 10 ** 9) for t in TARGETS}   # target -> (seed, |blank - target|)
for seed in range(1, 600):
    net = unreal.HexMapGrowthLibrary.grow_road_network(growth, core, seed)
    buckets, _c, _u = rd._bucket_cells(list(rd._sf(net, "cells")), axials)
    blank = buckets.get(0, 0)
    for t in TARGETS:
        if abs(blank - t) < best[t][1]:
            best[t] = (seed, abs(blank - t), blank)

gen.recalibrate()
for t in TARGETS:
    seed, _d, blank = best[t][0], best[t][1], best[t][2]
    gen.build_from_seed(seed)
    gen.save_roll()
    unreal.log_warning("[RefRolls] target %d -> seed %d (blank=%d) saved as Roll_seed%d"
                       % (t, seed, blank, seed))
unreal.log_warning("=== reference rolls done ===")
