"""Rim-tile generator — ring 7, take two: LOW AND BROKEN (Docs/Rim.md B2).

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_rim_tiles.py

The first B2 pass failed the only judge that matters: from street eye height,
a continuous ring of hills occluded the Range entirely (reverted 9fcaaec; the
sight-line lesson is in the worklog). Take two, per the director's "both"
ruling: ring 7 is FLAT — waterway band + meadow/shingle banks — with sparse low
BERM CLUSTERS (<= 2.8 m, broken, gaps everywhere) on a minority of stations.
The parallax lives in the sky band instead: TWO Range rings at different radii
(gen_range.py + setup_scenery.py). Sight-line math at eye 2.4 m: berms subtend
~3 degrees at 15 m; the near Range ~13 degrees at 250 m; the far Range ~16
degrees at 500 m — everything visible, far stacking above near, town-wide.
The one tall thing is the tunnel KNOLL (6 m, a single station, locally walked
around — a portal needs a hill to enter).

Kit (T_rim_<key>, Weight-pooled like the gardens):
  bank_a   meadow bank: grass, footpath along the water        (1.0)
  bank_b   shingle bank: gravel patches, boulders              (1.0)
  berm_a   grassy mound cluster, rocky toes, side gaps         (0.5)
  berm_b   one low diagonal ridge-let + boulders               (0.5)
  adit     berm_a + sealed timber adit set into the big mound  (0.25)
  tunnel   the knoll: 6 m mound, gated portal, gate bridge     (1.0)
  pass     PARKED at Weight 0 (kept for a future ruling)       (0.0)
  outfall  flat bank + spill steps + hidden water key          (1.0)
  intake   flat bank + sill + grate bars + hidden water key    (1.0)

Carried over from the proven first pass: the notched canvas (every tile leaves
its inward BAND_W strip open — gen_waterway.py's single ring fills all 42), the
gate bridge (M_Road deck = the edge-0 measure), the RimKey sunk below the bed
(XY-only measurer), and the hidden underwater M_Water mouth keys.

Writes rim_kit.json for Tools/setup_rim.py. NEVER saves the master. Idempotent.
"""

import os
import sys
import json
import math
import bmesh
import bpy

_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
if _HERE and _HERE not in sys.path:
    sys.path.append(_HERE)

import gen_curved_tiles as _street
import gen_river_tiles as _river
import gen_blank_variants as _blank   # _box_into/_blob_into/_disc_into helpers

R        = _street.R
TOP      = _street.TOP
PAVE_TOP = _street.PAVE_TOP
INR      = _street.INR
HW       = _street.HW

BAND_W   = 3.6                  # the waterway band (the loop mesh fills it)
CUT_Y    = INR - BAND_W
BERM_H   = 2.8                  # berms never exceed this (sight-line law)
KNOLL_H  = 6.0                  # the tunnel's hill — one station, walked around
ROCK_RGBA = (0.23, 0.205, 0.18, 1.0)

# (road_mask, water_mask, weight) — masks authored on edge 0 (inward).
VARIANTS = {
    "bank_a":  (0, 0, 1.0),
    "bank_b":  (0, 0, 1.0),
    "berm_a":  (0, 0, 0.5),
    "berm_b":  (0, 0, 0.5),
    "adit":    (0, 0, 0.25),
    "tunnel":  (1, 0, 1.0),
    "pass":    (1, 0, 0.0),    # PARKED: rim is flat now; a pass needs a ridge
    "outfall": (0, 1, 1.0),
    "intake":  (0, 1, 1.0),
}


def rock_material():
    m = bpy.data.materials.get("M_Rock")
    if m is None:
        m = bpy.data.materials.new("M_Rock")   # no 'Road'/'Water' substrings
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        if b:
            b.inputs["Base Color"].default_value = ROCK_RGBA
        m.use_fake_user = True
    return m


def rimkey_material():
    m = bpy.data.materials.get("M_RimKey")
    if m is None:
        m = bpy.data.materials.new("M_RimKey")
        m.use_fake_user = True
    return m


def _xmax(y):
    return R - abs(y) * (R - R * 0.5) / INR


def _notched_prism(name, z0, z1, mat):
    """The rim canvas: the hex with the inward waterway band cut away."""
    pts = [(-_xmax(CUT_Y), CUT_Y), (_xmax(CUT_Y), CUT_Y), (R, 0.0),
           (R * 0.5, -INR), (-R * 0.5, -INR), (-R, 0.0)]
    me = bpy.data.meshes.new(name + "_m")
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new([bot[i], bot[j], top[j], top[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    return o


def _rimkey(name):
    """Orientation marker at the inward (edge 0) midpoint, sunk below the
    waterway bed (-2.1; the measurer is XY-only — depth is free invisibility)."""
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in ((-0.4, INR - 0.05, -2.1),
                                   (0.4, INR - 0.05, -2.1),
                                   (0.0, INR - 0.45, -2.1))]
    bm.faces.new(v)
    return _blank._new_obj(name, bm, rimkey_material())


def _hidden_water_key(name, mats):
    """Mouth identity: an M_Water patch 3 cm under the loop's -0.9 surface."""
    bm = bmesh.new()
    _blank._box_into(bm, 0.0, INR - 0.35, 1.0, 0.6, -0.96, -0.93)
    return _blank._new_obj(name, bm, mats["water"])


def _mound_into(bm, cx, cy, r, h, segs=10):
    """A grounded grassy mound: squashed blob whose underside stays inside the
    slab (never pokes below z=0)."""
    sq = max(0.18, h / r)
    cz = PAVE_TOP + h - r * sq
    if cz - r * sq < 0.05:                      # clamp: grounding law
        sq = (PAVE_TOP + h - 0.05) / (2.0 * r)
        cz = 0.05 + r * sq
    _blank._blob_into(bm, cx, cy, cz, r, z_squash=sq, segs=segs)


def _gate_bridge(objs, key, mats):
    """The exit's crossing: M_Road deck over the band (the edge-0 measure) with
    low parapets, inward edge to the far-bank walk."""
    y0, y1 = INR + 0.3, CUT_Y - 0.2
    bm = bmesh.new()
    _street.sweep_into(bm, [(0.0, y0), (0.0, y1)], HW, TOP - _river.DECK_T, TOP + 0.01)
    objs.append(_blank._new_obj(key + "_deck", bm, mats["road"]))
    bm = bmesh.new()
    for side in (-1, 1):
        _blank._box_into(bm, side * (HW + _river.PARAPET_W / 2), (y0 + y1) / 2,
                         _river.PARAPET_W, y0 - y1, TOP, TOP + _river.PARAPET_H)
    objs.append(_blank._new_obj(key + "_parapets", bm, mats["pave"]))


# ---- the take-two masses (all low, all broken) ----
def _masses_bank_a(objs, key, mats):    # meadow bank
    bm = bmesh.new()
    _blank._disc_into(bm, -1.8, 0.2, 4.6, PAVE_TOP - 0.02, PAVE_TOP + 0.06, segs=20)
    _blank._disc_into(bm, 3.6, -3.0, 3.2, PAVE_TOP - 0.02, PAVE_TOP + 0.05, segs=16)
    objs.append(_blank._new_obj(key + "_meadow", bm, mats["green"]))
    bm = bmesh.new()                     # footpath along the water
    _street.sweep_into(bm, [(-_xmax(CUT_Y) + 0.8, CUT_Y - 1.1), (0.6, CUT_Y - 1.5),
                            (_xmax(CUT_Y) - 0.8, CUT_Y - 1.0)], 0.55,
                       PAVE_TOP + 0.045, PAVE_TOP + 0.07)
    objs.append(_blank._new_obj(key + "_path", bm, mats["pave"]))


def _masses_bank_b(objs, key, mats):    # shingle bank
    bm = bmesh.new()
    _blank._disc_into(bm, 1.2, 1.0, 3.8, PAVE_TOP - 0.02, PAVE_TOP + 0.04, segs=18)
    _blank._disc_into(bm, -3.4, -2.2, 2.6, PAVE_TOP - 0.02, PAVE_TOP + 0.035, segs=14)
    objs.append(_blank._new_obj(key + "_shingle", bm, mats["pave"]))
    bm = bmesh.new()
    for x, y, r in ((-1.0, 0.8, 0.7), (2.6, -1.4, 0.9), (-4.2, -4.0, 0.6),
                    (0.8, -5.0, 0.75)):
        _blank._blob_into(bm, x, y, PAVE_TOP + r * 0.45, r, z_squash=0.7, segs=8)
    objs.append(_blank._new_obj(key + "_boulders", bm, mats["rock"]))


def _masses_berm_a(objs, key, mats):    # grassy mound cluster, gaps at the sides
    bm = bmesh.new()
    _mound_into(bm, -1.6, -2.6, 4.2, BERM_H)
    _mound_into(bm, 2.8, -5.0, 3.0, 1.9)
    _mound_into(bm, 1.4, -0.6, 2.2, 1.2)
    objs.append(_blank._new_obj(key + "_mounds", bm, mats["green"]))
    bm = bmesh.new()                     # rocky toes
    for x, y, r in ((-4.6, -1.6, 0.6), (1.0, -7.4, 0.7), (4.6, -3.8, 0.5)):
        _blank._blob_into(bm, x, y, PAVE_TOP + r * 0.4, r, z_squash=0.65, segs=8)
    objs.append(_blank._new_obj(key + "_toes", bm, mats["rock"]))


def _masses_berm_b(objs, key, mats):    # one low diagonal ridge-let
    bm = bmesh.new()
    for i in range(4):                   # overlapping lenses = a soft ridge line
        t = i / 3.0
        _mound_into(bm, -3.6 + 7.0 * t, -1.2 - 4.2 * t, 2.6, BERM_H * (0.75 + 0.25 * math.sin(t * 3.1)))
    objs.append(_blank._new_obj(key + "_ridge", bm, mats["green"]))
    bm = bmesh.new()
    for x, y, r in ((2.2, -1.0, 0.8), (-2.0, -6.2, 0.65)):
        _blank._blob_into(bm, x, y, PAVE_TOP + r * 0.4, r, z_squash=0.7, segs=8)
    objs.append(_blank._new_obj(key + "_boulders", bm, mats["rock"]))


def _masses_adit(objs, key, mats):      # berm cluster + the sealed adit in its face
    _masses_berm_a(objs, key, mats)
    bm = bmesh.new()
    _blank._box_into(bm, -2.6, 0.4, 0.3, 0.3, PAVE_TOP, PAVE_TOP + 1.9)   # posts
    _blank._box_into(bm, -0.6, 0.4, 0.3, 0.3, PAVE_TOP, PAVE_TOP + 1.9)
    _blank._box_into(bm, -1.6, 0.4, 2.6, 0.35, PAVE_TOP + 1.7, PAVE_TOP + 2.1)  # lintel
    _blank._box_into(bm, -1.6, -0.4, 1.9, 1.6, PAVE_TOP, PAVE_TOP + 1.65)       # seal
    objs.append(_blank._new_obj(key + "_adit", bm, mats["border"]))


def _masses_tunnel(objs, key, mats):
    _gate_bridge(objs, key, mats)
    bm = bmesh.new()                     # the knoll: one station's hill
    _mound_into(bm, 0.0, -2.8, 6.2, KNOLL_H, segs=12)
    objs.append(_blank._new_obj(key + "_knoll", bm, mats["green"]))
    bm = bmesh.new()                     # far-bank road to the portal
    _street.sweep_into(bm, [(0.0, CUT_Y - 0.1), (0.0, 1.0)], HW,
                       TOP - 0.02, TOP + 0.01)
    objs.append(_blank._new_obj(key + "_apron", bm, mats["road"]))
    bm = bmesh.new()                     # portal set into the knoll face
    _blank._box_into(bm, -2.1, 0.6, 1.1, 2.0, PAVE_TOP, PAVE_TOP + 3.6)
    _blank._box_into(bm, 2.1, 0.6, 1.1, 2.0, PAVE_TOP, PAVE_TOP + 3.6)
    _blank._box_into(bm, 0.0, 0.6, 5.3, 2.2, PAVE_TOP + 3.3, PAVE_TOP + 4.3)
    objs.append(_blank._new_obj(key + "_portal", bm, mats["rock"]))
    bm = bmesh.new()
    _blank._box_into(bm, 0.0, 0.1, 3.0, 1.5, TOP, PAVE_TOP + 3.1)         # throat
    _blank._box_into(bm, -1.45, 2.6, 0.18, 0.18, TOP, TOP + 1.4)          # gateposts
    _blank._box_into(bm, 1.45, 2.6, 0.18, 0.18, TOP, TOP + 1.4)
    objs.append(_blank._new_obj(key + "_throat", bm, mats["border"]))


def _masses_pass(objs, key, mats):      # parked (Weight 0) — minimal valid tile
    _gate_bridge(objs, key, mats)
    bm = bmesh.new()
    _street.sweep_into(bm, [(0.0, CUT_Y - 0.1), (0.0, -4.0)], HW * 0.8,
                       TOP - 0.02, TOP + 0.01)
    objs.append(_blank._new_obj(key + "_trail", bm, mats["road"]))


def _water_mouth(objs, key, mats, outfall):
    objs.append(_hidden_water_key(key + "_wkey", mats))
    bm = bmesh.new()
    if outfall:
        for i in range(3):               # spill steps down toward the band
            _blank._box_into(bm, 0.0, CUT_Y - 0.25 - 0.45 * i, 5.4 - 1.2 * i, 0.45,
                             TOP - 0.55 - 0.35 * i, TOP + 0.05 - 0.30 * i)
    else:
        _blank._box_into(bm, 0.0, CUT_Y - 0.35, 5.8, 0.7, TOP - 0.4, TOP + 0.25)
        for i in range(5):
            _blank._box_into(bm, -2.0 + i, CUT_Y - 0.3, 0.14, 0.5, TOP - 1.4, TOP + 0.2)
    objs.append(_blank._new_obj(key + "_works", bm, mats["rock"]))
    bm = bmesh.new()
    for side in (-1, 1):
        _blank._box_into(bm, side * 3.3, CUT_Y - 0.5, 0.3, 0.3, PAVE_TOP, PAVE_TOP + 1.1)
    objs.append(_blank._new_obj(key + "_posts", bm, mats["border"]))


_MASSES = {
    "bank_a": _masses_bank_a, "bank_b": _masses_bank_b,
    "berm_a": _masses_berm_a, "berm_b": _masses_berm_b,
    "adit": _masses_adit, "tunnel": _masses_tunnel, "pass": _masses_pass,
    "outfall": lambda o, k, m: _water_mouth(o, k, m, True),
    "intake":  lambda o, k, m: _water_mouth(o, k, m, False),
}


def build_tile_obj(key, edges=None):
    """Registry-compatible: build one rim tile, return the joined object."""
    mats = {
        "rock": rock_material(),
        "grnd": bpy.data.materials["M_HexGround"],
        "pave": bpy.data.materials["M_Pavement"],
        "road": bpy.data.materials["M_Road"],
        "water": _river.water_material(),
        "green": _blank.green_material(),
        "border": _street.border_material(),
    }
    name = "T_rim_" + key
    base = _notched_prism(name, 0.0, TOP, mats["grnd"])
    objs = [base, _notched_prism(key + "_pave", TOP, PAVE_TOP, mats["pave"]),
            _rimkey(key + "_key")]
    _MASSES[key](objs, key, mats)

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


def make_tile(key):
    base = build_tile_obj(key)
    path = os.path.join(_street.out_dir(), "T_rim_%s.glb" % key)
    bpy.ops.object.select_all(action='DESELECT')
    base.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              use_selection=True, export_apply=True,
                              export_yup=True, export_materials='EXPORT')
    bpy.data.objects.remove(base, do_unlink=True)
    return os.path.basename(path), os.path.getsize(path)


def write_kit_json():
    kit = {"tiles": {("T_rim_%s" % k): {"road_mask": rm, "water_mask": wm,
                                        "weight": w, "family": "Rim"}
                     for k, (rm, wm, w) in VARIANTS.items()}}
    path = os.path.join(_street.out_dir(), "rim_kit.json")
    with open(path, "w") as f:
        json.dump(kit, f, indent=2)
        f.write("\n")
    return path


def _bespoke_names():
    try:
        import tile_common
        return tile_common.bespoke_tile_names()
    except Exception as exc:
        print("  (bespoke skip-list unavailable: %s)" % exc)
        return set()


def main():
    _street.reset()
    bespoke = _bespoke_names()
    print("=== gen_rim_tiles (take two): writing to %s ===" % _street.out_dir())
    for key in VARIANTS:
        tile = "T_rim_%s" % key
        if tile in bespoke:
            print("  %-28s SKIPPED (bespoke)" % tile)
            continue
        fn, sz = make_tile(key)
        print("  %-28s %7d bytes" % (fn, sz))
    print("  %s" % write_kit_json())
    print("=== gen_rim_tiles: done ===")


if __name__ == "__main__":
    main()
