"""Rim-tile generator — ring 7, the bowl that holds the town (Docs/Rim.md B1).

    blender --background Source_Art/Blender/HexBase.blend \
            --python Tools/blender/gen_rim_tiles.py

Eight blockout tiles for the boundary ring: three foothill faces (+ a sealed mine
adit), the artery tunnel portal + mountain pass, and the river outfall + intake.
Street-kit canvas underneath; a ruled mountain FLANK rises from the inward apron
to ~H_RIM at the outward edge; every tile carries side SKIRTS (vertical walls on
all six hex sides) so neighbouring rim tiles can never show a see-through gap.

THE RIM CONTRACT (B1 practical form): the flank height is a pure function f(t)
of the inward->outward axis, identical across all rim tiles, with the inward
APRON third held flat at pavement level. Side-edge profiles therefore agree
between same-orientation neighbours; corner stations may crease — skirts + fog
carry the blockout, and the vertex-class refinement is a B2 item if the walk
objects. Variant masses stay inside the side margins.

ORIENTATION KEY: every rim tile embeds a small M_RimKey-material triangle inside
the base slab at the INWARD edge (edge 0) midpoint. The engine measures it like
the Road/Water layers (MeasureTileMask key 'RimKey') and rotates the tile so the
key lands on each station's inward edge — mask-(0,0) faces are unorientable any
other way. The name contains neither 'Road' nor 'Water'.

Water mouths mirror gen_river_tiles' channel cross-section exactly (5 m channel,
surface -0.9, floor -2.0) so the rim meets the ring-6 river tile flush.

Writes rim_kit.json (masks + weights + family) for Tools/setup_rim.py.
NEVER saves the master. Idempotent. Manifest-aware.
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

# B2 parallax sandwich (director, 2026-06-11): ring 7 carries the WATERWAY BAND at
# its inward edge + LOW HILLS behind it (near parallax layer); the tall varied
# mountains are the off-grid Range (gen_range.py, far layer); fog lives between.
H_RIM    = 8.5       # LOW hills — the near layer must not eat the Range's silhouette
BAND_W   = 3.6       # the waterway band: every rim tile leaves its inward strip OPEN
                     # (no slab/pave there) — gen_waterway.py's single ring mesh fills
                     # all 42 bands continuously (bed + far wall + water at -0.9; the
                     # near bank wall is ring 6's own slab face, so river mouths open
                     # into the loop with zero per-destiny scenery changes)
CUT_Y    = INR - BAND_W
APRON_T  = (BAND_W + 2.4) / (2.0 * INR)   # band + a 2.4 m far-bank walk, then hills
ROCK_RGBA = (0.23, 0.205, 0.18, 1.0)   # light enough to take alpenglow later

# (name suffix, road_mask, water_mask, weight) — masks authored on edge 0 (inward).
VARIANTS = {
    "face_a":  (0, 0, 1.0),    # scree fan
    "face_b":  (0, 0, 1.0),    # crag steps
    "face_c":  (0, 0, 1.0),    # timber stand
    "adit":    (0, 0, 0.25),   # sealed mine adit (the Pit is not the only hole)
    "tunnel":  (1, 0, 1.0),    # artery exit: gated portal
    "pass":    (1, 0, 0.5),    # artery exit: road into a fog notch (rarer)
    "outfall": (0, 1, 1.0),    # river leaves town (weir + culvert basin)
    "intake":  (0, 1, 1.0),    # river enters town (basin + lip)
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
    """Hex half-width at height y (flat-top, vertices on the x axis)."""
    return R - abs(y) * (R - R * 0.5) / INR


def _f(t, notch_u=None, u=0.0, crest_phase=0.0):
    """The rim contract: flank height vs inward->outward fraction t in [0,1].
    Identical for every tile AT THE SIDE EDGES (u = ±1): the crest ripple that
    keeps the skyline from reading as a fortress wall fades to zero there, so
    any rim tile still tiles with any other. Optional notch: a centred dip."""
    if t <= APRON_T:
        return 0.0
    s = (t - APRON_T) / (1.0 - APRON_T)
    h = H_RIM * (s * s * (3.0 - 2.0 * s)) ** 1.25      # smoothstep, biased steep
    interior = max(0.0, 1.0 - u * u)                    # 0 at side edges (the contract)
    h *= 1.0 + 0.16 * interior * s * math.sin(u * 5.2 + crest_phase)
    if notch_u is not None:
        g = math.exp(-((u - notch_u) ** 2) / (2.0 * 0.18 ** 2))
        h *= (1.0 - 0.65 * g * min(1.0, s * 2.2))       # dip grows with altitude
    return h


def _notched_prism(name, z0, z1, mat):
    """The rim canvas slab: the hex with the inward waterway band CUT AWAY (the
    polygon's top edge sits at CUT_Y instead of the inward hex edge)."""
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


def _flank(name, mat, notch=False, crest_phase=0.0):
    """Ruled hill flank over the notched hex + side skirts to z=0. The first row
    sits exactly at the band cut (its skirt is the tile's own back-of-channel
    wall, hidden behind the waterway ring's far wall). Inward edge = +Y."""
    NY, NU = 12, 8
    bm = bmesh.new()
    grid = []
    for j in range(NY + 1):
        y = CUT_Y - (CUT_Y + INR) * j / NY      # rows span the NOTCHED extent
        t = (INR - y) / (2.0 * INR)             # t stays on the FULL axis (contract)
        xm = _xmax(y)
        row = []
        for i in range(NU + 1):
            u = -1.0 + 2.0 * i / NU
            h = _f(t, notch_u=0.0 if notch else None, u=u, crest_phase=crest_phase)
            row.append(bm.verts.new((u * xm, y, PAVE_TOP + h)))
        grid.append(row)
    for j in range(NY):
        for i in range(NU):
            bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
    # skirts: drop every boundary vertex column/row to z=0 (gap armor at seams)
    def skirt(va, vb):
        a0 = bm.verts.new((va.co.x, va.co.y, 0.0))
        b0 = bm.verts.new((vb.co.x, vb.co.y, 0.0))
        bm.faces.new([va, vb, b0, a0])
    for j in range(NY):
        skirt(grid[j][0], grid[j + 1][0])
        skirt(grid[j + 1][NU], grid[j][NU])
    for i in range(NU):
        skirt(grid[0][i + 1], grid[0][i])           # inward edge row (apron lip)
        skirt(grid[NY][i], grid[NY][i + 1])         # outward edge row (back wall)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _blank._new_obj(name, bm, mat)


def _rimkey(name):
    """Orientation marker: a small triangle at the inward (edge 0) midpoint, sunk
    BELOW the waterway bed (the band has no slab to hide it in any more; the
    measurer is XY-only, so depth is free invisibility). Verts sit well within
    the 250 uu measure radius of edge 0's midpoint, far from all other edges."""
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in ((-0.4, INR - 0.05, -2.1),
                                   (0.4, INR - 0.05, -2.1),
                                   (0.0, INR - 0.45, -2.1))]
    bm.faces.new(v)
    return _blank._new_obj(name, bm, rimkey_material())


def _hidden_water_key(name, mats):
    """Mouth identity marker: a small M_Water patch at the inward edge midpoint,
    3 cm BELOW the waterway's -0.9 surface — measures as water on edge 0, never
    visible (submerged under the ring's own water plane)."""
    bm = bmesh.new()
    _blank._box_into(bm, 0.0, INR - 0.35, 1.0, 0.6, -0.96, -0.93)
    return _blank._new_obj(name, bm, mats["water"])


# ---- variant masses (on top of canvas + flank; m_* passed in) ----
def _masses_face_a(objs, key, mats):   # scree fan
    bm = bmesh.new()
    rs = [(0.0, -2.0, 0.9), (-2.6, -3.4, 0.7), (2.8, -3.0, 0.8), (-1.2, -5.2, 1.1),
          (1.6, -5.8, 0.9), (-3.8, -5.6, 0.8), (3.6, -6.2, 1.0), (0.4, -7.2, 1.3)]
    for x, y, r in rs:
        t = (INR - y) / (2.0 * INR)
        _blank._blob_into(bm, x, y, PAVE_TOP + _f(t) + 0.2, r, z_squash=0.7, segs=8)
    objs.append(_blank._new_obj(key + "_scree", bm, mats["rock"]))


def _masses_face_b(objs, key, mats):   # crag steps
    bm = bmesh.new()
    for i, (w, d) in enumerate(((6.5, 2.2), (5.0, 1.8), (3.4, 1.5))):
        y = -2.4 - 2.0 * i
        t = (INR - y) / (2.0 * INR)
        h0 = PAVE_TOP + _f(t)
        _blank._box_into(bm, (-1) ** i * 1.2, y, w, d, h0 - 0.5, h0 + 2.2 + 0.8 * i,
                         rot_deg=(-1) ** i * 9.0)
    objs.append(_blank._new_obj(key + "_crags", bm, mats["rock"]))


def _masses_face_c(objs, key, mats):   # timber stand on the lower slope
    trunks = bmesh.new()
    crowns = bmesh.new()
    pts = [(-3.2, 1.2), (-1.0, 0.2), (1.8, 1.0), (3.4, -0.6), (0.2, -1.8),
           (-2.4, -2.8), (2.6, -3.4)]
    for x, y in pts:
        t = (INR - y) / (2.0 * INR)
        g = PAVE_TOP + _f(t)
        _blank._box_into(trunks, x, y, 0.22, 0.22, g, g + 1.5)
        _blank._blob_into(crowns, x, y, g + 2.3, 0.95, z_squash=1.35, segs=8)
    objs.append(_blank._new_obj(key + "_trunks", trunks, mats["border"]))
    objs.append(_blank._new_obj(key + "_crowns", crowns, mats["green"]))


def _masses_adit(objs, key, mats):     # face_a base + sealed timber adit at the apron
    _masses_face_a(objs, key, mats)
    bm = bmesh.new()
    _blank._box_into(bm, -1.5, 2.6, 0.35, 0.35, PAVE_TOP, PAVE_TOP + 2.2)   # posts
    _blank._box_into(bm, 1.5, 2.6, 0.35, 0.35, PAVE_TOP, PAVE_TOP + 2.2)
    _blank._box_into(bm, 0.0, 2.6, 3.7, 0.4, PAVE_TOP + 2.0, PAVE_TOP + 2.5)  # lintel
    _blank._box_into(bm, 0.0, 1.6, 2.4, 2.0, PAVE_TOP, PAVE_TOP + 1.9)        # dark seal
    objs.append(_blank._new_obj(key + "_adit", bm, mats["border"]))


def _gate_bridge(objs, key, mats):
    """The exit's crossing: a deck over the waterway band (M_Road top — the
    measurer reads Road at edge 0 from the deck itself) with low parapets.
    Spans from past the inward edge to the far-bank walk."""
    y0, y1 = INR + 0.3, CUT_Y - 0.2
    bm = bmesh.new()
    _street.sweep_into(bm, [(0.0, y0), (0.0, y1)], HW, TOP - _river.DECK_T, TOP + 0.01)
    objs.append(_blank._new_obj(key + "_deck", bm, mats["road"]))
    bm = bmesh.new()
    for side in (-1, 1):
        _blank._box_into(bm, side * (HW + _river.PARAPET_W / 2), (y0 + y1) / 2,
                         _river.PARAPET_W, y0 - y1, TOP, TOP + _river.PARAPET_H)
    objs.append(_blank._new_obj(key + "_parapets", bm, mats["pave"]))


def _masses_tunnel(objs, key, mats):
    _gate_bridge(objs, key, mats)
    bm = bmesh.new()                              # far-bank road to the portal
    _street.sweep_into(bm, [(0.0, CUT_Y - 0.1), (0.0, 1.4)], HW,
                       TOP - 0.02, TOP + 0.01)
    objs.append(_blank._new_obj(key + "_apron", bm, mats["road"]))
    bm = bmesh.new()
    _blank._box_into(bm, -2.2, 0.8, 1.2, 2.4, PAVE_TOP, PAVE_TOP + 4.4)      # piers
    _blank._box_into(bm, 2.2, 0.8, 1.2, 2.4, PAVE_TOP, PAVE_TOP + 4.4)
    _blank._box_into(bm, 0.0, 0.8, 5.6, 2.6, PAVE_TOP + 4.0, PAVE_TOP + 5.2) # lintel
    objs.append(_blank._new_obj(key + "_portal", bm, mats["rock"]))
    bm = bmesh.new()
    _blank._box_into(bm, 0.0, 0.2, 3.2, 1.6, TOP, PAVE_TOP + 3.8)            # throat
    _blank._box_into(bm, -1.45, 2.6, 0.18, 0.18, TOP, TOP + 1.4)             # gateposts
    _blank._box_into(bm, 1.45, 2.6, 0.18, 0.18, TOP, TOP + 1.4)
    objs.append(_blank._new_obj(key + "_throat", bm, mats["border"]))


def _masses_pass(objs, key, mats):
    _gate_bridge(objs, key, mats)
    # road climbs the flank into the notch and fades at the crest line
    pts = _street._bezier3((0.0, CUT_Y - 0.1), (0.6, 1.6), (-0.8, -1.5), (0.0, -6.0), 18)
    bm = bmesh.new()
    N = len(pts)
    for i in range(N - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        t0 = (INR - y0) / (2.0 * INR)
        t1 = (INR - y1) / (2.0 * INR)
        z0 = PAVE_TOP + _f(t0, notch_u=0.0, u=x0 / max(0.1, _xmax(y0)))
        z1 = PAVE_TOP + _f(t1, notch_u=0.0, u=x1 / max(0.1, _xmax(y1)))
        seg = bmesh.new()
        _street.sweep_into(seg, [(x0, y0), (x1, y1)], HW * 0.8, -0.02, 0.012)
        for v in seg.verts:
            v.co.z += (z0 + z1) * 0.5 + 0.02
        me = bpy.data.meshes.new("tmp")
        seg.to_mesh(me)
        seg.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    objs.append(_blank._new_obj(key + "_trail", bm, mats["road"]))


def _water_mouth(objs, key, mats, outfall):
    """The river meets the ring HERE: the town channel (ring 6) opens straight
    into the waterway band — the water connection is the annulus's job, so the
    tile carries only its IDENTITY (the hidden water key) and the bank works
    that mark flow direction on the far bank."""
    objs.append(_hidden_water_key(key + "_wkey", mats))
    bm = bmesh.new()                              # far-bank works at the band edge
    if outfall:
        # spill steps: the town water visually drops over a stepped weir face
        for i in range(3):
            _blank._box_into(bm, 0.0, CUT_Y - 0.25 - 0.45 * i, 5.4 - 1.2 * i, 0.45,
                             TOP - 0.55 - 0.35 * i, TOP + 0.05 - 0.30 * i)
    else:
        # intake lip + grate bars: the ring feeds the valley under a sill
        _blank._box_into(bm, 0.0, CUT_Y - 0.35, 5.8, 0.7, TOP - 0.4, TOP + 0.25)
        for i in range(5):
            _blank._box_into(bm, -2.0 + i, CUT_Y - 0.3, 0.14, 0.5, TOP - 1.4, TOP + 0.2)
    objs.append(_blank._new_obj(key + "_works", bm, mats["rock"]))
    bm = bmesh.new()                              # flanking bollard posts
    for side in (-1, 1):
        _blank._box_into(bm, side * 3.3, CUT_Y - 0.5, 0.3, 0.3, PAVE_TOP, PAVE_TOP + 1.1)
    objs.append(_blank._new_obj(key + "_posts", bm, mats["border"]))


_MASSES = {
    "face_a": _masses_face_a, "face_b": _masses_face_b, "face_c": _masses_face_c,
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
    # The notched canvas: slab + pavement stop at the waterway band (no border
    # lip on the rim — the bowl needs no metric aid, and the band would break it).
    base = _notched_prism(name, 0.0, TOP, mats["grnd"])
    objs = [base, _notched_prism(key + "_pave", TOP, PAVE_TOP, mats["pave"]),
            _rimkey(key + "_key")]

    # Per-variant crest phase: deterministic skyline variety, contract-safe
    # (the ripple is zero at side edges).
    phase = (sum(ord(c) for c in key) % 7) * 0.9
    objs.append(_flank(key + "_flank", mats["rock"], notch=(key == "pass"),
                       crest_phase=phase))
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


def main():
    _street.reset()
    try:
        import tile_common
        bespoke = tile_common.bespoke_tile_names()
    except Exception:
        bespoke = set()
    print("=== gen_rim_tiles: writing to %s ===" % _street.out_dir())
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
