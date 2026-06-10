"""Verify the parallel building ISMs spawn after wiring. Opens ShuffleLab, calls
Randomize, then dumps per-ISM counts and the DA's BuildingMesh state."""
import unreal
eal = unreal.EditorAssetLibrary
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

MAP = "/Game/_project/Maps/ShuffleLab"

# --- DA state ---
ts = eal.load_asset("/Game/_project/Data/DA_HexTileSet_Streets")
unreal.log("=== DA rows ===")
for i, row in enumerate(ts.get_editor_property("tiles")):
    nm   = str(row.get_editor_property("name"))
    bldg = row.get_editor_property("building_mesh")
    bs   = str(bldg) if bldg else "<none>"
    unreal.log("  row[%d] %s building=%s" % (i, nm, bs[:80]))

# --- load level + run Randomize ---
LES.load_level(MAP)
world = UES.get_editor_world()
actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
gen = next((a for a in actors if a.get_class().get_name() == "HexShuffleGenerator"), None)
if not gen:
    unreal.log_error("HexShuffleGenerator not found"); raise SystemExit
unreal.log("gen actor = " + gen.get_actor_label())
gen.call_method("Recalibrate")
gen.call_method("Randomize")
souls = gen.get_editor_property("souls")
unreal.log("Randomized: Souls=%d" % souls)

isms = gen.get_components_by_class(unreal.InstancedStaticMeshComponent)
street, bldg, other = 0, 0, 0
for c in isms:
    m = c.get_editor_property("static_mesh")
    n = m.get_name() if m else "<none>"
    cnt = c.get_instance_count()
    if n.startswith("T_bldg_"):     bldg += cnt
    elif n.startswith("T_street_"): street += cnt
    elif n.startswith("T_core_"):   other += cnt
    else:                            other += cnt
    unreal.log("  ISM %-28s instances=%d" % (n, cnt))
unreal.log("TOTAL: street=%d building=%d core/other=%d" % (street, bldg, other))
