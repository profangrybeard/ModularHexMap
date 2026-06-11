# Testing.md — the user testing script

> Run this instead of intuition. Every case lists exact steps and the exact expected
> result, calibrated against the verified gates (2026-06-11). Work top to bottom for a
> full pass (~30–40 min), or jump to the feature you touched. Log results in the table
> at the bottom. Anything that fails its **Expect** is a real bug — file it in the
> Roadmap or hand it to Claude. Anything in **§Known-expected oddities** is NOT a bug.

## Conventions (read once)

- **The actor:** open `/Game/_project/Maps/ShuffleLab` (the startup map), select
  **HexShuffleGenerator** in the Outliner. Everything lives in its **Details** panel
  under the categories `Hex Shuffle`, `…|Growth`, `…|Growth|River`, `…|Constraints`,
  `…|Restoration`, `…|Rolls`, `…|Calibration`.
- **Output Log:** Window ▸ Output Log; filter on `HexShuffle` for engine lines,
  `RollDiag` for diagnostics, `RestoreVerify`/`RiverR4` for gate scripts.
- **Python console:** Output Log, switch the input dropdown from Cmd to **Python**.
  Most tests that need it start with this grab-the-actor snippet:
  ```python
  import unreal
  eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
  gen = next(a for a in eas.get_all_level_actors()
             if a.get_class().get_name() == "HexShuffleGenerator")
  ```
- **Golden numbers** (Radius 6, CoreRadius 1, the blessed tuning): **127 cells,
  core = 7, 0 unresolved, souls = 120**. The build log line is:
  `HexShuffle: built 127 cells (measured resolver), core=7, 0 unresolved, souls=120, restored=N`.
- Builds need the **editor closed** (`.\Tools\Build.ps1` — never the VS Build menu,
  Resistance #29).

---

## T0 — Build & launch

1. Close the editor. Run `.\Tools\Build.ps1` from the repo root.
   **Expect:** `Result: Succeeded`. (Failure mentioning *Live Coding* = an editor is
   still open. Failure mentioning *env var too long* = you used MSBuild somehow.)
2. Launch the editor; it opens on ShuffleLab.
   **Expect:** Output Log shows
   `[HexTiles] registered Tools > Reimport Hex Tiles / Diagnose Last Roll / Hex Roll Sweep / Constrained Randomize`
   — the Tools menu carries all four entries.

## T1 — Calibration & the dev roll

1. Select the generator. Click **Recalibrate** (calibration is always-on; this forces a
   fresh measure).
   **Expect:** one log line per catalog tile (20), each ending **OK** — road AND water
   masks measured (`road measured=… | water measured=…`), then
   `calibration OK (20 tiles measured from geometry)`. ANY `MISMATCH` = fail.
2. Set Details ▸ Restoration ▸ `bRestorationMode` **OFF** (dev view). Click **Randomize**.
   **Expect:** the golden line (127/7/0/120). A full solid town: streets + buildings,
   the core star at center, the river somewhere through it, the label reads `Souls: 120`.
3. Click **Randomize** five more times.
   **Expect:** a different town every click (Seed increments), golden line every time,
   `0 unresolved` every time. Tile borders always align; roads never dead-end into a
   block face (the stub prune).
4. Click **Clear**.
   **Expect:** all tiles gone; label keeps its last text; no errors.

## T2 — Determinism & BuildFromSeed

1. Note the current Seed value. Python:
   ```python
   gen.build_from_seed(6)
   ```
   **Expect:** Seed shows 6; golden line. The layout is THE seed-6 town.
2. Run `gen.build_from_seed(6)` again.
   **Expect:** pixel-identical town (determinism — same seed, same destiny).
3. Click **Randomize** once.
   **Expect:** Seed becomes 7 — the button is "reroll to NEXT seed" (`BuildFromSeed(Seed+1)`).

## T3 — Growth knobs (quick feel, dev view)

1. Details ▸ Growth: set `RoadBudget` 40 (from 174). Randomize.
   **Expect:** drastically sparser streets, big open blocks. Still 0 unresolved.
2. Set `RoadBudget` back to **174**. Set `MaxStraightRun` 2. Randomize.
   **Expect:** kinky, medieval-feeling streets (forced turns). Restore to **0**.
3. Knobs you may freely play with and what they bias: `BranchChance` (side-street
   density), `StraightBias`/`StraightDecay` (sightlines), `ArteryKinkChance`/
   `ArteryForkChance` (avenue character). **Always restore the blessed values**
   (174 / .21 / .72 / .8 / .35 / .12) or re-load the level without saving.

## T4 — Roll save/load (the town save)

1. `gen.build_from_seed(6)`, then click **Save Roll**.
   **Expect:** log `saved roll -> …Design/Rolls/Roll_seed6.json`.
2. Click **Randomize** twice (now on a different town). Set Details ▸ Rolls ▸
   `RollToLoad` = `Roll_seed6`. Click **Load Roll**.
   **Expect:** the seed-6 town returns EXACTLY; Seed shows 6; golden line. (Loading
   rebuilds the saved masks verbatim — it works even if growth code changed since.)
3. Open `Design/Rolls/Roll_seed6.json` in a text editor.
   **Expect:** `network.cells[*]` with `axial/roadMask/waterMask`, plus a `restored`
   array — destiny + healing progress in one file.

## T5 — Constraints (bias the destiny)

1. Details ▸ Constraints: confirm `RollConstraints` = `DT_RollConstraints_reqJunction`
   (or assign it). Tools ▸ **Constrained Randomize**.
   **Expect:** log shows `source=DataTable:DT_RollConstraints_reqJunction`, per-attempt
   `FAIL` lines (bounces), then `satisfied at seed=N`, then
   **`placed roll re-verified against constraints (seed=N)`** — the placed town IS the
   validated one. Diagnose (T6) shows `junction ≥ 1`.
2. Swap `RollConstraints` to `DT_RollConstraints_Default`, repeat.
   **Expect:** same flow; satisfied roll has `junction ≥ 1` AND `tee_c ≥ 1`.
3. Failure mode: open `DT_RollConstraints_Default`, set junction Min = 8 (absurd).
   Constrained Randomize.
   **Expect:** exhaustion warning naming the **biggest bouncer** (`junction`) and the
   **closest miss** (largest observed vs needed 8). **Undo the row edit.**
4. Clear `RollConstraints` (None). Constrained Randomize.
   **Expect:** `source=JSON:default` — the file fallback engages.

## T6 — Diagnostics

1. After any roll: Tools ▸ **Diagnose Last Roll**.
   **Expect:** per-necklace histogram of the PLACED town (sums to 120 with water
   counted in its own section), `water: N river cells, M bridges` + water necklaces +
   bridge pairs. Run after **Load Roll** too — it reads the placed network, not a
   re-grow.
2. Tools ▸ **Hex Roll Sweep (200 rolls)** (~10 s).
   **Expect:** per-necklace mean/std/p95 table; `sum(mean)=120.0`,
   `mean unresolved 0.00`; WATER block (river cells mean ~11, bridges mean ~0.4);
   exactly **3 bridge pair kinds**; a CSV lands in `Design/Rolls/`. Compare against
   `Design/Rolls/Baseline.csv` after any growth change.

## T7 — The River

1. Details ▸ Growth|River: `bRiver` ON, set `RiverOutflowDir` = **4**.
   `gen.build_from_seed(6)`.
   **Expect:** the river enters from one boundary, reaches the core, makes the 60°
   bend past the Pit, exits west-ish (heading 4). Arms touch the core star and STOP
   at ring 1 (§oddities #1). Blue water sits down in its channel; banks at pavement
   level; tiles snap C1 across cells.
2. Try each `RiverOutflowDir` 0–5 with the same seed.
   **Expect:** the outflow arm leaves through the matching gate each time; town stays
   golden (0 unresolved) for all six.
3. Set `RiverOutflowDir` = **-1**. Randomize several times.
   **Expect:** heading varies per seed; every roll still golden.
4. `bRiver` OFF, Randomize. **Expect:** a dry town, golden line, no water anywhere.
   Turn it back **ON**.
5. Banks, Python (after `build_from_seed(6)` at heading 4):
   ```python
   print(gen.get_bank_name(unreal.IntPoint(0, 5)),
         gen.get_bank(unreal.IntPoint(0, 0)),
         gen.get_bank(unreal.IntPoint(2, -2)))
   ```
   **Expect:** a bank name for the land cell; `-1` for the core; `-1` for a water cell.
   At seed 6 / heading 4 the split is **Left 15 / Right 95** — the wedge between the
   arms is the small bank.
6. Bridges: find a road crossing the river (Diagnose says how many; seed 6 heading 4
   has 2). **Expect:** a deck with parapets at street level, water flowing beneath,
   roads continuing both sides.

## T8 — Restoration (the first playable)

1. Details ▸ Restoration: `bRestorationMode` **ON**, `GhostMaterial` = `M_GhostTile`.
   `gen.build_from_seed(6)`.
   **Expect:** label **`Pop 1 / 121`** (you are the one). The core star solid;
   EVERYTHING else a pale translucent ghost (streets visible, NO buildings on ghosts).
   Golden line ends `restored=0 [restoration]`.
2. Click **Restore Next** ~10 times, watching.
   **Expect:** one tile turns solid per click, radiating outward from the wound,
   ring 2 first; buildings pop in WITH their tile; label counts `Pop 2 / 121` … and
   the log `restored=N` tracks each click.
3. Far-bank gating: keep clicking toward the river.
   **Expect:** healing crosses water ONLY at a bridge cell or around the core gates —
   never through open river. (The wedge district heals via the core throat.)
4. **Save Roll** mid-heal (say Pop 30), Randomize away, `RollToLoad`=`Roll_seed6`,
   **Load Roll**.
   **Expect:** the mid-heal state returns exactly — same solids, same `Pop 30 / 121`.
5. Click **Restore All**.
   **Expect:** every cell solid, label **`Pop 121 / 121`**, `restored=120`. Clicking
   Restore Next now logs `every soul is home`.
6. Click **Reset Restoration**. **Expect:** back to `Pop 1 / 121`, full ghost.
7. Player-agency hooks, Python:
   ```python
   c = gen.get_restoration_candidates()
   print(len(c), [(p.x, p.y) for p in c[:5]])
   print(gen.restore_cell(c[-1]))     # settle a soul of YOUR choosing
   print(gen.restore_cell(unreal.IntPoint(5, -5)))  # not a candidate
   ```
   **Expect:** 12 candidates on a fresh seed-6 roll, all ring 2; first call returns
   `True` and that specific tile turns solid; second returns `False` with a warning
   (illegal settle is refused, never silently misplaced).
8. Mode interplay: `bRestorationMode` OFF, Randomize.
   **Expect:** the dev shuffle view is byte-for-byte the pre-restoration behavior
   (everything solid, label `Souls: 120`).

## T9 — Walkthrough (PIE)

1. Restoration ON, `build_from_seed(6)`, **Restore All** (a full solid town).
   Right-click a street tile near the core ▸ **Play From Here**.
2. Walk: streets, pavements, curbs.
   **Expect:** walkable everywhere solid; curbs step up ~15 cm; tile seams flush
   underfoot (no lips except the border bead).
3. Walk into a building through a door.
   **Expect:** you fit (0.9 × 2.1 m doors), interior floor is the flagstone, interior
   walls/ceiling render (no see-through backfaces), threshold reads as a step.
4. Walk to the river bank, then onto a bridge.
   **Expect:** bank walk at pavement level with a hard drop to water (no rail yet —
   art phase); the bridge deck carries you across between parapets.
5. **Reset Restoration** (in-editor, then Play From Here again) and walk INTO a ghost
   region. **Expect:** you fall/walk through ghosts — they have no collision (the
   destiny isn't real yet).

## T10 — Blender pipeline (only when touching tile geometry)

1. Bake any kit from the repo root (master is never saved by scripts):
   `& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background ".\Source_Art\Blender\HexBase.blend" --python ".\Tools\blender\gen_curved_tiles.py"`
   (likewise `gen_pit_core.py`, `gen_buildings.py`, `gen_river_tiles.py`).
   **Expect:** per-tile `… bytes` lines, zero tracebacks; `.glb`s in
   `Content/_project/HexTiles/Source/` (+ `river_kit.json` for the river kit).
2. In-editor: Tools ▸ **Reimport Hex Tiles**, then **Recalibrate**, then Randomize.
   **Expect:** reimport count logged, collision re-asserted, materials self-healed to
   the 4 masters; calibration all OK; golden line. **Recalibrate after ANY reimport**
   — stale calibration is the classic silent wrongness.
3. Master hygiene spot-check (Resistance #30):
   `git show HEAD:Source_Art/Blender/HexBase.blend` → pointer `size` ≈ **101.5 KB**.
   A jump means stowaways got saved into the master.

## T11 — The automated gates (run after any C++/growth change)

One-shot, editor closed, from the repo root — each prints PASS/FAIL lines and exits:

| Gate | Command target | Covers |
| --- | --- | --- |
| Smoke | `Tools/verify_shuffle.py` | calibrate, roll, histogram, constrained + placed-roll assert |
| Restoration | `Tools/verify_restoration.py` | Pop 1 start, candidates, save/load progress, 120/120, reset |
| River R4 | `Tools/verify_river_r4.py` | gates watered, chosen heading honored, arms reach boundary, banks |
| Buildings | `Tools/_verify_buildings.py` | street/building ISM pairing |
| Census | `Tools/_census_run.py` | 200-roll sweep + water/bridge census vs `Baseline.csv` |

Pattern: `& "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" "$PWD\ModularHexMap.uproject" -ExecutePythonScript="$PWD\Tools\<gate>.py" -unattended`
then grep the log: `Select-String -Path Saved\Logs\ModularHexMap.log -Pattern "PASS|FAIL"`.

## Known-expected oddities (do NOT file as bugs)

1. **River arms stop at ring 1.** The two ring-1 gate tiles carry water MASKS but no
   channel geometry yet — that's the director's pour-in art pass. Interim by design.
2. **Bridgeless destinies are common** (bridges mean ≈ 0.4 since core-anchoring).
   Healing rounds the core instead. Parked tuning knob, not a defect.
3. **Blank share swings hard between rolls** (σ/μ ≈ 0.43) — known volatility;
   min-block-size rule is the queued fix.
4. **Bank split is lopsided** (~15/95) — geometry of the 60° bend; the wedge district
   is a feature.
5. **`is_dirty` lies after scripted edits** in Blender (Resistance #31) and **a level
   you didn't save keeps transient rolls only** — reopening ShuffleLab shows its last
   SAVED state, not your last roll. Save Roll is the durable record, not the level.
6. **First roll after editor start takes a beat** (synchronous mesh loads + calibration);
   subsequent rolls are instant.

## Results log

| Date | Build/commit | T0 | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | T9 | T10 | T11 | Notes |
| ---- | ------------ | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | --- | --- | ----- |
|      |              |    |    |    |    |    |    |    |    |    |    |     |     |       |
