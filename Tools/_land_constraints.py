# _land_constraints.py — one-shot (GUI editor): land the layer-2 curated clamp.
# Director's picks (2026-06-11, screenshot + clarification):
#   junction 1..3, tee_c 1..3 (scarce landmarks, snappy rolls)
#   blank 2..40 (census row: >=2 dry cells so gardens always exist; <=40 culls the
#                geography-strangled tail)
#   plain-void scarcity = 2-4 raw blanks via FHexTileDef.Weight 0.4 on the plain
#   T_street_blank row (the census can't see variant dressing; Weight is the dial:
#   0.4 vs three gardens at 1.0 -> ~12% of dry cells stay void, ~3 per town).
# Then PROVE it: constrained_randomize must land a satisfying seed, and the placed
# roll's void/garden instance counts get logged.
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
eal = unreal.EditorAssetLibrary

# 1) rewrite the constraints table (wholesale row replacement via CSV — the
#    create_default_constraints_table mechanism; first header column is '---')
DT = "/Game/_project/Data/DT_RollConstraints_junction_mxBlank"
table = eal.load_asset(DT)
csv = (
    "---,Min,Max,Exact\n"
    "junction,1,3,-1\n"
    "tee_c,1,3,-1\n"
    "blank,2,40,-1\n"
)
# Returns bool (success) in UE 5.7; older bindings returned a list of error strings.
res = unreal.DataTableFunctionLibrary.fill_data_table_from_csv_string(table, csv)
if res is False:
    err("[Land] CSV fill FAILED for %s — rows unchanged" % DT)
elif not isinstance(res, bool) and res:
    for e in res:
        warn("[Land] CSV fill: %s" % e)
ok = eal.save_loaded_asset(table, only_if_is_dirty=False)
# Read back what the table now actually holds (column-as-string — the only row
# read that works on arbitrary structs in 5.7; see _load_constraints_from_datatable).
dtl = unreal.DataTableFunctionLibrary
names = [str(n) for n in dtl.get_data_table_row_names(table)]
mins = list(dtl.get_data_table_column_as_string(table, "Min"))
maxs = list(dtl.get_data_table_column_as_string(table, "Max"))
warn("[Land] %s rows now: %s save=%s"
     % (DT, ", ".join("%s[%s..%s]" % t for t in zip(names, mins, maxs)), ok))

# 2) plain-void scarcity: Weight 0.4 on the plain blank street row (found by MESH
#    name, robust to row naming; index assignment + force save — Resistance #11)
DA = "/Game/_project/Data/DA_HexTileSet_Streets"
asset = unreal.load_asset(DA)
tiles = list(asset.get_editor_property("tiles"))
hit = -1
for i, t in enumerate(tiles):
    mesh = t.get_editor_property("mesh")
    m = mesh.get_asset() if hasattr(mesh, "get_asset") else mesh
    name = m.get_name() if m else ""
    if name == "T_street_blank":
        d = tiles[i]
        d.set_editor_property("weight", 0.4)
        tiles[i] = d
        hit = i
        break
if hit < 0:
    err("[Land] T_street_blank row not found in %s — Weight NOT set" % DA)
else:
    asset.set_editor_property("tiles", tiles)
    ok = eal.save_loaded_asset(asset, only_if_is_dirty=False)
    warn("[Land] plain blank Weight -> 0.4 (row %d) save=%s" % (hit, ok))

# 3) prove it: constrained roll against the live table (the actor's assignment)
import importlib
import roll_diagnostics
importlib.reload(roll_diagnostics)
seed = roll_diagnostics.constrained_randomize("default", max_attempts=300, verbose=False)
warn("[Land] constrained_randomize -> seed=%s" % seed)

# 4) census the PLACED roll's dressing: void vs garden instance counts (solid +
#    ghost ISMs both count — a fresh destiny renders all-frontier as ghosts)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = None
for a in eas.get_all_level_actors():
    if a.get_class().get_name() == "HexShuffleGenerator":
        gen = a
        break
if gen and seed is not None:
    counts = {}
    for c in gen.get_components_by_class(unreal.InstancedStaticMeshComponent):
        m = c.get_editor_property("static_mesh")
        if m is None:
            continue
        n = m.get_name()
        if n.startswith(("T_street_blank", "T_blank_")):
            counts[n] = counts.get(n, 0) + c.get_instance_count()
    voids = counts.get("T_street_blank", 0)
    gardens = {k: v for k, v in counts.items() if k.startswith("T_blank_")}
    warn("[Land] dressing census: voids=%d  gardens=%s  dry-total=%d"
         % (voids, gardens, voids + sum(gardens.values())))
warn("=== land_constraints: done ===")
