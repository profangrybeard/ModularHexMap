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
3. **Phase 2 — Rivers plan** ✅ **DELIVERED 2026-06-10** → **[Rivers.md](Rivers.md)**.
   Design brief (director, from Richmond/the James): the river **divides business and
   culture while putting everyone on the same team** — and the plan shows the divide is
   *emergent* (the far bank only receives roads through bridges, so two street cultures
   fall out of the existing growth model). Layered two-mask architecture, water-first
   `GrowRiver`, frontier-only routing, artery-only bridging (scarcity by construction),
   census-driven tile budget, phases R1–R4 with gates. **Director rulings landed
   (Rivers.md §7): river souls YES** (bridge-climber / kayak-keeper / lifeguard / one
   lost to the river — souls = 120 holds), **name = "River"** (vanilla by choice),
   **channel = 5 m one-cell** (game scale). R1 is unblocked.
4. **Phase 4→3 PIVOT (director, 2026-06-10): rivers implementation FIRST** — "I really
   want to trust the river design before we design much more." **R1–R3 LANDED same
   day**, gates met:
   - R1 growth: `WaterMask` layer, `GrowRiver` momentum walk (frontier-only),
     water-as-wall roads, artery-only one-deck bridging. 200-roll sweep: river mean
     10.6 cells, bridges mean 1.52 (min 0 — quiet-bank rolls exist; tuning knob later),
     souls 120.0, 0 unresolved.
   - R2 kit: `gen_river_tiles.py` — 3 water tiles + **3 census-complete bridge tiles**
     (straight×straight 120°/60°, straight×curve — the ONLY pairs that occur) +
     `river_kit.json`; `setup_river.py` wiring (catalog = 20 rows).
   - R3 resolution: two-layer measure-and-rotate (`M_Water`), joint-rotation
     `FindPlacement`; **in-engine: 20-tile calibration OK both layers, 127 cells /
     0 unresolved / souls=120 with the river through town and bridges placed.**
   - **R4 ✅ LANDED 2026-06-11** with a director design evolution: the river is
     **core-anchored** (passes the wound; pour-in art is the director's pass; ring-1
     water masks system-injected until then), **`RiverOutflowDir`** is the player's
     destiny-roll choice, and banks are flow-relative **Left/Right Bank**
     (`GetBank`/`GetBankName`). Gates ALL PASS; census: same 3 bridge pairs.
     **Open tuning flags:** bridges mean fell to 0.41 (radial arms parallel arteries) —
     meander/side-street-bridging/min-bridge constraint when it matters; embankment
     *dressing* and bank-keyed material params remain an art-phase item.
5. **Phase 3 — Restoration loop** ✅ **LANDED 2026-06-11** (the first playable):
   - Engine: `bRestorationMode` + `GhostMaterial` + `RestoredCells` on the generator;
     `RestoreNext` / `RestoreAll` / `ResetRestoration` / `RestoreCell(Axial)` /
     `GetRestorationCandidates()` (the player-agency hook). Healing propagates over
     land + bridges, never open water — the far bank waits for its bridge; an
     across-water fallback keeps bridge-less destinies fully reachable.
   - Presentation: unrestored frontier renders as the ghost silhouette (street mesh,
     `M_GhostTile` translucent unlit, no collision); buildings materialize with their
     soul; label = `Pop <restored+1> / 121`.
   - Save format: `FHexRoll.Restored` — a roll file is now the complete town save
     (destiny + healing progress); old rolls load as fresh Pop 1.
   - **Gate ALL PASS** (`Tools/verify_restoration.py`): fresh destiny = Pop 1; healing
     opens at ring 2; Save/Load round-trips progress; RestoreAll reaches all 120
     souls, 0 stranded; reset clean. Proof shot: Pop 46 mid-heal in Docs/Images.
   - Still game-side (not this repo's engine work): the player-facing settle-a-soul UI
     and soul-identity records (who lives where) — content/UI layer on the hooks above.
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
- [ ] ~~**`MeasureTileMask` tolerance → absolute**~~ ✅ done 2026-06-10 (250 uu).
- [ ] **River material consolidation**: the river kit import minted per-mesh material
  dupes under `HexTiles/River/` (Resistance #19); `setup_river.py` doesn't run the
  consolidator and `hextile_materials.py` doesn't know `M_Water` yet. Add `M_Water` to
  the masters map + run consolidate (or just run Tools ▸ Reimport Hex Tiles after the
  next bake).
