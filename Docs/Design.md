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

## Tiles

- A tile is a **flat-top hex, 5 m radius / 10 m across** (LOCKED — see Source_Art/README).
- Tiles are mostly **building lots** (shops, homes, pubs, civic) plus **road/street tiles**.
- **Roads govern connection**: which of a tile's 6 edges carry a road determines how tiles
  neighbor and how the street network forms. This is the assembly grammar.
- Each building tile fronts the street via a **door on a road edge**.

## Population = rescued people

The town's size *is* the rescue count: tiles house the people you save underground. Every
tile type carries an **Occupancy** (housing capacity); a layout's total is its **rescue
capacity / vacancies**. The `HexShuffleGenerator` sums it live and shows it, so layouts can
be judged by how many they'd hold. Seed rule for the street kit: `Occupancy = (6 − roadEdges)
× 2` (roads displace housing) — per-tile editable in the catalog. Building tiles will set
their own capacities as they're authored.

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

**Build status — intact "pre-destruction" blockout (validated).** Before carving the sinkhole we
built and walked the *intact* street network (`gen_pit_core.py` → `PitCoreLab`). The town-center
streets read as a **wheel**:
- **Hub** = the center tile, a 6-way **3 m** junction — the grand crossing every road drains to
  (and where the sinkhole will open: *all roads lead down into the dungeon*).
- **Spokes** = each ring tile carries a **3 m** road inward to the hub.
- **Boundary alley** = a closed **2 m** loop around the *outer* perimeter. Hex reality: the six
  petals only touch near the hub, so the outer loop can't close on the 7 core tiles alone — it
  threads through **6 "valley" tiles** (the distance-2 cells in the notches between petals). Those
  valleys are *frontier*, not core; they're shown to close the loop. Cross-section throughout:
  carriageway 0.5 m / raised flagstone pavement 0.65 m / 0.15 m curb.

The **boolean sinkhole carve is the next pass** (phase 2): a zig-zag void through the core down to
−3 m, leaving the chaotic collapsed-building rim, then hardwiring the core into the generator.

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

## Open

- **Story beats for the 6 ring-1 tiles** — their narrative-gated restoration arc (TBD).
- **Unlock/placement:** how frontier tiles enter the town as achievements (manual designer
  placement vs. progression-driven) — affects the generator's role.
