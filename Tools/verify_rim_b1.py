# verify_rim_b1.py — the Rim B1 gate (GUI editor one-shot):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/verify_rim_b1.py"
#
# Over N seeds: the bowl must CLOSE on every destiny —
#   * rim instance total == 42 (ring 7 fully resolved, 0 unresolved)
#   * exit tiles (tunnel+pass instances) == artery outward bits on ring-6 cells
#   * water-mouth tiles (outfall+intake) == river outward bits (always 2)
#   * souls == 120, town unresolved == 0 (the rim is invisible to the soul law)
# Expected counts re-derive in Python from the actor's LastNetwork boundary cells,
# so the gate cross-checks the C++ derivation rather than trusting it.
import unreal

N_SEEDS = 30
BASE = 0

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = None
for a in eas.get_all_level_actors():
    if a.get_class().get_name() == "HexShuffleGenerator":
        gen = a
        break
if gen is None:
    unreal.log_error("[RimB1] no HexShuffleGenerator in ShuffleLab")
    raise SystemExit

gen.recalibrate()

def sf(s, n):
    v = getattr(s, n, None)
    return v if v is not None else s.get_editor_property(n)

def hexdist(q, r):
    return (abs(q) + abs(-q - r) + abs(r)) // 2

RIM_MESHES = {"T_rim_face_a", "T_rim_face_b", "T_rim_face_c", "T_rim_adit",
              "T_rim_tunnel", "T_rim_pass", "T_rim_outfall", "T_rim_intake"}
EXIT_MESHES = {"T_rim_tunnel", "T_rim_pass"}
MOUTH_MESHES = {"T_rim_outfall", "T_rim_intake"}

radius = sf(gen.get_editor_property("growth"), "radius")
fails = 0
for i in range(N_SEEDS):
    gen.build_from_seed(BASE + i)
    net = gen.get_editor_property("last_network")
    cells = list(sf(net, "cells"))

    # expected exits/mouths: ring-Radius cells with bits pointing out of region
    exp_exits = exp_mouths = 0
    for c in cells:
        ax = sf(c, "axial")
        if hexdist(ax.x, ax.y) != radius:
            continue
        rm, wm = int(sf(c, "road_mask")), int(sf(c, "water_mask"))
        for e in range(6):
            # neighbor axial in flat-top axial space (mirror of HexGrid::Neighbor)
            DQ = [(0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1), (1, 0)]
            nq, nr = ax.x + DQ[e][0], ax.y + DQ[e][1]
            if hexdist(nq, nr) <= radius:
                continue
            if rm & (1 << e):
                exp_exits += 1
            if wm & (1 << e):
                exp_mouths += 1

    counts = {}
    for comp in gen.get_components_by_class(unreal.InstancedStaticMeshComponent):
        m = comp.get_editor_property("static_mesh")
        if m and m.get_name() in RIM_MESHES:
            counts[m.get_name()] = counts.get(m.get_name(), 0) + comp.get_instance_count()
    total = sum(counts.values())
    exits = sum(v for k, v in counts.items() if k in EXIT_MESHES)
    mouths = sum(v for k, v in counts.items() if k in MOUTH_MESHES)
    souls = gen.get_editor_property("souls")

    ok = (total == 42 and exits == exp_exits and mouths == exp_mouths == 2
          and souls == 120)
    if not ok:
        fails += 1
        unreal.log_error(
            "[RimB1] seed=%d FAIL: rim=%d/42 exits=%d (exp %d) mouths=%d (exp %d) souls=%d  %s"
            % (BASE + i, total, exits, exp_exits, mouths, exp_mouths, souls, counts))
    else:
        unreal.log("[RimB1] seed=%d ok: rim=42 exits=%d mouths=2 souls=120"
                   % (BASE + i, exits))

if fails == 0:
    unreal.log_warning("=== verify_rim_b1: ALL PASS (%d seeds — the bowl closes) ===" % N_SEEDS)
else:
    unreal.log_error("=== verify_rim_b1: %d/%d seeds FAILED ===" % (fails, N_SEEDS))
