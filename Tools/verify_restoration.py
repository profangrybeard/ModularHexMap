# verify_restoration.py — one-shot (GUI editor) gate for the restoration loop:
#   * fresh destiny starts at restored=0 (Pop 1 — you)
#   * candidates exist and start at ring 2 (healing radiates from the wound)
#   * RestoreNext advances; SaveRoll/LoadRoll round-trips the progress
#   * RestoreAll reaches every soul: restored == souls == 120, candidates == 0
#     (includes the across-water fallback if the destiny rolled no bridge)
#   * ResetRestoration returns to 0
#   UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/verify_restoration.py"
import unreal

log, warn, err = unreal.log, unreal.log_warning, unreal.log_error
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/_project/Maps/ShuffleLab")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gen = next((a for a in eas.get_all_level_actors()
            if a.get_class().get_name() == "HexShuffleGenerator"), None)
if gen is None:
    err("verify_restoration: no HexShuffleGenerator")
    raise SystemExit

ok = True
def check(name, cond, detail=""):
    global ok
    (log if cond else err)("[RestoreVerify] %-34s %s %s" % (name, "PASS" if cond else "FAIL", detail))
    ok = ok and cond

gen.set_editor_property("restoration_mode", True)
gen.recalibrate()
gen.build_from_seed(6)

souls = gen.get_editor_property("souls")
restored = list(gen.get_editor_property("restored_cells"))
check("fresh destiny starts empty", len(restored) == 0, "restored=%d" % len(restored))
check("souls is 120", souls == 120, "souls=%d" % souls)

cands = list(gen.get_restoration_candidates())
check("candidates exist", len(cands) > 0, "n=%d" % len(cands))
ring2 = all(abs(c.x) + abs(-c.x - c.y) + abs(c.y) == 4 for c in cands[:1])  # first is ring 2
check("healing starts at ring 2", ring2, "first=(%d,%d)" % (cands[0].x, cands[0].y) if cands else "")

for _ in range(3):
    gen.restore_next()
check("RestoreNext advances", len(list(gen.get_editor_property("restored_cells"))) == 3)

gen.save_roll()
seed = gen.get_editor_property("seed")
gen.set_editor_property("roll_to_load", "Roll_seed%d" % seed)
gen.load_roll()
check("Save/Load round-trips progress",
      len(list(gen.get_editor_property("restored_cells"))) == 3)

gen.restore_all()
restored = list(gen.get_editor_property("restored_cells"))
cands = list(gen.get_restoration_candidates())
check("RestoreAll reaches every soul", len(restored) == souls,
      "restored=%d souls=%d" % (len(restored), souls))
check("no candidates remain", len(cands) == 0)

gen.reset_restoration()
check("Reset returns to 0", len(list(gen.get_editor_property("restored_cells"))) == 0)

warn("=== verify_restoration: %s ===" % ("ALL PASS" if ok else "FAILURES — see above"))
