"""Generate SM_GroundHex.glb — a plain flat-top hex ground slab.

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_ground_hex.py

The generator's ground-only review mode drops one of these per cell (roads come from the
spline layer), so the empty hexes between roads read as the blocks. Flat-top R=5, z 0..0.5
(carriageway top = 0.5 m, so spline carriageways sit flush). Material M_HexGround. Centered.
"""

import os
import math
import bmesh
import bpy

R = 5.0
TOP = 0.5


def main():
    for o in list(bpy.data.objects):
        if o.name.startswith("SM_GroundHex"):
            bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)

    mat = bpy.data.materials["M_HexGround"]
    me = bpy.data.meshes.new("SM_GroundHex_mesh")
    bm = bmesh.new()
    ang = [math.radians(60 * i) for i in range(6)]
    bot = [bm.verts.new((R * math.cos(a), R * math.sin(a), 0.0)) for a in ang]
    top = [bm.verts.new((R * math.cos(a), R * math.sin(a), TOP)) for a in ang]
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
    seg = bpy.data.objects.new("SM_GroundHex", me)
    seg.data.materials.append(mat)
    seg.location = (0.0, 0.0, 0.0)
    bpy.context.scene.collection.objects.link(seg)

    repo = os.path.dirname(os.path.dirname(os.path.dirname(bpy.data.filepath)))
    out = os.path.join(repo, "Content", "_project", "HexTiles", "Source")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "SM_GroundHex.glb")
    bpy.ops.object.select_all(action='DESELECT')
    seg.select_set(True)
    bpy.context.view_layer.objects.active = seg
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_materials='EXPORT')
    print("=== gen_ground_hex: wrote %s (%d bytes) ===" % (os.path.basename(path), os.path.getsize(path)))


if __name__ == "__main__":
    main()
