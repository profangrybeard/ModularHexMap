"""render_eyeline.py — THE pre-engine gate for scenery composition (Docs/Rim.md).

    blender --background --factory-startup \
            --python Tools/blender/render_eyeline.py

Born from the B2 revert: the first parallax sandwich read perfectly from the
orbit camera and vanished at street eye height. This tool assembles the world
OUTSIDE the engine — town stand-in disc, the waterway loop, all 42 rim stations
(a representative variant mix at true positions/rotations), both Range rings at
the true placement-table transforms — and renders from EYE HEIGHT (2.4 m) at
street positions. If the Range isn't visible above the rim in these renders,
the composition is wrong and nothing ships to the editor.

Outputs Docs/Images/ContactSheets/Eyeline_*.png. Reads staged .glbs only.
"""

import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)


def repo_root():
    return os.path.dirname(os.path.dirname(HERE))


def src_dir():
    return os.path.join(repo_root(), "Content", "_project", "HexTiles", "Source")


def out_dir():
    d = os.path.join(repo_root(), "Docs", "Images", "ContactSheets")
    os.makedirs(d, exist_ok=True)
    return d


# ---- placement math (mirrors HexCoordinates.h / setup_scenery.py) ----
R, INR = 10.0, 10.0 * 0.86602540378
AXIAL_DIR = [(0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1), (1, 0)]


def world_xy(q, r):
    return (1.5 * R * q, INR * q + 2.0 * INR * r)


def hexdist(q, r):
    return (abs(q) + abs(-q - r) + abs(r)) // 2


def ring_stations(ring=7):
    q, r = AXIAL_DIR[4][0] * ring, AXIAL_DIR[4][1] * ring
    out = []
    for d in range(6):
        for _ in range(ring):
            out.append((q, r))
            q, r = q + AXIAL_DIR[d][0], r + AXIAL_DIR[d][1]
    return out


def inward_yaw(q, r):
    """Yaw (rad) turning the tile's +Y (edge 0) toward its inward neighbor —
    the same geometric first-wins pick the engine uses."""
    cx, cy = world_xy(q, r)
    best_d, best = 10 ** 9, 0
    for e in range(6):
        nq, nr = q + AXIAL_DIR[e][0], r + AXIAL_DIR[e][1]
        d = hexdist(nq, nr)
        if d < best_d:
            best_d, best = d, e
    ex, ey = world_xy(q + AXIAL_DIR[best][0], r + AXIAL_DIR[best][1])
    return math.atan2(ey - cy, ex - cx) - math.pi / 2.0


# Two-ring Range table — keep in lockstep with Tools/setup_scenery.py (meters).
RANGE_TABLE = [
    ("T_range_a", 245.0,  12.0, 0.98), ("T_range_b", 262.0,  58.0, 1.10),
    ("T_range_c", 250.0, 100.0, 0.92), ("T_range_a", 268.0, 152.0, 1.04),
    ("T_range_c", 242.0, 196.0, 0.96), ("T_range_b", 256.0, 238.0, 1.00),
    ("T_range_a", 260.0, 278.0, 1.08), ("T_range_c", 252.0, 336.0, 0.94),
    ("T_range_b", 495.0,  35.0, 2.35), ("T_range_c", 528.0,  80.0, 2.60),
    ("T_range_a", 504.0, 174.0, 2.45), ("T_range_b", 540.0, 218.0, 2.70),
    ("T_range_c", 510.0, 258.0, 2.40), ("T_range_a", 532.0, 352.0, 2.55),
]


_proto = {}


def proto(name):
    """Import each glb once; placements use linked duplicates."""
    if name in _proto:
        return _proto[name]
    path = os.path.join(src_dir(), name + ".glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    ob = new[0]
    ob.location = (10000.0, 10000.0, 0.0)       # park the prototype off-stage
    _proto[name] = ob
    return ob


def place(name, x, y, yaw_rad, scale=1.0, z=0.0):
    src = proto(name)
    ob = src.copy()                              # linked duplicate (shared mesh)
    ob.location = (x, y, z)
    ob.rotation_euler = (0.0, 0.0, yaw_rad)
    ob.scale = (scale, scale, scale)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def grey(name, rgba):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = rgba
    return m


def build_world():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _proto.clear()

    # Town stand-in: a disc at pavement level out to the rim
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=7.0 * 2.0 * INR - INR,
                                        depth=0.65, location=(0, 0, 0.325))
    town = bpy.context.active_object
    town.data.materials.append(grey("M_TownStandin", (0.42, 0.40, 0.38, 1.0)))

    place("T_waterway", 0.0, 0.0, 0.0)

    # Rim ring: representative variant mix at true transforms. Tunnel parked at
    # station 0 (camera looks at it in shot 2); mouths at 10/31; berm clusters
    # roughly every third station; banks elsewhere.
    stations = ring_stations(7)
    for i, (q, r) in enumerate(stations):
        if i == 0:
            name = "T_rim_tunnel"
        elif i == 10:
            name = "T_rim_outfall"
        elif i == 31:
            name = "T_rim_intake"
        elif i % 3 == 1:
            name = "T_rim_berm_a" if i % 2 else "T_rim_berm_b"
        elif i % 7 == 3:
            name = "T_rim_adit"
        else:
            name = "T_rim_bank_a" if i % 2 else "T_rim_bank_b"
        x, y = world_xy(q, r)
        place(name, x, y, inward_yaw(q, r))

    for name, radius, heading, scale in RANGE_TABLE:
        a = math.radians(heading)
        place(name, radius * math.cos(a), radius * math.sin(a),
              a + math.pi / 2.0, scale)

    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 4.5
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(-35))
    bpy.context.scene.collection.objects.link(sun)
    bpy.context.scene.world = bpy.data.worlds.new("W")
    bpy.context.scene.world.use_nodes = True
    bg = bpy.context.scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.65, 0.78, 0.92, 1.0)   # sky placeholder
        bg.inputs[1].default_value = 1.0


def shoot(label, cam_xy, look_azim_deg, fov_deg=70.0):
    cam = bpy.data.objects.new("Cam_" + label, bpy.data.cameras.new("C"))
    cam.data.angle = math.radians(fov_deg)
    az = math.radians(look_azim_deg)
    cam.location = (cam_xy[0], cam_xy[1], 2.4)             # EYE HEIGHT — the law
    cam.rotation_euler = (math.radians(90), 0.0, az + math.radians(90))
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.filepath = os.path.join(out_dir(), "Eyeline_%s.png" % label)
    sc.render.image_settings.file_format = 'PNG'
    try:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception:
        sc.render.engine = 'BLENDER_WORKBENCH'
    bpy.ops.render.render(write_still=True)
    print("  Eyeline_%s.png" % label)


def main():
    build_world()
    # Station 0 sits at axial (7,-7)*? — ring walk starts at AxialDir[4]*7 ->
    # world (105, -60.6); its azimuth from origin:
    sx, sy = world_xy(*ring_stations(7)[0])
    tun_az = math.degrees(math.atan2(sy - 0, sx - 0))
    shoot("ring4_banks", (40.0, 30.0, ), math.degrees(math.atan2(30.0, 40.0)))
    shoot("ring4_tunnel", (sx * 0.55, sy * 0.55), tun_az)
    shoot("town_center", (0.0, 2.0), 90.0)
    shoot("rim_road", (sx * 0.82, sy * 0.82), tun_az + 38.0)


print("=== render_eyeline: the eye-height gate ===")
main()
print("=== render_eyeline: done ===")
