"""Generate SM_RoadSeg.glb — the tilable spline-road module.

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_road_segment.py

A single London road cross-section (3 m carriageway + 1 m raised walks + curb) extruded
1 m along +X as a CLOSED solid (has a bottom, 1 m deep) but with OPEN ends along X — so
consecutive pieces tiled by ASplineRoad flow into one continuous mesh and the open-end edge
loops control the bend. Forward axis = +X. Exports centred to Content/HexTiles/Source/.

Materials: carriageway top = M_Road, everything else (walks, curbs, sides, bottom) = M_Pavement.
"""

import os
import bmesh
import bpy

LEN = 1.0  # piece length along +X (the tiling / connect axis)

# closed cross-section profile (y, z): walks + carriageway on top, solid 1 m deep, flat bottom
PROFILE = [(-2.5, 0.15), (-1.5, 0.15), (-1.5, 0.0), (1.5, 0.0),
           (1.5, 0.15), (2.5, 0.15), (2.5, -1.0), (-2.5, -1.0)]
# material slot per profile edge i (edge PROFILE[i] -> PROFILE[i+1]); only carriageway top = road
EDGE_MAT = [1, 1, 0, 1, 1, 1, 1, 1]  # 0 = M_Road, 1 = M_Pavement


def main():
    for o in list(bpy.data.objects):
        if o.name.startswith("SM_RoadSeg"):
            bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)

    m_road = bpy.data.materials["M_Road"]
    m_pave = bpy.data.materials["M_Pavement"]

    me = bpy.data.meshes.new("SM_RoadSeg_mesh")
    me.materials.append(m_road)   # slot 0
    me.materials.append(m_pave)   # slot 1
    bm = bmesh.new()
    r0 = [bm.verts.new((0.0, y, z)) for (y, z) in PROFILE]   # open end at X=0
    r1 = [bm.verts.new((LEN, y, z)) for (y, z) in PROFILE]   # open end at X=LEN
    n = len(PROFILE)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new([r0[i], r0[j], r1[j], r1[i]])       # wall quad; NO end caps
        f.material_index = EDGE_MAT[i]
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False

    seg = bpy.data.objects.new("SM_RoadSeg", me)
    seg.location = (0.0, 0.0, 0.0)
    bpy.context.scene.collection.objects.link(seg)

    repo = os.path.dirname(os.path.dirname(os.path.dirname(bpy.data.filepath)))
    out = os.path.join(repo, "Content", "HexTiles", "Source")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "SM_RoadSeg.glb")
    bpy.ops.object.select_all(action='DESELECT')
    seg.select_set(True)
    bpy.context.view_layer.objects.active = seg
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_materials='EXPORT')
    print("=== gen_road_segment: wrote %s (%d bytes) dims=%s ===" % (
        os.path.basename(path), os.path.getsize(path), tuple(round(v, 2) for v in seg.dimensions)))


if __name__ == "__main__":
    main()
