"""Curved street-tile generator — per-tile spline-smoothed roads (the 2026-06-06 pivot).

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_curved_tiles.py

Supersedes the faceted center->edge arms in gen_street_tiles.py. Same 14 road-edge
configs, same boolean-carve pipeline (full-hex flagstone pavement minus a carriageway
channel + a cobble carriageway surface), but the channel CENTRELINE is now smooth:

  * THROUGH-ROUTES (exactly 2 connected edges, not opposite) -> a single CIRCULAR ARC.
    The arc centre is the intersection of the two edges' supporting lines; the radius is
    the distance from there to each edge midpoint. Because the centre lies ON each edge's
    line, the radius to the midpoint runs ALONG the edge -> the road meets the edge exactly
    perpendicular at its midpoint (the anchor contract) for free. Adjacent tiles therefore
    join C1-smooth across the shared edge while staying perfectly modular.
      - bend (0,1): centre = shared hex vertex, r = 2.5  (tight 120deg turn)
      - curve (0,2): centre off-tile,          r = 7.5  (wide 60deg turn)
  * STRAIGHT (2 opposite edges): the edge lines are parallel -> a straight line through centre.
  * DEADEND (1 edge) and JUNCTIONS (3-6 edges): radial arms from centre to each edge midpoint.
    A radial arm already meets its edge perpendicular (anchor satisfied), and an angular
    meeting at the centre is CORRECT for an endpoint / intersection. Only through-routes
    needed smoothing; junctions stay as a per-tile intersection.

See Docs/PerTileSplineRoads.md (the pivot) and Source_Art/README.md (the contract).
NEVER saves the master. Re-running is idempotent. Exports T_street_*.glb to Content/HexTiles/Source/.
"""

import os
import math
import bmesh
import bpy

# ---- contract constants (Source_Art/README.md) ----
# SCALE KNOB: R is the single hex-size dial. Street/walk metrics are ABSOLUTE (carriageway 3 m,
# walk ~1 m, curb) so they stay fixed as R grows -- a bigger hex just gains buildable block depth
# and room for the arcs to read as curves. Keep the engine in sync: set the ShuffleLab generator's
# HexCircumradiusUU = R * 100 (R=10 m -> 1000 uu). 2026-06-06: scaled 5 -> 10 (2x) for parkable blocks.
R        = 10.0                             # hex circumradius (m)  [was 5.0]
TOP      = 0.5                              # base slab top = carriageway level
PAVE_H   = 0.15                            # pavement raise / curb height
PAVE_TOP = TOP + PAVE_H
HW       = 1.5                             # carriageway half-width (-> 3 m carriageway, 1 m walk per 5 m edge)
INR      = R * math.cos(math.radians(30))  # edge-midpoint distance (4.33)
EDGE_ANG = {0: 90, 1: 150, 2: 210, 3: 270, 4: 330, 5: 30}

CUT_EXT  = 0.9   # cutter overshoot past each edge (clean carve to the boundary)
CUT_Z0, CUT_Z1 = 0.45, 0.80   # cutter spans the full pavement raise
RD_Z0, RD_Z1   = TOP - 0.02, TOP + 0.01   # thin cobble carriageway surface

# Per-tile boundary lip (metric/debug aid): a grey band hugging the hex perimeter so each
# tile reads as its own cell in the assembled map. Its own material (NOT "Road") so the
# rotation resolver -- which measures M_Road verts at the edge midpoints -- ignores it.
BORDER_W       = 0.12                      # band width (m), inset from the hex edge
BORDER_Z0, BORDER_Z1 = PAVE_TOP, PAVE_TOP + 0.035  # sits on the pavement, a raised lip
BORDER_RGB     = (0.015, 0.015, 0.02, 1.0)  # near-black ink: bold hex outline on the pale blocks

EDGE_SETS = {
    "blank":    [],
    "deadend":  [0],
    "bend":     [0, 1],
    "curve":    [0, 2],
    "straight": [0, 3],
    "tee":      [0, 2, 4],
    "tee_a":    [0, 1, 2],
    "tee_b":    [0, 1, 3],
    "tee_c":    [0, 1, 4],
    "quad":     [0, 1, 2, 3],
    "quad_b":   [0, 2, 3, 4],
    "quad_c":   [0, 1, 3, 4],
    "penta":    [0, 1, 2, 3, 4],
    "junction": [0, 1, 2, 3, 4, 5],
}

CANON = {"Hex_Base", "Camera", "Light",
         "RoadAnchor_0", "RoadAnchor_1", "RoadAnchor_2",
         "RoadAnchor_3", "RoadAnchor_4", "RoadAnchor_5"}


# ---- hex-edge geometry ----
def edge_mid(e):
    a = math.radians(EDGE_ANG[e])
    return (INR * math.cos(a), INR * math.sin(a))

def edge_normal(e):                # outward radial (perpendicular to the edge)
    a = math.radians(EDGE_ANG[e])
    return (math.cos(a), math.sin(a))

def edge_dir(e):                   # along the edge (the edge's supporting-line direction)
    a = math.radians(EDGE_ANG[e])
    return (-math.sin(a), math.cos(a))

def _cross(ax, ay, bx, by):
    return ax * by - ay * bx


def arc_centerline(e0, e1, ext, seg_per_deg=1.0 / 6.0):
    """Circular arc midpoint(e0) -> midpoint(e1), or None if the edge lines are parallel.
    Centre = intersection of the two edge supporting-lines. `ext` extends straight stubs
    outward (along each edge normal, C1 with the arc) past the midpoints for the cutter."""
    p0, p1 = edge_mid(e0), edge_mid(e1)
    d0, d1 = edge_dir(e0), edge_dir(e1)
    denom = _cross(d0[0], d0[1], d1[0], d1[1])
    if abs(denom) < 1e-6:
        return None                          # parallel -> straight (opposite edges)
    t = _cross(p1[0] - p0[0], p1[1] - p0[1], d1[0], d1[1]) / denom
    cx, cy = p0[0] + t * d0[0], p0[1] + t * d0[1]
    r = math.hypot(p0[0] - cx, p0[1] - cy)
    th0 = math.atan2(p0[1] - cy, p0[0] - cx)
    th1 = math.atan2(p1[1] - cy, p1[0] - cx)
    delta = (th1 - th0 + math.pi) % (2 * math.pi) - math.pi   # minor arc (shortest path)
    segs = max(8, int(abs(math.degrees(delta)) * seg_per_deg))
    pts = []
    if ext:                                  # outward stub at the e0 end
        n0 = edge_normal(e0)
        pts.append((p0[0] + n0[0] * ext, p0[1] + n0[1] * ext))
    for s in range(segs + 1):
        th = th0 + delta * (s / segs)
        pts.append((cx + r * math.cos(th), cy + r * math.sin(th)))
    if ext:                                  # outward stub at the e1 end
        n1 = edge_normal(e1)
        pts.append((p1[0] + n1[0] * ext, p1[1] + n1[1] * ext))
    return pts


def centerlines(edges, ext):
    """Return a list of polylines (each a list of (x,y)) for this config's road centre(s).
    ext = overshoot past each edge midpoint (CUT_EXT for the cutter, 0.0 for the surface)."""
    if len(edges) == 2:
        a, b = edges
        arc = arc_centerline(a, b, ext)
        if arc is not None:                  # bend / curve
            return [arc]
        # opposite edges -> straight line through centre
        pa, pb = edge_mid(a), edge_mid(b)
        na, nb = edge_normal(a), edge_normal(b)
        return [[(pa[0] + na[0] * ext, pa[1] + na[1] * ext),
                 (pb[0] + nb[0] * ext, pb[1] + nb[1] * ext)]]
    # deadend / tee / quad / penta / junction -> radial arms centre -> each edge
    out = []
    for e in edges:
        m, n = edge_mid(e), edge_normal(e)
        out.append([(0.0, 0.0), (m[0] + n[0] * ext, m[1] + n[1] * ext)])
    return out


# ---- mesh building ----
def border_material():
    """Grey boundary material. Name deliberately has no 'Road' (resolver keys on that)."""
    m = bpy.data.materials.get("M_TileBorder")
    if m is None:
        m = bpy.data.materials.new("M_TileBorder")
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = BORDER_RGB
        m.use_fake_user = True
    return m


def hex_border(name, mat):
    """A `BORDER_W`-wide raised lip hugging the hex perimeter (full 6-edge outline)."""
    ro = R                                  # outer ring = hex perimeter (vertices at R)
    ri = R * (INR - BORDER_W) / INR         # inner ring inset BORDER_W perpendicular to each edge
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    ob, ot, ib, it = [], [], [], []
    for i in range(6):
        a = math.radians(60 * i)
        c, s = math.cos(a), math.sin(a)
        ob.append(bm.verts.new((ro * c, ro * s, BORDER_Z0)))
        ot.append(bm.verts.new((ro * c, ro * s, BORDER_Z1)))
        ib.append(bm.verts.new((ri * c, ri * s, BORDER_Z0)))
        it.append(bm.verts.new((ri * c, ri * s, BORDER_Z1)))
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new([ot[i], ot[j], it[j], it[i]])      # top of the lip
        bm.faces.new([ib[i], ib[j], ob[j], ob[i]])      # bottom
        bm.faces.new([ob[i], ob[j], ot[j], ot[i]])      # outer wall
        bm.faces.new([it[i], it[j], ib[j], ib[i]])      # inner wall
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    return o


def hex_prism(name, z0, z1, mat):
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    ang = [math.radians(60 * i) for i in range(6)]
    bot = [bm.verts.new((R * math.cos(a), R * math.sin(a), z0)) for a in ang]
    top = [bm.verts.new((R * math.cos(a), R * math.sin(a), z1)) for a in ang]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new([bot[i], bot[j], top[j], top[i]])
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    return o


def sweep_into(bm, pts, half, z0, z1):
    """Sweep a `half`-wide, z0..z1-tall box cross-section along polyline `pts` into bmesh `bm`."""
    N = len(pts)
    rings = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(N - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1.0
        sx, sy = -ty / L, tx / L             # left perpendicular (lateral offset)
        rings.append([bm.verts.new((x + sx * half, y + sy * half, z0)),
                      bm.verts.new((x - sx * half, y - sy * half, z0)),
                      bm.verts.new((x - sx * half, y - sy * half, z1)),
                      bm.verts.new((x + sx * half, y + sy * half, z1))])
    for i in range(N - 1):
        for k in range(4):
            j = (k + 1) % 4
            bm.faces.new([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]])
    bm.faces.new(list(reversed(rings[0])))   # end caps -> closed solid
    bm.faces.new(rings[-1])


def make_tile(name, edges):
    m_road = bpy.data.materials["M_Road"]
    m_pave = bpy.data.materials["M_Pavement"]
    m_grnd = bpy.data.materials["M_HexGround"]

    # base slab built parametrically at R (decoupled from the R=5 master Hex_Base, which we now
    # only load for its shared materials). Bottom-center pivot, z 0..TOP, like the master.
    base = hex_prism("T_street_" + name, 0.0, TOP, m_grnd)

    pave = hex_prism(name + "_pave", TOP, PAVE_TOP, m_pave)
    border = hex_border(name + "_border", border_material())
    objs = [base, pave, border]

    if edges:
        # carriageway channel cutter (overshoots the edges) -> carve the pavement
        cm = bpy.data.meshes.new(name + "_cut")
        bm = bmesh.new()
        for poly in centerlines(edges, CUT_EXT):
            sweep_into(bm, poly, HW, CUT_Z0, CUT_Z1)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(cm)
        bm.free()
        cutter = bpy.data.objects.new(name + "_cut", cm)
        bpy.context.scene.collection.objects.link(cutter)
        md = pave.modifiers.new("carve", 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.object = cutter
        md.solver = 'EXACT'
        md.use_self = True            # arms/arcs can self-overlap at the centre (gotcha #14)
        md.use_hole_tolerant = True
        bpy.ops.object.select_all(action='DESELECT')
        pave.select_set(True)
        bpy.context.view_layer.objects.active = pave
        bpy.ops.object.modifier_apply(modifier="carve")
        bpy.data.objects.remove(cutter, do_unlink=True)

        # cobble carriageway surface (ends exactly at each edge midpoint -> neighbours meet flush)
        rm = bpy.data.meshes.new(name + "_road")
        bm = bmesh.new()
        for poly in centerlines(edges, 0.0):
            sweep_into(bm, poly, HW, RD_Z0, RD_Z1)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(rm)
        bm.free()
        road = bpy.data.objects.new(name + "_road", rm)
        road.data.materials.append(m_road)
        bpy.context.scene.collection.objects.link(road)
        objs.append(road)

    # join into one tile object, drop empty material slots
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    for i in reversed(range(len(base.material_slots))):
        if base.material_slots[i].material is None:
            base.active_material_index = i
            bpy.ops.object.material_slot_remove()

    path = os.path.join(out_dir(), "T_street_%s.glb" % name)
    bpy.ops.object.select_all(action='DESELECT')
    base.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              use_selection=True, export_apply=True,
                              export_yup=True, export_materials='EXPORT')
    bpy.data.objects.remove(base, do_unlink=True)
    return os.path.basename(path), os.path.getsize(path)


def out_dir():
    repo = os.path.dirname(os.path.dirname(os.path.dirname(bpy.data.filepath)))
    d = os.path.join(repo, "Content", "HexTiles", "Source")
    os.makedirs(d, exist_ok=True)
    return d


def reset():
    for o in list(bpy.data.objects):
        if o.name not in CANON:
            bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


def main():
    reset()
    print("=== gen_curved_tiles: writing to %s ===" % out_dir())
    for name, edges in EDGE_SETS.items():
        fn, sz = make_tile(name, edges)
        print("  %-28s %6d bytes  edges=%s" % (fn, sz, edges))
    print("=== gen_curved_tiles: done (%d tiles) ===" % len(EDGE_SETS))


if __name__ == "__main__":
    main()
