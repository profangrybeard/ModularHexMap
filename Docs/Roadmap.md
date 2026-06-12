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
7. **Phase 6 — The Rim (ring 7)** — **RULED THE PRIORITY 2026-06-11** (ahead of
   Phase 5 facades, which are "a Blender back-and-forth and myopically detailed" —
   the director's hands-on pass, later). **PLAN → [Rim.md](Rim.md)**; B1 underway.
   The bowl that holds the town: 42-cell boundary ring (zero souls, eternal, derived
   from the network's boundary state — save format untouched), artery exits into
   gated mountain tunnels (the named roads leave town), the river closing its
   hydrology into a ring waterway (recommended) with an outfall weir + intake, the
   Range silhouette backdrop with authored ray notches, and UE 5.7's Day Sequence
   day/night with the sun anchored to the destiny's river axis — dawn fog / noon
   diorama / golden-hour alpenglow / short lamplit night as the four acceptance
   moments. Phases B1–B4 with census gates; **six open rulings in Rim.md §8**
   (waterway-vs-caves, sun anchor, Range lighting, night share, ghost-glow,
   names). Implementation slots on the director's priority call vs Phase 5.

## Platform answers — sooner, not later (director's mandate 2026-06-11)

> "Look for bigger-picture answers we want sooner rather than later." Things where
> a wrong default now compounds into rework later. Each gets an early ANSWER (a
> decision + a smoke test), not necessarily an early build-out.

- [ ] **Navmesh (the named example).** The trap is restoration: ghost tiles have NO
  collision, so every `RestoreCell` changes the walkable world at runtime — static
  navmesh is dead on arrival. **Answer:** RuntimeGeneration = **Dynamic**, tile ISMs
  flagged CanEverAffectNavigation (solid only — ghosts/rim faces excluded), navmesh
  bounds sized to ring 6 + exit aprons; per-restore dirty area is one tile (~cheap).
  Wrinkles the kit already created: garden rail GATES must admit nav (gaps are
  authored ✓), the river is a nav barrier except bridges (matches healing law ✓),
  waterway/rim never navigable. **Smoke test** (the gate): spawn a nav agent at the
  Pit rim, RestoreNext ×20, agent must path to every restored cell — wire into
  `verify_restoration.py`. Decide + test during Rim B1–B2 (souls walking the town
  is the game's point; nav is its floor).
- [ ] **Lighting is dynamic, forever.** Day/night = movable sun ⇒ **no baked
  lighting, ever** (Lumen + dynamic shadows; no lightmap UV debt in any kit mesh).
  State it as law now so no future mesh pays lightmap tax. (Rim plan §6 implies it;
  this makes it explicit.)
- [ ] **One persistent level, no streaming.** The playscape is a ~260 m diorama:
  ShuffleLab stays a single always-loaded level; World Partition/streaming is
  permanently out of scope. Origin shifting never needed.
- [ ] **Nanite: not yet, decide at bespoke-promotion time.** Blockout kits are
  trivial geometry; the call matters when bespoke detail passes start (affects
  import settings + material choices on the masters). Capture the decision point,
  don't pay it now.
- [ ] **Soul embodiment architecture (answer the shape, defer the build).** 120
  souls = lightweight actors spawned per restored tile, day-schedule driven off the
  day-cycle clock (shops by day, lamps by night, home at dark). Decide actor-vs-
  crowd now (recommend: plain actors — 120 is small), build at the souls phase.
  Depends on: navmesh answer, `AHexDayCycle` time broadcast (Rim B3).
- [ ] **Day-cycle event hooks ride along free.** `AHexDayCycle` (Rim B3) broadcasts
  time-band delegates (Dawn/Day/Dusk/Night) from day one — audio beds, window
  emissives, lamp posts, and soul schedules all subscribe later instead of
  retrofitting a clock.
- [ ] **The dungeon data envelope.** Define the town↔dungeon interface early (what
  the town hands down: roll seed, restored set, which exit/door; what comes back:
  rescued-soul records) — a one-page contract in Design.md when the director next
  works the junction; interfaces calcify fastest.
- [ ] **Traversal feel pin.** One T-step: walk speed vs 10 m tiles vs camera — the
  street cross-section is locked law, so if traversal feels off the fix must be
  controller-side. Verify once, pin numbers in Testing.md.

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
- [x] ~~**Min-block-size rule**~~ **STRUCK 2026-06-11** (director discussion): conceived
  for the dead multi-hex-footprint era; congestion is explicitly FINE ("the city street
  and river flow work even with extreme congested rolls"); never a player rule (players
  don't draw roads — enforcement philosophy is curation-of-offers, not policing).
- [ ] **The "too much nothing" plan** (director: "all the blank tiles kill it"):
  1. ✅ **Layer 1 COMPLETE 2026-06-11** — three structural fixes, census-proven
     (full table in Worklog): bridge-at-the-gate + daring lanes (`SideBridgeChance`,
     default 0.35 — the bridge-scarcity dial) + **wave reseeding** (the dominant fix:
     growth was stranding ~85% of RoadBudget; budget is now the real density
     contract). Blank mean 83.7 → **36.5**; bridges 0.47 → **2.54** (the original
     design read, center-clustered). 4th bridge pair authored from the census
     (`T_bridge_09_06`, straight × bend-water; catalog = 21).
  2. ✅ **Curated clamp LANDED 2026-06-11**: `DT_RollConstraints_junction_mxBlank`
     = **junction 1–3, tee_c 1–3, blank 2–40 (dry)** — git mirror
     `Design/RollConstraints/curated.json`. Plain-VOID scarcity (the director's
     "2–4 raw blanks") is the **Weight dial, not a census row**: plain
     `T_street_blank` Weight 0.4 vs three gardens at 1.0. Proof roll: constrained
     satisfied at seed 65 in 4 attempts; placed re-verify PASS; dressing census
     voids=4 / gardens 9+10+6 / dry 29. History below:
     `blank: {max: N}` constraint row
     culls the geography-strangled tail. **Semantics ruled + fixed 2026-06-11**
     (water is water, blank is blank): `blank` now counts **dry ground only** —
     pure river cells moved to their own `water` bucket (also a legal constraint
     row = river-length clamp); bridges stay under their road necklace. Reference
     rolls in dry terms: `Roll_seed22` (**15**) / `Roll_seed5` (**24**) /
     `Roll_seed188` (**36**) — note these are old-tuning destinies (decay 0.8);
     they load verbatim but fresh rolls run blanker. **Baseline re-anchored dry +
     StraightDecay 0.33 (2026-06-11)**: blank mean 27.8 / p50 23 / p95 69 / max
     87; water mean 14.7 (p95 25); sum(mean) = 120.0 exact. The
     geography-strangled tail is real in dry terms — the clamp still earns its
     keep.
     ⚠ The first eyeball pass set Max = 5 in `DT_RollConstraints_junction_mxBlank`
     — under the old census semantics that was **impossible** (the river alone
     always exceeds 5, census floor was 12), and on exhaustion Constrained
     Randomize changes nothing and returns None — so the "good results" were
     unconstrained Layer-1 rolls. In dry terms Max 5 is still extreme (dry min
     over 200 rolls = 6). **Re-pick N from the dry 0.33-decay baseline** (p50 23 /
     mean 27.8 — a Max around 35–40 cuts the dead tail while keeping constrained
     rolls fast), then SAVE the DataTable and mirror a JSON preset under
     `Design/RollConstraints/`.
     ⚠ The committed table's other rows are also infeasible-to-coinflip against
     the post-Layer-1 distribution (verify 2026-06-11): **junction Max 2**
     (junction means 6.5 — densification made 6-ways common; if junction scarcity
     is the intent, that's a growth/landmark design pass, not a constraint) and
     **tee_c Min 1** (tee_c mean 0.69, p50 = 0 — a near-coinflip alone). Director's
     ruling needed on both rows.
  3. **Open ground is occupied ground** (the read fix): blank VARIANTS — every blank
     is a SOUL's home, so absence should read as tended ground, not void (Bloomsbury
     garden-square energy). ✅ **LANDED 2026-06-11** (build + setup + consolidate +
     verify all green: calibration 24 tiles, 127 cells / 0 unresolved / souls=120;
     awaiting the director's look ruling + Weight dialing):
     - Engine: `FHexTileDef.Weight` returned WITH its consumer — both resolvers
       (`FindPlacement` measured / `FindTileForMask` authored) now collect ALL tiles
       matching a cell's (road, water) masks and pick Weight-proportionally from a
       per-cell `FRandomStream(VariantSeedFor(Seed, Axial))`; mask-0 cells also roll
       a free heading (gardens don't stamp). Deterministic per destiny: LoadRoll +
       healing re-place identical variants, save format unchanged.
     - Kit: `gen_blank_variants.py` → `T_blank_garden` (railed green, two gates,
       monument) / `T_blank_green` (off-centre lawn, desire-line S path, tree,
       mounds) / `T_blank_allotment` (5 raised beds, shed on the sixth plot,
       compost). Street-kit canvas reused verbatim; `M_Green` new master; manifest +
       registry entries live; contact sheets in `Docs/Images/ContactSheets/`.
     - Wiring: `Tools/setup_blank_variants.py` (catalog rows from `blank_kit.json`,
       incl. Weight; run AFTER the C++ build — `weight` doesn't exist in old
       binaries). Plain `T_street_blank` stays in the pool at Weight 1.0 (the
       void-vs-tended ratio is the director's catalog dial).
     - Still open: yard / orchard variants (cheap siblings once the look is ruled
       on), bespoke promotions per the manifest.
- [ ] **Player layout agency: RULED OUT beyond heading/order/assignment** (2026-06-11) —
  "rebuilding a lifetime hex by hex and discovering how they connect is part of the
  beauty." Not a city sim. Fully walkable + interactable (shops, quests) stays the bar —
  blank variants must stay walkable and eventually host their souls' interactions.
- [ ] **Master-clean guard**: `HexBase.blend` pollution shipped committed once (fixed in
  `e63eb75`). Add a guard — pre-commit check that flags the master when its LFS size
  changes, and/or an addon Build-path warning when non-CANON objects exist outside
  `TilePreview`.
- [ ] **Soul → building-group assignment** mechanic (engine-side API first:
  `GetRestorationCandidates()`, soul-to-tile assignment record in the save).
- [ ] **Pop label** = `Pop <restored+1> / 121` once restoration exists (interim after the
  occupancy nuke: frontier soul count).
- [x] ~~**Stable-named baseline sweep CSV**~~ ✅ live (`Design/Rolls/Baseline.csv`,
  re-anchored per default change).
- [ ] **R=10 master propagation** *(recovered 2026-06-11 — dropped in the doc
  restructure)*: the master `HexBase.blend` still carries the R=5 base + anchors;
  generators build parametrically and only pull materials, so nothing is blocked —
  but the master and `Source_Art/README.md` should match the R=10 contract eventually.
  Deliberate master save required (Resistance #30 hygiene).
- [ ] **Asymmetric Pit rim + deeper carve** *(recovered — director's bespoke art pass)*:
  irregular slumped collapsed-building rim on `T_core_pit` (not a clean hex) + the
  −3 m zig-zag descent; now joined by the **ring-1 pour-in water tiles** (the river
  passing the wound) from the core-anchored evolution.
- [x] ~~**Headless contact-sheet render**~~ ✅ tool live 2026-06-11
  (`Tools/blender/render_contact.py` → `Docs/Images/ContactSheets/`; per-bake
  auto-run still optional later).
- [ ] ~~**`MeasureTileMask` tolerance → absolute**~~ ✅ done 2026-06-10 (250 uu).
- [x] ~~**River material consolidation**~~ ✅ fixed in code 2026-06-11: `M_Water` (+
  the new `M_Green`) added to `hextile_materials.CANON`; the dupes fold into masters
  on the next **Tools ▸ Reimport Hex Tiles** (then Recalibrate — the master keeps the
  'Water' key the measurer reads).
