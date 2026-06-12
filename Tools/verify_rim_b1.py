# verify_rim_b1.py — the Rim gate (GUI editor one-shot):
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/verify_rim_b1.py"
#
# Four layers of teeth (each added after a failure the previous layers missed):
#   1. COUNTS  — ring 7 42/42 + ring 8 48/48, exits == mask-derived,
#                mouths == 2, souls == 120.
#   2. TRUST   — hard-abort if calibration is distrusted (counts can't see that
#                every yaw silently fell back to authored guesses).
#   3. RING IDENTITY — a ring-7 mesh on a ring-8 station (or vice versa) fails
#                even when the masks happen to fit (land7/bank8 are
#                mask-identical; only the family keeps the rings apart).
#   4. ORIENTATION — for EVERY placed rim instance, read its actual yaw and
#                prove its MEASURED water mask lands on the required seam edge
#                (OUTWARD for ring 7, INWARD for ring 8). Measured, not
#                authored — authored masks differ by the import transform.
#                (Counts and trust together couldn't see a wrong rotation
#                convention or a bad inward pick — 2026-06-12, twice.)
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

# The two-ring seam kit: ring 7 = land7/river7/exit7 (42 stations), ring 8 =
# bank8 (48). The river mouth is a REAL tile again (river7 == 2 every destiny).
RING7_MESHES = {"T_rim_land7", "T_rim_river7", "T_rim_exit7"}
RING8_MESHES = {"T_rim_bank8"}
RIM_MESHES = RING7_MESHES | RING8_MESHES
EXIT_MESHES = {"T_rim_exit7"}
MOUTH_MESHES = {"T_rim_river7"}
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
    """WORLD-distance pick with the SAME 1-uu^2 epsilon tie-break as BuildRim
    (corner-adjacent stations differ by ~2 uu^2 in 1e8 — float order must be
    deterministic and identical on both sides)."""
    best_d, best = 1e30, 0
    for e in range(6):
        nx, ny = world_xy(q + DQ[e][0], r + DQ[e][1])
        d = nx * nx + ny * ny
        if d < best_d - 1.0:
            best_d, best = d, e
    return best


radius = prop(gen.get_editor_property("growth"), ("radius", "Radius"))
b_invert = bool(prop(gen, ("b_invert_yaw_shift", "bInvertYawShift"), False))

# mesh name -> MEASURED water mask (the orientation witness: the measured mask
# IS the actual M_Water geometry — authored masks differ from it by the import
# transform, so asserting with authored flags correct placements as wrong).
tile_set = gen.get_editor_property("tile_set")
real_water = list(prop(gen, ("tile_real_water_mask", "TileRealWaterMask"), []))
mesh_water = {}
for i, t in enumerate(tile_set.get_editor_property("tiles")):
    m = t.get_editor_property("mesh")
    mm = m.get_asset() if hasattr(m, "get_asset") else m
    if mm and i < len(real_water):
        mesh_water[mm.get_name()] = int(real_water[i]) & 0x3F

# both rings' stations: world key -> (inward edge, ring index 0/1)
stations = {}
for ring_idx in (0, 1):
    ring = (radius or 6) + 1 + ring_idx
    for q in range(-ring, ring + 1):
        for r in range(-ring, ring + 1):
            if hexdist(q, r) == ring:
                wx, wy = world_xy(q, r)
                stations[(round(wx), round(wy))] = (inward_edge(q, r), ring_idx)

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

    t7 = t8 = exits = mouths = orient_bad = 0
    for comp in gen.get_components_by_class(unreal.InstancedStaticMeshComponent):
        m = comp.get_editor_property("static_mesh")
        if not m or m.get_name() not in RIM_MESHES:
            continue
        name = m.get_name()
        wmask = mesh_water.get(name, 0)
        for j in range(comp.get_instance_count()):
            xf = comp.get_instance_transform(j, True)
            loc = xf.translation
            st = stations.get((round(loc.x), round(loc.y)))
            if st is None:
                orient_bad += 1
                continue
            inward, ring_idx = st
            if ring_idx == 0:
                t7 += 1
            else:
                t8 += 1
            # Ring identity: a ring-7 mesh on a ring-8 station (or vice versa)
            # is a placement failure even when masks happen to fit.
            if (ring_idx == 0) != (name in RING7_MESHES):
                orient_bad += 1
                if i == 0:
                    unreal.log_error("[RimB1]   WRONG-RING: %s on ring%d at (%d,%d)"
                                     % (name, 7 + ring_idx, round(loc.x), round(loc.y)))
                continue
            if name in EXIT_MESHES:
                exits += 1
            if name in MOUTH_MESHES:
                mouths += 1
            # ORIENTATION: the placed rotation must map the tile's authored
            # water onto the required seam edge — OUTWARD for ring 7, INWARD
            # for ring 8. The water is the content; no proxy can drift.
            need = (inward + 3) % 6 if ring_idx == 0 else inward
            k = int(round(((xf.rotation.rotator().yaw % 360) + 360) % 360 / 60.0)) % 6
            rot = (6 - k) % 6 if b_invert else k
            if not (rot6(wmask, rot) & (1 << need)):
                orient_bad += 1
                if i == 0:   # name the offenders once, with full numbers
                    unreal.log_error(
                        "[RimB1]   offender: %s at (%d,%d) ring%d inward=%d "
                        "need=%d k=%d rot=%d wmask=0x%02X rotated=0x%02X"
                        % (name, round(loc.x), round(loc.y), 7 + ring_idx,
                           inward, need, k, rot, wmask, rot6(wmask, rot)))

    souls = gen.get_editor_property("souls")
    ok = (t7 == 42 and t8 == 48 and exits == exp_exits and mouths == exp_mouths == 2
          and orient_bad == 0 and souls == 120)
    if not ok:
        fails += 1
        unreal.log_error(
            "[RimB1] seed=%d FAIL: r7=%d/42 r8=%d/48 exits=%d (exp %d) mouths=%d "
            "(exp %d==2) BAD-ORIENT=%d souls=%d"
            % (BASE + i, t7, t8, exits, exp_exits, mouths, exp_mouths,
               orient_bad, souls))
    else:
        unreal.log("[RimB1] seed=%d ok: r7=42 r8=48 exits=%d mouths=2 orient-clean souls=120"
                   % (BASE + i, exits))

if fails == 0:
    unreal.log_warning("=== verify_rim_b1: ALL PASS (%d seeds — counts, trust, "
                       "ORIENTATION) ===" % N_SEEDS)
else:
    unreal.log_error("=== verify_rim_b1: %d/%d seeds FAILED ===" % (fails, N_SEEDS))
