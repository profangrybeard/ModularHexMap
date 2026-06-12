"""Rim-tile generator — the two-ring seam waterway (Docs/Rim.md, director's design
2026-06-12: "ring 7 is land on the city side, blank, river on the edge; ring 8 is
water on the inside edge completing the river bank, land blending to horizon —
a standard loop solves the water connectivity, then swap in the water and street
connection points.")

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_rim_tiles.py

THE SEAM CHANNEL: each ring contributes ONE BANK. Ring-7 tiles carry a
half-channel at their OUTWARD edge; ring-8 tiles carry the mirror half at their
INWARD edge. Every 7<->8 edge pairing is water-meets-water by construction —
water connectivity IS edge-socket matching, the grammar the whole kit already
lives by. The connection points are ordinary mask-matched variants: the river
mouth is a water "straight" (channel through, inward->outward), the street exit
is a bridge (road through + deck over the half-channel).

ORIENTATION IS THE MASK: every rim tile's water pattern is rotation-asymmetric,
so the resolver's normal measure-and-rotate places it — the M_RimKey marker and
the flank inference are DELETED (both could disagree with reality while agreeing
with themselves; a single measured water bit cannot).

Authoring convention: edge 0 = the WATER edge (the engine rotates it outward for
ring 7, inward for ring 8). The channel half holds ~3.8 m through the mid-edge
(quartic plateau, not a parabola — the v1 lens pinched at every seam and the
loop read as 42 beads; B2.1 gap pass 2026-06-12) easing to 2.6 m at the side
corners, where the band runs to |x| 6.1 so the RADIAL seams carry a deliberate
shared corner pool (side-edge midpoints stay ~2.8 m clear — the measured mask
stays single-bit). Cross-section matches the river kit (surface -0.9, floor
-2.0) so town-river mouths meet the loop flush.

Tiles (T_rim_<key>):
  land7    ring 7: town-side blank canvas + the outward half-channel      (1.0)
  river7   ring 7: the town river flows THROUGH into the loop (water 0,3) (1.0)
  exit7    ring 7: artery crosses on a deck + gateposts (road 0,3)        (1.0)
  bank8    ring 8: inward half-channel + low horizon land (<= 2.5 m)      (1.0)

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
import gen_blank_variants as _blank

R        = _street.R
TOP      = _street.TOP
PAVE_TOP = _street.PAVE_TOP
INR      = _street.INR
HW       = _street.HW

WATER_Z  = _river.WATER_Z          # -0.9
FLOOR_Z  = _river.FLOOR_Z          # -2.0
BAND_D   = 3.4                     # half-channel depth target (v2 gap pass — v1's 2.2 lens
                                   # pinched every seam into a pothole; near-constant width
                                   # is what reads as ONE river)
BAND_MID = 3.8                     # gentle mid-edge swell (life, not a lens)
BAND_CLIP = 6.1                    # band x-extent: the corner pool across the radial seam
MEAS_R   = 2.5                     # MeasureTileMask's NearDist (250 uu): ANY water vertex
                                   # within this EUCLIDEAN radius of an edge midpoint sets
                                   # that edge's measured bit. v2.1 ignored this and the
                                   # measured mask went 3-bit -> popcount mismatch ->
                                   # calibration DISTRUSTED the catalog -> authored-fallback
                                   # yaw -> every water edge flipped (director's screenshots,
                                   # 2026-06-12). The sampler discs are part of the contract.
MEAS_MARGIN = 0.25                 # authoring margin outside the sampler disc
ROCK_RGBA = (0.23, 0.205, 0.18, 1.0)

# (road_mask, water_mask, weight) in the AUTHORED frame (edge 0 = the water edge).
VARIANTS = {
    "land7":  (0, 1, 1.0),
    "river7": (0, 9, 1.0),     # water through: edges 0 and 3
    "exit7":  (9, 1, 1.0),     # road through (0,3) + the half-channel at 0
    "bank8":  (0, 1, 1.0),
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


def _band_y(x, key):
    """The bankline of the half-channel, measured from the WATER edge (edge 0 at
    y=+INR): water occupies y in [bank(x), INR]. Quartic PLATEAU: holds near
    BAND_MID through the middle and eases to BAND_D only near the corners — the
    v1 parabola dove steepest exactly at the seams, which is what beaded the
    loop (B2.1). The river/exit tiles keep a straight channel margin where
    their through-feature crosses."""
    u = max(-1.0, min(1.0, x / 5.0))
    d = BAND_D + (BAND_MID - BAND_D) * (1.0 - u ** 4)
    # Hug the measurer's exclusion discs: the side-edge midpoints sit at
    # (±7.5, INR/2); water inside MEAS_R of one would flip the measured mask
    # multi-bit and distrust the whole calibration. The bank sweeps around
    # the disc instead — the corner pool keeps every meter the sampler allows.
    r = MEAS_R + MEAS_MARGIN
    for mx in (-7.5, 7.5):
        dx2 = (x - mx) ** 2
        if dx2 < r * r:
            d = min(d, INR * 0.5 - math.sqrt(r * r - dx2))
    if key == "river7":
        d = max(d, 0.0)                     # the through-channel carves anyway
    return INR - d


def _top_edge(x):
    if abs(x) <= 5.0:
        return INR
    return INR - (abs(x) - 5.0) * (INR / 5.0)


def _half_channel(key, objs, mats):
    """Water + bed + bank wall along the edge-0 side. THE WATER IS CLOSED SOLID
    GEOMETRY — the saga's mechanical lesson (2026-06-12): the river kit's water
    has measured flawlessly forever because _swept_slab makes closed slabs; my
    open single-sided ribbons measured erratically (only their end columns
    registered). M_Water and M_Road must always be closed solids; unmeasured
    materials may stay ribbons. The surface is ONE closed strip following the
    bankline — the v1 axis-aligned box strips staircased against the sloped
    corner edges (the director's sawtooth screenshot, B2.1). Band ends clip at
    |x| BAND_CLIP so the radial seams carry the shared corner pool while the
    side-edge midpoints stay ~2.8 m clear (single measured bit); the surface
    overshoots its boundary edges (+0.3) to seam with the mirrored halves."""
    surf = bmesh.new()
    N = 40
    cols = []
    for j in range(N + 1):
        x = -BAND_CLIP + 2.0 * BAND_CLIP * j / N
        ty = _top_edge(x) + 0.3
        by = _band_y(x, key) + 0.1
        if by > ty - 0.2:
            by = ty - 0.2
        cols.append({
            "tb": surf.verts.new((x, by, WATER_Z)),
            "tt": surf.verts.new((x, ty, WATER_Z)),
            "bb": surf.verts.new((x, by, WATER_Z - 0.06)),
            "bt": surf.verts.new((x, ty, WATER_Z - 0.06)),
        })
    for a, b in zip(cols, cols[1:]):
        surf.faces.new([a["tb"], a["tt"], b["tt"], b["tb"]])   # top
        surf.faces.new([a["bb"], a["bt"], b["bt"], b["bb"]])   # bottom
        surf.faces.new([a["tt"], a["bt"], b["bt"], b["tt"]])   # outer wall
        surf.faces.new([a["tb"], a["bb"], b["bb"], b["tb"]])   # bank wall
    surf.faces.new([cols[0]["tb"], cols[0]["tt"], cols[0]["bt"], cols[0]["bb"]])
    surf.faces.new([cols[-1]["tb"], cols[-1]["tt"], cols[-1]["bt"], cols[-1]["bb"]])
    bmesh.ops.recalc_face_normals(surf, faces=surf.faces)
    bmesh.ops.remove_doubles(surf, verts=surf.verts, dist=1e-4)
    objs.append(_blank._new_obj(key + "_water", surf, mats["water"]))

    bed = bmesh.new()
    wall = bmesh.new()
    M = 30
    prev = None
    for j in range(M + 1):
        x = -6.4 + 12.8 * j / M
        ty = _top_edge(x) + (0.3 if abs(x) <= 5.0 else 0.0)
        by = min(_band_y(x, key), ty - 0.15)
        cur = {
            "b0": bed.verts.new((x, ty, FLOOR_Z)),  "b1": bed.verts.new((x, by, FLOOR_Z)),
            "w0": wall.verts.new((x, by, FLOOR_Z)), "w1": wall.verts.new((x, by, PAVE_TOP)),
        }
        if prev is not None:
            bed.faces.new([prev["b0"], prev["b1"], cur["b1"], cur["b0"]])
            wall.faces.new([prev["w0"], prev["w1"], cur["w1"], cur["w0"]])
        prev = cur
    for bmx, nm in ((bed, "_bed"), (wall, "_bankwall")):
        bmesh.ops.recalc_face_normals(bmx, faces=bmx.faces)
        objs.append(_blank._new_obj(key + nm, bmx, mats["grnd"]))


def _land_slab(key, objs, mats, z_top=PAVE_TOP):
    """The tile's land: the hex MINUS the channel band — built as column strips
    from the bankline to the far boundary, with skirts to z=0."""
    N = 40
    xs = [-9.99 + 19.98 * i / N for i in range(N + 1)]
    land = bmesh.new()
    prev = None
    for x in xs:
        by = min(_band_y(x, key), _top_edge(x) - 0.15)
        ly = -_top_edge(x)
        cur = {
            "l0": land.verts.new((x, by, z_top)), "l1": land.verts.new((x, ly, z_top)),
            "k0": land.verts.new((x, ly, z_top)), "k1": land.verts.new((x, ly, 0.0)),
            "j0": land.verts.new((x, by, z_top)), "j1": land.verts.new((x, by, 0.0)),
        }
        if prev is not None:
            land.faces.new([prev["l0"], prev["l1"], cur["l1"], cur["l0"]])
            land.faces.new([prev["k0"], prev["k1"], cur["k1"], cur["k0"]])
        prev = cur
    bmesh.ops.recalc_face_normals(land, faces=land.faces)
    objs.append(_blank._new_obj(key + "_land", land, mats["pave"]))


def _masses_land7(objs, key, mats):
    bm = bmesh.new()
    _blank._disc_into(bm, -1.6, -2.0, 3.4, PAVE_TOP - 0.02, PAVE_TOP + 0.05, segs=18)
    objs.append(_blank._new_obj(key + "_green", bm, mats["green"]))
    bm = bmesh.new()
    for x, y, r in ((2.8, -1.2, 0.6), (-4.6, -4.4, 0.5)):
        _blank._blob_into(bm, x, y, PAVE_TOP + r * 0.4, r, z_squash=0.7, segs=8)
    objs.append(_blank._new_obj(key + "_boulders", bm, mats["rock"]))


def _masses_river7(objs, key, mats):
    # The town river flows through: a straight 5 m channel from the inward edge
    # (edge 3, y=-INR) into the half-channel — the river kit's exact section.
    chw = _river.CH_HW
    y0, y1 = -INR - 0.3, _band_y(0.0, key) + 0.6
    bm = bmesh.new()
    _street.sweep_into(bm, [(0.0, y0), (0.0, y1)], chw - _river.WATER_INSET,
                       WATER_Z - _river.WATER_T, WATER_Z)
    objs.append(_blank._new_obj(key + "_chwater", bm, mats["water"]))
    bm = bmesh.new()
    _street.sweep_into(bm, [(0.0, y0), (0.0, y1)], chw, FLOOR_Z, FLOOR_Z + _river.FLOOR_T)
    for side in (-1, 1):
        _blank._box_into(bm, side * (chw + 0.15), (y0 + y1) / 2, 0.3, y0 - y1,
                         FLOOR_Z, PAVE_TOP)
    objs.append(_blank._new_obj(key + "_chworks", bm, mats["grnd"]))


def _masses_exit7(objs, key, mats):
    # The artery crosses: road inward edge (3) -> over the half-channel on a
    # deck -> off the water edge (0) onto ring 8.
    bm = bmesh.new()
    _street.sweep_into(bm, [(0.0, -INR - 0.3), (0.0, INR + 0.3)], HW,
                       TOP - _river.DECK_T, TOP + 0.01)
    objs.append(_blank._new_obj(key + "_deck", bm, mats["road"]))
    bm = bmesh.new()
    y0, y1 = _band_y(0.0, key) - 1.0, INR + 0.3
    for side in (-1, 1):
        _blank._box_into(bm, side * (HW + _river.PARAPET_W / 2), (y0 + y1) / 2,
                         _river.PARAPET_W, y1 - y0, TOP, TOP + _river.PARAPET_H)
    objs.append(_blank._new_obj(key + "_parapets", bm, mats["pave"]))
    bm = bmesh.new()
    _blank._box_into(bm, -2.0, _band_y(0.0, key) - 1.6, 0.3, 0.3, PAVE_TOP, PAVE_TOP + 1.6)
    _blank._box_into(bm, 2.0, _band_y(0.0, key) - 1.6, 0.3, 0.3, PAVE_TOP, PAVE_TOP + 1.6)
    objs.append(_blank._new_obj(key + "_gate", bm, mats["border"]))


def _masses_bank8(objs, key, mats):
    # Horizon land: a low rolled rise away from the water (eye-height law:
    # under 2.5 m — the Range rings own the silhouette).
    bm = bmesh.new()
    for cx, cy, r, h in ((-2.4, -3.6, 4.0, 2.2), (3.2, -5.0, 3.0, 1.6)):
        sq = 0.3
        cz = PAVE_TOP + h - r * sq
        _blank._blob_into(bm, cx, cy, max(cz, 0.05 + r * sq), r, z_squash=sq, segs=10)
    objs.append(_blank._new_obj(key + "_rise", bm, mats["green"]))
    bm = bmesh.new()
    for x, y, r in ((0.6, -2.2, 0.55), (-4.8, -5.2, 0.5)):
        _blank._blob_into(bm, x, y, PAVE_TOP + r * 0.4, r, z_squash=0.7, segs=8)
    objs.append(_blank._new_obj(key + "_boulders", bm, mats["rock"]))


_MASSES = {"land7": _masses_land7, "river7": _masses_river7,
           "exit7": _masses_exit7, "bank8": _masses_bank8}


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
    objs = []
    _half_channel(key, objs, mats)
    _land_slab(key, objs, mats)
    _MASSES[key](objs, key, mats)

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


def _measured_mask(obj, key_sub):
    """The engine's MeasureTileMask, reimplemented on the authored mesh: any
    vertex of a keyed-material face within MEAS_R (Euclidean, XY) of an edge
    midpoint sets that edge's bit. Popcount is rotation-invariant, so this is
    exactly the calibration trust check — run BEFORE anything ships."""
    mids = [(INR * math.cos(math.radians(90.0 - 60.0 * e)),
             INR * math.sin(math.radians(90.0 - 60.0 * e))) for e in range(6)]
    slots = set(i for i, ms in enumerate(obj.material_slots)
                if ms.material and key_sub in ms.material.name)
    if not slots:
        return 0
    mask = 0
    me = obj.data
    r2 = MEAS_R * MEAS_R
    for poly in me.polygons:
        if poly.material_index not in slots:
            continue
        for vi in poly.vertices:
            co = me.vertices[vi].co
            for e, (mx, my) in enumerate(mids):
                if not (mask & (1 << e)) and \
                        (co.x - mx) ** 2 + (co.y - my) ** 2 < r2:
                    mask |= 1 << e
    return mask


def _bake_gate(base, key):
    """HARD-FAIL the bake on a popcount lie. The v2.1 pools put water 1.74 m
    from the side-edge midpoints; the engine measured 3 bits against 1
    authored, distrusted the WHOLE catalog, and every rim tile flipped to an
    authored-guess yaw (the director's reversed-water screenshots,
    2026-06-12). The bake now runs the engine's own arithmetic first."""
    road_a, water_a, _w = VARIANTS[key]

    def pop(m):
        return bin(m & 0x3F).count("1")

    mr, mw = _measured_mask(base, "Road"), _measured_mask(base, "Water")
    print("  bake-gate %-7s road 0x%02X(%d) authored 0x%02X(%d) | "
          "water 0x%02X(%d) authored 0x%02X(%d)"
          % (key, mr, pop(mr), road_a, pop(road_a),
             mw, pop(mw), water_a, pop(water_a)))
    if pop(mr) != pop(road_a) or pop(mw) != pop(water_a):
        raise SystemExit("BAKE GATE FAIL: %s measured popcount != authored — "
                         "the engine would distrust calibration." % key)


def make_tile(key):
    base = build_tile_obj(key)
    _bake_gate(base, key)
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
                                        "weight": w,
                                        "family": "Rim8" if k.endswith("8") else "Rim"}
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
    print("=== gen_rim_tiles (two-ring seam): writing to %s ===" % _street.out_dir())
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
