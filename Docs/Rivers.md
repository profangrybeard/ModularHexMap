# Rivers & Bridges — the plan (Phase 2 deliverable, 2026-06-10)

> **The brief (director, 2026-06-10):** the river is a **divider of business and culture
> that simultaneously puts everyone on the same team** — the James in Richmond, the
> Thames in London ("north of the river" / "south of the river" is a real London cultural
> divide; cabbies famously refused to cross it). Our town should *feel* that: two banks
> with distinct character, one shared identity that both banks orient around.
>
> **Locked decisions** (Design.md Resolved #11): water is generated FIRST (foundation,
> not reaction); the river is **frontier-only** (routes around ring 1, the core stays
> dry); architecture is **layered masks** (parallel road + water 6-bit masks per cell —
> never a ternary socket, which would balloon 14 necklaces to ~130); bridges are
> **scarce**.

---

## 1. The design thesis: divide by mechanics, unite by identity

The town already has one organizing feature: the **Pit** — a radial wound, rings of
restoration spreading outward. The river adds the second: a **linear axis** that cuts the
frontier into two banks. Radial + linear is the classic great-city geometry (London =
the City radiating + the Thames cutting; Richmond = the grid + the James and its fall
line). The two features must not compete for the same ground — hence frontier-only: the
wound owns the center, the water owns a chord.

**The divide is emergent, not authored.** Here is the load-bearing insight: all roads
grow outward **from the core**, and the core sits on ONE side of the river. The far bank
can therefore only receive roads **through bridges**. Consequences, all free:

- The **near bank** (core side) is road-dense — the business side, the "City."
- The **far bank** is fed by only the artery roads that bridged — sparser streets, bigger
  blocks, quieter — the residential / working side. **Two cultures, one growth
  algorithm.** No bank-flavor authoring required for the difference to *read*.
- **Connectivity stays guaranteed by construction** — the far bank's entire street
  network descends from bridge crossings, exactly as today's network descends from the
  core's stubs.

**The unifier is permanence + address + assembly.** Three mechanics make the river
"team town":

1. **The river outlasts everything.** The destiny roll rolls the river once per save and
   it is **never re-rolled** — the act-2 rearrange re-rolls the *unrestored remainder* of
   roads and buildings around wound AND water. Two permanent anchors: the Pit (what was
   lost) and the river (what endures).
2. **Banks enter the diegetic address system.** Cells gain a derived `Bank` attribute
   (which side of the chord); addresses gain the divide ("12 Riverside, North Bank").
   The river itself gets a name with billing equal to Main / 1st / Arapahoe.
3. **Bridges are where the town meets.** Scarce by design (one per artery crossing,
   roughly 2–3 per map), so each one is a landmark by default — and the dense-London
   move is available later: **an inhabited bridge** (Old London Bridge carried houses,
   shops, and a chapel for 600 years). A bridge tile can be a soul's home (§5.4).

---

## 2. Architecture: the layered two-mask system

Every cell carries two parallel 6-bit masks:

| Layer | Field | Grown by | Resolved against |
| --- | --- | --- | --- |
| Roads | `FHexCellResult::RoadMask` (exists) | `GrowRoadNetwork` (exists) | `M_Road` verts (exists) |
| Water | `FHexCellResult::WaterMask` (new, default 0) | `GrowRiver` (new, runs FIRST) | `M_Water` verts (new) |

Why layers beat a ternary socket: each layer keeps the binary-necklace math (14 classes
max, rotation by bit-shift, the existing `RotateMask6`); the cross-product only
materializes in the **handful of cells where both layers are nonzero — the bridges** —
and the census (§5.2) tells us exactly which combinations to author instead of
enumerating ~130 ternary classes defensively.

Cell taxonomy after both passes:

| RoadMask | WaterMask | Cell is | Tile source |
| --- | --- | --- | --- |
| 0 | 0 | blank block | `T_street_blank` (as today) |
| ≠0 | 0 | street | 14-config street kit (as today) |
| 0 | ≠0 | river | new water kit (§5.1) |
| ≠0 | ≠0 | **bridge** | new bridge tiles (§5.2) |

**The anchor contract is reused wholesale.** A water edge crosses its hex edge at the
**midpoint, perpendicular** — exactly the road rule — so river curves are C1-smooth
across tiles, river tiles snap like street tiles, and `gen_curved_tiles.py`'s
`arc_centerline` machinery drives the channel centerline unchanged. The river is "just"
a second swept cross-section obeying the same modular law. JSON rolls stay compatible:
old rolls lack `waterMask` → loads as 0 → pure-road rolls reproduce verbatim.

---

## 3. Generation: water first, roads constrained, arteries bridge

### 3.1 `GrowRiver` (new, pure, seeded — sibling of `GrowRoadNetwork`)

A momentum walk, almost the inverse of a road: **loves crossing, hates branching**.

1. Pick an entry edge cell on the map boundary (seeded; biased toward a side angle so
   the chord reads diagonal more often than axis-aligned).
2. Walk cell-to-cell with strong momentum (`RiverStraightBias` ≈ 0.8), gentle meander
   (±1 step), **zero branching in v1**.
3. **Core repulsion:** any step into `Distance ≤ CoreRadius + 1` is forbidden — the
   walk deflects around the core ring (frontier-only, locked). A soft bias *toward*
   passing near (rings 2–3) keeps the water near the heart for drama without violating
   the lock.
4. Exit at the far boundary. Entry/exit cells keep their off-map water edge (the river
   visibly flows off the world — no prune on the water layer; the road-stub prune is a
   road-layer rule only).
5. Result: ~11–13 water cells on the radius-6 map, each with a 2-edge water necklace
   (straight / curve / bend) by construction.

### 3.2 Water-aware road growth (surgical changes to `GrowRoadNetwork`)

- **`MarkRoad` treats water cells like the core**: immutable, un-enterable — a branch
  or side-street that would step into water simply doesn't (the existing
  consider/prune flow handles the refusal cleanly). Lanes never bridge.
- **Arteries bridge.** When a cardinal artery's walk meets the river, it **crosses**:
  the water cell gets the artery's road mask written through it (straight crossing,
  same direction in/out), and the walk continues on the far bank. This is the ONLY
  road-onto-water writer ⇒ bridges ≈ the number of artery–river intersections
  (typically 2–3) ⇒ **scarcity falls out of the growth rules**, no budget knob needed
  (an optional `MaxBridges` cap can come later if a seed misbehaves).
- **Optional later (not v1):** quays — let a side street *end* at the river bank as a
  wharf (`deadend`-at-water). Deferred; it's a flourish, and the prune currently
  removing such stubs is correct v1 behavior.

### 3.3 Diagnostics extended (same discipline as the street kit)

- `run_roll_sweep` buckets **water necklaces** and **bridge (road × water, canonical
  rotation-pair) combinations** — the empirical census that sets the authoring budget,
  exactly how the 200-roll sweep anchored the ~40-mesh street budget.
- `verify_shuffle` asserts: river spans boundary-to-boundary; zero water cells inside
  ring 1; road graph connected (every road cell reachable from a core stub through
  mutual road edges — crossing bridges); **0 unresolved including bridges**;
  souls still = 120 (§5.4).

---

## 4. Engine resolution: two-mask calibration and placement

- `FHexTileDef` gains an authored `WaterMask` (int, default 0) next to `Edges`.
- **Calibration measures water like it measures roads:** `MeasureTileMask` is
  generalized to take a material-name key; water tiles calibrate against `M_Water`
  section verts at edge midpoints (the absolute 250 uu tolerance applies unchanged).
  The popcount sanity check runs per layer.
- **`FindPlacement` matches both layers under the SAME rotation:**
  `RotateMask6(roadReal, k) == cellRoad && RotateMask6(waterReal, k) == cellWater`.
  One extra comparison; the search space is unchanged (tiles × 6 rotations).
- Placement is the existing ISM flow — water tiles and bridge tiles are just more
  catalog rows. Building overlay placement skips water and bridge cells in v1
  (inhabited-bridge geometry is a bespoke later — §5.4).

---

## 5. The tile kit

### 5.1 Water tiles (`gen_river_tiles.py`, manifest-aware, ~4 meshes)

The river cell carries **both banks inside its own tile** — the same move as street
tiles carrying their own sidewalks, and it means **street and building tiles need ZERO
water-adjacent variants** (their edges always meet a standard bank-top at pavement
level). Cross-section contract (all tunable, suggested v1 numbers):

| Element | Width | Z |
| --- | --- | --- |
| Channel (water surface) | 5.0 m | −0.9 m (≈1.55 m below walk level — Camden Lock feel) |
| Channel floor | — | −2.0 m |
| Embankment wall | vertical | bank top → floor |
| Bank walk (each side) | 1.75 m | +0.65 (= `PAVE_TOP`, flush with street pavement) |

Total corridor 8.5 m — fits the R=10 tile with block margin. Materials: `M_Water`
(the resolver key — name must contain "Water", not "Road"), `M_Embankment` (or reuse
`M_Pavement` for the bank walk + a stone wall material). Configs: **straight, curve,
bend** (+ the boundary cells reuse these with an off-map edge — no special tile).
Necklace-complete for a no-branch river by the same argument as the street kit's
completeness over 2-edge classes.

### 5.2 Bridge tiles (start with ONE, let the census order the rest)

A bridge cell = water cross-section + a **road deck** carried over it at street level
(deck top = carriageway 0.5 m, parapets 1.0 m — London stone bridge read), with the
road's edges meeting *its* midpoints perpendicular as always. The dominant case by
construction is **straight road × straight water**; relative angle varies by rotation
pairing (60°/90°-ish crossings). Author `T_bridge_straight` first; run the sweep census;
author only the (road × water) pairs that actually occur with meaningful frequency.
Expectation: 2–3 bridge meshes total. Resist authoring defensively — the census is the
budget, same as it was for streets.

### 5.3 Banks & identity pass (the Richmond layer)

- **`Bank` attribute** (derived, engine-side): flood-fill the frontier from the core —
  cells reachable without crossing water = near bank; the rest = far bank. Exposed on
  the generator for naming, soul assignment, and later per-bank dressing.
- **Addressing:** river name joins the artery names in `HexCoordinates.h`'s diegetic
  helpers; bank enters the address string. Naming candidates for the director: **Clear
  Creek** (Golden, CO — the subtle Front Range seasoning, and Golden's actual creek) or
  a James homage; director picks (§7.2).
- **Per-bank read (later, cheap):** the style-over-fidelity lever — bank-keyed material
  parameter (brick warmth, trim color) on the shared masters, not new meshes.

### 5.4 Souls on the water — the ruling this plan needs (§7.1)

The Pop One arithmetic is sacred: 127 = 7 scar + **120 souls**. A ~12-cell river
occupying frontier cells would eat souls unless ruled otherwise. **Recommendation:
river and bridge cells HOUSE SOULS like any frontier tile** — the ferryman, the
lock-keeper, houseboat moorings, and (the crown move) **the inhabited bridge**: Old
London Bridge carried homes, shops, and a chapel for six centuries; a bridge soul is
the most London thing this town could own. Design.md already allows souls to be "the
town's whole living population, broadly read." This keeps `120 + you = 121` exact,
keeps the soul-count invariant trivial (souls = frontier cells, full stop), and turns
the river from a soul *tax* into the town's most characterful addresses — the divider
literally housing the people who unite it.

---

## 6. Implementation phases (each with a verification gate)

| Phase | Work | Gate (must pass before the next phase) |
| --- | --- | --- |
| **R1 — growth** | `WaterMask` on `FHexCellResult` + `FHexRoll` (schema-compatible); `GrowRiver`; water-aware `MarkRoad`; artery bridging; sweep + verify extensions | Sweep over 200 rolls: river spans edge-to-edge every roll; 0 water cells in ring ≤ 1; bridges 1–4; road graph connected; souls = 120; water-necklace + bridge-pair census printed |
| **R2 — water kit** | Cross-section locked; `gen_river_tiles.py` (straight/curve/bend) + `T_bridge_straight`; manifest + registry + addon rows; `M_Water` master | Tiles snap C1 in the addon preview grid; bake → reimport clean; materials consolidate to masters |
| **R3 — resolution** | `FHexTileDef.WaterMask`; material-keyed `MeasureTileMask`; two-layer `FindPlacement`; catalog rows; bridge ISM placement | `verify_shuffle` with river on: calibration OK (both layers), **0 unresolved**, placed-roll re-verify passes |
| **R4 — identity** | `Bank` attribute; river name + bank addressing; constraint knobs (`bRiver`, `MeanderChance`); embankment dressing pass | Design walk: the two banks *read* different; the bridge reads as a landmark; addresses speak the divide |

R1 and R2 are independent (C++ vs Blender) and can interleave. Per the locked queue
(Roadmap), the **restoration loop ships between this plan and R1** — when R1 lands, the
river becomes part of every destiny roll with zero migration (old rolls = waterMask 0).
One interaction to honor in the restoration loop's BFS: bridge cells gate the far bank's
restoration order, which is *correct* — the far bank heals after its bridge does.

## 7. Decisions — RULED (director, 2026-06-10)

1. **River souls: YES.** River/bridge cells house souls; Pop 121 arithmetic untouched.
   Director's framing of the river-soul cast (capture verbatim — this is authoring
   direction): *"a person climbing under the bridge, or a person maintaining the
   kayaks, or a person that's a lifeguard, or a person that was lost to the river."*
   Note the last one — a soul the river TOOK is still one of the 120 you bring home.
   The inhabited bridge (Old London Bridge precedent) stays a marquee landmark
   candidate.
2. **The river's name: "River."** Deliberately vanilla — flavoring it Richmond *and*
   Golden is muddy evolution; plain until the director makes up his damn mind.
   (Accidentally authentic: Londoners call the Thames "the river" in daily speech.)
   Implementation: the diegetic helper uses the literal string `River`; trivially
   re-nameable later.
3. **Channel scale: 5 m, one cell wide.** Game scale, not sim scale. The two-cell-wide
   option stays architecturally possible and deliberately unbuilt.
4. **Quays/wharfs** — deferred to post-R4 flourish (reopens the prune rule deliberately
   when wanted).

## 8. Tuning knobs (planned)

| Knob | Default | Effect |
| --- | --- | --- |
| `bRiver` | true | Roll a river at all (off = today's behavior, bit-exact) |
| `RiverStraightBias` | 0.8 | Momentum; lower = lazier meander |
| `RiverCoreStandoff` | CoreRadius + 1 | Rings the river may not enter (locked ≥ this) |
| `RiverNearBias` | gentle | Pull toward rings 2–3 so water passes near the heart |
| `MaxBridges` | 0 (= uncapped) | Safety cap; scarcity already emerges from artery-only crossing |
| `CHANNEL_W / BANK_W / WATER_Z` | 5.0 / 1.75 / −0.9 | Blender cross-section contract (§5.1) |
