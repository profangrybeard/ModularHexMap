"""Range generator — the far parallax layer (Docs/Rim.md B2: "mountains of
varying heights that create the parallax, or at least attempt it").

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_range.py

Three long ridge meshes (T_range_a/b/c): bowed silhouette walls ~170 m long with
12-16 peaks of deterministic varied height (45-70 m baked; placement scaling
takes instances to ~50-120 m apparent). Wedge cross-section (thick base, knife
crest), flat-shaded M_Rock, bases sunk 3 m so grounding never shows. These are
OFF-GRID scenery — placed around the bowl at radius ~300-400 m by
Tools/setup_scenery.py with varied yaw/scale, NOT destiny-dependent: the
mountains do not reroll. Low rim hills (8.5 m) in front, these behind, fog
between = the depth sandwich. NEVER saves the master.
"""

import os
import sys
import math
import bmesh
import bpy

_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
if _HERE and _HERE not in sys.path:
    sys.path.append(_HERE)

import gen_curved_tiles as _street
import gen_rim_tiles as _rim
import gen_blank_variants as _blank

LENGTH   = 170.0
N_VERTS  = 40       # crest sample count (gaussian peaks need smooth sampling)
N_PEAKS  = 5        # WIDE-based mountains, not saw teeth (base:height ~2:1)
BASE_HT  = 16.0
HALF_TH  = 10.0     # base half-thickness
BOW      = 14.0     # plan-view sagitta (the range hugs the bowl)
SINK     = 3.0

RIDGES = {"a": 11, "b": 47, "c": 83}    # deterministic phase seeds


def _rand(j, seed):
    """Deterministic [0,1) — same trick the shaders use."""
    v = math.sin(j * 12.9898 + seed) * 43758.5453
    return v - math.floor(v)


def _peaks(seed):
    """5 gaussian mountains: jittered centers (irregular rhythm), varied heights
    and base widths. The silhouette is the MAX over these + a low base ridge."""
    pks = []
    for k in range(N_PEAKS):
        c = (k + 0.5) / N_PEAKS + (_rand(k * 7 + 1, seed) - 0.5) * 0.12
        h = 38.0 + _rand(k * 7 + 2, seed) * 30.0          # 38..68 m
        w = 0.06 + _rand(k * 7 + 3, seed) * 0.05          # base ~20-37 m per side
        pks.append((c, h, w))
    return pks


def build_ridge(key, seed):
    pks = _peaks(seed)
    bm = bmesh.new()
    front, crest, back = [], [], []
    for i in range(N_VERTS + 1):
        t = i / N_VERTS
        x = (t - 0.5) * LENGTH
        y = BOW * (1.0 - (2.0 * t - 1.0) ** 2)            # plan bow toward the town
        base = BASE_HT * (0.6 + 0.4 * math.sin(t * 9.7 + seed))
        z = max([base] + [h * math.exp(-((t - c) ** 2) / (2.0 * w * w))
                          for (c, h, w) in pks])
        ends = min(1.0, t * 6.0, (1.0 - t) * 6.0)         # taper to low ends so
        z = z * (0.25 + 0.75 * ends)                      # instances overlap cleanly
        th = HALF_TH * (0.45 + 0.55 * ends)
        front.append(bm.verts.new((x, y + th, -SINK)))
        crest.append(bm.verts.new((x, y, z)))
        back.append(bm.verts.new((x, y - th, -SINK)))
    n = len(crest)
    for i in range(n - 1):
        bm.faces.new([front[i], front[i + 1], crest[i + 1], crest[i]])
        bm.faces.new([crest[i], crest[i + 1], back[i + 1], back[i]])
    bm.faces.new([front[0], crest[0], back[0]])
    bm.faces.new([back[n - 1], crest[n - 1], front[n - 1]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _blank._new_obj("T_range_" + key, bm, _rim.rock_material())


def main():
    _street.reset()
    for key, seed in RIDGES.items():
        ob = build_ridge(key, seed)
        path = os.path.join(_street.out_dir(), "T_range_%s.glb" % key)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                                  use_selection=True, export_apply=True,
                                  export_yup=True, export_materials='EXPORT')
        print("  T_range_%s.glb  %d bytes" % (key, os.path.getsize(path)))
        bpy.data.objects.remove(ob, do_unlink=True)


if __name__ == "__main__":
    print("=== gen_range: the far layer ===")
    main()
    print("=== gen_range: done ===")
