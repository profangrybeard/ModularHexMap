"""gen_pit_core.py — the 7-tile fixed core (The Pit's town center) + 6 valley tiles.

Caught up (2026-06-06) to the frontier kit: **2x scale (R=10)**, **tile-border lips**, parametric
base, and the Pit itself — the center hub is now a **recessed void with the six roads BREAKING at
the rim** (a terminus / sink), not an intact junction. Cross-section + widths stay ABSOLUTE
(carriageway 3 m, alley 2 m) so they hold as R grows.

Street network (a radial star): center = **the Pit** (roads drain in and dead-end at the rim);
each of the 6 ring tiles = a straight 3 m spoke (inward to the Pit + outward as the cardinal
artery into the frontier). No rim/alley ring (it zigzagged through distance-2 valley tiles into a
cogwheel — dropped 2026-06-06).

Run against the master base (for the shared materials). NEVER saves the master; idempotent.
Exports T_core_*.glb + core_layout.json (7 tiles) to Content/_project/HexTiles/Source/.
The Pit now carries a solid ~30deg descent ramp (corner-to-corner down one wall) so the player
can walk in/out and test the level transition; the void floor faces up (+Z) so it collides.
NOTE: the asymmetric collapsed-building rim (irregular slumped edges) is still the NEXT pass; this
is the clean blockout representation + a traversable ramp.
"""
import os
import math
import bmesh
import bpy

# ---- contract metrics (match gen_curved_tiles.py) ----
R        = 10.0                              # hex circumradius (m)  [scaled 5 -> 10, 2x]
TOP      = 0.5                               # base slab top = carriageway level
PAVE_H   = 0.15                             # pavement raise / curb height
PAVE_TOP = TOP + PAVE_H                      # 0.65 flagstone top
INR      = R * math.cos(math.radians(30))    # edge-midpoint distance
EDGE_ANG = {0: 90, 1: 150, 2: 210, 3: 270, 4: 330, 5: 30}

# ---- street widths (ABSOLUTE — fixed as R scales) ----
HW_ART = 1.5     # arterial / spoke half-width (3 m carriageway)
HW_ALY = 1.0     # boundary alley half-width (2 m)
ARM_OUT = INR + 0.9          # arm overshoot past the edge (clean carve to the boundary)

# ---- the Pit (center tile) ----
RIM_R     = 4.5              # pit rim radius (roads break here)
PIT_FLOOR = -2.0            # recessed void floor (m)
RAMP_W     = 2.0             # walkable descent-ramp width (m)
RAMP_THICK = 0.25           # ramp slab thickness (m) — solid so it collides reliably

# ---- tile-border lip (metric/debug aid; own material so the resolver ignores it) ----
BORDER_W = 0.12
BORDER_Z0, BORDER_Z1 = PAVE_TOP, PAVE_TOP + 0.035
BORDER_RGB = (0.015, 0.015, 0.02, 1.0)

CANON = {"Hex_Base", "Camera", "Light",
         "RoadAnchor_0", "RoadAnchor_1", "RoadAnchor_2",
         "RoadAnchor_3", "RoadAnchor_4", "RoadAnchor_5"}


def out_dir():
    repo = os.path.dirname(os.path.dirname(os.path.dirname(bpy.data.filepath)))
    d = os.path.join(repo, "Content", "_project", "HexTiles", "Source")
    os.makedirs(d, exist_ok=True)
    return d


def reset():
    for o in list(bpy.data.objects):
        if o.name not in CANON:
            bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


def border_material():
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
    ro, ri = R, R * (INR - BORDER_W) / INR
    me = bpy.data.meshes.new(name + "_m"); bm = bmesh.new()
    ob, ot, ib, it = [], [], [], []
    for i in range(6):
        a = math.radians(60 * i); c, s = math.cos(a), math.sin(a)
        ob.append(bm.verts.new((ro*c, ro*s, BORDER_Z0)))
        ot.append(bm.verts.new((ro*c, ro*s, BORDER_Z1)))
        ib.append(bm.verts.new((ri*c, ri*s, BORDER_Z0)))
        it.append(bm.verts.new((ri*c, ri*s, BORDER_Z1)))
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new([ot[i], ot[j], it[j], it[i]])
        bm.faces.new([ib[i], ib[j], ob[j], ob[i]])
        bm.faces.new([ob[i], ob[j], ot[j], ot[i]])
        bm.faces.new([it[i], it[j], ib[j], ib[i]])
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    o = bpy.data.objects.new(name, me); o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o); return o


def hex_prism(z0, z1, mat, name):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    ang = [math.radians(60 * i) for i in range(6)]
    bot = [bm.verts.new((R*math.cos(a), R*math.sin(a), z0)) for a in ang]
    top = [bm.verts.new((R*math.cos(a), R*math.sin(a), z1)) for a in ang]
    bm.faces.new(list(reversed(bot))); bm.faces.new(top)
    for i in range(6):
        j = (i + 1) % 6; bm.faces.new([bot[i], bot[j], top[j], top[i]])
    bm.normal_update(); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    o = bpy.data.objects.new(name, me); o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o); return o


def hex_annulus(z0, z1, r_in, mat, name):
    """Hex donut (outer R, inner r_in) — the pit tile's base/pavement with a central hole."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    ang = [math.radians(60 * i) for i in range(6)]
    ob = [bm.verts.new((R*math.cos(a), R*math.sin(a), z0)) for a in ang]
    ot = [bm.verts.new((R*math.cos(a), R*math.sin(a), z1)) for a in ang]
    ib = [bm.verts.new((r_in*math.cos(a), r_in*math.sin(a), z0)) for a in ang]
    it = [bm.verts.new((r_in*math.cos(a), r_in*math.sin(a), z1)) for a in ang]
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new([ot[i], ot[j], it[j], it[i]])   # top ring
        bm.faces.new([ib[i], ib[j], ob[j], ob[i]])   # bottom ring
        bm.faces.new([ob[i], ob[j], ot[j], ot[i]])   # outer wall
        bm.faces.new([it[i], it[j], ib[j], ib[i]])   # inner wall
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    o = bpy.data.objects.new(name, me); o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o); return o


def pit_void(r, z_top, z_floor, mat, name):
    """Inward-facing shaft walls + floor — the recessed pit interior."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    ang = [math.radians(60 * i) for i in range(6)]
    top = [bm.verts.new((r*math.cos(a), r*math.sin(a), z_top)) for a in ang]
    bot = [bm.verts.new((r*math.cos(a), r*math.sin(a), z_floor)) for a in ang]
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new([top[i], bot[i], bot[j], top[j]])   # wall, inward-facing
    bm.faces.new(bot)                                    # floor, up-facing (+Z) — CCW from above
    bm.normal_update(); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    o = bpy.data.objects.new(name, me); o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o); return o


def pit_ramp(mat, name):
    """Solid ~30deg descent ramp hugging one rim wall (corner 0 -> corner 60), rim top to floor.
    A hex rim edge is ~R long and the drop is PAVE_TOP-PIT_FLOOR, so a single corner-to-corner
    span lands on the floor at ~30deg. Built as a thick slab (normals out) so it collides as
    Complex-As-Simple. NOTE: import mirrors the tile (gotcha #16) so the ramp appears on the
    mirrored edge in UE — fine for traversal; the asymmetric-rim pass authors open/closed edges."""
    aA, aB = 0.0, math.radians(60)
    r_out, r_in = RIM_R, RIM_R - RAMP_W
    C = lambda ang, rad, z: (rad * math.cos(ang), rad * math.sin(ang), z)
    top = [C(aA, r_out, PAVE_TOP), C(aB, r_out, PIT_FLOOR),
           C(aB, r_in, PIT_FLOOR), C(aA, r_in, PAVE_TOP)]
    bot = [(x, y, z - RAMP_THICK) for (x, y, z) in top]
    me = bpy.data.meshes.new(name + "_m"); bm = bmesh.new()
    vt = [bm.verts.new(p) for p in top]; vb = [bm.verts.new(p) for p in bot]
    bm.faces.new(vt); bm.faces.new(list(reversed(vb)))   # top (walk surface) + bottom
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([vt[i], vt[j], vb[j], vb[i]])        # 4 sides
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    o = bpy.data.objects.new(name, me); o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o); return o


def add_box(bm, ang_deg, t0, t1, z0, z1, hw):
    a = math.radians(ang_deg); dx, dy = math.cos(a), math.sin(a); px, py = -dy, dx
    P = lambda t, s, z: (t*dx + s*px, t*dy + s*py, z)
    cs = [P(t0, -hw, z0), P(t1, -hw, z0), P(t1, hw, z0), P(t0, hw, z0),
          P(t0, -hw, z1), P(t1, -hw, z1), P(t1, hw, z1), P(t0, hw, z1)]
    vs = [bm.verts.new(c) for c in cs]
    for f in [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
              (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]:
        bm.faces.new([vs[i] for i in f])


def build_tile(name, road_edges, is_pit=False):
    """road_edges: {edge_index: carriageway_half_width}. base slab + raised pavement carved by
    per-edge carriageway channels + recessed road surface (+ border), joined into one object.
    is_pit: base/pave are annuli, roads run rim->edge (break at the rim), + recessed void."""
    m_road = bpy.data.materials["M_Road"]
    m_pave = bpy.data.materials["M_Pavement"]
    m_grnd = bpy.data.materials["M_HexGround"]

    arm_in = RIM_R - 0.3 if is_pit else -0.7   # arms start at the rim (pit) or past centre
    surf_in = RIM_R if is_pit else -1.0

    if is_pit:
        base = hex_annulus(0.0, TOP, RIM_R, m_grnd, name)
        pave = hex_annulus(TOP, PAVE_TOP, RIM_R, m_pave, name + "_pave")
        objs = [base, pave, pit_void(RIM_R, PAVE_TOP, PIT_FLOOR, m_grnd, name + "_void"),
                pit_ramp(m_road, name + "_ramp")]
    else:
        base = hex_prism(0.0, TOP, m_grnd, name)
        pave = hex_prism(TOP, PAVE_TOP, m_pave, name + "_pave")
        objs = [base, pave]
    objs.append(hex_border(name + "_border", border_material()))

    if road_edges:
        # carriageway channel cutter (one arm per road edge, at that edge's width)
        cm = bpy.data.meshes.new(name + "_cut"); bm = bmesh.new()
        for e, hw in road_edges.items():
            add_box(bm, EDGE_ANG[e], arm_in, ARM_OUT, 0.45, 0.80, hw)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(cm); bm.free()
        cutter = bpy.data.objects.new(name + "_cut", cm)
        bpy.context.scene.collection.objects.link(cutter)
        md = pave.modifiers.new("carve", 'BOOLEAN'); md.operation = 'DIFFERENCE'
        md.object = cutter; md.solver = 'EXACT'; md.use_self = True; md.use_hole_tolerant = True
        bpy.ops.object.select_all(action='DESELECT')
        pave.select_set(True); bpy.context.view_layer.objects.active = pave
        bpy.ops.object.modifier_apply(modifier="carve")
        bpy.data.objects.remove(cutter, do_unlink=True)

        # recessed cobble carriageway surface (arms; + a junction disc for non-pit tiles)
        rm = bpy.data.meshes.new(name + "_road"); bm = bmesh.new(); z = TOP + 0.01
        for e, hw in road_edges.items():
            a = math.radians(EDGE_ANG[e]); dx, dy = math.cos(a), math.sin(a); px, py = -dy, dx
            Q = lambda t, s: bm.verts.new((t*dx + s*px, t*dy + s*py, z))
            bm.faces.new([Q(surf_in, -hw), Q(INR, -hw), Q(INR, hw), Q(surf_in, hw)])
        if not is_pit:
            seg = 16; cr = max(road_edges.values()) * 1.25
            bm.faces.new([bm.verts.new((cr*math.cos(2*math.pi*k/seg),
                                        cr*math.sin(2*math.pi*k/seg), z)) for k in range(seg)])
        bm.normal_update(); bm.to_mesh(rm); bm.free()
        road = bpy.data.objects.new(name + "_road", rm)
        road.data.materials.append(m_road)
        bpy.context.scene.collection.objects.link(road); objs.append(road)

    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    for i in reversed(range(len(base.material_slots))):
        if base.material_slots[i].material is None:
            base.active_material_index = i
            bpy.ops.object.material_slot_remove()
    return base


# Axial neighbor directions, matching HexCoordinates.h (edge 0 = +Y, CCW).
AXDIR = [(0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1), (1, 0)]


def axial_to_world(q, r):
    return (1.5 * R * q, INR * q + 2.0 * INR * r)


def core_specs():
    """{name: (road_edges{edge: half_width}, (q, r), is_pit)} — the 7-tile fixed core: the Pit +
    6 ring tiles, each a straight 3 m SPOKE (inward to the Pit + outward to the frontier artery).
    A clean radial star draining to the Pit — no rim/alley ring (it zigzagged through the
    distance-2 valley tiles into a cogwheel; dropped 2026-06-06)."""
    specs = {}
    specs["T_core_pit"] = ({e: HW_ART for e in range(6)}, (0, 0), True)   # the Pit (void)
    for e in range(6):
        road = {(e + 3) % 6: HW_ART, e: HW_ART}   # spoke in (to Pit) + artery out (straight through)
        specs["T_core_ring_%d" % e] = (road, AXDIR[e], False)
    return specs


def _bespoke_names():
    """Tiles the pipeline manifest marks bespoke -> skip building/exporting their .glb so we
    never clobber hand work (they stay in core_layout.json so placement is unaffected).
    Defensive: if tile_common isn't importable, build everything (old behaviour)."""
    try:
        import sys
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.append(here)
        import tile_common
        return tile_common.bespoke_tile_names()
    except Exception as exc:
        print("  (bespoke skip-list unavailable: %s)" % exc)
        return set()


def build_core():
    reset()
    bespoke = _bespoke_names()
    tiles = {}
    for name, (road, (q, r), is_pit) in core_specs().items():
        if name in bespoke:
            print("  %-22s SKIPPED (bespoke)" % name)
            continue
        t = build_tile(name, road, is_pit)
        wx, wy = axial_to_world(q, r)
        t.location = (wx, wy, 0.0)
        tiles[name] = t
    bpy.context.view_layer.update()
    return tiles


def export_core(tiles):
    import json
    specs = core_specs()
    layout = {}; results = []
    # core_layout.json lists EVERY core tile (incl. bespoke) so placement/masks are intact;
    # only tiles that were actually built (non-bespoke) get their .glb (re)exported.
    for name, (road, (q, r), _is_pit) in specs.items():
        mask = 0
        for e in road: mask |= (1 << e)
        layout[name] = {"q": q, "r": r, "mask": mask}
        t = tiles.get(name)
        if t is None:
            continue   # bespoke / not built -> keep in layout, don't touch its .glb
        t.location = (0.0, 0.0, 0.0)   # export centered (else UE double-offsets — gotcha #13)
        path = os.path.join(out_dir(), name + ".glb")
        bpy.ops.object.select_all(action='DESELECT')
        t.select_set(True); bpy.context.view_layer.objects.active = t
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_materials='EXPORT')
        results.append((name, os.path.getsize(path)))
    with open(os.path.join(out_dir(), "core_layout.json"), "w") as f:
        json.dump({"hex_radius_m": R, "tiles": layout}, f, indent=2)
    return results


def main():
    tiles = build_core()
    results = export_core(tiles)
    for fn, sz in results:
        print("  %-22s %7d bytes" % (fn, sz))
    print("=== gen_pit_core: built + exported %d core/valley tiles (R=%g, pit void) ===" % (
        len(results), R))


if __name__ == "__main__":
    main()
