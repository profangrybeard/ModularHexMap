"""_make_bespoke.py — headless creator of a bespoke per-tile .blend.

Spawned by the tile_pipeline addon's "Promote to Bespoke" so the user's open session is
never touched. Starts from --factory-startup (empty), LINKS the shared materials + a
reference Hex_Base from the master, builds the tile's blockout as a LOCAL editable mesh,
and saves with relative library paths (so the link to HexBase.blend survives repo moves).

  blender --background --factory-startup --python _make_bespoke.py -- <tile> <out_blend> <hexbase>
"""
import bpy
import sys
import os

LINK_MATS = ["M_Road", "M_Pavement", "M_HexGround", "M_TileBorder"]
REF_OBJECTS = ["Hex_Base"]


def _args():
    a = sys.argv
    return a[a.index("--") + 1:] if "--" in a else []


def main():
    tile, out_blend, hexbase = _args()[:3]
    out_blend = os.path.abspath(out_blend)   # Blender won't inherit the shell cwd for argv paths
    hexbase = os.path.abspath(hexbase)
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.append(here)

    # empty the factory scene
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)

    # LINK shared materials + reference hex from the master (read-only)
    with bpy.data.libraries.load(hexbase, link=True) as (src, dst):
        dst.materials = [m for m in LINK_MATS if m in src.materials]
        dst.objects = [o for o in REF_OBJECTS if o in src.objects]
    ref = bpy.data.collections.new("Reference")
    bpy.context.scene.collection.children.link(ref)
    for o in dst.objects:
        if o is not None:
            ref.objects.link(o)
            o.hide_select = True            # guide only — don't grab it while modelling
    bpy.context.view_layer.layer_collection.children["Reference"].exclude = False

    # build the LOCAL editable blockout (assigns the linked materials by name)
    import tile_registry
    entry = tile_registry.get(tile)
    if entry is None:
        print("ERROR: unknown tile '%s'" % tile)
        sys.exit(2)
    obj = entry.build()
    obj.name = tile
    obj.location = (0.0, 0.0, 0.0)

    # save with library paths made relative to the bespoke file
    os.makedirs(os.path.dirname(out_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend, relative_remap=True, compress=True)
    print("OK: wrote %s (%d bytes)" % (out_blend, os.path.getsize(out_blend)))


if __name__ == "__main__":
    main()
