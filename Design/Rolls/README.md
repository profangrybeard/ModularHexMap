# Rolls — saved layouts

Each `Roll_seed<N>_vac<V>.json` is a **layout we liked**, saved from the
`HexShuffleGenerator` (Details → **Save Roll**). Git-tracked on purpose: this folder is a
**curated history** of candidate towns, diffable and reviewable over time.

## What's in a roll
A serialized `FHexRoll`:
- `network.cells` — the **ground truth**: `axial` (Q,R) + `roadMask` (6-bit) per cell. Reloads
  verbatim via **Load Roll**, so a roll survives later changes to the generator code.
- `seed`, `growth` — **provenance**: the recipe that produced it. Lets you re-tune *from* a
  roll, but note it only *reproduces* the layout while the generator code is unchanged.
- `vacancies` — the frontier rescue-capacity tally at save time (excludes the fixed core).

## Reload
Set the generator's **RollToLoad** to a filename here (e.g. `Roll_seed42_vac312`, `.json`
optional) or a full path, then click **Load Roll**. It rebuilds the saved network directly —
no re-growth.

## Notes
- Filenames key on seed + vacancies; re-saving the same roll overwrites.
- Rolls are the curation layer feeding the eventual **bake-to-level** step (Next steps #3).
