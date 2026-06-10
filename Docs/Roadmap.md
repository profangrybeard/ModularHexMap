# Roadmap — direction & captured ToDos

> The **direction** doc: where the project is going and what's queued, in priority order.
> Decisions live in [Design.md](Design.md) once resolved; session history lives in the
> worklog; gotchas live in the resistance doc. Seeded 2026-06-10 from the audit feedback
> session ([Audit_2026-06-10.md](Audit_2026-06-10.md)); the CLAUDE.md restructure will
> finish wiring the four-doc split.

## Locked direction (2026-06-10 feedback session)

- **The randomizer is a dev tool.** The growth knobs / constraint machinery prove the kit
  and roll destinies; they are not the game's growth system.
- **1 tile = 1 soul is the pipeline's law.** Production may bend it for fun; the pipeline
  never does. All occupancy-sum machinery is to be removed (engine, catalog, scripts,
  saved-roll fields).
- **Souls join building groups.** A rescued soul settling on a tile with building
  sections joins that tile's building group — *which* tile the player assigns a soul to
  is the lever that makes each player's city feel different. (Engine hook: restoration
  candidates + soul-to-tile assignment; UI later.)
- **Growth model: destiny roll, witnessed restoration.** Roll the full layout once per
  save; restore one tile per rescue, BFS outward from the Pit; player agency = choosing
  among frontier candidates (necklace-complete kit ⇒ always legal, no dead ends).
- **Min-block-size rule is the goal** for growth tuning (refuse roads that shrink a block
  below N tiles) — directly serves destiny-roll quality.
- **The Pit's gameplay (descend prompt, level transition) is NOT this repo's scope.** It
  lives with the dungeon project; the town↔dungeon junction is a standing design goal
  managed by the director across both projects. Do not plan or build it here.
- **Interiors (14 shells × dressing)** are being built as coursework this quarter —
  outside this repo's execution plan; keep the door/interior hooks stable.
- **Rivers & bridges plan = highest-priority design deliverable** (layered-mask
  architecture; see queue below).

## Execution queue (order locked 2026-06-10)

1. **Phase 0 — Platform** (one editor-closed C++ build cycle + Python pass). Fix the five
   audit bugs (`BuildFromSeed`, the two join-tuple crashes, closest-miss logic,
   `last_network` read); **nuke occupancy** (FHexTileDef.Occupancy, EstimatedVacancies,
   FHexRoll.Vacancies, save/set_occupancy scripts, label → souls); **delete the entire
   retired spline-road system** (ASplineRoad code, the four actor props, BuildSplineRoads,
   SM_RoadSeg + SM_GroundHex assets); delete dead `Weight`; MeasureTileMask tolerance →
   absolute; promote the blessed ShuffleLab growth tuning to the C++ defaults. Verify:
   Recalibrate/Randomize, constrained roll (now constraint-true, with post-placement
   assertion), quick sweep.
2. **Phase 1 — Heal.** Delete the Tools/ graveyard (stale-path scripts, superseded
   generators, spent one-shots); heal the keepers (machine-neutral, `_project` paths:
   setup_shuffle_lab, setup_pit_core, setup_buildings, wire_core_into_shufflelab,
   verify_shuffle, _verify_buildings); delete orphaned UE assets — `T_valley_0..5` and
   **all four legacy maps (CoreGenLab, SplineLab, TestMap, Z_Houses — director-approved)**;
   fix every doc-drift item; add the master-clean guard; **restructure CLAUDE.md** into
   context (CLAUDE.md on-ramp) / direction (Roadmap.md) / memory (Worklog.md) /
   resistance (Resistance.md), and add the new Resolved entries to Design.md.
3. **Phase 2 — Rivers plan** (`Docs/Rivers.md`, highest-priority design deliverable):
   layered two-mask architecture (road + water as parallel 6-bit masks, never a ternary
   socket), water-first generation pass, **river is frontier-only (director-decided:
   core stays authored-and-dry)**, water-necklace census, sparse bridge/bank tile
   inventory, resolver + diagnostics changes, phased implementation with gates.
4. **Phase 3 — Restoration loop first playable** (director-decided: before rivers
   implementation): destiny roll persists; `RestoreNextTile` BFS from the Pit;
   ghost/rubble treatment for unrestored cells; `Pop <restored+1> / 121` label;
   `GetRestorationCandidates()` hook for soul→tile assignment.
5. **Phase 4 — Rivers implementation** per the plan doc.
6. **Phase 5 — Buildings facade continuity + min-block-size rule** (per-edge
   `M_BuildingBack` variation, party-wall pilaster, landmark slots; growth-side block
   guarantee).

## Captured ToDos (do not lose)

- [ ] **Normalizing landmark tiles** *(art-direction risk, captured per director)*: every
  hex intersection is 60°/120°, which fights the Edwardian read at street level. The
  6-way junction is literally a **Seven Dials** — own that. Counter the hex rhythm where
  the eye lingers with 2–5 bespoke multi-hex landmarks (market square, churchyard,
  terminus hotel) that introduce right angles and break the lattice.
- [ ] **Buildings facade continuity** (the next building tackle, per director):
  - Per-edge back/side facade variation via the `M_BuildingBack` engine seam
    (hide/replace per neighbor type — designed for this, not yet implemented).
  - **Party-wall pilaster** at tile boundaries where two building tiles abut — Victorian
    terraces read continuous because of shared party walls and repeated bays, not
    building size. One extra mesh.
- [ ] **Min-block-size rule** in `GrowRoadNetwork` (refuse a road edge that would shrink
  an enclosed block below N cells) — the durable fix for blank volatility (σ/μ ≈ 0.43).
- [ ] **Master-clean guard**: `HexBase.blend` pollution shipped committed once (fixed in
  `e63eb75`). Add a guard — pre-commit check that flags the master when its LFS size
  changes, and/or an addon Build-path warning when non-CANON objects exist outside
  `TilePreview`.
- [ ] **Soul → building-group assignment** mechanic (engine-side API first:
  `GetRestorationCandidates()`, soul-to-tile assignment record in the save).
- [ ] **Pop label** = `Pop <restored+1> / 121` once restoration exists (interim after the
  occupancy nuke: frontier soul count).
- [ ] **Stable-named baseline sweep CSV** (`Design/Rolls/Baseline.csv`) + diff after any
  growth change.
- [ ] **Headless contact-sheet render** of the kit after each bake (visual diff artifact).
- [ ] **`MeasureTileMask` tolerance → absolute** (currently scales with R; cross-section
  is absolute, so the test should be too).
