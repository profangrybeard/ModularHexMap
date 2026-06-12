"""Waterway-ring generator — the moat at the town's foot (Docs/Rim.md B2).

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_waterway.py

ONE closed ring mesh lofted through all 42 ring-7 stations' inward bands: channel
floor (-2.0), FAR wall (up the hills' side), and the water plane at -0.9 — the
exact river cross-section depths, so the two town-river mouths open into the loop
flush, on any destiny, with zero per-roll scenery changes. The NEAR bank wall is
deliberately absent: ring 6's own slab faces are the town-side bank (and the open
river-mouth channels pass straight through).

Per-tile water was rejected at plan time: the ring turns 60 degrees at six
corners, and per-tile channel continuity would double the rim kit. One loop means
the waterline never jogs. The rim tiles leave their inward BAND_W strip open
(gen_rim_tiles `_notched_prism`); this ring fills all 42 at once.

Geometry math mirrors the engine exactly: WorldXY basis (x = 1.5Rq,
y = inr*q + 2*inr*r) and the geometric inward pick (first direction minimizing
the neighbor's distance-to-origin). Exports T_waterway.glb; placed ONCE at the
origin by Tools/setup_scenery.py. NEVER saves the master.
"""

import os
import sys
import math
import bmesh
import bpy

_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
if _HERE and _HERE not in sys.path:
    sys.path.append(_HERE)

import gen_curved_tiles as _street
import gen_river_tiles as _river
import gen_rim_tiles as _rim
import gen_blank_variants as _blank

R    = _street.R
INR  = _street.INR
TOP  = _street.TOP
RING = 7

AXIAL_DIR = [(0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1), (1, 0)]   # HexCoordinates.h


def world_xy(q, r):
    """Mirror of HexGrid::WorldXY at R=10 m (meters, not uu)."""
    inr = R * 0.86602540378
    return (1.5 * R * q, inr * q + 2.0 * inr * r)


def hexdist(q, r):
    return (abs(q) + abs(-q - r) + abs(r)) // 2


def ring_stations():
    """Ring-7 axials ordered around the loop (standard ring walk)."""
    q, r = AXIAL_DIR[4][0] * RING, AXIAL_DIR[4][1] * RING
    out = []
    for d in range(6):
        for _ in range(RING):
            out.append((q, r))
            q, r = q + AXIAL_DIR[d][0], r + AXIAL_DIR[d][1]
    return out


def band_polyline():
    """Closed polyline through each station's band centre (inward strip middle)."""
    pts = []
    for (q, r) in ring_stations():
        cx, cy = world_xy(q, r)
        best_d, best = 1e18, 0
        for e in range(6):
            nq, nr = q + AXIAL_DIR[e][0], r + AXIAL_DIR[e][1]
            d = hexdist(nq, nr)
            if d < best_d:
                best_d, best = d, e
        ex, ey = world_xy(q + AXIAL_DIR[best][0], r + AXIAL_DIR[best][1])
        ux, uy = ex - cx, ey - cy
        L = math.hypot(ux, uy)
        off = INR - _rim.BAND_W / 2.0
        pts.append((cx + ux / L * off, cy + uy / L * off))
    return pts


def loop_sweep(bm, pts, profile):
    """Sweep a 2D profile (list of (lateral, z)) along a CLOSED polyline. The
    lateral axis points OUTWARD (away from the origin) at every ring point."""
    n = len(pts)
    rings = []
    for i, (x, y) in enumerate(pts):
        ax, ay = pts[(i - 1) % n]
        bx, by = pts[(i + 1) % n]
        tx, ty = bx - ax, by - ay
        L = math.hypot(tx, ty) or 1.0
        px, py = -ty / L, tx / L                  # left perpendicular
        if px * x + py * y < 0:                   # flip so +lateral faces outward
            px, py = -px, -py
        rings.append([bm.verts.new((x + px * lat, y + py * lat, z))
                      for (lat, z) in profile])
    m = len(profile)
    for i in range(n):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(m - 1):
            bm.faces.new([a[k], a[k + 1], b[k + 1], b[k]])


def main():
    _street.reset()
    pts = band_polyline()
    hw = _rim.BAND_W / 2.0
    wz, fz = _river.WATER_Z, _river.FLOOR_Z

    # Channel shell: open near side, floor across, far wall up to ground level.
    shell = [(-hw, fz), (hw, fz), (hw, TOP)]
    bm = bmesh.new()
    loop_sweep(bm, pts, shell)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    base = _blank._new_obj("T_waterway", bm, bpy.data.materials["M_HexGround"])

    # Water plane (inset, the river's -0.9 surface) as a second material part.
    bm = bmesh.new()
    wi = hw - _river.WATER_INSET
    loop_sweep(bm, pts, [(-wi, wz), (wi, wz)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    water = _blank._new_obj("T_waterway_water", bm, _river.water_material())

    bpy.ops.object.select_all(action='DESELECT')
    base.select_set(True)
    water.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()

    path = os.path.join(_street.out_dir(), "T_waterway.glb")
    bpy.ops.object.select_all(action='DESELECT')
    base.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              use_selection=True, export_apply=True,
                              export_yup=True, export_materials='EXPORT')
    print("  T_waterway.glb  %d bytes (%d stations)" % (os.path.getsize(path), len(pts)))
    bpy.data.objects.remove(base, do_unlink=True)


if __name__ == "__main__":
    print("=== gen_waterway: the ring ===")
    main()
    print("=== gen_waterway: done ===")
