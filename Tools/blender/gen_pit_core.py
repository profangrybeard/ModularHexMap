"""gen_pit_core.py — the 7-tile fixed core (The Pit's town center).

Staged build (per the agreed re-approach):
  PHASE 1 (current): assemble the INTACT "pre-destruction" street network only —
    7 hex tiles, correct intersections, correct walk heights, a ring-alley boundary.
    No sinkhole, no boolean, no export. We look at this and sign off first.
  PHASE 2 (after sign-off): carve the zig-zag sinkhole + per-tile origin reset + export.

Run against the master base (like gen_street_tiles), or exec'd in the connected session.
It NEVER saves the master; re-running is idempotent.

Street network (a wheel): center = 6-way 3 m junction (the grand crossing); each ring tile =
a 3 m spoke on its center-facing edge + a 2 m alley on its two ring-neighbour edges, so the
six rim segments form a continuous boundary loop around the hub.
"""
import os
import math
import bmesh
import bpy

# ---- contract metrics (match Source_Art/README.md + gen_street_tiles.py) ----
R        = 5.0                               # hex circumradius (m)
TOP      = 0.5                               # base slab top = carriageway level
PAVE_H   = 0.15                              # pavement raise / curb height
PAVE_TOP = TOP + PAVE_H                      # 0.65 flagstone top
INR      = R * math.cos(math.radians(30))    # 4.330 edge-midpoint distance
SPACING  = 2.0 * INR                         # 8.660 neighbor center distance
EDGE_ANG = {0: 90, 1: 150, 2: 210, 3: 270, 4: 330, 5: 30}

# ---- street widths ----
HW_ART = 1.5     # arterial / spoke half-width (3 m carriageway)
HW_ALY = 1.0     # boundary alley half-width (2 m)

# ---- sinkhole void (PHASE 2 — not used yet) ----
PIT_DEPTH = 3.0
ZZ_TEETH  = 18
ZZ_RMIN   = 4.5
ZZ_RMAX   = 8.5

CANON = {"Hex_Base", "Camera", "Light",
         "RoadAnchor_0", "RoadAnchor_1", "RoadAnchor_2",
         "RoadAnchor_3", "RoadAnchor_4", "RoadAnchor_5"}


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


def hex_prism(z0, z1, mat, name):
    me = bpy.data.meshes.new(name)
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


def add_box(bm, ang_deg, t0, t1, z0, z1, hw):
    a = math.radians(ang_deg)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy, dx
    P = lambda t, s, z: (t * dx + s * px, t * dy + s * py, z)
    cs = [P(t0, -hw, z0), P(t1, -hw, z0), P(t1, hw, z0), P(t0, hw, z0),
          P(t0, -hw, z1), P(t1, -hw, z1), P(t1, hw, z1), P(t0, hw, z1)]
    vs = [bm.verts.new(c) for c in cs]
    for f in [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
              (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]:
        bm.faces.new([vs[i] for i in f])


def build_tile(name, road_edges):
    """road_edges: {edge_index: carriageway_half_width}. Builds base slab + raised pavement
    carved by per-edge carriageway channels + recessed road surface, joined into one object."""
    m_road = bpy.data.materials["M_Road"]
    m_pave = bpy.data.materials["M_Pavement"]

    src = bpy.data.objects["Hex_Base"]
    base = src.copy()
    base.data = src.data.copy()
    base.name = name
    base.location = (0.0, 0.0, 0.0)
    bpy.context.scene.collection.objects.link(base)

    pave = hex_prism(TOP, PAVE_TOP, m_pave, name + "_pave")
    objs = [base, pave]

    if road_edges:
        # carriageway channel cutter (one arm per road edge, at that edge's width)
        cm = bpy.data.meshes.new(name + "_cut")
        bm = bmesh.new()
        for e, hw in road_edges.items():
            add_box(bm, EDGE_ANG[e], -0.7, 6.0, 0.45, 0.75, hw)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(cm)
        bm.free()
        cutter = bpy.data.objects.new(name + "_cut", cm)
        bpy.context.scene.collection.objects.link(cutter)
        md = pave.modifiers.new("carve", 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.object = cutter
        md.solver = 'EXACT'
        md.use_self = True           # arms overlap at the junction (self-intersecting cutter);
        md.use_hole_tolerant = True  # without these EXACT eats the whole pavement
        bpy.ops.object.select_all(action='DESELECT')
        pave.select_set(True)
        bpy.context.view_layer.objects.active = pave
        bpy.ops.object.modifier_apply(modifier="carve")
        bpy.data.objects.remove(cutter, do_unlink=True)

        # recessed cobble carriageway surface (arms + a junction disc filling the center)
        rm = bpy.data.meshes.new(name + "_road")
        bm = bmesh.new()
        z = TOP + 0.01
        for e, hw in road_edges.items():
            a = math.radians(EDGE_ANG[e])
            dx, dy = math.cos(a), math.sin(a)
            px, py = -dy, dx
            Q = lambda t, s: bm.verts.new((t * dx + s * px, t * dy + s * py, z))
            bm.faces.new([Q(-1.0, -hw), Q(INR, -hw), Q(INR, hw), Q(-1.0, hw)])
        seg = 16
        cr = max(road_edges.values()) * 1.25
        bm.faces.new([bm.verts.new((cr * math.cos(2 * math.pi * k / seg),
                                    cr * math.sin(2 * math.pi * k / seg), z))
                      for k in range(seg)])
        bm.normal_update()
        bm.to_mesh(rm)
        bm.free()
        road = bpy.data.objects.new(name + "_road", rm)
        road.data.materials.append(m_road)
        bpy.context.scene.collection.objects.link(road)
        objs.append(road)

    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
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
    """Flat-top axial (q, r) -> world XY (meters), matching HexGrid::WorldXY."""
    return (1.5 * R * q, INR * q + 2.0 * INR * r)


def core_specs():
    """{name: (road_edges{edge: half_width}, (q, r))} — the 7 fixed core tiles plus the 6
    perimeter 'valley' tiles (frontier, distance 2) that close the boundary alley loop."""
    specs = {}
    # Hub: 3 m road to every edge — the grand crossing; all spokes drain to this portal.
    specs["T_core_pit"] = ({e: HW_ART for e in range(6)}, (0, 0))
    # Ring tile e: 3 m spoke inward (edge e+3) + 2 m boundary alley on its two OUTER shoulder
    # edges (e+1, e-1), which reach the valley cells on either side.
    for e in range(6):
        road = {(e + 3) % 6: HW_ART, (e + 1) % 6: HW_ALY, (e + 5) % 6: HW_ALY}
        specs["T_core_ring_%d" % e] = (road, AXDIR[e])
    # Valley tile e (frontier, distance 2, sits in the outer notch between ring e and ring e+1):
    # a 2 m alley bend joining the two — the six valleys chain the boundary loop closed.
    for e in range(6):
        f = (e + 1) % 6
        q, r = AXDIR[e][0] + AXDIR[f][0], AXDIR[e][1] + AXDIR[f][1]
        road = {(e + 3) % 6: HW_ALY, (e + 4) % 6: HW_ALY}
        specs["T_valley_%d" % e] = (road, (q, r))
    return specs


def build_core():
    reset()
    specs = core_specs()
    tiles = {}
    for name, (road, (q, r)) in specs.items():
        t = build_tile(name, road)
        wx, wy = axial_to_world(q, r)
        t.location = (wx, wy, 0.0)
        tiles[name] = t
    bpy.context.view_layer.update()
    return tiles


def set_origin_to(obj, x, y):
    """Reset object origin to (x, y, 0) so the exported tile pivots on its own hex center."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    cur = bpy.context.scene.cursor.location.copy()
    bpy.context.scene.cursor.location = (x, y, 0.0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.context.scene.cursor.location = cur


def export_core(tiles):
    """Origin-reset each tile to its hex center and export a .glb. Also write a layout manifest
    (name -> axial q,r) so the UE side can place each tile at the matching generator coord."""
    import json
    specs = core_specs()
    layout = {}
    results = []
    for name, t in tiles.items():
        # Export CENTERED: the mesh data is already centered on its bottom-center pivot, so move
        # the object to the origin. Otherwise the world location bakes into the glTF node and UE
        # double-offsets it against the actor placement (tiles spread out at 2x spacing).
        t.location = (0.0, 0.0, 0.0)
        path = os.path.join(out_dir(), name + ".glb")
        bpy.ops.object.select_all(action='DESELECT')
        t.select_set(True)
        bpy.context.view_layer.objects.active = t
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_materials='EXPORT')
        layout[name] = list(specs[name][1])
        results.append((name, os.path.getsize(path)))
    with open(os.path.join(out_dir(), "core_layout.json"), "w") as f:
        json.dump({"hex_radius_m": R, "tiles": layout}, f, indent=2)
    return results


def main():
    build_core()
    print("=== gen_pit_core PHASE 1: intact 7-tile core assembled (no pit, no export) ===")


if __name__ == "__main__":
    main()
