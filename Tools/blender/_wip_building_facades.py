"""WIP: single-story building facades that follow the spline-curved roads (2026-06-07).

Run inside the open HexBase.blend GUI session via the Blender MCP (exec the body).
Throwaway TMP_ objects -- never saves the master.

Why this exists: per-hex full-volume gables (the prior `_wip_building_blockout.py`) read
as a field of tents. This iteration is the post-pivot ask: single-story FACADES that
trace the actual splined road centreline, with the 1 m sidewalk preserved between curb
and wall. The roads are curved (gen_curved_tiles.py), so the facade lines must be too
-- we reuse `g.centerlines(...)` verbatim so adjacent tiles' facade endpoints land
exactly at the shared edge midpoint (same C1 modular contract as the road).

Design (signed off 2026-06-07):
  - footprint = hex MINUS the road corridor. The corridor is each centreline polyline
    `.buffer(KEEP_HW = HW + WALK = 2.5 m, cap_style=flat, join_style=mitred)`. Subtract,
    then morph-open at 0.2 m to erase sub-0.4 m flatiron slivers (bend inner corner).
  - Walls: single-story 3.5 m. NO GABLE -- flat roof slab. Gables were the "tents" read.
  - Walls authored as single-faced vertical quads per polygon edge (no boolean -- cheap
    and blockout-correct). Doors are made by SPLITTING the wall into side-panel + lintel
    + side-panel, leaving a 0.9 x 2.1 m gap. Avoids the EXACT-boolean tax + crash risk.
  - Material slots:
      * `M_Building`     -- facade walls (front, along the road corridor).
      * `M_BuildingBack` -- back & side walls (along the hex boundary). Separate slot
        so the engine can later split / hide these to render the "Inset only on
        blank-side" alley behaviour without an explosion of authoring variants.
      * `M_BuildingRoof` -- flat roof slab.
  - Per-edge classification uses the segment-midpoint distance to the hex perimeter:
    < 0.15 m -> back/side (hex-boundary wall); else -> front (road-buffer wall).

Configs in this turn: `straight`, `bend`, `curve`. Skip `junction` (no buildable area).
Defer `deadend`/`tee*`/`quad*`/`penta` until the through-route reads land. Defer the
`blank` cell entirely -- that's the open design problem the prior pause flagged, and
facades don't answer it.

Requires Shapely (installed 2026-06-05).
"""

import bpy, bmesh, math, sys, importlib

TOOLS_DIR = r"C:\SCAD\_projects\ModularHexMap\Tools\blender"
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)
import gen_curved_tiles as g
importlib.reload(g)                            # gotcha #21: live session may hold stale module

from shapely.geometry import Polygon, LineString, Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

# ---- constants ----
R        = g.R                                 # 10.0 m (R=10 contract)
INR      = g.INR                               # apothem (8.66 m)
HW       = g.HW                                # carriageway half-width (1.5 m)
PAVE_TOP = g.PAVE_TOP                          # 0.65 m
WALK     = 1.0                                 # flagstone walk between curb and facade (m)
KEEP_HW  = HW + WALK                           # 2.5 m  carriageway + walk = building-face offset
WALL_H   = 3.5                                 # single-story eaves (m)
ROOF_T   = 0.20                                # flat roof slab thickness (m)
DOOR_W   = 0.9
DOOR_H   = 2.1
OPEN_R   = 0.20                                # morph-open radius (kills sub-0.4 m slivers)
MIT      = 5.0
EDGE_EPS = 0.15                                # tolerance for "this segment lies on a hex edge"

# CORNER pieces (any pair of adjacent road edges sharing a hex vertex) emit NO geometry
# -- they're the user's playground for hand-authored content. Classification still tags
# them so build_tile knows to skip; the inner-bend disc subtraction below still grows
# each corner to ~9 m^2 so there's room to author.

# Inner-bend rule (signed off 2026-06-07): on the INSIDE of every bend (every pair of
# adjacent road edges sharing a hex vertex V), the road corridor's inner edge retreats
# from KEEP_HW to INNER_KEEP_HW. Implementation: subtract a disc of radius
# (arc_r - INNER_KEEP_HW) centred at V from the road corridor. Bend arc radius is R/2.
# Net: the corner garden grows from ~4 m^2 to ~9 m^2 -- big enough to feel like a plot.
INNER_KEEP_HW = HW                             # 1.5 m (carriageway only; no sidewalk inset)
ARC_R         = R / 2                          # 5.0 m -- bend arc radius about the shared vertex
INNER_DISC_R  = ARC_R - INNER_KEEP_HW          # 3.5 m

# Hub keep-out for 3+ road junctions: gen_curved_tiles draws a road hub of radius
# JUNCTION_HUB_R at origin. Pad it by WALK so the buildings give the hub a sidewalk too.
JUNCTION_HUB_R = g.JUNCTION_HUB_R              # 2.25 m
HUB_KEEPOUT_R  = JUNCTION_HUB_R + WALK         # 3.25 m

EDGE_SETS = {
    "straight": [0, 3],
    "bend":     [0, 1],
    "curve":    [0, 2],
    "deadend":  [0],
    "tee":      [0, 2, 4],
    "tee_a":    [0, 1, 2],
    "tee_b":    [0, 1, 3],
    "tee_c":    [0, 1, 4],
    "quad":     [0, 1, 2, 3],
    "quad_b":   [0, 2, 3, 4],
    "quad_c":   [0, 1, 3, 4],
    "penta":    [0, 1, 2, 3, 4],
    # "junction" omitted -- all road, no buildable area.
}


# ---- helpers ----
def reset_tmp():
    for o in list(bpy.data.objects):
        if o.name.startswith("TMP_"):
            bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


def ensure_mat(name, rgba):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgba
        m.use_fake_user = True
    return m


def hexpoly():
    return Polygon([(R * math.cos(math.radians(60 * i)),
                     R * math.sin(math.radians(60 * i))) for i in range(6)])


def adjacent_pairs(edges):
    """Pairs (e0, e1) of road edges that are adjacent on the hex (i.e., share a vertex)."""
    edge_set = set(edges)
    pairs = []
    for e in edges:
        en = (e + 1) % 6
        if en in edge_set:
            pairs.append((e, en))
    return pairs


def shared_vertex_xy(e0, e1):
    """World-XY of the hex vertex shared by adjacent edges e0 and e1.
    The vertex angle is the angular midpoint of the two edge-midpoint angles, with the
    0-deg/360-deg wraparound handled (matters for the e4-e5 / e5-e0 case)."""
    a0, a1 = g.EDGE_ANG[e0], g.EDGE_ANG[e1]
    if abs(a0 - a1) > 180:
        if a0 < a1: a0 += 360
        else:       a1 += 360
    vang = math.radians((a0 + a1) / 2.0)
    return (R * math.cos(vang), R * math.sin(vang))


# ---- footprint ----
def footprints(edges):
    """Hex MINUS road corridor, opened. Returns a list of Shapely Polygons (one per building piece)."""
    fp = hexpoly()
    if edges:
        polylines = g.centerlines(edges, 0.0)
        # Tiny epsilon overshoot at each polyline end so the flat cap clears the hex edge cleanly
        eps = 0.02
        extended = []
        for poly in polylines:
            if len(poly) < 2:
                continue
            (x0, y0), (x1, y1) = poly[0], poly[1]
            dx, dy = x0 - x1, y0 - y1; L0 = math.hypot(dx, dy) or 1.0
            head = (x0 + dx / L0 * eps, y0 + dy / L0 * eps)
            (xa, ya), (xb, yb) = poly[-2], poly[-1]
            dx, dy = xb - xa, yb - ya; L1 = math.hypot(dx, dy) or 1.0
            tail = (xb + dx / L1 * eps, yb + dy / L1 * eps)
            extended.append([head] + list(poly) + [tail])
        corridor = unary_union([LineString(p).buffer(KEEP_HW, cap_style=2, join_style=2,
                                                     mitre_limit=MIT) for p in extended])
        if len(edges) >= 3:                    # hub keep-out so buildings respect the road hub
            corridor = corridor.union(Point(0.0, 0.0).buffer(HUB_KEEPOUT_R, resolution=24))
        # Inner-bend rule: shrink corridor at each shared bend vertex so the corner garden grows.
        for e0, e1 in adjacent_pairs(edges):
            vx, vy = shared_vertex_xy(e0, e1)
            corridor = corridor.difference(Point(vx, vy).buffer(INNER_DISC_R, resolution=32))
        fp = fp.difference(corridor)
    fp = (fp.buffer(-OPEN_R, join_style=2, mitre_limit=MIT)
            .buffer( OPEN_R, join_style=2, mitre_limit=MIT))
    if fp.is_empty:
        return []
    if fp.geom_type == 'Polygon':
        return [fp]
    return [p for p in fp.geoms if p.geom_type == 'Polygon' and p.area > 0.1]


def classify_pieces(edges, pieces):
    """Tag each piece 'garden' (corner piece touching a bend vertex) or 'building'.
    Uses Shapely distance(piece, vertex) < EDGE_EPS as 'piece contains vertex'."""
    bend_pts = [Point(*shared_vertex_xy(e0, e1)) for e0, e1 in adjacent_pairs(edges)]
    out = []
    for pc in pieces:
        kind = 'building'
        for v in bend_pts:
            if pc.distance(v) < EDGE_EPS:
                kind = 'garden'; break
        out.append((pc, kind))
    return out


# ---- per-edge classification ----
HEX_BOUNDARY = hexpoly().exterior   # cached for distance queries


def is_back_segment(p_mid, tol=EDGE_EPS):
    """A segment whose midpoint is on the hex perimeter is back/side (neighbour-shared).
    Everything else came from the road-corridor buffer -> facade (front). `tol` lets
    inset garden polygons relax the threshold by their inset distance."""
    return HEX_BOUNDARY.distance(Point(p_mid)) < tol


# ---- wall builders ----
def add_quad(bm, p0_xy, p1_xy, z0, z1):
    """Add a single vertical quad spanning (p0_xy,z0)..(p1_xy,z1). CCW-from-outside
    vertex order so the normal points away from the polygon interior (which is on the
    LEFT of the (p0 -> p1) direction for a CCW Shapely exterior)."""
    x0, y0 = p0_xy; x1, y1 = p1_xy
    v00 = bm.verts.new((x0, y0, z0))
    v10 = bm.verts.new((x1, y1, z0))
    v11 = bm.verts.new((x1, y1, z1))
    v01 = bm.verts.new((x0, y0, z1))
    return bm.faces.new([v00, v10, v11, v01])


def doors_for_run(L):
    """Door count for a front run of total arc length L (matches gen_buildings.py)."""
    if L < DOOR_W + 0.4: return 0
    if L < 7.0:          return 1
    if L < 25.0:         return 2
    return 3


def _plan_door_ranges(coords):
    """{seg_idx: [(start_in_seg, end_in_seg), ...]} -- doors placed at evenly-spaced
    arc-length positions inside each contiguous front run; doors spanning multiple
    curved sub-segments produce a lintel quad on every overlapped segment."""
    N = len(coords)
    info = []
    for i in range(N):
        p0 = coords[i]; p1 = coords[(i + 1) % N]
        is_front = not is_back_segment(((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2))
        seg_len  = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        info.append((seg_len, is_front))
    start = 0
    for i in range(N):
        if not info[i][1]:
            start = (i + 1) % N; break
    runs, cur = [], []
    for k in range(N):
        i = (start + k) % N
        if info[i][1]: cur.append((i, info[i][0]))
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)

    door_ranges = {}
    for run in runs:
        run_len = sum(ln for _, ln in run)
        n_doors = doors_for_run(run_len)
        if n_doors == 0: continue
        positions = [run_len * (k + 0.5) / n_doors for k in range(n_doors)]
        spans = [(max(0.0, p - DOOR_W / 2), min(run_len, p + DOOR_W / 2)) for p in positions]
        acc = 0.0
        for seg_idx, seg_len in run:
            seg_a, seg_b = acc, acc + seg_len
            for d_a, d_b in spans:
                ov_a = max(d_a, seg_a); ov_b = min(d_b, seg_b)
                if ov_b > ov_a + 1e-6:
                    door_ranges.setdefault(seg_idx, []).append((ov_a - acc, ov_b - acc))
            acc += seg_len
    return door_ranges


def build_walls(pc, name, mat_front, mat_back):
    """Slot 0 = M_Building (front), Slot 1 = M_BuildingBack (back/side).
    orient(CCW) so add_quad's [v00,v10,v11,v01] winding gives outward normals.
    Doors placed by arc-length across the whole front (see _plan_door_ranges)."""
    pc = orient(pc, sign=1.0)
    coords = list(pc.exterior.coords)[:-1]
    N = len(coords)
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()

    z_lo, z_hi = PAVE_TOP, PAVE_TOP + WALL_H
    z_lintel  = PAVE_TOP + DOOR_H

    face_kind = []

    door_ranges = _plan_door_ranges(coords)

    def lerp_along(p0, p1, tx, ty, d):
        return (p0[0] + tx * d, p0[1] + ty * d)

    for i in range(N):
        p0 = coords[i]
        p1 = coords[(i + 1) % N]
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        back = is_back_segment((mx, my))
        seg_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1])

        if back:
            add_quad(bm, p0, p1, z_lo, z_hi); face_kind.append(1); continue

        ranges = sorted(door_ranges.get(i, []))
        if not ranges:
            add_quad(bm, p0, p1, z_lo, z_hi); face_kind.append(0); continue

        tx = (p1[0] - p0[0]) / seg_len
        ty = (p1[1] - p0[1]) / seg_len
        cursor = 0.0
        for ds, de in ranges:
            if ds > cursor + 1e-4:
                a = lerp_along(p0, p1, tx, ty, cursor); b = lerp_along(p0, p1, tx, ty, ds)
                add_quad(bm, a, b, z_lo, z_hi); face_kind.append(0)
            a = lerp_along(p0, p1, tx, ty, ds); b = lerp_along(p0, p1, tx, ty, de)
            add_quad(bm, a, b, z_lintel, z_hi); face_kind.append(0)
            cursor = de
        if cursor < seg_len - 1e-4:
            a = lerp_along(p0, p1, tx, ty, cursor)
            add_quad(bm, a, p1, z_lo, z_hi); face_kind.append(0)

    # DO NOT call bmesh.ops.recalc_face_normals here. VERIFIED 2026-06-07: the
    # per-segment quads are disconnected (no shared vertices); recalc tries to enforce
    # neighbour-consistency anyway and ends up flipping alternating panels in any
    # door-split run -> half the facade ends up backwards. With orient(CCW) above the
    # explicit add_quad winding produces correct outward normals on its own; trust it.
    bm.to_mesh(me); bm.free()

    me.materials.append(mat_front)   # slot 0
    me.materials.append(mat_back)    # slot 1
    for i, p in enumerate(me.polygons):
        p.material_index = face_kind[i] if i < len(face_kind) else 0

    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def _front_run_midpoint(coords, back_tol=EDGE_EPS):
    """Return (x, y, tx, ty) at the arc-length midpoint of the LONGEST contiguous run
    of front (road-facing) segments around `coords`. Handles wraparound by rotating
    the start to a back segment. None if there's no front segment at all.

    back_tol = how close a segment midpoint must be to the hex boundary to count as
    back/side. Inset garden polygons need a relaxed tolerance (~GARDEN_INSET + EDGE_EPS)
    since their back segments have retreated that far from the hex edge."""
    N = len(coords)
    if N == 0:
        return None
    front = []
    lens  = []
    for i in range(N):
        p0 = coords[i]; p1 = coords[(i + 1) % N]
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        front.append(not is_back_segment((mx, my), tol=back_tol))
        lens.append(math.hypot(p1[0] - p0[0], p1[1] - p0[1]))

    # Rotate start to a back segment so a wrapping front run becomes contiguous.
    start = 0
    for i in range(N):
        if not front[i]:
            start = (i + 1) % N
            break

    runs = []                                  # list of [(i, length), ...]
    cur  = []
    for k in range(N):
        i = (start + k) % N
        if front[i]:
            cur.append((i, lens[i]))
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)

    if not runs:
        return None
    runs.sort(key=lambda r: sum(L for _, L in r), reverse=True)
    best = runs[0]
    total = sum(L for _, L in best)
    target = total / 2.0
    acc = 0.0
    for i, L in best:
        if acc + L >= target:
            t = (target - acc) / L
            p0 = coords[i]; p1 = coords[(i + 1) % N]
            x  = p0[0] + t * (p1[0] - p0[0])
            y  = p0[1] + t * (p1[1] - p0[1])
            tx = (p1[0] - p0[0]) / L
            ty = (p1[1] - p0[1]) / L
            return (x, y, tx, ty)
        acc += L
    return None


def _gate_cutter(name, cx, cy, tx, ty):
    """A box cutter for a single garden gate. Width = GATE_W along the wall tangent,
    depth = wide enough to pierce both wall faces, height = full wall (+ epsilon)."""
    nx, ny = -ty, tx
    hw = GATE_W / 2
    hd = (GARDEN_WALL_T * 4)                   # well wider than the 0.25 m wall thickness
    z0, z1 = PAVE_TOP - 0.05, PAVE_TOP + GARDEN_WALL_H + 0.05
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    corners = [
        (cx - tx*hw - nx*hd, cy - ty*hw - ny*hd),
        (cx + tx*hw - nx*hd, cy + ty*hw - ny*hd),
        (cx + tx*hw + nx*hd, cy + ty*hw + ny*hd),
        (cx - tx*hw + nx*hd, cy - ty*hw + ny*hd),
    ]
    bot = [bm.verts.new((x, y, z0)) for (x, y) in corners]
    top = [bm.verts.new((x, y, z1)) for (x, y) in corners]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for k in range(4):
        j = (k + 1) % 4
        bm.faces.new([bot[k], bot[j], top[j], top[k]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def build_garden(pc, name, mat_wall):
    """Knee-height stone edging around a garden plot. Steps:
       0. INSET the polygon by GARDEN_INSET so the wall sits inside the original
          footprint, leaving a wider sidewalk in front than buildings get. None if
          the inset polygon is empty (too small after retreat).
       1. Single-faced quads on the inset perimeter (per-segment).
       2. Weld duplicate verts (so solidify sees one closed loop, not N slabs).
       3. SOLIDIFY inward by GARDEN_WALL_T -- gives the wall a stone-cap top + interior
          face for free, all in one material slot.
       4. Cut a single GATE_W-wide gap centred on the longest front (road-facing) run.
          Back-tol is GARDEN_INSET + EDGE_EPS so inset back segments still classify."""
    inset = pc.buffer(-GARDEN_INSET, join_style=2, mitre_limit=MIT)
    if inset.is_empty:
        return None
    if inset.geom_type != 'Polygon':
        inset = max(inset.geoms, key=lambda g: g.area)

    coords = list(inset.exterior.coords)[:-1]
    N = len(coords)
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    z0, z1 = PAVE_TOP, PAVE_TOP + GARDEN_WALL_H
    for i in range(N):
        add_quad(bm, coords[i], coords[(i + 1) % N], z0, z1)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    me.materials.append(mat_wall)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)

    md = o.modifiers.new("solid", 'SOLIDIFY')
    md.thickness = GARDEN_WALL_T
    md.offset    = -1.0
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="solid")

    # Gate: single cut at the arc-length midpoint of the longest road-facing run.
    gate = _front_run_midpoint(coords, back_tol=GARDEN_INSET + EDGE_EPS)
    if gate is not None:
        gx, gy, tx, ty = gate
        cutter = _gate_cutter(name + "_gc", gx, gy, tx, ty)
        gd = o.modifiers.new("gate", 'BOOLEAN')
        gd.operation = 'DIFFERENCE'; gd.object = cutter
        gd.solver = 'EXACT'; gd.use_self = True; gd.use_hole_tolerant = True
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="gate")
        bpy.data.objects.remove(cutter, do_unlink=True)
    return o


def build_roof_slab(pc, name, mat):
    """Flat slab at z_top..z_top+ROOF_T. Footprint = polygon (forced CCW)."""
    pc = orient(pc, sign=1.0)
    coords = list(pc.exterior.coords)[:-1]
    z0, z1 = PAVE_TOP + WALL_H, PAVE_TOP + WALL_H + ROOF_T
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for (x, y) in coords]
    top = [bm.verts.new((x, y, z1)) for (x, y) in coords]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    n = len(coords)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bot[i], bot[j], top[j], top[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---- tile assembly ----
def build_tile(name, edges, origin):
    """Build TMP_ road context + buildings (or gardens) at `origin`. Each Shapely piece
    is classified by area: >= MIN_BUILDING_AREA -> building (walls + flat roof + doors);
    < MIN_BUILDING_AREA -> garden (waist-height stone wall ring only). The threshold
    catches the bend inner-wedge and the tee_a/b/c slivers near adjacent road pairs."""
    # Visual context: the actual road tile from gen_curved_tiles (so we see the curve under the facades)
    tile = g.build_tile_obj("street_" + name, edges)
    tile.name = "TMP_street_" + name
    tile.location = (origin[0], origin[1], 0.0)

    m_bld    = ensure_mat("M_Building",     (0.72, 0.66, 0.55, 1.0))   # warm beige stone
    m_back   = ensure_mat("M_BuildingBack", (0.55, 0.50, 0.42, 1.0))   # darker debug tint
    m_roof   = ensure_mat("M_BuildingRoof", (0.18, 0.18, 0.20, 1.0))   # dark slate

    for k, (pc, kind) in enumerate(classify_pieces(edges, footprints(edges))):
        if kind == 'garden':
            continue                                                    # corner playground; user authors
        walls = build_walls(pc, "TMP_bld_%s_%d_walls" % (name, k), m_bld, m_back)
        roof  = build_roof_slab(pc, "TMP_bld_%s_%d_roof"  % (name, k), m_roof)
        walls.location = (origin[0], origin[1], 0.0)
        roof.location  = (origin[0], origin[1], 0.0)


def main():
    reset_tmp()
    # 4x3 grid covering all non-blank/non-junction configs (11 tiles)
    SP = 22.0
    layout = [
        ("straight", 0, 0), ("bend",  1, 0), ("curve",  2, 0), ("deadend", 3, 0),
        ("tee",      0, 1), ("tee_a", 1, 1), ("tee_b",  2, 1), ("tee_c",   3, 1),
        ("quad",     0, 2), ("quad_b",1, 2), ("quad_c", 2, 2), ("penta",   3, 2),
    ]
    for name, cx, cy in layout:
        build_tile(name, EDGE_SETS[name], (cx * SP, -cy * SP))
    print("Built building configs:", [n for n, _, _ in layout])


main()
