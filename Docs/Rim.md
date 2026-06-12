# Rim.md — Ring 7: the bowl that holds the town

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

- **Ring 7 = the Rim. 42 cells** (`HexGrid::Distance == 7`). It is the world's
  edge dressed as geography.
- **Zero souls, forever.** `120 + you = Pop 121` is untouchable; rim cells are
  scenery-terminus cells, counted nowhere, restorable never. (Same family as the
  core: outside the soul law, placed by their own pass.)
- **The Rim is eternal.** At Pop 1 the town renders as ghost — the Rim renders
  SOLID. The bowl witnesses the healing; the mountains were here before the wound
  and will outlast it. (Also: rim never re-renders during restoration — static.)
- **Downstream of growth, never upstream.** The rim derives from the grown
  network's boundary state. It never influences growth, constraints, the census,
  or the save format. `FHexRoll` does not change.
- **No gameplay leaks.** Tunnels are sealed (gate + dark interior). The
  town↔elsewhere junction remains the director's cross-project call. The rim is
  atmosphere with hooks, not exits.

## 2. The three instruments

The scale problem decides the architecture: a "mountain" on a 10 m hex footprint
is a tooth, not a range. So the rim is **two layers of theater plus the sky**:

1. **The Rim ring (hex-true near stage).** 42 ring-7 tiles on the normal grid —
   foothill faces, tunnel portals, river mouths. Tile contract holds (R=10
   flat-top, inward edge anchors, measure-and-rotate, manifest discipline).
   Masses rise outward to ~18–25 m: scree, crag, timber, rock face. Parallax-true,
   fog-rooted, walk-up-able where a road runs out.
2. **The Range (backdrop ring, off-grid).** One authored silhouette-ridge mesh
   family (2–3 ridgeline meshes, instanced/rotated/scaled around the bowl at
   apparent 200–800 m, peaks 60–150 m apparent). NOT hex-gridded — placed once by
   the lab setup script. This is the dawn/dusk instrument: the sun rises and sets
   against it. **2–3 authored notches** (low passes) are deliberate gaps for
   crepuscular rays — the skyline's landmark tiles, same medicine as the
   street-level landmark ToDo, applied at altitude.
3. **The sky stack (the engine's built-ins).** Directional sun + SkyAtmosphere +
   SkyLight (real-time capture) + ExponentialHeightFog (volumetric) + optional
   Volumetric Clouds, driven by a day cycle (§6). Lumen makes time-of-day GI free.

A standing **fog seam** at the Rim/Range join hides the parallax lie. The fog is
diegetically honest: cold ring water + warm valley floor = morning mist.

## 3. Derivation & engine architecture

**RimMask** — each ring-7 cell reads its single inward ring-6 neighbor's outward
edge (and nothing else):

| inward edge carries | rim cell becomes |
| --- | --- |
| Road (an artery exit) | **tunnel portal** (or pass) — road runs to a gated arch |
| Water (a river arm) | **river mouth** — outfall or intake (§5) |
| Pavement (everything else) | **foothill face** — weighted variant |

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
  Diegetic gift: the tunnels inherit the artery names — the Main Gate, the 1st
  Street tunnel, the Arapahoe pass.
- **Water mouths = exactly 2** (the river is boundary-to-boundary through the
  wound: one inflow, one outflow, at the destiny's chosen headings, always at two
  distinct stations). Implementation gift discovered at B1: the arm walk ALWAYS
  wrote its outward water bit at the boundary ("visibly flow off the map") — the
  water side needed zero growth changes.
- **Families in the catalog.** Rim tiles' inward edges carry road/water sockets
  that would collide with street necklaces (a tunnel tile reads as a deadend), so
  `FHexTileDef` gains `EHexTileFamily { Street, Rim }` and the resolver filters by
  family per pass. The Weight machinery (2026-06-11) is reused as-is — the rim is
  its second consumer, proving it generalizes.
- **Determinism for free.** Rim variant picks use `VariantSeedFor(Seed, Axial)`
  — same destiny, same mountains, through save/load, no new save fields.
- **Placement pass.** After the frontier loop in `Build()`: derive 42 rim cells,
  resolve against the Rim family, place into rim ISMs (always solid, never
  ghost). Calibration measures rim tiles like any other (their masses carry no
  'Road'/'Water' material keys except the portal road apron / mouth water, which
  is exactly what the measurer should see on the inward edge).

## 4. The rim contract (the kit discipline that makes 42 tiles tile)

Rim tiles neighbor *each other*, and their masses must meet without gaps or
cliffs at shared edges. The street kit's law was "roads cross edge midpoints
perpendicular"; the rim's law is:

> **Every rim tile's two side edges carry the canonical shoulder profile** — a
> fixed height cross-section (ground at the inward third, rising on a fixed curve
> to ~20 m at the outward edge). Variants sculpt only the tile INTERIOR.

Any rim tile then tiles with any other, in any order, at any of the 42 stations.
Notch/pass tiles dip in their *middle*, never at their side edges, so the
profile holds. **B1 implementation:** the flank is one shared height function
`_f(t)` with an interior-only **crest ripple** (zero at side columns — the
skyline stops reading as a fortress wall without breaking the contract) plus
full-perimeter side SKIRTS to z=0 as gap armor at every seam; corner-station
creases are accepted blockout debt for the B2 walk to judge.

## 5. The kit

Blockout discipline, street-kit canvas where ground shows, masses flat-shaded.
New master material: **M_Rock** (plus reuse M_Green for timber stands/benches,
M_Water for mouths, M_TileBorder for gates/timberwork — no 'Road'/'Water'
substrings in new names).

| tile | role | est. |
| --- | --- | --- |
| `T_rim_face_a/b/c` | foothill variants: scree fan / crag steps / pine bench (Weight-pooled) | 3 |
| `T_rim_adit` | face variant with a sealed timber mine adit — the Pit is not the only hole in this valley (low Weight) | 1 |
| `T_rim_tunnel` | artery exit: road apron → gated portal arch in the rock face, lantern hook | 1 |
| `T_rim_pass` | artery exit variant: road switchbacks into a fog-filled notch (ray slot) | 1 |
| `T_rim_outfall` | river mouth: town water pours over a low weir into the ring waterway (THE dusk shot: backlit spray) | 1 |
| `T_rim_intake` | river mouth: ring waterway feeds the inflow arm under a rock lip | 1 |
| the Range | 2–3 ridgeline silhouette meshes, off-grid, instanced around the bowl | 2–3 |
| the ring waterway | one authored annulus mesh following the ring-7 polyline (see below) | 1 |

≈ 8 hex tiles + 3–4 off-grid meshes → catalog lands ~36 meshes, inside the ~40
asset anchor.

**The waterway ruling (recommended: the annulus).** Two ways to terminate the
river; the plan recommends **both, layered**:

- **A — the ring waterway (recommended core).** ONE authored water annulus at the
  mountain foot, following the ring-7 polyline, ~8–12 m wide, sitting just below
  pavement level. The outflow arm pours into it over the outfall weir; the intake
  draws from it — **the destiny's hydrology closes into a loop** (diegetically a
  tarn ring / mill leat — Golden had mills). Because it is one off-grid mesh, the
  per-tile channel-continuity problem (C1 water across 42 rim tiles) never
  exists. It is also the lighting's best friend: a reflection band all the way
  around — the Range doubles in it at dusk, the fog pools on it at dawn.
  Exit roads cross it on small **gate bridges** (we own bridge grammar) — the
  toll-bridge-and-lantern beat at every tunnel mouth.
- **B — mountain caves (the trim).** The waterway itself visibly drains under
  1–2 grated culvert arches (rim-face dressing) — answering "where does the
  water go" with the same shrug the Pit taught us: *down*.

If the director prefers tunnels-only (no annulus): `T_rim_outfall/intake` become
gorge caves and the waterway row is struck — the plan degrades cleanly.

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
- **B2 — The water answers.** The annulus waterway + outfall weir + intake lip +
  gate bridges at exits (+ the culvert grates).
  **Gate:** walk the ring-6 perimeter road: waterway continuous all the way
  around, both mouths read, no z-fighting at the seam; LoadRoll reproduces the
  identical rim.
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

1. **Waterway vs caves**: annulus loop (recommended) or tunnel-mouth caves only?
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

- **Perf:** trivial geometry (42 instances + 4 meshes); the only real cost is
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
