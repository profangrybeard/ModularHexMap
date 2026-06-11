# Design Vision

The north star for what the hex map *is* and what it's for. Pipeline mechanics live in
[Pipeline.md](Pipeline.md); tile authoring rules in
[../Source_Art/README.md](../Source_Art/README.md).

## The map is a town hub, not a level

The hex map is a **persistent town** — the surface counterpart to underground dungeon
crawling. It is **not** a space for combat or parkour. The player comes up from the
dungeon to **tour the town, visit with locals, buy things, and head back down**.

Crucially, **the town is a record of the player's achievements**: it grows and fills in
as the player progresses below. Tiles are earned/placed over time, so the assembled city
is a visible trophy case of how far the player has come.

## Look & feel

- **Dense, turn-of-the-century London** (Edwardian / late-Victorian, ~1900): tightly
  packed streets and row buildings, not sprawl. The 10 m tile size was chosen specifically
  to support this density — big enough to move around in, small enough to pack a city.
- **Subtle Colorado Front Range flavor** — quietly inflected by **Golden** and **Louisville,
  CO** (historic brick Main Streets, old mining-town character, foothills). A light seasoning
  on the London base, *not* a replacement — it surfaces in naming (e.g. the **Arapahoe**
  artery) and tile detailing rather than wholesale architecture.
- **Style, not fidelity.** The visual target is a **coherent stylized look driven by a modular
  material / lighting pipeline** — **trim sheets, lighting tricks, reused modular meshes** — *not*
  an AAA per-asset fidelity pass. This is the lens for the whole build: 120 walk-in interiors are
  only reachable as a *style* (shared trim-sheet materials + lighting + per-soul dressing,
  organized by the handful of road-edge configs), never 120 bespoke from scratch. The pipeline is
  what makes breadth cheap; the art direction is consistency over polish.

## Tiles

- A tile is a **flat-top hex, 5 m radius / 10 m across** (LOCKED — see Source_Art/README).
- Tiles are mostly **building lots** (shops, homes, pubs, civic) plus **road/street tiles**.
- **Roads govern connection**: which of a tile's 6 edges carry a road determines how tiles
  neighbor and how the street network forms. This is the assembly grammar.
- Each building tile fronts the street via a **door on a road edge**.

## Population = rescued people (1 tile = 1 soul — the LAW)

The town's size *is* the rescue count. **One frontier tile houses one soul, full stop** —
this is the pipeline's law (locked 2026-06-10; production may bend it for fun, the
pipeline never does). The generator's `Souls` property + label is the count of frontier
tiles; the core is the scar and is never counted. **A soul settling on a tile with
building sections joins that tile's building group** — the player's choice of *which*
tile a rescued soul settles is the lever that makes each player's city feel different.

*(History: an interim `Occupancy = (6 − roadEdges) × 2` sum existed through 2026-06-09;
all of that machinery was removed 2026-06-10 — count, not sum.)*

## "Pop One" — the spine (1 → 121)

**Title & win-number.** The game is **Pop One**: you begin as the *one* — the last of the
town's population — and end at **Pop 121**. The number isn't picked, it's the map's geometry:
a **radius-6** hex town is the centered hexagonal number `3·6·7 + 1 = 127` tiles. The center
**7 collapse** into the Pit (the inciting wound), leaving **120 frontier tiles**. Each frontier
tile is **one soul** you recover from the dungeon and bring home. `120 rescued + you = 121`
(= 11²). You are the **alpha and the omega** — Pop 1 at the start, Pop 121 at completion. The
readout is already on screen (the live population / vacancy metric).

**The 7 are never rebuilt.** The collapsed core is a **permanent scar** — the dead whose loss
began the story, and the mouth of the dungeon. The heart stays a wound; the **ring of life
around it** is what you bring back. You (Pop One) are the **survivor / player, not a tile** —
you don't occupy a frontier cell, you restore them.

**1 tile = 1 soul (the model the game commits to).** This resolves the population question in
favor of a **count, not a sum**. The interim metric (`Occupancy = (6 − roadEdges) × 2`, summed)
was a *road-cells-vs-block-cells* model; the spine instead makes **every frontier tile a soul's
home that also carries its share of street**. This is exactly what the **per-tile spline roads**
(pivot 2026-06-06, see [PerTileSplineRoads.md](PerTileSplineRoads.md)) enable: each tile is
self-contained — its road is baked along its own edges (anchored at the midpoints, C1-smooth to
neighbors), and the rest is that soul's block / interior. So roads stop being separate cells;
**growth decides which *edges* carry road**, and a cell's road-edge config selects **which
building-variant** fits it (corner home, through-street home, dead-end home…). 120 tiles ⇒ 120
souls, 1:1.

**Souls aren't only people.** A recovered "soul / shadow" can be **another living creature**, not
just a person — the 120 are the town's whole living population, broadly read. Variety of
inhabitant = variety of tile / interior.

## Interiors

- Every building has a **simple interior** — deliberately minimal, in the spirit of a
  **classic JRPG room**: just enough to convey the **owner's character/personality**
  (a shopkeeper's counter, a cluttered study), and nothing more.
- Interiors are flavor + light interaction (talk, buy), **not** gameplay arenas.
- **Model: walk-in, on-tile.** The player walks straight into the room on the tile — no
  separate scene, no load. Interiors are constrained to the ~5×6 m footprint and live in
  the same world as the streets.

## The Pit & the fixed core — the anchor (0,0)

The town has a **focal point**: a **pit/sinkhole at the dead center**, where 1st & Main once
crossed. It's the story hook — *the wound the whole town regrew around* — and it doubles as
the **level transition** down to the dungeon. It is anchored at axial **(0,0)** and **never
moves**: the one fixed landmark for saves, quests, and the act-2 "rearrange the town" beat
(you rearrange *around* the Pit; the wound stays put).

**The Pit tile (first true bespoke tile):**
- **A terminus, not a roundabout.** Roads and sidewalks flow *into* the Pit and dead-end at
  the rim — it's a *sink* in both the literal and graph sense. It must be **approachable by
  any street or sidewalk route** that reaches it, so multiple edges are open.
- **Irregular, not a circle.** Some of its 6 edges are open (a street/pavement leads in);
  others are **blocked by buildings that slumped into the hole** — a chaotic, collapsed rim.
  Its edge mask is **authored and asymmetric**, *not* a necklace from the 14-config street kit.
- **Descent + transition.** Stairs / slides / ropes / ladders (varied, authored). The player
  approaches and descends; at some point a prompt model asks *"Ready to descend?"* → that
  confirmation triggers a **level load** into the dungeon. (Gameplay/BP layer on the tile, not
  generator math.)

**Fixed Core vs Procedural Frontier.** The map runs in two regimes:
- **Fixed Core = `Distance ≤ 1`** — the Pit plus its 6 neighbors = **7 authored, pinned,
  immovable tiles**. The 6 ring-1 tiles are **story tiles** with their own *narrative-gated*
  restoration arc (story beats TBD), **decoupled from the rescue-count/population metric** —
  their occupancy is **excluded entirely** from `Estimated Vacancies` (the tally counts only
  frontier tiles, `Distance > CoreRadius`).
- **Procedural Frontier = `Distance ≥ 2`** — everything the randomizer grows, *around* the
  locked core.
- **Growth reseeds around the core.** Today `GrowRoadNetwork` spawns arteries from `(0,0)`.
  New flow: the core's road masks are **pinned**; arteries seed from the **ring-1 outer edges**
  and grow outward. The Pit emits no roads — it *receives* them. Connectivity stays guaranteed
  because the frontier reads the core's exposed road stubs.

**Build status — the center, caught up (2026-06-06).** `gen_pit_core.py` builds the **7-tile fixed
core** at the current scale/style (**2× R=10**, the curved-frontier kit, tile-border lips) and it's
**hardwired into the live `HexShuffleGenerator`** (`DA_HexCoreLayout`, placed verbatim with a
*measured* rotation — see gotchas). The center reads as a **radial star**:
- **The Pit** = the center tile (0,0): a recessed hexagonal **void** (~2 m, dirt walls + floor)
  with all six carriageways **breaking at the rim** — roads drain in and dead-end (the sink). Its
  edges still present road so neighbours connect; the break is *internal* geometry.
- **6 spokes** = each ring tile is a straight **3 m** road, Pit→frontier (the cardinal arteries
  pass through it). A clean radial star draining to the Pit.
- **No rim/alley ring.** The earlier "boundary alley" threaded a 2 m loop out through 6 distance-2
  *valley* tiles, which hex-geometrically zigzagged into a **cogwheel**, not a ring — **dropped**.
  Those cells are ordinary frontier now.

**Still the next pass:** the **asymmetric collapsed-building rim + descent geometry** (stairs /
ladders / the "Ready to descend?" prompt) and, eventually, a deeper zig-zag −3 m carve. The clean
hex void is the *representation*; the irregular slumped rim is the art pass on top.

## Coordinate & address system

The hex math is unchanged — axial `(Q,R)`, cube `y = −Q−R`, flat-top, edge 0 = +Y (see
`HexCoordinates.h`). Two **semantic layers** sit on top:

1. **Restoration rings.** `HexGrid::Distance(C)` *is* the ring index: Pit = ring 0, story
   ring = 1, frontier = 2+. Rings read as concentric restoration arcs radiating from the Pit.
2. **Named arteries → diegetic addresses** (the player-facing "1st & Main"). The three hex
   axes are three through-streets that all meet at the Pit:

   | Cube line | Cells | World run | Street |
   | --------- | ----- | --------- | ------ |
   | `Q = 0`   | `(0, r)`   | N–S   | **Main Street** |
   | `y = 0`   | `(−t, t)`  | NW–SE | **1st Street** → the Pit is *1st & Main* |
   | `R = 0`   | `(t, 0)`   | NE–SW | **Arapahoe** |

   Block number along an artery = ring index (×100 for address feel) with a direction suffix
   (e.g. `(0,2)` ≈ *"200 N Main"*). On-artery cells address cleanly; off-artery frontier cells
   get a "nearest cross-street" approximation later.

**Code path when built:** (1) `GrowRoadNetwork` gains `CoreRadius` + a pinned-mask input
(pin core, seed arteries from the boundary); (2) an authored **core layout** asset (7 cells:
coords, masks, bespoke-mesh refs, story-beat IDs); (3) the **Pit bespoke tile** (asymmetric
sinkhole, collapsed-edge mask, descent geometry); (4) vacancy tally excludes the core; (5) an
address helper in `HexCoordinates.h` (axis name + block).

## Rivers & bridges (next challenge — design intent)

> **2026-06-10:** plan in progress as the highest-priority deliverable (Docs/Rivers.md).
> Two decisions locked: the river is **frontier-only** (routes around ring 1; the authored
> core stays dry), and the architecture is **layered masks** (parallel road + water 6-bit
> masks per cell — never a ternary socket). See Resolved #11.

**Water is foundation, not reaction.** The river is generated **first**, as the bedrock the
city forms around — roads and tiles react to *it*, never the reverse. This flips the
generation order: **water → roads → buildings**, with water as a first-class layer, not a
post-process.

River rules are almost the *inverse* of roads:
- **Spans the map** edge-to-edge (loves crossing from one side to the other) — connection-like.
- **Hates branching.** A single dominant channel; branches are rare. (Momentum/meander, very
  low branch chance.)
- Because it runs as a continuous, rarely-branching **barrier**, it forces **roads to struggle
  to cross it** — crossings are **bridges**: scarce, special tiles (road-over-water).

Generator implications: a **river growth pass before road growth**; a new edge socket type
(**water** vs road vs pavement); roads grow with water as a constraint and **bridge only where
needed**; bridge tiles carry both road and water sockets. (Resumes the rivers/bridges work
from the prior prototype.)

## Scope guardrails

- No combat. No platforming/parkour. No physics playground.
- Interiors stay simple — character over complexity.
- The town's job is **identity, NPCs, and shopping** between dungeon runs.

## Resolved

1. **Interior model → walk-in, on-tile room** (no separate interior scene; footprint-bound).
2. **First authoring target → road/street connection grammar** (the street tile set).
3. **The map is anchored on the Pit at (0,0)** — a fixed 7-tile core (Pit + ring 1), with the
   randomizer growing the frontier around it. The Pit is the dungeon level-transition.
4. **Diegetic coordinates** — three named arteries (**Main**, **1st**, **Arapahoe**) meeting
   at *1st & Main* (the Pit); ring index = restoration ring.
5. **Regional flavor** — subtle Golden / Louisville, CO seasoning over the London base.
6. **Core occupancy is excluded** from the vacancy tally (frontier-only count).
7. **"Pop One" spine** — radius-6 town = 127 tiles; 7-tile core collapses (permanent scar) →
   **120 frontier souls**; **1 tile = 1 soul** (count, not occupancy-sum); `120 + you = Pop 121`
   (alpha & omega). Souls may be people *or* other creatures. Enabled by per-tile spline roads.
8. **Growth model: destiny roll, witnessed restoration** (2026-06-10). The full 120-cell
   layout is rolled **once per save** (constraint-checked; the roll JSON is the durable
   record), then **restored one tile per rescue**, BFS outward from the Pit along the road
   graph — the town heals from the wound outward. Player agency = choosing **among frontier
   candidates** (and which soul settles where), never freeform layout: the necklace-complete
   kit guarantees every candidate is legal, so placement can't dead-end. The act-2 rearrange
   re-rolls the *unrestored remainder* under a story justification.
9. **Occupancy is retired** (2026-06-10) — see "Population" above. Count, not sum, in code
   as well as design.
10. **The randomizer is a dev tool.** Growth knobs, sweeps, and constraints exist to prove
    the kit and roll destinies — they are not a player-facing system.
11. **The River** (plan + rulings 2026-06-10; core-anchored evolution 2026-06-11).
    Architecture: **layered masks** — road and water are parallel 6-bit masks per cell,
    never a ternary socket. Rulings: **river/bridge cells house souls** (the
    bridge-climber, the kayak-keeper, the lifeguard, one lost to the river — souls = 120
    holds exactly); the river's name is **"River"** (vanilla by choice, until the
    director decides); **channel = 5 m, one cell** (game scale). **2026-06-11, superseding
    frontier-only: the River is CORE-ANCHORED — it passes the wound** through two
    adjacent ring-1 story tiles, water sloshing/pouring into the Pit (authored art);
    **the player picks the outflow heading at destiny-roll time** ("grow the river in a
    direction you prefer") and it is permanent after — the River still endures, never
    re-rolled. Banks are flow-relative: **Left Bank / Right Bank**. The wound unites the
    banks: ring-1 water tiles are core, and the core propagates healing. Plan + status:
    **Docs/Rivers.md**.
12. **The Pit's descend prompt / level transition is NOT this repo's scope** — it lives with
    the dungeon project. The town↔dungeon junction is a standing design goal the director
    manages across both projects; this repo only keeps the Pit tile + its anchor stable.
13. **Water is water, blank is blank** (2026-06-11). A river cell hosts a *water* soul;
    a blank cell hosts a soul whose **efforts and time exist in that blank** — open
    ground is occupied ground (garden squares, greens, allotments), never void. The
    two never share a census bucket or a curation clamp: `blank` counts DRY ground
    only (road 0 AND water 0); pure-water cells census as `water`; bridges count as
    their road necklace. Blank variants stay fully walkable and will eventually host
    their souls' interactions.

## Open

- **Story beats for the 6 ring-1 tiles** — their narrative-gated restoration arc (TBD).
