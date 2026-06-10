"""River-tile generator -- the water layer of the layered-mask system (Docs/Rivers.md).

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_river_tiles.py

Parallel to gen_curved_tiles.py and reusing its machinery wholesale: the SAME edge-anchor
contract (water crosses each hex edge at the midpoint, perpendicular -> C1-smooth across
tiles), the same arc/centerline math, the same R=10 base. A river cell carries BOTH BANKS
inside its own tile (the same move as streets carrying their sidewalks), so street and
building tiles need zero water-adjacent variants.

Cross-section (director-ruled 2026-06-10: 5 m, one cell, game scale):
  * channel 5.0 m wide, carved full-depth through pavement + base
  * water surface (M_Water -- the resolver key) at -0.9 m, inset 0.2 m per side
  * channel floor at -2.0 m
  * banks = the surviving flagstone pavement at PAVE_TOP, flush with street tiles

Bridges (BRIDGE_SETS): water tile + a road carve + a stone deck spanning the channel +
parapets + the cobble road surface (M_Road reaches the road edge midpoints, so the
two-layer resolver measures both layers from one mesh). Variants are CENSUS-DRIVEN --
author only the (road x water) pairs the 200-roll sweep reports (Rivers.md §5.2).

NEVER saves the master (Resistance #2/#18/#30). Manifest-aware -- skips bespoke tiles.
"""

import os
import sys
import math

import bpy
import bmesh

_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
if _HERE and _HERE not in sys.path:
    sys.path.append(_HERE)
import gen_curved_tiles as g                    # noqa: E402  (contract + mesh machinery)
import tile_common                              # noqa: E402  (canonical export + manifest)

# ---- cross-section (Rivers.md §5.1) ----
CHANNEL_W = 5.0
CH_HW     = CHANNEL_W / 2.0          # 2.5 m
WATER_Z   = -0.9                     # water surface
WATER_T   = 0.05                     # surface slab thickness
WATER_INSET = 0.2                    # surface inset per side (no z-fight with walls;
                                     # verts land ~230 uu from midpoints, well inside the
                                     # resolver's 250 uu absolute tolerance)
FLOOR_Z   = -2.0                     # channel floor
FLOOR_T   = 0.12
DECK_T    = 0.20                     # bridge deck slab (bottom at TOP - DECK_T)
DECK_MARGIN = 1.0                    # deck overhang past the channel each side
PARAPET_H = 0.9
PARAPET_W = 0.18

WATER_RGBA = (0.13, 0.32, 0.45, 1.0)

# Water-layer necklaces. Census (200 rolls): straight 75.3%, curve 23.0%, bend 1.7%.
EDGE_SETS = {
    "straight": [0, 3],
    "curve":    [0, 2],
    "bend":     [0, 1],
}

# Bridge variants: name -> (road_edges, water_edges). CENSUS-DRIVEN (Rivers.md §5.2):
# the 200-roll sweep (2026-06-10, post one-deck fix) reports ONLY these three
# joint-canonical pairs — the complete bridge inventory. Names carry the two masks in
# hex so the catalog wiring is mechanical.
BRIDGE_SETS = {
    "bridge_09_24": ([0, 3], [2, 5]),   # straight over straight, 120deg crossing (45.7%)
    "bridge_09_12": ([0, 3], [1, 4]),   # straight over straight,  60deg crossing (43.8%)
    "bridge_09_14": ([0, 3], [2, 4]),   # straight over curving water             (10.5%)
}


def _mask_to_edges(mask):
    return [e for e in range(6) if (mask >> e) & 1]


def _edges_to_mask(edges):
    m = 0
    for e in edges:
        m |= (1 << e)
    return m


def _bridge_name(road_mask, water_mask):
    return "bridge_%02x_%02x" % (road_mask, water_mask)


def add_bridge_variant(road_mask, water_mask):
    """Register a census pair as a buildable bridge variant."""
    BRIDGE_SETS[_bridge_name(road_mask, water_mask)] = (
        _mask_to_edges(road_mask), _mask_to_edges(water_mask))


def water_material():
    m = bpy.data.materials.get("M_Water")
    if m is None:
        m = bpy.data.materials.new("M_Water")   # name MUST contain "Water" (resolver key)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = WATER_RGBA
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.15
        m.use_fake_user = True
    return m


# ---- polyline helpers (deck spans) ----
def _poly_len(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def _point_at(pts, s):
    """Point at arc length s along polyline pts (clamped)."""
    acc = 0.0
    for i in range(len(pts) - 1):
        seg = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        if acc + seg >= s or i == len(pts) - 2:
            t = 0.0 if seg == 0 else max(0.0, min(1.0, (s - acc) / seg))
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
                    pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
        acc += seg
    return pts[-1]


def _sub_polyline(pts, s0, s1, samples=12):
    return [_point_at(pts, s0 + (s1 - s0) * (k / float(samples))) for k in range(samples + 1)]


def _min_dist_param(road_pts, water_polys):
    """Arc length s along road_pts of the closest approach to any water centerline."""
    best_s, best_d = 0.0, 1e9
    L = _poly_len(road_pts)
    n = max(24, len(road_pts) * 2)
    for k in range(n + 1):
        s = L * k / float(n)
        px, py = _point_at(road_pts, s)
        for wp in water_polys:
            m = max(24, len(wp) * 2)
            WL = _poly_len(wp)
            for j in range(m + 1):
                qx, qy = _point_at(wp, WL * j / float(m))
                d = math.hypot(px - qx, py - qy)
                if d < best_d:
                    best_d, best_s = d, s
    return best_s, best_d


def _offset_polyline(pts, lateral):
    """Offset each point laterally (left of travel = +) by `lateral`."""
    out = []
    N = len(pts)
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(N - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        Lv = math.hypot(tx, ty) or 1.0
        out.append((x - ty / Lv * lateral, y + tx / Lv * lateral))
    return out


# ---- builders ----
def _carved_ground(name, water_edges, road_edges=None):
    """Base+pavement joined, with the water corridor carved full-depth (and the road
    channel carved through the pavement when road_edges given — the bridge case)."""
    m_pave = bpy.data.materials["M_Pavement"]
    m_grnd = bpy.data.materials["M_HexGround"]
    base = g.hex_prism(name, 0.0, g.TOP, m_grnd)
    pave = g.hex_prism(name + "_pave", g.TOP, g.PAVE_TOP, m_pave)
    bpy.ops.object.select_all(action='DESELECT')
    base.select_set(True); pave.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    solid = base

    def carve(polys, half, z0, z1, tag):
        cm = bpy.data.meshes.new(name + tag)
        bm = bmesh.new()
        for poly in polys:
            g.sweep_into(bm, poly, half, z0, z1)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(cm); bm.free()
        cutter = bpy.data.objects.new(name + tag, cm)
        bpy.context.scene.collection.objects.link(cutter)
        md = solid.modifiers.new("carve" + tag, 'BOOLEAN')
        md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
        md.use_self = True; md.use_hole_tolerant = True       # Resistance #14
        bpy.ops.object.select_all(action='DESELECT')
        solid.select_set(True); bpy.context.view_layer.objects.active = solid
        bpy.ops.object.modifier_apply(modifier="carve" + tag)
        bpy.data.objects.remove(cutter, do_unlink=True)

    carve(g.centerlines(water_edges, g.CUT_EXT), CH_HW, FLOOR_Z - 0.3, g.PAVE_TOP + 0.15, "_wcut")
    if road_edges:
        carve(g.centerlines(road_edges, g.CUT_EXT), g.HW, g.CUT_Z0, g.CUT_Z1, "_rcut")
    return solid


def _swept_slab(name, polys, half, z0, z1, mat):
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    for poly in polys:
        g.sweep_into(bm, poly, half, z0, z1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    return o


def build_water_obj(name, water_edges, road_edges=None):
    """One river tile (or, with road_edges, one bridge tile). Returns the joined object."""
    m_road = bpy.data.materials["M_Road"]
    m_pave = bpy.data.materials["M_Pavement"]
    m_grnd = bpy.data.materials["M_HexGround"]
    m_watr = water_material()

    tile_name = ("T_%s" % name) if name.startswith("bridge_") else ("T_river_%s" % name)
    solid = _carved_ground(tile_name, water_edges, road_edges)
    water_polys = g.centerlines(water_edges, 0.0)
    objs = [solid,
            _swept_slab(tile_name + "_floor", water_polys, CH_HW, FLOOR_Z, FLOOR_Z + FLOOR_T, m_grnd),
            _swept_slab(tile_name + "_water", water_polys, CH_HW - WATER_INSET,
                        WATER_Z - WATER_T, WATER_Z, m_watr),
            g.hex_border(tile_name + "_border", g.border_material())]

    if road_edges:
        road_polys = g.centerlines(road_edges, 0.0)
        # Cobble road surface, full length (the resolver reads M_Road at the midpoints).
        objs.append(_swept_slab(tile_name + "_road", road_polys, g.HW, g.RD_Z0, g.RD_Z1, m_road))
        # Deck + parapets across the channel on every road run that meets the water.
        for ri, rp in enumerate(road_polys):
            s_star, d_min = _min_dist_param(rp, water_polys)
            if d_min > CH_HW + DECK_MARGIN:
                continue
            L = _poly_len(rp)
            s0 = max(0.0, s_star - (CH_HW + DECK_MARGIN))
            s1 = min(L, s_star + (CH_HW + DECK_MARGIN))
            span = _sub_polyline(rp, s0, s1)
            objs.append(_swept_slab("%s_deck%d" % (tile_name, ri), [span], g.HW,
                                    g.TOP - DECK_T, g.TOP, m_pave))
            for side in (+1.0, -1.0):
                rail = _offset_polyline(span, side * (g.HW + PARAPET_W / 2.0))
                objs.append(_swept_slab("%s_rail%d%s" % (tile_name, ri, "L" if side > 0 else "R"),
                                        [rail], PARAPET_W / 2.0,
                                        g.TOP, g.TOP + PARAPET_H, m_pave))

    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    tile = objs[0]
    tile.name = tile_name
    for i in reversed(range(len(tile.material_slots))):
        if tile.material_slots[i].material is None:
            tile.active_material_index = i
            bpy.ops.object.material_slot_remove()
    return tile


def build_tile_obj(name, edges):
    """Registry entry point for plain river tiles (no export, no cleanup)."""
    return build_water_obj(name, edges)


def build_bridge_obj(name, road_edges, water_edges):
    """Registry entry point for bridge tiles."""
    return build_water_obj(name, water_edges, road_edges)


def make_tile(name, edges):
    tile = build_water_obj(name, edges)
    path = tile_common.glb_path(tile.name)
    size = tile_common.export_glb(tile, path)
    bpy.data.objects.remove(tile, do_unlink=True)
    return os.path.basename(path), size


def make_bridge(name, road_edges, water_edges):
    tile = build_water_obj(name, water_edges, road_edges)
    path = tile_common.glb_path(tile.name)
    size = tile_common.export_glb(tile, path)
    bpy.data.objects.remove(tile, do_unlink=True)
    return os.path.basename(path), size


def reset():
    for o in list(bpy.data.objects):
        if o.name not in g.CANON:
            bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


def main():
    reset()
    bespoke = tile_common.bespoke_tile_names()
    out = tile_common.source_glb_dir()
    print("=== gen_river_tiles: writing to %s ===" % out)
    for name, edges in EDGE_SETS.items():
        tile = "T_river_%s" % name
        if tile in bespoke:
            print("  %-28s SKIPPED (bespoke)" % tile)
            continue
        fn, sz = make_tile(name, edges)
        print("  %-28s %7d bytes  water=%s" % (fn, sz, edges))
    for name, (r_edges, w_edges) in BRIDGE_SETS.items():
        tile = "T_%s" % name
        if tile in bespoke:
            print("  %-28s SKIPPED (bespoke)" % tile)
            continue
        fn, sz = make_bridge(name, r_edges, w_edges)
        print("  %-28s %7d bytes  road=%s water=%s" % (fn, sz, r_edges, w_edges))

    # Kit manifest: the single source UE-side wiring reads (setup_river.py), so the
    # mask data is never duplicated by hand — same pattern as core_layout.json.
    import json
    kit = {}
    for name, edges in EDGE_SETS.items():
        kit["T_river_%s" % name] = {"road_mask": 0, "water_mask": _edges_to_mask(edges)}
    for name, (r_edges, w_edges) in BRIDGE_SETS.items():
        kit["T_%s" % name] = {"road_mask": _edges_to_mask(r_edges),
                              "water_mask": _edges_to_mask(w_edges)}
    with open(os.path.join(out, "river_kit.json"), "w") as f:
        json.dump({"channel_w": CHANNEL_W, "water_z": WATER_Z, "tiles": kit}, f, indent=2)
        f.write("\n")
    print("  river_kit.json: %d tiles" % len(kit))
    print("=== gen_river_tiles: done ===")


if __name__ == "__main__":
    main()
