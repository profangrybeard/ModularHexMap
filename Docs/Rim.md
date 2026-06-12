# Rim.md — Rings 7–8: the seam waterway and the horizon

> The boundary-ring plan (director's brief 2026-06-11): roads vanishing into mountain
> tunnels, the River emptying into a ring waterway or mountain caves, plain ring-7
> tiles in variants, and a skyline that makes UE5's built-in day/night cycle EARN
> something — mountain silhouettes, an excuse for fog, dawn and dusk moments.
> Sibling doc to [Rivers.md](Rivers.md); same discipline: layered architecture,
> census-gated phases, rulings asked before they're needed.

## 0. The brief, distilled

The town is a diorama with no fourth wall: at ring 6 the streets stop, the river
stops, the world stops. Ring 7 closes the bowl — **the town sits in a mountain
valley** (the Golden, CO seasoning finally gets its Front Range). The rim is not
more town; it is the *stage* the town sits on and the *instrument* the lighting
plays. Everything in this plan serves four readable moments: **dawn fog burning
off the water, noon's clean diorama, golden-hour rakes and alpenglow, lamplit
night under a silhouette ridge.**

## 1. Identity & law

- **The Rim = rings 7 AND 8. 90 cells** (42 at `HexGrid::Distance == 7`, 48 at
  `== 8`). Ring 7 is the town's far bank; ring 8 completes the water and rolls
  away as horizon. It is the world's edge dressed as geography.
- **Zero souls, forever.** `120 + you = Pop 121` is untouchable; rim cells are
  scenery-terminus cells, counted nowhere, restorable never. (Same family as the
  core: outside the soul law, placed by their own pass.)
- **The Rim is eternal.** At Pop 1 the town renders as ghost — the Rim renders
  SOLID. The bowl witnesses the healing; the mountains were here before the wound
  and will outlast it. (Also: rim never re-renders during restoration — static.)
- **Downstream of growth, never upstream.** The rim derives from the grown
  network's boundary state. It never influences growth, constraints, the census,
  or the save format. `FHexRoll` does not change.
- **No gameplay leaks.** Exit decks run off toward the haze (gateposts, no
  destination). The town↔elsewhere junction remains the director's
  cross-project call. The rim is atmosphere with hooks, not exits.

## 2. The instruments (B2 take two — LANDED 2026-06-12)

> History: the first B2 build (continuous 8.5 m hill ring + one Range ring,
> `69a7e52`) was **reverted on the director's walk** — from street eye height the
> near layer occluded the far one entirely. The law that came out of it: **all
> scenery composition passes the eye-height gate (`render_eyeline.py`) before it
> ships to the engine.** The orbit camera doesn't get a vote.

The town sees its mountains the way a real valley town does: across water, over
low ground, in the SKY BAND above the rooftops. Sight-line law at eye 2.4 m:
berms ≤ 3°, near Range ~13°, far Range ~16° — everything visible, far stacking
above near, from ring 6 and from the town's heart alike.

1. **The two-ring seam — rings 7+8 ARE the waterway** (director, 2026-06-12,
   after the one-ring Ringwater lost the rotation war: "ring 7 is land on the
   city side, blank, river on the edge; ring 8 is water on the inside edge
   completing the river bank, land blending to horizon — a standard loop
   solves the water connectivity, then swap in the water and street connection
   points"). Each ring contributes ONE BANK: ring-7 tiles carry a half-channel
   at their OUTWARD edge, ring-8 tiles the mirror half at their INWARD edge —
   every 7↔8 edge is water-meets-water **by construction**, so connectivity IS
   edge-socket matching, the grammar the whole kit lives by. Connection points
   are ordinary mask-matched variants: `river7` (the town river flows through
   into the loop) and `exit7` (the artery crosses on a deck with gateposts).
   No mouth tiles, no forced-bit ring water law, no special cases.
   **Orientation is the mask:** every rim tile's water pattern is
   rotation-asymmetric, so the resolver's normal measure-and-rotate places it
   — the M_RimKey marker and the flank inference are DELETED (each could agree
   with itself while wrong; a measured water bit cannot).
2. **Retired, in order:** the notched-band draft; the land grammar
   (banks/berms/knoll/adit/tunnel/pass/mouth works) and the separate loop mesh
   (`gen_waterway.py`); the one-ring **Ringwater** (water_a/b/c/wide + bridge —
   its 5.5 m full-width seam contract, its forced-inward-bit ring water law,
   the RimKey marker, the flank inference). Each pruned from the catalog with
   its assets when its successor landed; the lessons stayed (the loop must
   read as one body, seams cross at full width, orientation derives from
   measured water).
3. **The Range, TWICE (the parallax that survived).** Two off-grid ridge rings:
   **near ~250 m** (peaks ~38–75 m, 8 instances) and **far ~500 m** (peaks
   ~90–180 m, 6 instances, headings offset so far peaks rise in near saddles).
   Ring slides against ring as you walk — the depth lives where it can be seen.
   Two aligned gaps (~120°/~300°) stay empty in BOTH rings for B3's sun-path
   ray notches. In-engine, SkyAtmosphere's aerial perspective tints the far
   ring for free — true atmospheric depth cueing without a second material.
4. **The sky stack (B3).** Directional sun + SkyAtmosphere + SkyLight +
   volumetric ExponentialHeightFog, driven by the day cycle (§6). Fog stacks in
   the three gaps: water-to-berms, berms-to-near-ring, near-to-far.

The fog is diegetically honest: cold ring water + warm valley floor = morning
mist.

## 3. Derivation & engine architecture

**Ring 7** — each cell reads the road/water bits its adjacent ring-6 cells send
across the boundary. Its inward edge is the **WORLD-distance pick with a 1-uu²
epsilon tie-break** (hex distance TIES on side stations and skews the tile 60°;
corner-adjacent stations differ by ~2 uu² in 10⁸, so float order must be
deterministic and identical in engine, gate, and eyeline mock):

| town sends | ring-7 cell becomes |
| --- | --- |
| Road (an artery exit) | **`exit7`** — road through (inward→outward) on a deck over the half-channel |
| Water (a river arm) | **`river7`** — water through; the town river flows into the loop |
| Pavement (everything else) | **`land7`** — town-side blank canvas |

Every ring-7 tile carries the half-channel at its OUTWARD edge regardless.
**Ring 8** — `bank8` everywhere: the mirror half-channel at its INWARD edge,
low horizon land otherwise. (Exit decks currently END at the seam — ring 8
does not yet continue the road off the map; a named B3 item.)

- **Exits = artery mouths only.** `NumArteries = 3` (Main / 1st / Arapahoe), and
  each avenue walks BOTH directions — so destinies carry **2–6 exits** (B1 census:
  typically 3–4; bank-died arms reduce it). The dangling-stub prune keeps killing
  ordinary streets at the boundary — only the NAMED roads leave town. Growth
  change is one rule: *an artery tip that reaches ring 6 keeps its outward edge*
  (the bit was always written; the prune now exempts it). Two laws found by the
  B1 census (each was a real 1-in-30 roll):
  - **The road yields the gap** — an artery may not claim a station the river (or
    an earlier artery) already owns; it dead-ends at the rim like any street
    (same philosophy as gate avenues yielding to the river in town).
  - **The river leaves by two different gaps** — the arm walk retries any roll
    whose two arms exit the same station (a hydrological U-turn no tile serves).
  Diegetic gift: the exits inherit the artery names — the Main Gate, the 1st
  Street crossing, the Arapahoe deck.
- **Water mouths = exactly 2** (the river is boundary-to-boundary through the
  wound: one inflow, one outflow, at the destiny's chosen headings, always at two
  distinct stations). Implementation gift discovered at B1: the arm walk ALWAYS
  wrote its outward water bit at the boundary ("visibly flow off the map") — the
  water side needed zero growth changes.
- **Families in the catalog.** Rim tiles' edges carry road/water sockets that
  would collide with street necklaces, so `FHexTileDef` gains
  `EHexTileFamily { Street, Rim, Rim8 }` and the resolver filters by family per
  pass. Ring 8 NEEDS its own family: `land7` and `bank8` are mask-identical
  (one water bit), and without the family split the rings interleave. The
  Weight machinery (2026-06-11) is reused as-is.
- **Determinism for free.** Rim variant picks use `VariantSeedFor(Seed, Axial)`
  — same destiny, same mountains, through save/load, no new save fields.
- **Placement pass.** After the frontier loop in `Build()`: derive 42 + 48 rim
  cells, resolve each ring's road/water target masks against its family, place
  into rim ISMs (always solid, never ghost). Calibration measures rim tiles
  like any other — and **water must be CLOSED SOLIDS to measure** (the river
  kit always was; open ribbons measure erratically).

## 4. The rim contract (the kit discipline that makes 42 tiles tile)

Rim tiles neighbor *each other*, and their water must meet seamlessly at every
shared edge. The street kit's law was "roads cross edge midpoints
perpendicular"; the rim's law is:

> **The seam channel: each ring contributes one bank.** Ring-7 tiles carve the
> half-channel at their OUTWARD edge; ring-8 tiles the mirror half at their
> INWARD edge. The half holds ~3.8 m through the mid-edge, easing only to
> 3.4 m at the side corners (quartic plateau, near-constant width — v1's
> 2.2 m parabolic lens beaded the loop; B2.1), and the band runs to |x| 6.1
> so every RADIAL seam carries a shared corner pool that **hugs the
> measurer's exclusion discs** (no water within 2.75 m of a side-edge
> midpoint = the engine's 2.5 m sampler + margin; the measurement law lives
> in Source_Art/README) — each side edge measures as a single water bit.
> The water surface is ONE closed swept solid (v1's axis-aligned box
> strips staircased against the sloped corner edges). Cross-section matches
> the river kit (surface −0.9, floor −2.0) — town river mouths meet the loop
> flush. Variants sculpt only the tile INTERIOR.

Authoring convention: **edge 0 = the water edge**; the engine rotates it
outward for ring 7, inward for ring 8. Any ring-7 tile then meets any ring-8
tile water-to-water at every 7↔8 edge, and orientation derives from the
measured water mask itself — no marker that can drift from the thing it marks.

## 5. The kit

Blockout discipline, street-kit canvas where ground shows, masses flat-shaded.
New master material: **M_Rock** (plus reuse M_Green for timber stands/benches,
M_Water for mouths, M_TileBorder for gates/timberwork — no 'Road'/'Water'
substrings in new names).

| tile | role | Weight |
| --- | --- | --- |
| `T_rim_land7` | ring 7: town-side blank canvas + the outward half-channel | 1.0 |
| `T_rim_river7` | ring 7: the town river flows THROUGH into the loop (water 0,3) | 1.0 |
| `T_rim_exit7` | ring 7: artery crosses on a deck + gateposts (road 0,3) | 1.0 |
| `T_rim_bank8` | ring 8: inward half-channel + low horizon land (≤ 2.5 m, eyeline-gated) | 1.0 |
| the Range | near (~250 m) + far (~500 m) ridge rings, off-grid, transforms in `scenery_table.json` | — |

4 hex tiles + the Range → catalog = 28 rows. **Named debt:** one variant per
role at Weight 1.0 — `land7` repeats ~36× and `bank8` ~46× per destiny.
Bankline meander variants (gentle arc / lazy S / bulge — the Ringwater's
vision, still right) are the obvious Weight-pooled expansion, slotted after
the director's gap review names what the seam needs first.

**The waterway ruling — RESOLVED past both of its own options (2026-06-12).**
Neither an authored annulus nor cave mouths: the loop IS rings 7+8. Because
the channel is built from the kit's own edge-socket grammar, the per-tile
channel-continuity problem the annulus existed to dodge dissolved instead of
being dodged. Everything the annulus promised still stands, now destiny-true:
the hydrology closes into a loop (diegetically a tarn ring / mill leat —
Golden had mills), a reflection band all the way around — the Range doubles
in it at dusk, the fog pools on it at dawn — and exit decks with gateposts
keep the toll-bridge-and-lantern beat at every crossing.

## 6. Day/night — the playscape's pulse

**Stack:** UE 5.7's built-in **Day Sequence** plugin (the engine's day/night
framework — a DaySequenceActor driving the sun/sky/fog on a 24 h timeline) is the
first choice; verify its 5.7 maturity at B3 start, with the eternal fallback
being SunSky (Sun Position Calculator) + our own curves. Either way a small
`AHexDayCycle` director actor owns the dials: `TimeOfDay` (0–24), `DayLength`
(real minutes per cycle; night compressed), pause/scrub, and the curves below.

**The sun follows the river.** Sun azimuth anchors to the destiny's river axis by
default (override dial for the director): the sun rises near the intake heading
and sets near the outflow. Every save composes its own golden hour — light lying
down the water at dusk is the Thames-on-fire shot, and it's *destiny-aware*.
The Range's authored notches get placed at the anchor headings by the setup
script, so the first and last light come through the passes as rays.

**The four moments (the acceptance tests of the whole feature):**

1. **Dawn** — thick valley fog pooled on the waterway and river (LocalFogVolume
   ring + low ExponentialHeightFog), burning off on a curve; first rays through
   the east notch; rim faces light before the town floor (the bowl effect).
2. **Noon** — fog floor near zero, clean diorama read, short shadows; the hex
   lattice at its most legible (the dev-tool hours).
3. **Golden hour** — long shadow rakes from the Range across 10 m tiles (chunky,
   readable); **alpenglow**: east-facing rim masses hold warm light while the
   town dims (a warmth param on M_Rock keyed to sun angle — same trick family as
   the bank-keyed water params); building windows kick on near dusk (emissive
   param on the M_Building master — the seam already exists).
4. **Night** — short by design (DayLength curve spends ~15% on night); moon as a
   second cool directional; the Range silhouette against stars; tunnel portals
   and gate-bridge lanterns as warm points; the ghost destiny question (below).

**Fog instruments:** one ExponentialHeightFog (volumetric on, density/height on
the day curve) + LocalFogVolumes for: the waterway ring (dawn pool), the Pit (the
wound breathes — pairs with the pour-in art pass already queued), and the
Rim/Range seam bank (constant, hides the join).

**Known check item:** `M_GhostTile` is translucent **unlit** — at night the
unhealed destiny will glow against the dark. That might be the best accident in
the project (the un-lived town shimmers until you heal it) or a bug. B3 walks it
at night before we decide; if bug, the ghost master gets a day-cycle dim param.

## 7. Phases & gates

- **B1 — The bowl closes (geometry).** ✅ **LANDED 2026-06-11.** Engine:
  `EHexTileFamily` + family-filtered resolvers + the `M_RimKey` measured
  orientation layer (third `MeasureTileMask` key — mask-(0,0) faces orient by
  it) + `BuildRim` pass (derive 42 stations from boundary outward bits, resolve,
  place always-solid) + artery-exit prune exemption + the two yield laws (above).
  Kit: `gen_rim_tiles.py` (8 blockout tiles on the shared flank contract; river
  channel cross-section mirrored exactly at the mouths) + manifest/registry +
  `setup_rim.py` (catalog = 32 rows) + bounds-framed contact sheets.
  **Gate: `verify_rim_b1.py` ALL PASS** — 30 seeds, rim 42/42 every roll, exits
  == mask-derived expectation (2–6 observed), mouths == 2, souls == 120,
  0 unresolved; expectations re-derive from LastNetwork masks in Python so the
  gate cross-checks the C++ derivation rather than trusting it.
  *(The B1 kit — 8 land-grammar blockouts on the flank contract — was retired
  by B2's redesigns; the families, the placement pass, and the gate survived.)*
- **B2 — The water answers.** ✅ **LANDED 2026-06-12, three designs deep**: the
  parallax sandwich (reverted on the walk) → the one-ring Ringwater (killed by
  the rotation war) → **the two-ring seam** (§2). Engine: `BuildRim` derives
  and places rings 7+8 (90 cells) by family; orientation from measured water
  masks (key marker + flank inference deleted). Kit: `gen_rim_tiles.py`, 4
  tiles on the seam-channel contract (§4).
  **Gate: `verify_rim_b1.py` ALL PASS 30/30** — four layers, each added after
  a failure the previous layers could not see: counts (r7 42 / r8 48 / exits
  == mask-derived / mouths == 2), calibration trust (hard-abort), ring
  identity, per-instance orientation vs MEASURED masks (~2,700 instances/run).
  Director's walk 2026-06-12: **passed** — "it isn't good yet but the promise
  of the first pass held"; the gaps are named and answered in B2.1.
- **B2.1 — The gap pass (v2.2 IN-ENGINE 2026-06-12, gate ALL PASS; director's
  walk pending).**
  The director's walk screenshots named the disease: **the loop read as a
  necklace of 42 lens ponds, not one body** — the v1 parabolic bank dove
  steepest exactly at the seams, bead-to-bead water was a ~1 m stepped
  thread — plus the corner sawtooth (the water surface was 16 axis-aligned
  boxes staircasing on the sloped corner edges) and the metronome (one
  dressing per role on a perfectly regular rhythm). The ruled law stands:
  the loop must read as ONE body. **The answer, two takes.** v2.1 (quartic
  plateau 3.8 → 3.4 m, corner pools to |x| 6.1, surface rebuilt as one
  closed swept solid — sawtooth dead) put pool water 1.74 m from the
  side-edge midpoints — INSIDE the measurer's 2.5 m sampling disc — so the
  measured mask went 3-bit against 1 authored: **calibration distrusted the
  whole catalog and every rim tile flipped to authored-guess yaw** (the
  director's reversed-water walk; the v1 disease, self-inflicted, and it
  reached his eyes because the walk ran before the gate). **v2.2 (BAKED,
  bake-gate green):** the corner pools hug the exclusion discs — water
  crosses each radial seam through the ~2 m wedge between disc and corner
  vertex, swelling fast off the seam (the legal maximum under the 250-uu
  sampler) — and `gen_rim_tiles.py` now runs the engine's sampler arithmetic
  as a HARD BAKE GATE: measured == authored on all four tiles, a popcount
  lie can never reach the engine again. **The import then exposed a deeper
  lie:** render LOD0 is PRESENTATION — the Nanite fallback decimated v2.2's
  slender water strips (420 authored verts → 26 in-engine) and the measurer
  read 0x00; `MeasureTileMask` now measures the imported **MeshDescription**
  (source payload; render data = cooked-runtime fallback) and unions all
  key-matching slots (Resistance #33). Recovery chain (probe → reimport →
  gate): **calibration OK, `verify_rim_b1` ALL PASS 30/30.** The measurement
  law is recorded in Source_Art/README. The eyeline harness grew
  **seam close-up shots**
  (seam_side / seam_corner / seam_junction) — the 90 m plan frame could not
  see a 3 m junction, which is how the necklace shipped under a green gate.
  **Escalation, if the walk wants wider junctions:** a water-specific
  sampler radius (250 → ~150 uu; one C++ line + a full recalibration sweep)
  legalizes near-full-width junction bays — through-water sits AT the
  midpoints, so detection is unaffected. Director's call after the v2.2
  walk.
  **Still owed:** the director's walk; then the metronome (meander variants
  — the §5 debt, second bake).
- **B3 — The sky works.** Day Sequence (or SunSky fallback) + `AHexDayCycle` +
  river-axis sun anchor + fog instruments + the Range placed with notches on the
  anchor headings.
  **Gate:** a scripted 24 h timelapse (HighResShot sequence — the known capture
  path) hitting all four moments; director walks dawn and dusk live; ghost-glow
  ruling made.
- **B4 — The moments (polish).** Alpenglow warmth param, window emissives at
  dusk, lanterns at portals/bridges, moon/stars, adit/pine variant expansion,
  Weight dialing on rim faces. All director's-eyeball items, no gates — rulings
  recorded here as they land.

## 8. Open rulings (director — asked before they block)

1. ~~**Waterway vs caves**~~ — **RESOLVED 2026-06-12**, past both options: the
   rings ARE the waterway (§2, §5).
2. **Sun anchor**: river-axis default (recommended) or fixed east–west?
3. **The Range's light**: pure silhouette (cheapest, always-dark cards) or
   lit-at-grazing faces (buys real alpenglow — recommended)?
4. **Night share** of the cycle (~15% recommended) and whether the cycle runs by
   default in ShuffleLab or only when the day-cycle actor says so.
5. **Ghost glow at night**: feature or bug? (Walk it at B3 before ruling.)
6. **Names**: the waterway wants one (the Tailrace? the Leat? the Ringwater?) —
   the River stayed "River" by choice; same option stands. The exits inherit
   artery names regardless.

## 9. Budget & risks

- **Perf:** trivial geometry (90 rim instances + the Range); the only real cost is
  volumetric fog, which is the point. Lumen eats time-of-day for free. Rim never
  rebuilds during restoration.
- **Scale illusion** is the design risk: if the Range reads as 40 m props the
  bowl dies. Mitigations: fog seam, grazing-light silhouettes, notch placement,
  no player path that flanks the Rim (ring 6 is the closest approach).
- **Scope traps, named:** no tunnel interiors, no weather system (curves only),
  no seasonal pass, no rim souls ever. The moment a tunnel wants gameplay it
  becomes the dungeon project's junction conversation, not a rim feature.
- **Asset anchor:** ~36 of ~40 meshes after the rim kit — the next kit after this
  one pays the consolidation tax first.
