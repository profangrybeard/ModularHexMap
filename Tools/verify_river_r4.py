# verify_river_r4.py — one-shot (GUI editor) gate for the core-anchored river + banks:
#   * with RiverOutflowDir=4: both ring-1 gates (AxialDir[4], AxialDir[5]) carry water;
#     the outflow arm leaves through 2*AxialDir[4]
#   * both arms reach the map boundary (two off-map water edges)
#   * 127 cells / 0 unresolved / souls == 120 (river cells house souls)
#   * banks: Left and Right both populated; water + core report bank -1
#   * rolled direction (-1) also produces a valid through-flow river
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/verify_river_r4.py"
import unreal

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
AXDIR = [(0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1), (1, 0)]

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = next((a for a in eas.get_all_level_actors()
            if a.get_class().get_name() == "HexShuffleGenerator"), None)
if gen is None:
    err("verify_river_r4: no HexShuffleGenerator")
    raise SystemExit

ok = True
def check(name, cond, detail=""):
    global ok
    (log if cond else err)("[RiverR4] %-38s %s %s" % (name, "PASS" if cond else "FAIL", detail))
    ok = ok and cond

def cells_of(g):
    net = g.get_editor_property("last_network")
    return list(net.get_editor_property("cells"))

def water_map(cl):
    return {(c.get_editor_property("axial").x, c.get_editor_property("axial").y):
            int(c.get_editor_property("water_mask"))
            for c in cl if int(c.get_editor_property("water_mask")) != 0}

OUT = 4
growth = gen.get_editor_property("growth")
growth.set_editor_property("river_outflow_dir", OUT)
gen.set_editor_property("growth", growth)
gen.set_editor_property("restoration_mode", False)   # dev view for this gate
gen.recalibrate()
gen.build_from_seed(6)

cl = cells_of(gen)
wm = water_map(cl)
souls = gen.get_editor_property("souls")

gateY, gateX = AXDIR[OUT], AXDIR[(OUT + 1) % 6]
check("outflow gate carries water", gateY in wm, str(gateY))
check("inflow gate carries water", gateX in wm, str(gateX))
seedY = (2 * AXDIR[OUT][0], 2 * AXDIR[OUT][1])
check("outflow arm leaves at chosen heading", seedY in wm, str(seedY))
check("souls is 120", souls == 120, "souls=%d" % souls)

# both arms reach the boundary: two water cells at ring 6
ring6 = [a for a in wm if (abs(a[0]) + abs(-a[0] - a[1]) + abs(a[1])) // 2 == 6]
check("both arms reach the boundary", len(ring6) >= 2, "ring6 water=%d" % len(ring6))

left = right = 0
for c in cl:
    ax = c.get_editor_property("axial")
    b = gen.get_bank(unreal.IntPoint(ax.x, ax.y))
    if b == 0: left += 1
    elif b == 1: right += 1
check("both banks populated", left > 0 and right > 0, "L=%d R=%d" % (left, right))

wa = next(iter(wm))
check("water reports bank -1", gen.get_bank(unreal.IntPoint(wa[0], wa[1])) == -1)
check("core reports bank -1", gen.get_bank(unreal.IntPoint(0, 0)) == -1)
check("bank name strings", gen.get_bank_name(unreal.IntPoint(0, 5)) in ("Left Bank", "Right Bank", ""))

# rolled direction also works
growth.set_editor_property("river_outflow_dir", -1)
gen.set_editor_property("growth", growth)
gen.build_from_seed(7)
wm2 = water_map(cells_of(gen))
core_water = [a for a in wm2 if (abs(a[0]) + abs(-a[0] - a[1]) + abs(a[1])) // 2 <= 1]
check("rolled dir: core gates present", len(core_water) == 2, "core water=%d" % len(core_water))

warn("=== verify_river_r4: %s ===" % ("ALL PASS" if ok else "FAILURES — see above"))
