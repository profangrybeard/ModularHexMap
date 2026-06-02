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

## Tiles

- A tile is a **flat-top hex, 5 m radius / 10 m across** (LOCKED — see Source_Art/README).
- Tiles are mostly **building lots** (shops, homes, pubs, civic) plus **road/street tiles**.
- **Roads govern connection**: which of a tile's 6 edges carry a road determines how tiles
  neighbor and how the street network forms. This is the assembly grammar.
- Each building tile fronts the street via a **door on a road edge**.

## Interiors

- Every building has a **simple interior** — deliberately minimal, in the spirit of a
  **classic JRPG room**: just enough to convey the **owner's character/personality**
  (a shopkeeper's counter, a cluttered study), and nothing more.
- Interiors are flavor + light interaction (talk, buy), **not** gameplay arenas.
- **Model: walk-in, on-tile.** The player walks straight into the room on the tile — no
  separate scene, no load. Interiors are constrained to the ~5×6 m footprint and live in
  the same world as the streets.

## Scope guardrails

- No combat. No platforming/parkour. No physics playground.
- Interiors stay simple — character over complexity.
- The town's job is **identity, NPCs, and shopping** between dungeon runs.

## Resolved

1. **Interior model → walk-in, on-tile room** (no separate interior scene; footprint-bound).
2. **First authoring target → road/street connection grammar** (the street tile set).

## Open

- **Unlock/placement:** how tiles enter the town as achievements (manual designer
  placement vs. progression-driven) — affects the generator's role.
