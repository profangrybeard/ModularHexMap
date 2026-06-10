"""Building-tile generator -- single-story facades that follow the spline-curved roads.

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_buildings.py

Parallel to gen_curved_tiles.py: same EDGE_SETS (minus 'blank' and 'junction'), same R=10
contract, same C1 modular contract at edge midpoints. Each building tile sits ON TOP of the
matching street tile at the same cell -- the engine places both at the same world position.

Geometry layers per tile (one joined mesh per glb):
  * Walls    -- single-story (3.5 m eaves), facades trace the road centreline offset by
                KEEP_HW = 2.5 m, doors by per-run arc length (doors_for_run).
  * Roof     -- FLAT slab (no gables -- those read as a field of tents in a hex grid).
  * Interior -- coincident inward-facing wall duplicates + the roof underside (ceiling).
  * Doors    -- jambs + header + threshold per door, in M_DoorFrame.
  * Gardens  -- corner pieces (any pair of adjacent road edges sharing a hex vertex)
                emit NO geometry: that plot is the user's hand-authoring playground.
                The inner-bend disc subtraction grows each corner to ~9 m^2 of room.

Material slot order (kept stable so the engine can drive per-slot logic):
  * M_Building         -- facade walls (front, road-facing)
  * M_BuildingBack     -- back & side walls (along the hex boundary) -- the engine can
                          later split / hide / replace these per-edge to render the
                          "inset on blank-side" alley behaviour without 2^N variants.
  * M_BuildingRoof     -- flat roof slab top + sides
  * M_BuildingInterior -- inside face of every wall + the ceiling
  * M_DoorFrame        -- jambs + headers + thresholds

NEVER saves the master (gotcha #2/#18). Manifest-aware -- skips any T_bldg_* tile marked
bespoke. See Docs/BuildingFootprints.md for the design history (paused -> resumed pivot).
"""

import os
import sys
import math

import bpy
import bmesh

from shapely.geometry import Polygon, LineString, Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

# Sibling-module imports (works whether run via --python or imported by the registry).
_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
if _HERE and _HERE not in sys.path:
    sys.path.append(_HERE)
import gen_curved_tiles as g                   # noqa: E402  (centerlines + constants)
import tile_common                              # noqa: E402  (canonical export + manifest)


# ---- constants (mirrored from the WIP, signed off 2026-06-07) ----
R        = g.R                                 # 10.0 m
INR      = g.INR                               # apothem (8.66 m)
HW       = g.HW                                # carriageway half-width (1.5 m)
PAVE_TOP = g.PAVE_TOP                          # 0.65 m
WALK     = 1.0                                 # flagstone walk between curb and facade
KEEP_HW  = HW + WALK                           # 2.5 m
WALL_H   = 3.5                                 # single-story eaves
ROOF_T   = 0.20                                # flat roof slab thickness
DOOR_W   = 0.9
DOOR_H   = 2.1
# Door dressing: jambs + header mask the thin-wall edge visible at each door cut,
# threshold gives a sill underfoot at every entry.
FRAME_W       = 0.12                           # jamb width on the wall surface
FRAME_D       = 0.20                           # how far jamb/header project across the wall (~10cm each side)
HEADER_T      = 0.12                           # vertical thickness of the header cap above z_lintel
THRESHOLD_H   = 0.05                           # step height at the doorway
THRESHOLD_D   = 0.40                           # across-wall depth of the threshold sill
OPEN_R   = 0.20
MIT      = 5.0
EDGE_EPS = 0.15

# Shading + bevel: curves get smooth-shaded, sharp corners (>SHARP_ANGLE) stay crisp,
# and the same sharp edges get a small bevel for catch-light + softer silhouettes.
SHARP_ANGLE_DEG = 30.0
BEVEL_WIDTH     = 0.03
BEVEL_SEGMENTS  = 1


# Corner pieces (bend-vertex polygons) emit NO geometry -- the user authors what goes
# there. We still classify them so build_tile_obj knows to skip; the inner-bend disc
# subtraction below stays so each corner plot is ~9 m^2 (usable for hand-authoring).

# Inner-bend rule: shrink corridor at each shared bend vertex so the corner garden grows.
INNER_KEEP_HW = HW                             # 1.5 m
ARC_R         = R / 2                          # 5.0 m -- bend arc radius about shared vertex
INNER_DISC_R  = ARC_R - INNER_KEEP_HW          # 3.5 m

# Hub keep-out for 3+ road junctions -- buildings give the road hub its sidewalk too.
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
    # 'blank' and 'junction' omitted: blank is bespoke playground; junction has no buildable area.
}

CANON = {"Hex_Base", "Camera", "Light",
         "RoadAnchor_0", "RoadAnchor_1", "RoadAnchor_2",
         "RoadAnchor_3", "RoadAnchor_4", "RoadAnchor_5"}


# ---- materials (created on-demand, fake-user, never saved to master) ----
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


def _materials():
    return (
        ensure_mat("M_Building",         (0.72, 0.66, 0.55, 1.0)),  # exterior facade
        ensure_mat("M_BuildingBack",     (0.55, 0.50, 0.42, 1.0)),  # exterior back/side
        ensure_mat("M_BuildingRoof",     (0.18, 0.18, 0.20, 1.0)),  # roof top + sides
        ensure_mat("M_BuildingInterior", (0.88, 0.83, 0.74, 1.0)),  # interior walls + ceiling
        ensure_mat("M_DoorFrame",        (0.32, 0.22, 0.14, 1.0)),  # jambs + header + threshold (warm wood)
    )


# Interior wall offset: coincident with exterior would z-fight, so push the interior
# quad 5 mm into the building. Far smaller than wall thickness reads as.
INTERIOR_EPS = 0.005


# ---- topology helpers ----
def hexpoly():
    return Polygon([(R * math.cos(math.radians(60 * i)),
                     R * math.sin(math.radians(60 * i))) for i in range(6)])


def adjacent_pairs(edges):
    s = set(edges)
    return [(e, (e + 1) % 6) for e in edges if (e + 1) % 6 in s]


def shared_vertex_xy(e0, e1):
    a0, a1 = g.EDGE_ANG[e0], g.EDGE_ANG[e1]
    if abs(a0 - a1) > 180:
        if a0 < a1: a0 += 360
        else:       a1 += 360
    vang = math.radians((a0 + a1) / 2.0)
    return (R * math.cos(vang), R * math.sin(vang))


HEX_BOUNDARY = hexpoly().exterior


def is_back_segment(p_mid, tol=EDGE_EPS):
    return HEX_BOUNDARY.distance(Point(p_mid)) < tol


# ---- footprint ----
def footprints(edges):
    fp = hexpoly()
    if edges:
        polylines = g.centerlines(edges, 0.0)
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
        if len(edges) >= 3:
            corridor = corridor.union(Point(0.0, 0.0).buffer(HUB_KEEPOUT_R, resolution=24))
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
    bend_pts = [Point(*shared_vertex_xy(e0, e1)) for e0, e1 in adjacent_pairs(edges)]
    out = []
    for pc in pieces:
        kind = 'building'
        for v in bend_pts:
            if pc.distance(v) < EDGE_EPS:
                kind = 'garden'; break
        out.append((pc, kind))
    return out


# ---- mesh helpers ----
def add_quad(bm, p0_xy, p1_xy, z0, z1):
    x0, y0 = p0_xy; x1, y1 = p1_xy
    v00 = bm.verts.new((x0, y0, z0))
    v10 = bm.verts.new((x1, y1, z0))
    v11 = bm.verts.new((x1, y1, z1))
    v01 = bm.verts.new((x0, y0, z1))
    return bm.faces.new([v00, v10, v11, v01])


def doors_for_run(L):
    """Door count for a single front (road-facing) run of total arc length L.
       <1.3 m (DOOR_W+0.4) -> 0 (no room),  1.3-7 m -> 1,  7-25 m -> 2,  >=25 m -> 3.
    Multi-frontage buildings get this called once per run -> every run of >1.3 m gets
    >=1 door, so 'min 1 per frontage' falls out for free."""
    if L < DOOR_W + 0.4:
        return 0
    if L < 7.0:
        return 1
    if L < 25.0:
        return 2
    return 3


def _plan_doors(coords):
    """Return (door_ranges, door_centers).
       door_ranges  = {seg_idx: [(start_in_seg, end_in_seg), ...]} for wall splitting --
                      doors that span multiple curved sub-segments produce a lintel quad
                      on each overlapped segment.
       door_centers = [(seg_idx_of_center, center_in_seg), ...] for placing each door's
                      frame + threshold (one decor block per door regardless of how many
                      wall segments the door's lintel actually spans)."""
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
            start = (i + 1) % N
            break
    runs, cur = [], []
    for k in range(N):
        i = (start + k) % N
        if info[i][1]:
            cur.append((i, info[i][0]))
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)

    door_ranges = {}
    door_centers = []
    for run in runs:
        run_len = sum(ln for _, ln in run)
        n_doors = doors_for_run(run_len)
        if n_doors == 0:
            continue
        positions = [run_len * (k + 0.5) / n_doors for k in range(n_doors)]
        # Map each door center (arc-length in run) to a single segment + local distance.
        for d_pos in positions:
            acc = 0.0
            for seg_idx, seg_len in run:
                if acc + seg_len >= d_pos - 1e-6:
                    door_centers.append((seg_idx, d_pos - acc))
                    break
                acc += seg_len
        # Map each door SPAN onto the segments it overlaps for wall splitting.
        spans = [(max(0.0, p - DOOR_W / 2), min(run_len, p + DOOR_W / 2)) for p in positions]
        acc = 0.0
        for seg_idx, seg_len in run:
            seg_a, seg_b = acc, acc + seg_len
            for d_a, d_b in spans:
                ov_a = max(d_a, seg_a)
                ov_b = min(d_b, seg_b)
                if ov_b > ov_a + 1e-6:
                    door_ranges.setdefault(seg_idx, []).append((ov_a - acc, ov_b - acc))
            acc += seg_len
    return door_ranges, door_centers


def _plan_door_ranges(coords):
    """Back-compat shim (older callers want just the ranges)."""
    return _plan_doors(coords)[0]


def build_walls(pc, name, mat_front, mat_back, mat_interior):
    """Slot 0 = M_Building (front), Slot 1 = M_BuildingBack (back/side),
    Slot 2 = M_BuildingInterior (inside face of every wall AND every lintel).

    orient(CCW) so add_quad's [v00,v10,v11,v01] winding gives outward normals on the
    exterior; the interior quad uses reversed winding and is offset INTERIOR_EPS into
    the building (CCW polygon: left of walk-direction is the interior side)."""
    pc = orient(pc, sign=1.0)
    coords = list(pc.exterior.coords)[:-1]
    N = len(coords)
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    z_lo, z_hi = PAVE_TOP, PAVE_TOP + WALL_H
    z_lintel  = PAVE_TOP + DOOR_H
    face_slot = []   # 0 = exterior front, 1 = exterior back, 2 = interior

    door_ranges, _ = _plan_doors(coords)

    def wall_section(p0_xy, p1_xy, z0, z1, ext_slot):
        """Add an exterior quad (outward) + a coincident-but-offset interior quad
        (inward, in slot 2). Same z range -> same door gap on both sides."""
        x0, y0 = p0_xy; x1, y1 = p1_xy
        tx, ty = x1 - x0, y1 - y0
        L = math.hypot(tx, ty) or 1.0
        # Inward direction = left of walk direction on a CCW exterior.
        ix, iy = -ty / L * INTERIOR_EPS, tx / L * INTERIOR_EPS
        # Exterior, normal outward
        v0 = bm.verts.new((x0, y0, z0))
        v1 = bm.verts.new((x1, y1, z0))
        v2 = bm.verts.new((x1, y1, z1))
        v3 = bm.verts.new((x0, y0, z1))
        bm.faces.new([v0, v1, v2, v3]); face_slot.append(ext_slot)
        # Interior, normal inward (winding reversed), offset inward by INTERIOR_EPS
        u0 = bm.verts.new((x0 + ix, y0 + iy, z0))
        u1 = bm.verts.new((x1 + ix, y1 + iy, z0))
        u2 = bm.verts.new((x1 + ix, y1 + iy, z1))
        u3 = bm.verts.new((x0 + ix, y0 + iy, z1))
        bm.faces.new([u3, u2, u1, u0]); face_slot.append(2)

    def lerp(p0, p1, tx, ty, d):
        return (p0[0] + tx * d, p0[1] + ty * d)

    for i in range(N):
        p0 = coords[i]; p1 = coords[(i + 1) % N]
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        back = is_back_segment((mx, my))
        seg = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        ext_slot = 1 if back else 0
        if back:
            wall_section(p0, p1, z_lo, z_hi, ext_slot); continue
        ranges = sorted(door_ranges.get(i, []))
        if not ranges:
            wall_section(p0, p1, z_lo, z_hi, ext_slot); continue
        tx = (p1[0] - p0[0]) / seg
        ty = (p1[1] - p0[1]) / seg
        cursor = 0.0
        for ds, de in ranges:
            if ds > cursor + 1e-4:
                wall_section(lerp(p0, p1, tx, ty, cursor), lerp(p0, p1, tx, ty, ds),
                             z_lo, z_hi, 0)
            wall_section(lerp(p0, p1, tx, ty, ds), lerp(p0, p1, tx, ty, de),
                         z_lintel, z_hi, 0)
            cursor = de
        if cursor < seg - 1e-4:
            wall_section(lerp(p0, p1, tx, ty, cursor), p1, z_lo, z_hi, 0)
    bm.to_mesh(me); bm.free()
    me.materials.append(mat_front)      # slot 0
    me.materials.append(mat_back)       # slot 1
    me.materials.append(mat_interior)   # slot 2
    for i, p in enumerate(me.polygons):
        p.material_index = face_slot[i] if i < len(face_slot) else 0
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def _add_box(bm, cx, cy, z0, z1, tx, ty, along, across):
    """Closed box centered at (cx, cy) spanning z0..z1, oriented to the (tx, ty) tangent.
    `along` = extent along the tangent (centered); `across` = extent perpendicular (centered)."""
    nx, ny = -ty, tx
    ha, hc = along * 0.5, across * 0.5
    corners = [
        (cx - tx * ha - nx * hc, cy - ty * ha - ny * hc),
        (cx + tx * ha - nx * hc, cy + ty * ha - ny * hc),
        (cx + tx * ha + nx * hc, cy + ty * ha + ny * hc),
        (cx - tx * ha + nx * hc, cy - ty * ha + ny * hc),
    ]
    bot = [bm.verts.new((x, y, z0)) for (x, y) in corners]
    top = [bm.verts.new((x, y, z1)) for (x, y) in corners]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for k in range(4):
        j = (k + 1) % 4
        bm.faces.new([bot[k], bot[j], top[j], top[k]])


def build_door_decor(pc, door_centers, name, mat_frame):
    """Per door: 2 jambs + 1 header + 1 threshold, all closed boxes in M_DoorFrame.
    Frame projects FRAME_D across the wall surface (visible from both sides), masking
    the thin-wall edge at the door cut."""
    if not door_centers:
        return None
    pc = orient(pc, sign=1.0)
    coords = list(pc.exterior.coords)[:-1]
    N = len(coords)
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    z_lo = PAVE_TOP
    z_lintel = PAVE_TOP + DOOR_H
    for seg_idx, center_d in door_centers:
        p0 = coords[seg_idx]; p1 = coords[(seg_idx + 1) % N]
        seg_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1.0
        tx, ty = (p1[0] - p0[0]) / seg_len, (p1[1] - p0[1]) / seg_len
        cx = p0[0] + tx * center_d
        cy = p0[1] + ty * center_d
        # Jambs: a box each side of the door, with their door-facing edge at +-DOOR_W/2.
        for sign in (-1.0, +1.0):
            jx = cx + tx * sign * (DOOR_W * 0.5 + FRAME_W * 0.5)
            jy = cy + ty * sign * (DOOR_W * 0.5 + FRAME_W * 0.5)
            _add_box(bm, jx, jy, z_lo, z_lintel + HEADER_T, tx, ty, FRAME_W, FRAME_D)
        # Header: spans the full door width + jamb widths, sits z_lintel..z_lintel+HEADER_T.
        _add_box(bm, cx, cy, z_lintel, z_lintel + HEADER_T, tx, ty,
                 DOOR_W + 2.0 * FRAME_W, FRAME_D)
        # Threshold: sill at the bottom, slightly raised so it reads as a step.
        _add_box(bm, cx, cy, z_lo, z_lo + THRESHOLD_H, tx, ty, DOOR_W, THRESHOLD_D)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    me.materials.append(mat_frame)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def build_roof_slab(pc, name, mat_roof, mat_interior):
    """Roof slab: top + side faces use M_BuildingRoof, bottom face (ceiling, normal
    pointing down into the building) uses M_BuildingInterior so it shares the
    interior material with the walls."""
    pc = orient(pc, sign=1.0)
    coords = list(pc.exterior.coords)[:-1]
    z0, z1 = PAVE_TOP + WALL_H, PAVE_TOP + WALL_H + ROOF_T
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for (x, y) in coords]
    top = [bm.verts.new((x, y, z1)) for (x, y) in coords]
    bm.faces.new(list(reversed(bot)))     # bottom: normal down (= ceiling)
    bm.faces.new(top)                      # top: normal up
    for i in range(len(coords)):
        j = (i + 1) % len(coords)
        bm.faces.new([bot[i], bot[j], top[j], top[i]])   # vertical side
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    me.materials.append(mat_roof)         # slot 0
    me.materials.append(mat_interior)     # slot 1 -> ceiling
    for p in me.polygons:
        p.material_index = 1 if p.normal.z < -0.5 else 0
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---- tile assembly ----
def build_tile_obj(name, edges):
    """Build one building tile (walls + roofs) and return the joined object. Corner
    pieces classified as 'garden' emit NO geometry -- those plots are the user's
    playground (handauthored content drops in later). The inner-bend disc subtraction
    in footprints() still grows the corner to ~9 m^2 so there's room to author.
    No export, no cleanup -- the registry / addon calls this for in-scene previews."""
    m_bld, m_back, m_roof, m_interior, m_frame = _materials()
    pieces = classify_pieces(edges, footprints(edges))
    objs = []
    if pieces:
        for k, (pc, kind) in enumerate(pieces):
            if kind == 'garden':
                continue                                # user's playground; skip
            objs.append(build_walls   (pc, "%s_bld_%d_walls" % (name, k), m_bld, m_back, m_interior))
            objs.append(build_roof_slab(pc, "%s_bld_%d_roof"  % (name, k), m_roof, m_interior))
            # Door decor (jambs + header + threshold) per door on this piece.
            _, door_centers = _plan_doors(list(orient(pc, sign=1.0).exterior.coords)[:-1])
            dec = build_door_decor(pc, door_centers, "%s_bld_%d_decor" % (name, k), m_frame)
            if dec is not None:
                objs.append(dec)

    if not objs:
        # No building pieces (junction; or a config that's all garden). Emit an empty
        # placeholder so callers always get something positionable; .glb stays tiny.
        me = bpy.data.meshes.new("T_bldg_%s_empty" % name)
        o = bpy.data.objects.new("T_bldg_%s" % name, me)
        bpy.context.scene.collection.objects.link(o)
        return o

    # Join all pieces into one object named T_bldg_<name>.
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    tile = objs[0]
    tile.name = "T_bldg_%s" % name
    # Drop empty material slots (glTF doesn't like them).
    for i in reversed(range(len(tile.material_slots))):
        if tile.material_slots[i].material is None:
            tile.active_material_index = i
            bpy.ops.object.material_slot_remove()

    _apply_shading_and_bevel(tile)
    return tile


def _apply_shading_and_bevel(obj):
    """Weld coincident verts (so adjacent wall quads share edges and bevel can work),
    set every polygon to smooth shading, and add a Bevel modifier limited to sharp
    angles -- the bevel-introduced chamfer geometry IS the visual sharp-edge handling,
    no split-normals trickery needed. Modifier bakes at export via tile_common.export_glb.

    Why weld first: build_walls emits per-segment quads with fresh vertices each call,
    so adjacent arc segments are geometrically coincident but topologically disconnected.
    Without welding, bevel finds no shared edges to chamfer and smooth shading has no
    neighbour vertices to interpolate across.

    Blender 4.1+ note: per-edge sharp markers without a Smooth-by-Angle GN modifier
    have no visual effect on smooth shading (5.1's shade_smooth_by_angle marks edges
    but doesn't add the modifier). We just set use_smooth=True on every polygon and let
    the bevel modifier shape the hard corners directly."""
    import math as _m
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bm.to_mesh(me)
    bm.free()

    for p in obj.data.polygons:
        p.use_smooth = True

    md = obj.modifiers.new("bevel", 'BEVEL')
    md.width         = BEVEL_WIDTH
    md.segments      = BEVEL_SEGMENTS
    md.limit_method  = 'ANGLE'
    md.angle_limit   = _m.radians(SHARP_ANGLE_DEG)


def make_tile(name, edges):
    """Standalone (headless) path: build + export + remove."""
    tile = build_tile_obj(name, edges)
    path = tile_common.glb_path("T_bldg_%s" % name)
    tile_common.export_glb(tile, path)
    bpy.data.objects.remove(tile, do_unlink=True)
    return os.path.basename(path), os.path.getsize(path)


def reset():
    for o in list(bpy.data.objects):
        if o.name not in CANON:
            bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


def main():
    reset()
    bespoke = tile_common.bespoke_tile_names()
    out = tile_common.source_glb_dir()
    print("=== gen_buildings: writing to %s ===" % out)
    for name, edges in EDGE_SETS.items():
        tile = "T_bldg_%s" % name
        if tile in bespoke:
            print("  %-28s SKIPPED (bespoke)" % tile)
            continue
        fn, sz = make_tile(name, edges)
        print("  %-28s %6d bytes  edges=%s" % (fn, sz, edges))
    print("=== gen_buildings: done ===")


if __name__ == "__main__":
    main()
