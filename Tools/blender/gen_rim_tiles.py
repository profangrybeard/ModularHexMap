"""Rim-tile generator — ring 7 IS the water (Docs/Rim.md B2, the Ringwater).

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_rim_tiles.py

Director's ruling (2026-06-12, after the per-tile notch cuts failed to read as
one body of water): "design the entire ring 7 as a continuous waterway that can
be rerolled to match any water connection. The waterway can grow, shrink and
eat almost all of the ring-7 tiles. Ring seven is just to host this waterway
and make the city's boundary look nice."

THE RINGWATER MODEL — water from the INWARD EDGE outward:
  * Every ring-7 tile's water surface TOUCHES its inward edge (ring 6's slab
    face is the quay, exactly like the in-town river banks). Because the whole
    ring is water at the seam, ANY river mouth connects ANYWHERE, on every
    reroll, by construction — the "match any water connection" requirement is
    structural, not special-cased. (Engine side: BuildRim forces the inward
    water bit on every station — the ring water law.)
  * The OUTER bankline meanders per tile: gentle arc, lazy S, double bulge, or
    the wide variant that eats ~85% of the tile. Variants are Weight-pooled and
    seeded per destiny — rerolling the town rerolls the water's shape.
  * THE CONTINUITY CONTRACT (what the notch cuts lacked): the bankline crosses
    each SIDE edge at ONE canonical point (2.0 m down the side edge from the
    inward vertex), and all meander happens between the crossings. Any tile
    therefore meets any tile with an unbroken waterline. The crossing point
    sits ~3.0 m from the side-edge MIDPOINT, outside the 250 uu measure radius,
    so side-edge water never pollutes the measured masks.
  * Exits = the bridge tile: full-width water + a gate-bridge deck (M_Road —
    the edge-0 road measure) landing on the outer bank, gate posts, and the
    road running off the outward edge into the haze (B3's fog owns the rest).
  * RETIRED: the notched slab, the separate loop mesh (gen_waterway.py), and
    the whole land grammar (banks/berms/knoll/tunnel/adit/pass/mouth works) —
    ring 7 hosts the water, the parallax lives in the off-grid Range rings.

Writes rim_kit.json for Tools/setup_rim.py (which prunes the retired rows and
deletes their orphaned assets). NEVER saves the master. Idempotent.
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
import gen_blank_variants as _blank

R        = _street.R
TOP      = _street.TOP
PAVE_TOP = _street.PAVE_TOP
INR      = _street.INR
HW       = _street.HW

WATER_Z  = _river.WATER_Z        # -0.9 (the river's surface — flush at mouths)
FLOOR_Z  = _river.FLOOR_Z        # -2.0
ROCK_RGBA = (0.23, 0.205, 0.18, 1.0)

# Canonical side crossing: 5.5 m down the side edge from the inward vertex —
# the water occupies that whole 5.5 m stretch of every shared edge, so the
# waterline crosses seams at FULL WIDTH (the 2 m pinch of the first draft read
# as separate ponds). Legal since the rim resolver compares the INWARD edge
# only; side-edge water never participates in resolution.
# Side edge runs (5, INR) -> (10, 0); unit (0.5, -0.866).
CROSS = (5.0 + 5.5 * 0.5, INR - 5.5 * 0.86602540378)   # (7.75, 3.90)

# (road_mask, water_mask, weight). The authored water mask is the HONEST mirror
# of what calibration MEASURES in-engine (the popcount law): the two side-edge
# seam crossings register (the inward surface sits at the tolerance boundary
# post-import and does not), so measured water = 2 bits on every ring tile —
# authored 0x14 to match. Rim resolution doesn't read the water mask at all
# (key + road only; the ring water law makes every station water by design).
# Bridge: deck + landing road = road on edges 0 and 3 (0b001001 = 9).
VARIANTS = {
    "water_a":    (0, 20, 1.0),   # gentle arc bank, boulders
    "water_b":    (0, 20, 1.0),   # lazy S bank, reed posts
    "water_c":    (0, 20, 0.7),   # double bulge, a worn jetty
    "water_wide": (0, 20, 0.5),   # eats ~85% — a sliver of far bank
    "bridge":     (9, 20, 1.0),   # artery exit: deck over the ring
}


def rock_material():
    m = bpy.data.materials.get("M_Rock")
    if m is None:
        m = bpy.data.materials.new("M_Rock")
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


def _rimkey(name):
    """Orientation marker at the inward edge midpoint, sunk below the bed."""
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in ((-0.4, INR - 0.05, -2.1),
                                   (0.4, INR - 0.05, -2.1),
                                   (0.0, INR - 0.45, -2.1))]
    bm.faces.new(v)
    return _blank._new_obj(name, bm, rimkey_material())


def _top_edge(x):
    """The tile boundary on the inward side: edge 0 for |x|<=5, then the upper
    side edges out to the lateral vertices."""
    if abs(x) <= 5.0:
        return INR
    return INR - (abs(x) - 5.0) * (INR / 5.0)


def _bot_edge(x):
    """The tile boundary on the outward side (mirror)."""
    return -_top_edge(x)


def _bankline(key, x):
    """Outer bankline y(x) between the canonical side crossings (±7.75, 3.90).
    All meander lives between the crossings; the seam water is the full 5.5 m
    edge stretch, so width varies smoothly tile-to-tile instead of pinching."""
    u = max(-1.0, min(1.0, x / CROSS[0]))
    end_y = CROSS[1]                              # 3.90 at u = ±1
    t = 1.0 - u * u                               # 0 at crossings, 1 mid-tile
    if key == "water_a":
        mid = 2.0
    elif key == "water_b":
        mid = 3.0 - 2.6 * math.sin(u * 2.6)       # lazy S
    elif key == "water_c":
        mid = 2.4 - 2.2 * math.cos(u * 3.4)       # double bulge
    elif key == "water_wide":
        mid = -5.9    # eats almost everything (clamped: the bankline must stay
                      # >2.5 m from the OUTWARD edge midpoint or the measured
                      # water gains a 4th bit and calibration distrusts again)
    else:                                          # bridge: generous, steady
        mid = 1.0
    return end_y + (mid - end_y) * t


def _water_body(key, objs, mats):
    """Water surface + bed + bank wall + outer bank land, as column strips.
    |x| <= 6 (between the canonical crossings): water from the inward boundary
    to the bankline, land from the bankline to the outer boundary. |x| > 6 (the
    lateral wedges toward the side vertices): land only, full span — the water
    pinches to the crossing exactly, so neighbouring tiles' waterlines meet at
    one shared point per seam. Clean, manifold-enough blockout."""
    surf = bmesh.new()
    bed = bmesh.new()
    land = bmesh.new()
    wall = bmesh.new()
    N = 40
    xs = [-9.99 + 19.98 * i / N for i in range(N + 1)]
    prev = None
    for x in xs:
        in_water = abs(x) <= CROSS[0]
        ty = _top_edge(x) + (0.3 if abs(x) <= 5.0 else 0.0)   # inward overshoot
        by = _bankline(key, x) if in_water else ty            # wedge: land from the top
        ly = _bot_edge(x)
        cur = {
            "in_water": in_water,
            "s0": surf.verts.new((x, ty, WATER_Z)), "s1": surf.verts.new((x, by + 0.12, WATER_Z)),
            "b0": bed.verts.new((x, ty, FLOOR_Z)),  "b1": bed.verts.new((x, by, FLOOR_Z)),
            "w0": wall.verts.new((x, by, FLOOR_Z)), "w1": wall.verts.new((x, by, PAVE_TOP)),
            "l0": land.verts.new((x, by, PAVE_TOP)), "l1": land.verts.new((x, ly, PAVE_TOP)),
            "lw0": land.verts.new((x, ly, PAVE_TOP)), "lw1": land.verts.new((x, ly, 0.0)),
        }
        if prev is not None:
            if prev["in_water"] and cur["in_water"]:
                surf.faces.new([prev["s0"], prev["s1"], cur["s1"], cur["s0"]])
                bed.faces.new([prev["b0"], prev["b1"], cur["b1"], cur["b0"]])
                wall.faces.new([prev["w0"], prev["w1"], cur["w1"], cur["w0"]])
            land.faces.new([prev["l0"], prev["l1"], cur["l1"], cur["l0"]])
            land.faces.new([prev["lw0"], prev["lw1"], cur["lw1"], cur["lw0"]])
        prev = cur
    for bmx, nm, mat in ((surf, "_water", mats["water"]), (bed, "_bed", mats["grnd"]),
                         (wall, "_bankwall", mats["grnd"]), (land, "_bank", mats["pave"])):
        bmesh.ops.recalc_face_normals(bmx, faces=bmx.faces)
        objs.append(_blank._new_obj(key + nm, bmx, mat))


def _dressing(key, objs, mats):
    if key == "water_a":
        bm = bmesh.new()
        for x, y, r in ((-2.4, 1.4, 0.7), (3.0, 2.2, 0.55)):
            _blank._blob_into(bm, x, y, PAVE_TOP + r * 0.4, r, z_squash=0.7, segs=8)
        objs.append(_blank._new_obj(key + "_boulders", bm, mats["rock"]))
    elif key == "water_b":
        bm = bmesh.new()
        for i, (x, y) in enumerate(((-3.6, 3.2), (-3.0, 2.6), (4.0, 1.8))):
            _blank._box_into(bm, x, y, 0.12, 0.12, WATER_Z, PAVE_TOP + 0.9)
        objs.append(_blank._new_obj(key + "_reeds", bm, mats["green"]))
    elif key == "water_c":
        bm = bmesh.new()                          # a worn jetty over the water
        _blank._box_into(bm, 1.2, 4.6, 1.1, 3.2, WATER_Z + 0.55, WATER_Z + 0.75)
        _blank._box_into(bm, 0.8, 3.4, 0.16, 0.16, FLOOR_Z, WATER_Z + 0.75)
        _blank._box_into(bm, 1.6, 5.6, 0.16, 0.16, FLOOR_Z, WATER_Z + 0.75)
        objs.append(_blank._new_obj(key + "_jetty", bm, mats["border"]))
    elif key == "bridge":
        bm = bmesh.new()                          # deck: inward edge -> outer bank
        _street.sweep_into(bm, [(0.0, INR + 0.3), (0.0, 0.6)], HW,
                           TOP - _river.DECK_T, TOP + 0.01)
        objs.append(_blank._new_obj(key + "_deck", bm, mats["road"]))
        bm = bmesh.new()
        for side in (-1, 1):
            _blank._box_into(bm, side * (HW + _river.PARAPET_W / 2), (INR + 0.6) / 2,
                             _river.PARAPET_W, INR + 0.3 - 0.6, TOP, TOP + _river.PARAPET_H)
        objs.append(_blank._new_obj(key + "_parapets", bm, mats["pave"]))
        bm = bmesh.new()                          # landing road off the outward edge
        _street.sweep_into(bm, [(0.0, 0.8), (0.0, -INR - 0.3)], HW,
                           TOP - 0.02, TOP + 0.01)
        objs.append(_blank._new_obj(key + "_outroad", bm, mats["road"]))
        bm = bmesh.new()                          # gate posts at the landing
        _blank._box_into(bm, -2.0, 0.2, 0.3, 0.3, PAVE_TOP, PAVE_TOP + 1.6)
        _blank._box_into(bm, 2.0, 0.2, 0.3, 0.3, PAVE_TOP, PAVE_TOP + 1.6)
        objs.append(_blank._new_obj(key + "_gate", bm, mats["border"]))


def build_tile_obj(key, edges=None):
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
    # No slab canvas: the tile IS its water body + outer bank.
    objs = []
    _water_body(key, objs, mats)
    _dressing(key, objs, mats)
    objs.append(_rimkey(key + "_key"))

    base = objs[0]
    base.name = name
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


def main():
    _street.reset()
    try:
        import tile_common
        bespoke = tile_common.bespoke_tile_names()
    except Exception:
        bespoke = set()
    print("=== gen_rim_tiles (the Ringwater): writing to %s ===" % _street.out_dir())
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
