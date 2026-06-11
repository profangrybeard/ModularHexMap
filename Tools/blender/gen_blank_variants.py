"""Blank-variant generator — open ground is OCCUPIED ground (Roadmap layer 3).

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_blank_variants.py

Every blank frontier tile is a SOUL's home; absence should read as tended ground,
not void (director, 2026-06-11). This kit gives the resolver weighted siblings for
the road-mask-0 / water-mask-0 cell: the plain T_street_blank stays in the pool;
these add the Bloomsbury garden-square energy. Blockout discipline: style over
fidelity, flat-shaded masses, the street kit's exact canvas (parametric base slab +
full-hex pavement + border lip from gen_curved_tiles), everything walkable — low
steps only, railing rings broken by gate gaps, aprons at all six edge midpoints
left clear so neighbours meet flush.

Variants (T_blank_<key>):
  garden    — railed circular green, two gates, centre plinth + column, shrubs
  green     — informal common: off-centre lawn, desire-line path, one tree, mounds
  allotment — working ground: two ranks of raised beds, shed, compost bin

Materials: M_HexGround / M_Pavement / M_TileBorder from the street kit, plus
M_Green (created here, fake-user, like M_TileBorder). NO material may contain
'Road' or 'Water' in its name — the engine's calibration measures those keys, and
these tiles must measure (0, 0) on both layers.

Writes blank_kit.json next to the .glbs (names + masks + default Weight) — the
single source for Tools/setup_blank_variants.py catalog wiring, mirroring how
river_kit.json drives setup_river.py. NEVER saves the master. Idempotent.
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

# The street kit owns the canvas: reuse its constants + base/pave/border builders so
# the variants can never drift from the contract (R, slab heights, border, materials).
import gen_curved_tiles as _street

R        = _street.R
TOP      = _street.TOP
PAVE_TOP = _street.PAVE_TOP
INR      = _street.INR

GREEN_RGB = (0.085, 0.205, 0.075, 1.0)   # muted London-park green (blockout flat colour)

# Default resolver pick weight per variant (FHexTileDef::Weight). The plain
# T_street_blank row keeps the C++ default of 1.0 — at 1.0 each, plain void is a
# 25% draw. The director's dial lives in DA_HexTileSet_Streets, not here.
VARIANTS = {
    "garden":    1.0,
    "green":     1.0,
    "allotment": 1.0,
}


# ---- shared low-level builders (manual bmesh: stable across Blender versions) ----
def green_material():
    """Lawn material. Name deliberately contains neither 'Road' nor 'Water'."""
    m = bpy.data.materials.get("M_Green")
    if m is None:
        m = bpy.data.materials.new("M_Green")
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = GREEN_RGB
        m.use_fake_user = True
    return m


def _rot2(x, y, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c)


def _new_obj(name, bm, mat):
    me = bpy.data.meshes.new(name + "_m")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    return o


def _box_into(bm, cx, cy, sx, sy, z0, z1, rot_deg=0.0):
    """Axis-aligned box (optionally yawed) as a closed solid in bmesh."""
    hx, hy = sx * 0.5, sy * 0.5
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    pts = [(_rot2(x, y, rot_deg)[0] + cx, _rot2(x, y, rot_deg)[1] + cy) for x, y in corners]
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([bot[i], bot[j], top[j], top[i]])


def _disc_into(bm, cx, cy, r, z0, z1, segs=48):
    """Solid low cylinder (lawn pad / mound base)."""
    ang = [2.0 * math.pi * k / segs for k in range(segs)]
    bot = [bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z0)) for a in ang]
    top = [bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z1)) for a in ang]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new([bot[i], bot[j], top[j], top[i]])


def _blob_into(bm, cx, cy, cz, r, z_squash=1.0, segs=10):
    """Squashed uv-sphere blob (shrub / canopy / mound cap)."""
    out = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=max(6, segs - 2),
                                    radius=r)
    for v in out["verts"]:
        v.co.x += cx
        v.co.y += cy
        v.co.z = v.co.z * z_squash + cz


def _arc_pts(cx, cy, r, a0_deg, a1_deg, segs):
    return [(cx + r * math.cos(math.radians(a0_deg + (a1_deg - a0_deg) * k / segs)),
             cy + r * math.sin(math.radians(a0_deg + (a1_deg - a0_deg) * k / segs)))
            for k in range(segs + 1)]


# ---- the three variants (masses on the blank canvas; canvas added by build_tile_obj) ----
def _masses_garden(objs, key, m_green, m_pave, m_border):
    lawn_r = 5.8
    lawn_top = PAVE_TOP + 0.08
    bm = bmesh.new()
    _disc_into(bm, 0.0, 0.0, lawn_r, PAVE_TOP - 0.02, lawn_top)
    # 4 shrub blobs inside the rail, clear of both gates
    for h in (45, 135, 225, 315):
        x, y = _rot2(0.0, 4.3, h - 90)
        _blob_into(bm, x, y, lawn_top + 0.30, 0.55, z_squash=0.8)
    objs.append(_new_obj(key + "_lawn", bm, m_green))

    # Iron rail: posts + top-rail bands, broken by two 40-degree gates facing
    # edges 0 (+Y, 90 deg) and 3 (-Y, 270 deg) so the square never blocks a walk.
    rail_r, post_h = 6.15, 0.85
    gates = ((70, 110), (250, 290))
    bm = bmesh.new()
    for k in range(20):
        a = 360.0 * k / 20
        if any(g0 <= a <= g1 for g0, g1 in gates):
            continue
        x, y = rail_r * math.cos(math.radians(a)), rail_r * math.sin(math.radians(a))
        _box_into(bm, x, y, 0.07, 0.07, lawn_top, lawn_top + post_h, rot_deg=a)
    for a0, a1 in ((110, 250), (290, 430)):     # the two arcs BETWEEN the gates
        pts = _arc_pts(0.0, 0.0, rail_r, a0, a1, 28)
        _street.sweep_into(bm, pts, 0.035, lawn_top + post_h - 0.07, lawn_top + post_h)
    objs.append(_new_obj(key + "_rail", bm, m_border))

    # Centre feature: plinth + column (stone)
    bm = bmesh.new()
    _box_into(bm, 0.0, 0.0, 1.0, 1.0, lawn_top, lawn_top + 0.45)
    _box_into(bm, 0.0, 0.0, 0.42, 0.42, lawn_top + 0.45, lawn_top + 2.0)
    objs.append(_new_obj(key + "_monument", bm, m_pave))


def _masses_green(objs, key, m_green, m_pave, m_border):
    lawn_cx, lawn_cy, lawn_r = 0.7, 0.4, 6.9
    lawn_top = PAVE_TOP + 0.06
    bm = bmesh.new()
    _disc_into(bm, lawn_cx, lawn_cy, lawn_r, PAVE_TOP - 0.02, lawn_top)
    # two grass mounds: strongly squashed lenses so the cap shows but the underside
    # stays inside the base slab (bottom must never dip below the tile's z=0)
    _blob_into(bm, 3.2, -2.2, lawn_top + 0.30 - 0.42, 1.4, z_squash=0.3)
    _blob_into(bm, -3.4, 2.8, lawn_top + 0.22 - 0.33, 1.1, z_squash=0.3)
    objs.append(_new_obj(key + "_lawn", bm, m_green))

    # Desire-line path worn between the edge-1 and edge-4 aprons: a smooth lazy S
    # (cubic through two pulled control points — the street kit's bezier, so no
    # hard corners), proud of the grass so it reads as trodden gravel, NOT road.
    e1, e4 = _street.edge_mid(1), _street.edge_mid(4)
    s = 6.4 / INR                              # pull endpoints just inside the lawn rim
    pts = _street._bezier3((e1[0] * s, e1[1] * s), (2.4, 2.6), (-2.0, -2.4),
                           (e4[0] * s, e4[1] * s), 22)
    bm = bmesh.new()
    _street.sweep_into(bm, pts, 0.65, lawn_top - 0.01, lawn_top + 0.015)
    objs.append(_new_obj(key + "_path", bm, m_pave))

    # One tree: dark trunk, green canopy — the common's landmark.
    bm = bmesh.new()
    _box_into(bm, -2.6, -1.8, 0.24, 0.24, lawn_top, lawn_top + 1.7)
    objs.append(_new_obj(key + "_trunk", bm, m_border))
    bm = bmesh.new()
    _blob_into(bm, -2.6, -1.8, lawn_top + 2.5, 1.6, z_squash=0.85, segs=12)
    objs.append(_new_obj(key + "_canopy", bm, m_green))


def _masses_allotment(objs, key, m_green, m_pave, m_border):
    m_grnd = bpy.data.materials["M_HexGround"]
    tilt = 18.0                                 # informal working-ground rotation
    bm = bmesh.new()
    # Beds: timber frame (ground material) with a planted top proud of the frame —
    # two solids per bed so the rows read as RAISED beds, not painted stripes.
    frames = bmesh.new()
    for rank in (-1.55, 1.55):
        for col in (-4.0, 0.0, 4.0):
            if rank > 0 and col > 0:
                continue                        # the shed stands on the sixth plot
            cx, cy = _rot2(col - 0.3, rank + 0.2, tilt)
            _box_into(frames, cx, cy, 3.3, 1.6, PAVE_TOP - 0.02, PAVE_TOP + 0.45,
                      rot_deg=tilt)
            _box_into(bm, cx, cy, 3.0, 1.3, PAVE_TOP + 0.30, PAVE_TOP + 0.55,
                      rot_deg=tilt)
    objs.append(_new_obj(key + "_bedframes", frames, m_grnd))
    objs.append(_new_obj(key + "_beds", bm, m_green))

    bm = bmesh.new()                            # weathered-timber shed (not ink-black)
    _box_into(bm, 4.9, 3.4, 1.7, 1.4, PAVE_TOP, PAVE_TOP + 1.9, rot_deg=tilt)
    objs.append(_new_obj(key + "_shed", bm, m_grnd))

    bm = bmesh.new()                            # compost bin, tucked by the shed
    _box_into(bm, 3.3, 4.6, 1.0, 1.0, PAVE_TOP, PAVE_TOP + 0.7, rot_deg=tilt)
    objs.append(_new_obj(key + "_compost", bm, m_border))


_MASSES = {
    "garden":    _masses_garden,
    "green":     _masses_green,
    "allotment": _masses_allotment,
}


# ---- registry-compatible build + headless export (mirrors gen_curved_tiles) ----
def build_tile_obj(key, edges=None):
    """Build one blank-variant tile and return the joined object (no export/cleanup).
    `edges` accepted (always empty) so the registry can treat us like a street tile."""
    m_pave = bpy.data.materials["M_Pavement"]
    m_grnd = bpy.data.materials["M_HexGround"]
    m_border = _street.border_material()
    m_green = green_material()

    name = "T_blank_" + key
    base = _street.hex_prism(name, 0.0, TOP, m_grnd)
    pave = _street.hex_prism(key + "_pave", TOP, PAVE_TOP, m_pave)
    border = _street.hex_border(key + "_border", m_border)
    objs = [base, pave, border]

    _MASSES[key](objs, key, m_green, m_pave, m_border)

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
    path = os.path.join(_street.out_dir(), "T_blank_%s.glb" % key)
    bpy.ops.object.select_all(action='DESELECT')
    base.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              use_selection=True, export_apply=True,
                              export_yup=True, export_materials='EXPORT')
    bpy.data.objects.remove(base, do_unlink=True)
    return os.path.basename(path), os.path.getsize(path)


def write_kit_json():
    """blank_kit.json — masks are zero by definition; Weight is the resolver dial's
    starting value. Single source for setup_blank_variants.py (cf. river_kit.json)."""
    kit = {"tiles": {("T_blank_%s" % k): {"road_mask": 0, "water_mask": 0, "weight": w}
                     for k, w in VARIANTS.items()}}
    path = os.path.join(_street.out_dir(), "blank_kit.json")
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
    print("=== gen_blank_variants: writing to %s ===" % _street.out_dir())
    for key in VARIANTS:
        tile = "T_blank_%s" % key
        if tile in bespoke:
            print("  %-28s SKIPPED (bespoke)" % tile)
            continue
        fn, sz = make_tile(key)
        print("  %-28s %6d bytes" % (fn, sz))
    print("  %s" % write_kit_json())
    print("=== gen_blank_variants: done ===")


if __name__ == "__main__":
    main()
