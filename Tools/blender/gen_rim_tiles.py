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

H_RIM    = 20.0      # flank height at the outward edge
APRON_T  = 0.28      # inward fraction of the axis held flat (the walkable/works zone)
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


def _flank(name, mat, notch=False, crest_phase=0.0):
    """Ruled mountain flank over the hex + side skirts to z=0. Inward edge = +Y."""
    NY, NU = 12, 8
    bm = bmesh.new()
    grid = []
    for j in range(NY + 1):
        t = j / NY
        y = INR - 2.0 * INR * t
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
    """Orientation marker: a small triangle INSIDE the base slab at the inward
    (edge 0) midpoint. Enclosed by the solid slab -> never visible; its verts sit
    well within the 250 uu measure radius of edge 0's midpoint and far from all
    other edge midpoints."""
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in ((-0.4, INR - 0.05, 0.10),
                                   (0.4, INR - 0.05, 0.10),
                                   (0.0, INR - 0.45, 0.10))]
    bm.faces.new(v)
    return _blank._new_obj(name, bm, rimkey_material())


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


def _masses_tunnel(objs, key, mats):
    # road apron: M_Road strip from the inward edge midpoint to the portal (the
    # measurer reads Road at edge 0); then piers + lintel + dark throat + gateposts.
    bm = bmesh.new()
    _street.sweep_into(bm, [(0.0, INR + 0.3), (0.0, 1.6)], HW,
                       TOP - 0.02, TOP + 0.01)
    objs.append(_blank._new_obj(key + "_apron", bm, mats["road"]))
    bm = bmesh.new()
    _blank._box_into(bm, -2.2, 1.0, 1.2, 2.4, PAVE_TOP, PAVE_TOP + 4.6)      # piers
    _blank._box_into(bm, 2.2, 1.0, 1.2, 2.4, PAVE_TOP, PAVE_TOP + 4.6)
    _blank._box_into(bm, 0.0, 1.0, 5.6, 2.6, PAVE_TOP + 4.2, PAVE_TOP + 5.4) # lintel
    objs.append(_blank._new_obj(key + "_portal", bm, mats["rock"]))
    bm = bmesh.new()
    _blank._box_into(bm, 0.0, 0.4, 3.2, 1.6, TOP, PAVE_TOP + 4.0)            # throat
    _blank._box_into(bm, -1.45, 2.4, 0.18, 0.18, TOP, TOP + 1.4)             # gateposts
    _blank._box_into(bm, 1.45, 2.4, 0.18, 0.18, TOP, TOP + 1.4)
    objs.append(_blank._new_obj(key + "_throat", bm, mats["border"]))


def _masses_pass(objs, key, mats):
    # road climbs the flank into the notch and fades at the crest line
    pts = _street._bezier3((0.0, INR + 0.3), (0.6, 2.0), (-0.8, -1.5), (0.0, -6.0), 18)
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
    """Channel from the inward edge (river cross-section: 5 m / -0.9 / -2.0) to a
    basin; a weir step (outfall) or rock lip (intake); culvert arch under the flank."""
    chw = _river.CH_HW
    wz, fz = _river.WATER_Z, _river.FLOOR_Z
    y0, y1 = INR + 0.3, 3.2                       # channel run (overshoots the edge)
    bm = bmesh.new()                              # banks: pavement-level side slabs,
    bank_y0, bank_y1 = INR - 0.1, y1              # clamped INSIDE the hex boundary
    for side in (-1, 1):
        cx = side * ((chw + 0.2 + 4.5) / 2)
        _blank._box_into(bm, cx, (bank_y0 + bank_y1) / 2, 4.5 - (chw + 0.2),
                         bank_y0 - bank_y1, TOP, PAVE_TOP)
    objs.append(_blank._new_obj(key + "_banks", bm, mats["pave"]))
    bm = bmesh.new()                              # channel floor + walls
    _street.sweep_into(bm, [(0.0, y0), (0.0, y1)], chw, fz, fz + _river.FLOOR_T)
    for side in (-1, 1):
        _blank._box_into(bm, side * (chw + 0.15), (y0 + y1) / 2, 0.3, y0 - y1, fz, PAVE_TOP)
    objs.append(_blank._new_obj(key + "_channel", bm, mats["grnd"]))
    bm = bmesh.new()                              # water: channel surface + basin pool
    _street.sweep_into(bm, [(0.0, y0), (0.0, y1 + 0.4)], chw - _river.WATER_INSET,
                       wz - _river.WATER_T, wz)
    bz = wz - (1.2 if outfall else 0.0)           # outfall pool sits below the weir
    _blank._disc_into(bm, 0.0, y1 - 2.2, 2.6, bz - _river.WATER_T, bz, segs=24)
    objs.append(_blank._new_obj(key + "_water", bm, mats["water"]))
    bm = bmesh.new()                              # weir / lip + culvert arch + basin ring
    if outfall:
        _blank._box_into(bm, 0.0, y1 + 0.15, chw * 2 + 0.6, 0.5, fz, wz + 0.05)
    else:
        _blank._box_into(bm, 0.0, y1 + 0.15, chw * 2 + 0.6, 0.5, fz, wz - 0.25)
    _blank._disc_into(bm, 0.0, y1 - 2.2, 3.1, bz - 0.9, TOP + 0.4, segs=24)
    _blank._box_into(bm, 0.0, y1 - 2.2, 3.4, 1.2, bz - 0.2, bz + 2.4)        # culvert block
    objs.append(_blank._new_obj(key + "_works", bm, mats["rock"]))


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
    base = _street.hex_prism(name, 0.0, TOP, mats["grnd"])
    objs = [base, _street.hex_border(key + "_border", mats["border"]), _rimkey(key + "_key")]

    # Water mouths build their own split apron around the channel; everyone else
    # gets the full street-canvas pavement under the flank.
    if key not in ("outfall", "intake"):
        objs.append(_street.hex_prism(key + "_pave", TOP, PAVE_TOP, mats["pave"]))

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
