# Per-Tile Spline Roads — design pivot, now LANDED (2026-06-06)

> **Read this first to resume.** This supersedes the map-wide spline-road direction. Originally
> written at a context-limit handoff; the redesign has since shipped — the open questions below
> are now resolved with the recipe used.
>
> **2026-06-10 cleanup:** everything the "RETIRE" section lists is now actually GONE, not just
> retired — `ASplineRoad`, `BuildSplineRoads()`, `bGroundOnly`/`GroundMesh`/`RoadSegmentMesh`/
> `SplineRoadZ`, the `SM_RoadSeg`/`SM_GroundHex` assets, and the `gen_street_tiles.py`/
> `gen_road_segment.py`/`gen_ground_hex.py` generators. Git history has all of it. This doc
> remains as the design record of the pivot.

## The pivot (why we changed course)
- **REJECTED:** the map-wide *runtime* spline-road system built this session (`ASplineRoad` chains
  traced over the whole grown network, reroll-driven). It works, but it's the wrong product fit —
  **players get curated, modular tiles that snap together cleanly, not a runtime spline generator
  they reroll a hundred times.** On a map scale it was a burden.
- **ADOPTED:** **per-tile spline road *smoothing* with ANCHORED edge connections.** Curves are
  **baked into the modular tile geometry**. Map-wide smoothness *emerges* from the anchor contract;
  there is no runtime spline system.

## The anchor principle (the whole idea — get this right)
- Every road crosses a hex edge at the **edge MIDPOINT, PERPENDICULAR to the edge** (contract:
  carriageway 3 m centred on the edge, walks flanking — see `Source_Art/README.md`).
- A tile's road centreline is a **spline whose endpoints are anchored**: position = the road-edge
  midpoint, tangent = perpendicular to that edge, pointing into the tile.
- Because **every** tile obeys this same anchor, two adjacent tiles' road curves meet at the shared
  edge midpoint with **matching (perpendicular) tangents** → **C1-smooth across the boundary**,
  while the tiles stay **perfectly modular / snap-together**.
- ⇒ Smooth, flowing roads across the entire map, **baked into modular tiles, zero runtime system.**
  This is the synthesis: keep the curve, lose the map-wide machinery.

## What to KEEP (proven this session — repurpose, don't rebuild)
- **The spline-as-road-smoother tech:** `SM_RoadSeg` London cross-section (3 m carriageway + 1 m
  raised walks + curb; modelled along +X, open X-ends, closed bottom) + **arc-length spline
  extrusion**. Built by `Tools/blender/gen_road_segment.py`; render/extrusion logic in
  `Plugins/HexMapGenerator/.../SplineRoad.{h,cpp}`. **Repurpose as the per-tile BAKE tool** (sweep
  the cross-section along a per-tile spline → curved road mesh), NOT a runtime renderer.
- The **London cross-section** + the **hex contract** (R=5 flat-top, apothem 4.33, 5 m edges, edge
  midpoints as anchors, neighbour offsets — `Source_Art/README.md`).
- The **14-config tile necklace set** and the **growth generator**
  (`HexShuffleGenerator` + `HexMapGrowthLibrary`): the generator's job is unchanged — grow the road
  topology and **place tiles** per cell. Only the tile *geometry* changes (faceted → curved-baked).
- The **growth-tuning work** (parkable blocks: lower `RoadBudget`/`BranchChance`/`NumArteries`/
  `ArteryForkChance`; the min-block-size rule is still the durable fix if params can't guarantee it).
  Still relevant — it shapes the network topology the tiles render.

## What to RETIRE / leave behind
- `ASplineRoad` as a **runtime map-wide renderer** (`AHexShuffleGenerator::BuildSplineRoads`
  spawning per-chain spline roads + junction fans). Keep the code as reference for the bake; stop
  using it to draw the map.
- `bGroundOnly` review mode + `SM_GroundHex` (`gen_ground_hex.py`) — scaffolding to *review* the
  map-wide splines. Harmless to leave; not part of the new design.
- The one-click auto-draw in `Build()` (`if (RoadSegmentMesh) BuildSplineRoads();`) — tied to the
  retired runtime renderer.

## The new pipeline (what the next session builds)
1. **Per-tile road centreline spline(s), per config** — endpoints anchored (edge midpoint +
   perpendicular tangent into the tile):
   - `straight` (0,3): straight through.
   - `bend` (0,1) / `curve` (0,2): smooth arc between the two edge anchors — **the curves**.
   - `deadend` (0): edge anchor → centre stub.
   - `tee` / `tee_a/b/c` / `quad` / `quad_b/c` / `penta` / `junction` (3–6 edges): a **junction
     within the tile** — arms from each edge anchor meeting at a designed central intersection.
     Bounded to ONE tile and anchored at the edges (far easier than the map-wide junction mess
     we hit; this is the per-tile version of that problem).
   - `blank`: no road (ground only).
2. **Sweep the London cross-section** (carriageway + raised walks + curb) along each tile's
   spline(s) → curved road geometry. **Walks/curbs curve too** (the original "splined streets AND
   sidewalks / curved curbs" goal). Mind inner-vs-outer radius on tight curves.
3. **Bake into the tile static mesh** — extend/replace the road geometry in
   `Tools/blender/gen_street_tiles.py` (currently straight center→edge arms) with the swept,
   spline-smoothed cross-section. Export one `.glb` per config, exactly as now.
4. **Existing generator places the (now curved) tiles** — unchanged flow. Roads flow smoothly
   across tile boundaries via the anchor contract.

## Resolutions (open questions, now landed)
- **Bend / curve treatment** — **circular arcs** between the two edge midpoints, centre =
  intersection of the two edge supporting-lines (`arc_centerline` in `gen_curved_tiles.py`).
  Anchored midpoint + perpendicular tangent → **C1-smooth across tile boundaries** (adjacent tiles
  share both the midpoint and the tangent by construction). Parallel-edge case (opposite edges) →
  straight line, same anchors.
- **Junction treatment** — **spline-fanned**, not radial. Recipe (`junction_centerlines` +
  `add_hub`):
  1. A **central road hub** (radius `JUNCTION_HUB_R = HW * 1.5`, i.e. ~2.25 m) merges all arms so
     there's no centre sliver — they "come together."
  2. Each arm is a **cubic Bézier** leaving its edge midpoint **perpendicular** to the edge (the
     modular anchor — neighbours still meet flush), then bowing toward the **centroid of all road
     mouths** (`JUNCTION_BOW = 0.90`) before converging at the hub.
  3. A tangential **swirl** offset (`JUNCTION_SWIRL = 0.25` × INR) is added to the second control
     point so even **symmetric** junctions (tee / 6-way junction, whose centroid sits ~on the
     centre) still curve — no faceted radial spikes.
- **Bake mechanism** — **all-Blender.** The generator sweeps the London cross-section along each
  per-tile spline and bakes the result into the tile `.glb`. (`ASplineRoad`-to-static-mesh was
  considered and dropped.)
- **Walk/curb on curves** — handled by the cross-section extrusion: carriageway + raised walks +
  curb all follow the same per-tile spline path, so walks/curbs curve with the road. Edge anchors
  hold the 3 m carriageway perpendicular to the edge → tiles still snap.
- **Curve variants** — **one variant per config** (single bend, single curve, etc.). Open for
  revisit if blocks read too uniform — anchors are fixed, so gentle/sharp variants would still
  snap.
- **Growth / config resolver** — unchanged. Same 14 configs, same placement; only the meshes are
  curved now.

## What shipped (the full 14-tile kit)
- **Canonical generator:** `Tools/blender/gen_curved_tiles.py` — supersedes
  `gen_street_tiles.py` (faceted; kept as reference, don't regenerate from it).
- **All 14 configs at LKG:** `blank` / `deadend` / `bend` / `curve` / `straight` /
  `tee[/_a/_b/_c]` / `quad[/_b/_c]` / `penta` / `junction`. Imported and validated in
  `ShuffleLab` (127 cells, core=7, 0 unresolved).
- **Knobs (in `gen_curved_tiles.py`):** `JUNCTION_HUB_R` (~`HW * 1.5`), `JUNCTION_BOW` (0.90),
  `JUNCTION_SWIRL` (0.25 × INR). Plus `CUT_EXT` for cutter overshoot past each edge.
- **Generator (unchanged role):** `Plugins/HexMapGenerator/.../HexShuffleGenerator` (topology,
  placement, tuning) + `HexMapGrowthLibrary` (pure growth). Same `FHexGrowthParams`. Only the
  tile meshes are curved now.
- **Building footprints:** parked — `Docs/BuildingFootprints.md` (resume after blocks).
- **Contract:** `Source_Art/README.md` (hex base, edge midpoints/anchors, neighbour offsets).
