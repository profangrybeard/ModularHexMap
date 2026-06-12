"""probe_rim_materials.py — read the IMPORTED rim assets' slot tables + per-section
sampler masks (the engine-side half of the 2026-06-12 'water measures 0x00' hunt).

The staged GLBs are proven clean (M_Water = slot 0, prim 0, 420 verts on every
tile; parsed from the GLB JSON directly). This prints what UE actually built
from them: slot order, slot names, materials, and a per-SECTION rerun of
MeasureTileMask's arithmetic — so we can see which section the engine's
first-"Water"-slot search lands on and what geometry that section really holds.

Run in the open editor's Python console:
    py "C:/SCAD/Projects/ModularHexMap/Tools/probe_rim_materials.py"
"""
import math
import unreal

INR = 866.025403784          # uu
R2 = 250.0 * 250.0           # MeasureTileMask NearDist^2
MIDS = [(INR * math.cos(math.radians(90.0 - 60.0 * e)),
         INR * math.sin(math.radians(90.0 - 60.0 * e))) for e in range(6)]

for n in ("T_rim_land7", "T_rim_exit7", "T_rim_bank8", "T_rim_river7"):
    path = "/Game/_project/HexTiles/Rim/%s/StaticMeshes/%s" % (n, n)
    sm = unreal.EditorAssetLibrary.load_asset(path)
    if not sm:
        print("%s: NOT FOUND at %s" % (n, path))
        continue
    slots = sm.get_editor_property("static_materials")
    print("%s slots:" % n)
    for i, s in enumerate(slots):
        mat = s.material_interface.get_name() if s.material_interface else "NONE"
        print("  slot %d: name='%s' material='%s' imported='%s'"
              % (i, s.material_slot_name, mat,
                 s.get_editor_property("imported_material_slot_name")))
    # BOUNDED loop: out-of-range section reads return EMPTY without raising —
    # the unbounded version locked the editor (2026-06-12). Sections never
    # exceed the slot count on these meshes.
    for sec in range(len(slots) + 1):
        try:
            verts = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(sm, 0, sec)[0]
        except Exception as exc:
            if sec == 0:
                print("  (section read unavailable: %s)" % exc)
            break
        mask = 0
        for q in verts:
            for e, (mx, my) in enumerate(MIDS):
                if (q.x - mx) ** 2 + (q.y - my) ** 2 < R2:
                    mask |= 1 << e
        print("  section %d: %d verts, sampler mask 0x%02X" % (sec, len(verts), mask))
