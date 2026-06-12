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


def ring_stations(ring):
    q, r = AXIAL_DIR[4][0] * ring, AXIAL_DIR[4][1] * ring
    out = []
    for d in range(6):
        for _ in range(ring):
            out.append((q, r))
            q, r = q + AXIAL_DIR[d][0], r + AXIAL_DIR[d][1]
    return out


def inward_yaw(q, r):
    """Yaw (rad) turning the tile's +Y (edge 0) toward its inward neighbor —
    WORLD-distance pick, in lockstep with BuildRim (hex distance TIES on side
    stations; the tie-break skewed half the ring 60 degrees, 2026-06-12)."""
    cx, cy = world_xy(q, r)
    best_d, best = 1e30, 0
    for e in range(6):
        nx, ny = world_xy(q + AXIAL_DIR[e][0], r + AXIAL_DIR[e][1])
        d = nx * nx + ny * ny
        if d < best_d:
            best_d, best = d, e
    ex, ey = world_xy(q + AXIAL_DIR[best][0], r + AXIAL_DIR[best][1])
    return math.atan2(ey - cy, ex - cx) - math.pi / 2.0


# Transforms come from Tools/scenery_table.json — the SAME file the editor
# setup reads. One table, one set of units (meters + unitless scale): the gate
# and the engine can no longer disagree (the 2026-06-12 x100 lesson).
import json as _json
with open(os.path.join(repo_root(), "Tools", "scenery_table.json")) as _f:
    _table = _json.load(_f)
RANGE_TABLE = [(r["mesh"], float(r["radius_m"]), float(r["heading_deg"]),
                float(r["scale"])) for r in _table["range"]]


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

    # Town stand-in: a HEXAGONAL prism matching the ring's inner boundary (a
    # circle at max radius buried the side stations' water — the inner boundary
    # is a hexagon: corners at ~112.5 m, flats at ~97 m). Vertices point at the
    # corner stations (first corner at -30 deg in this axial basis).
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=112.0, depth=0.65,
                                        location=(0, 0, 0.325),
                                        rotation=(0, 0, math.radians(-30)))
    town = bpy.context.active_object
    town.data.materials.append(grey("M_TownStandin", (0.42, 0.40, 0.38, 1.0)))

    # The two-ring seam: ring 7 land tiles (exit at station 0, river mouths at
    # 10/31) with their half-channel OUTWARD; ring 8 banks with the mirror half
    # INWARD. Authored water edge is 0; ring 7 rotates it outward (+180 from the
    # inward yaw), ring 8 rotates it inward.
    for i, (q, r) in enumerate(ring_stations(7)):
        name = "T_rim_exit7" if i == 0 else (
            "T_rim_river7" if i in (10, 31) else "T_rim_land7")
        x, y = world_xy(q, r)
        place(name, x, y, inward_yaw(q, r) + math.pi)
    for (q, r) in ring_stations(8):
        x, y = world_xy(q, r)
        place("T_rim_bank8", x, y, inward_yaw(q, r))

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


def shoot_plan(label, center_xy, height=90.0):
    """Top-down continuity check — the second read the gate owes the director
    (the Ringwater's waterline must read as ONE body from above)."""
    cam = bpy.data.objects.new("Plan_" + label, bpy.data.cameras.new("P"))
    cam.data.angle = math.radians(70)
    cam.location = (center_xy[0], center_xy[1], height)
    cam.rotation_euler = (0.0, 0.0, math.atan2(center_xy[1], center_xy[0]) + math.pi / 2)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 960, 720
    sc.render.filepath = os.path.join(out_dir(), "Eyeline_%s.png" % label)
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    print("  Eyeline_%s.png" % label)


def main():
    build_world()
    sx, sy = world_xy(*ring_stations(7)[0])
    tun_az = math.degrees(math.atan2(sy - 0, sx - 0))
    shoot("ring4_banks", (40.0, 30.0, ), math.degrees(math.atan2(30.0, 40.0)))
    shoot("ring4_tunnel", (sx * 0.55, sy * 0.55), tun_az)
    shoot("town_center", (0.0, 2.0), 90.0)
    shoot("rim_road", (sx * 0.82, sy * 0.82), tun_az + 38.0)
    shoot_plan("plan_ring", (sx * 0.86, sy * 0.86))


print("=== render_eyeline: the eye-height gate ===")
main()
print("=== render_eyeline: done ===")
