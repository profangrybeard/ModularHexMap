# Roll Constraints

Per-necklace requirements that a `HexShuffleGenerator` roll must satisfy.
Used by `roll_diagnostics.constrained_randomize()` to find a seed whose grown
network meets the requirements, then apply it to the actor.

## Preferred source: in-engine DataTable

`AHexShuffleGenerator` has a `RollConstraints` property (category
**Hex Shuffle | Constraints**) of type `UDataTable`. When assigned, the
constrained randomize reads its rows in preference to the JSON files in this
directory. Row struct: `FHexNecklaceConstraint` (`Min`, `Max`, `Exact`). Row
name: the necklace name (e.g. `junction`, `tee_c`, `straight`).

Setup:
1. In the Content Browser at `/Game/_project/Data/`, right-click → Miscellaneous
   → Data Table. Pick row structure **HexNecklaceConstraint**. Name it
   `DT_RollConstraints_Default` (or any flavour name).
2. Open it, click *Add*, set the row name to a necklace (e.g. `junction`), set
   `Min = 1`. Repeat for any other necklaces you want to constrain.
3. Open `ShuffleLab`, select `HexShuffleGenerator`, in Details under
   *Hex Shuffle | Constraints* assign your DataTable.
4. Click *Tools ▸ Constrained Randomize* — the Output Log should show
   `source=DataTable:DT_RollConstraints_Default` and the rules it loaded.

Clone the DataTable in the Content Browser to make alternate "town flavour"
presets (`DT_RollConstraints_PortalTown`, etc.). Switch between them by
reassigning the actor property — no Python edits needed.

## Fallback source: this directory (JSON)

When no DataTable is assigned, the constrained randomize falls back to
`Design/RollConstraints/<name>.json`. Useful for quick experiments without
creating an asset, and for keeping rule presets git-versioned alongside saved
rolls.

## File format

JSON. Top-level object. Keys are necklace names (must match the 14 mask
classes the generator emits — see the `roll_diagnostics.NECKLACE_NAMES` list).
Values are either:

- **Integer** — shorthand for `{"min": N}`. The roll must contain at least N
  frontier cells of that type.
- **Object** with any of:
  - `"min": N` — at least N
  - `"max": N` — at most N
  - `"exact": N` — exactly N (overrides min/max)

Reserved top-level keys are passed through unread: `schema_version`,
`description`, and any key starting with an underscore.

Necklace types **not listed** are unconstrained.

## Example

```json
{
  "schema_version": 1,
  "description": "Town with at least one true 6-way junction and limited deadends.",

  "junction":   1,
  "tee_c":      1,
  "deadend":    { "max": 8 },
  "straight":   { "min": 15, "max": 30 }
}
```

## Necklace names

```
blank   deadend   bend     curve    straight
tee     tee_a     tee_b    tee_c
quad    quad_b    quad_c
penta   junction
```

See `roll_diagnostics.py` for the bit-mask definitions.

## Feasibility hints

Cross-reference your minimums against the most recent sweep
(`Design/Rolls/Sweep_seed*_n*.csv`). If a `min` exceeds the sweep's `p95` for
that type, expect lots of retries — the constraint is satisfiable but rare.
If it exceeds `max` from the sweep, no seed can satisfy it given the current
growth params; loosen the constraint or tune growth.

Naming convention: `<flavour>.json` (e.g. `default.json`, `dense.json`,
`portal_town.json`). The constrained_randomize call takes the bare name:

```python
import roll_diagnostics
roll_diagnostics.constrained_randomize("default")
roll_diagnostics.constrained_randomize("portal_town", max_attempts=500)
```
