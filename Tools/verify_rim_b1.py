# verify_rim_b1.py — the Rim gate (GUI editor one-shot):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/verify_rim_b1.py"
#
# Three layers of teeth (each added after a failure the previous layer missed):
#   1. COUNTS  — rim 42/42, bridges == mask-derived exits, souls == 120.
#   2. TRUST   — hard-abort if calibration is distrusted (counts can't see that
#                every yaw silently fell back to authored guesses).
#   3. ORIENTATION — for EVERY placed rim instance, read its actual yaw and
#                prove the measured RimKey lands on the station's inward edge
#                (counts and trust together still couldn't see a wrong rotation
#                convention or a bad inward pick — 2026-06-12, twice).
import math
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


def prop(obj, names, default=None):
    for n in names:
        try:
            return obj.get_editor_property(n)
        except Exception:
            continue
    return default


gen.recalibrate()
if not prop(gen, ("b_calibrated", "bCalibrated", "calibrated")):
    unreal.log_error("[RimB1] CALIBRATION DISTRUSTED — every placement would be a "
                     "yaw guess. ABORT.")
    raise SystemExit

RIM_MESHES = {"T_rim_water_a", "T_rim_water_b", "T_rim_water_c",
              "T_rim_water_wide", "T_rim_bridge"}
EXIT_MESHES = {"T_rim_bridge"}
DQ = [(0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1), (1, 0)]   # HexCoordinates.h
RADIUS_UU = 1000.0


def world_xy(q, r):
    inr = RADIUS_UU * 0.86602540378
    return (1.5 * RADIUS_UU * q, inr * q + 2.0 * inr * r)


def hexdist(q, r):
    return (abs(q) + abs(-q - r) + abs(r)) // 2


def rot6(mask, r):
    r %= 6
    return ((mask << r) | (mask >> (6 - r))) & 0x3F


def inward_edge(q, r):
    """WORLD-distance pick — mirrors BuildRim exactly (hex distance ties on
    side stations and a tie-break skews the tile 60 degrees)."""
    best_d, best = 1e30, 0
    for e in range(6):
        nx, ny = world_xy(q + DQ[e][0], r + DQ[e][1])
        d = nx * nx + ny * ny
        if d < best_d:
            best_d, best = d, e
    return best


radius = prop(gen.get_editor_property("growth"), ("radius", "Radius"))
b_invert = bool(prop(gen, ("b_invert_yaw_shift", "bInvertYawShift"), False))

# mesh name -> the tile's FLANK-RULE reference edge, derived from the catalog's
# authored water mask (set to the measured pattern, so this matches what the
# engine derives from TileRealWaterMask). The flank rule: two seam-crossing
# water bits flank the true inward edge — transform-invariant ground truth,
# unlike the key marker (which the engine and gate trusted in lockstep while
# both were uniformly wrong).
tile_set = gen.get_editor_property("tile_set")
mesh_ref = {}
for t in tile_set.get_editor_property("tiles"):
    m = t.get_editor_property("mesh")
    mm = m.get_asset() if hasattr(m, "get_asset") else m
    if not mm:
        continue
    wm = int(t.get_editor_property("water_mask")) & 0x3F
    bits = [e for e in range(6) if wm & (1 << e)]
    ref = None
    if len(bits) == 2:
        gap = (bits[1] - bits[0]) % 6
        if gap == 2:
            ref = (bits[0] + 1) % 6
        elif gap == 4:
            ref = (bits[1] + 1) % 6
    if ref is not None:
        mesh_ref[mm.get_name()] = ref

# ring stations + their inward edges (fixed geometry, destiny-independent)
stations = {}
ring = (radius or 6) + 1
for q in range(-ring, ring + 1):
    for r in range(-ring, ring + 1):
        if hexdist(q, r) == ring:
            stations[(round(world_xy(q, r)[0]), round(world_xy(q, r)[1]))] = inward_edge(q, r)

fails = 0
for i in range(N_SEEDS):
    gen.build_from_seed(BASE + i)
    net = gen.get_editor_property("last_network")
    cells = list(getattr(net, "cells", None) or net.get_editor_property("cells"))

    exp_exits = exp_mouths = 0
    road_edge = {}    # station world key -> the edge its bridge must face
    for c in cells:
        ax = c.get_editor_property("axial")
        if hexdist(ax.x, ax.y) != radius:
            continue
        rm = int(c.get_editor_property("road_mask"))
        wm = int(c.get_editor_property("water_mask"))
        for e in range(6):
            sq, sr = ax.x + DQ[e][0], ax.y + DQ[e][1]
            if hexdist(sq, sr) <= radius:
                continue
            if rm & (1 << e):
                exp_exits += 1
                sx, sy = world_xy(sq, sr)
                road_edge[(round(sx), round(sy))] = (e + 3) % 6
            if wm & (1 << e):
                exp_mouths += 1

    total = exits = orient_bad = 0
    for comp in gen.get_components_by_class(unreal.InstancedStaticMeshComponent):
        m = comp.get_editor_property("static_mesh")
        if not m or m.get_name() not in RIM_MESHES:
            continue
        name = m.get_name()
        ref = mesh_ref.get(name)
        for j in range(comp.get_instance_count()):
            xf = comp.get_instance_transform(j, True)
            loc = xf.translation
            wkey = (round(loc.x), round(loc.y))
            st = stations.get(wkey)
            if st is None:
                orient_bad += 1
                continue
            total += 1
            if name in EXIT_MESHES:
                exits += 1
            # Bridges face their road; everyone else faces the geometric inward —
            # the SAME rule BuildRim applies, checked via the flank-rule reference.
            expect = road_edge.get(wkey, st)
            k = int(round(((xf.rotation.rotator().yaw % 360) + 360) % 360 / 60.0)) % 6
            rot = (6 - k) % 6 if b_invert else k
            if ref is None or not (rot6(1 << ref, rot) & (1 << expect)):
                orient_bad += 1

    souls = gen.get_editor_property("souls")
    ok = (total == 42 and exits == exp_exits and exp_mouths == 2
          and orient_bad == 0 and souls == 120)
    if not ok:
        fails += 1
        unreal.log_error(
            "[RimB1] seed=%d FAIL: rim=%d/42 bridges=%d (exp %d) river-bits=%d "
            "(exp 2) BAD-ORIENT=%d souls=%d"
            % (BASE + i, total, exits, exp_exits, exp_mouths, orient_bad, souls))
    else:
        unreal.log("[RimB1] seed=%d ok: rim=42 bridges=%d orient=42/42 souls=120"
                   % (BASE + i, exits))

if fails == 0:
    unreal.log_warning("=== verify_rim_b1: ALL PASS (%d seeds — counts, trust, "
                       "ORIENTATION) ===" % N_SEEDS)
else:
    unreal.log_error("=== verify_rim_b1: %d/%d seeds FAILED ===" % (fails, N_SEEDS))
