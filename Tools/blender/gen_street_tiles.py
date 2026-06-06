"""Procedural street-tile generator (single source of truth for road tiles).

Run against the master base file so the canonical Hex_Base + shared materials
(M_HexGround / M_Road / M_Pavement) are already loaded:

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_street_tiles.py

For each entry in EDGE_SETS it duplicates the master Hex_Base, lays the London
street cross-section (recessed cobble carriageway between raised flagstone
pavements with a curb), joins, and exports a glb to Content/_project/HexTiles/Source/.
It NEVER saves the master. Re-running is idempotent.

NOTE: this is the STREETS + WALKS kit. Building footprints were prototyped and then
removed (see Docs/BuildingFootprints.md for the research + how to re-add them); the
walk-in building layer lives in Tools/blender/_wip_building_blockout.py.

To add a tile type, add a name -> edge-index list to EDGE_SETS. Edge indices:
0=+Y(forward), then counter-clockwise 1..5 (see Source_Art/README.md).
"""

import os
import math
import bmesh
import bpy

# ---- constants (match the contract; see Source_Art/README.md) ----
R       = 5.0          # hex circumradius (m)
TOP     = 0.5          # base slab top = carriageway level
PAVE_H  = 0.15         # pavement raise / curb height
PAVE_TOP = TOP + PAVE_H
WR      = 3.0          # carriageway width (-> 1 m pavement at each 5 m edge)
HW      = WR / 2.0
INR     = R * math.cos(math.radians(30))   # edge-midpoint distance
EDGE_ANG = {0: 90, 1: 150, 2: 210, 3: 270, 4: 330, 5: 30}

# The full canonical set of road-edge configs up to rotation (14 binary necklaces of
# length 6). The in-engine generator applies rotation, so one tile per necklace covers
# every orientation. Growth can produce any of these, so the kit must provide all of them.
EDGE_SETS = {
    "blank":    [],                  # 0 roads — no-road backfill
    "deadend":  [0],                 # 1 road  — street stub / endpoint
    "bend":     [0, 1],              # 2 roads — 60° sharp turn (adjacent edges)
    "curve":    [0, 2],              # 2 roads — 120° wide turn
    "straight": [0, 3],              # 2 roads — through street (opposite edges)
    "tee":      [0, 2, 4],           # 3 roads — symmetric Y / 3-way
    "tee_a":    [0, 1, 2],           # 3 roads — three consecutive
    "tee_b":    [0, 1, 3],           # 3 roads — T (straight + adjacent branch)
    "tee_c":    [0, 1, 4],           # 3 roads — skewed 3-way
    "quad":     [0, 1, 2, 3],        # 4 roads
    "quad_b":   [0, 2, 3, 4],        # 4 roads
    "quad_c":   [0, 1, 3, 4],        # 4 roads
    "penta":    [0, 1, 2, 3, 4],     # 5 roads
    "junction": [0, 1, 2, 3, 4, 5],  # 6 roads — full crossroads / square
}

CANON = {"Hex_Base", "Camera", "Light",
         "RoadAnchor_0", "RoadAnchor_1", "RoadAnchor_2",
         "RoadAnchor_3", "RoadAnchor_4", "RoadAnchor_5"}


def out_dir():
    repo = os.path.dirname(os.path.dirname(os.path.dirname(bpy.data.filepath)))
    d = os.path.join(repo, "Content", "_project", "HexTiles", "Source")
    os.makedirs(d, exist_ok=True)
    return d


def reset():
    """Remove anything that isn't canonical so each run starts clean."""
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


def make_tile(name, edges):
    m_road = bpy.data.materials["M_Road"]
    m_pave = bpy.data.materials["M_Pavement"]

    # canonical base slab (duplicate of the master Hex_Base)
    src = bpy.data.objects["Hex_Base"]
    base = src.copy()
    base.data = src.data.copy()
    base.name = "T_street_" + name
    base.location = (0.0, 0.0, 0.0)
    bpy.context.scene.collection.objects.link(base)

    pave = hex_prism(TOP, PAVE_TOP, m_pave, name + "_pave")
    objs = [base, pave]

    if edges:
        # carriageway channel cutter (union of WR-wide arms, center -> each edge)
        cm = bpy.data.meshes.new(name + "_cut")
        bm = bmesh.new()
        for e in edges:
            add_box(bm, EDGE_ANG[e], -0.7, 6.0, 0.45, 0.75, HW)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(cm)
        bm.free()
        cutter = bpy.data.objects.new(name + "_cut", cm)
        bpy.context.scene.collection.objects.link(cutter)
        md = pave.modifiers.new("carve", 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.object = cutter
        md.solver = 'EXACT'
        md.use_self = True            # gotcha #14: arms meet at centre -> self-intersecting
        md.use_hole_tolerant = True   # cutter; without these the EXACT solver eats the curbs
        bpy.ops.object.select_all(action='DESELECT')
        pave.select_set(True)
        bpy.context.view_layer.objects.active = pave
        bpy.ops.object.modifier_apply(modifier="carve")
        bpy.data.objects.remove(cutter, do_unlink=True)

        # recessed cobble carriageway surface
        rm = bpy.data.meshes.new(name + "_road")
        bm = bmesh.new()
        z = TOP + 0.01
        for e in edges:
            a = math.radians(EDGE_ANG[e])
            dx, dy = math.cos(a), math.sin(a)
            px, py = -dy, dx
            Q = lambda t, s: bm.verts.new((t * dx + s * px, t * dy + s * py, z))
            bm.faces.new([Q(-1.0, -HW), Q(INR, -HW), Q(INR, HW), Q(-1.0, HW)])
        seg, cr = 14, HW * 1.25
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

    # join into one tile object
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    for i in reversed(range(len(base.material_slots))):
        if base.material_slots[i].material is None:
            base.active_material_index = i
            bpy.ops.object.material_slot_remove()

    # export
    path = os.path.join(out_dir(), "T_street_%s.glb" % name)
    bpy.ops.object.select_all(action='DESELECT')
    base.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              use_selection=True, export_apply=True,
                              export_yup=True, export_materials='EXPORT')
    bpy.data.objects.remove(base, do_unlink=True)
    return os.path.basename(path), os.path.getsize(path)


def main():
    reset()
    print("=== gen_street_tiles: writing to %s ===" % out_dir())
    for name, edges in EDGE_SETS.items():
        fn, sz = make_tile(name, edges)
        print("  %-28s %6d bytes  edges=%s" % (fn, sz, edges))
    print("=== gen_street_tiles: done (%d tiles) ===" % len(EDGE_SETS))


if __name__ == "__main__":
    main()
