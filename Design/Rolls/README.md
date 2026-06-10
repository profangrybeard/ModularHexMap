# Rolls — saved layouts

Each `Roll_seed<N>.json` is a **layout we liked**, saved from the
`HexShuffleGenerator` (Details → **Save Roll**). Git-tracked on purpose: this folder is a
**curated history** of candidate towns, diffable and reviewable over time. Under the
"destiny roll, witnessed restoration" model (Docs/Roadmap.md) a saved roll is exactly the
shape of a save-game's town layout, so this format is load-bearing for gameplay later.

## What's in a roll
A serialized `FHexRoll`:
- `network.cells` — the **ground truth**: `axial` (Q,R) + `roadMask` (6-bit) per cell. Reloads
  verbatim via **Load Roll**, so a roll survives later changes to the generator code.
- `seed`, `growth` — **provenance**: the recipe that produced it. Lets you re-tune *from* a
  roll, but note it only *reproduces* the layout while the generator code is unchanged.

(Older rolls also carry a `vacancies` field from the retired occupancy-sum metric —
ignored on load. 1 tile = 1 soul is the law now; a roll's soul count is just its frontier
cell count.)

## Reload
Set the generator's **RollToLoad** to a filename here (e.g. `Roll_seed42`, `.json`
optional, old `Roll_seed<N>_vac<V>` names still work) or a full path, then click
**Load Roll**. It rebuilds the saved network directly — no re-growth.

## Notes
- Filenames key on seed; re-saving the same seed overwrites (same seed + same generator
  code = same network, so that's idempotent, not lossy).
- Rolls are the curation layer feeding the restoration loop and the eventual
  bake-to-level step.
