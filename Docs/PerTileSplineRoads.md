# Per-Tile Spline Roads — design pivot & session handoff (2026-06-06)

> **Read this first to resume.** This supersedes the map-wide spline-road direction. Written at a
> context-limit handoff: everything a fresh session needs to pick up the redesign is here.

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

## Open design questions for the new session
- **Junction treatment** inside multi-road tiles: how the arms blend at centre (smooth merge /
  small plaza / designed intersection). Bounded per tile.
- **Curve variants:** one curve per config, or gentle/sharp variants for variety while staying
  anchored (all still snap, since anchors are fixed)?
- **Bake mechanism:** all-Blender (sweep the cross-section along a bmesh/curve in
  `gen_street_tiles.py`) is the established tile-authoring path and most likely home. Alternative:
  bake `ASplineRoad` output to a static mesh in-engine. Prefer Blender.
- **Walk/curb on curves:** continuity of the raised curb around the inside of a bend; carriageway
  width must stay 3 m at the edge so tiles connect (the anchor).
- Does the **growth/config resolver** need any change? Probably not — same 14 configs, same
  placement; only the meshes are curved now.

## State at handoff (where the repo is)
- **Spline tech (committed):** `SM_RoadSeg` (`gen_road_segment.py`), `ASplineRoad`
  (`SplineRoad.{h,cpp}`), `SplineLab`. Commits: `667a5bb` (render proven + walkable),
  `2e010fb` (map-wide junctions), plus the one-click / ground-only checkpoint commit.
- **Tile kit:** `Tools/blender/gen_street_tiles.py` — streets+walks, **faceted** roads, curb-bug
  fix (gotcha #14). **This is the file that gets the curved-bake upgrade.**
- **Building footprints:** parked — `Docs/BuildingFootprints.md` (resume after roads/blocks).
- **Generator:** `Plugins/HexMapGenerator/.../HexShuffleGenerator` (topology, placement, tuning) +
  `HexMapGrowthLibrary` (pure growth). Params: see `FHexGrowthParams`.
- **Contract:** `Source_Art/README.md` (hex base, edge midpoints/anchors, neighbour offsets).

## First moves for the new session
1. Re-read this doc + `Source_Art/README.md` (the anchor contract).
2. **Prototype ONE curved tile — the `bend` (edges 0,1) — in Blender:** spline from edge-0 midpoint
   to edge-1 midpoint with perpendicular-into-tile tangents; sweep the London cross-section along
   it; bake; export. Place **2–3 bend tiles together** and confirm the roads flow **smoothly across
   the shared edges** — this validates the whole anchor principle in one shot.
3. Then `straight` / `curve` / `deadend`. Then tackle the junction configs.
4. Fold the sweep into `gen_street_tiles.py` as the road-geometry generator, replacing the faceted
   center→edge arms. Regenerate the 14-tile kit; re-import; the generator places curved tiles.
