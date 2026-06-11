# Records of resistance — gotchas. Don't relearn these.

> The **resistance** doc: every place this project fought back, what the fight looked
> like (symptoms/diagnostics), and the working fix. Read the relevant entry BEFORE
> touching glTF import/export, Blender scripting, UE Python asset edits, git ops on
> binary files, or the build. Moved out of CLAUDE.md 2026-06-10; numbering preserved.

1. **Headless glTF import crashes on Slate** (`-run=pythonscript` commandlet, no Slate, asserts
   in the Interchange→ContentBrowser sync). → Import in a **GUI editor** (`-ExecutePythonScript`).
   Level *assembly* and *asset edits* (no import) are headless/commandlet-safe.
2. **Blender drops unused materials on save** → `material.use_fake_user = True` on shared mats.
3. **Migrated BPs needed the FULL `TP_ThirdPerson` module (~30 classes).** Copied the engine
   template module verbatim, `IMPLEMENT_PRIMARY_GAME_MODULE`→`IMPLEMENT_GAME_MODULE`, registered
   in both `*.Target.cs` + `.uproject`, enabled **StateTree + GameplayStateTree**. Names match
   `/Script/TP_ThirdPerson.*` so BPs resolve natively.
4. **New `UCLASS` types need a full editor restart + `Build.bat`** (Live Coding can't hot-add;
   editor locks the DLLs — close it first).
5. **Imported meshes aren't walkable until** Collision Complexity = **Use Complex As Simple**.
6. **glTF imports at true scale** (1 m → 100 uu).
7. **Hexes carry √3 between axes** — can't round both. **R=10** now (was 5; 2× scale 2026-06-06);
   the generator places tiles so 17.3 m is never hand-typed. `HexCircumradiusUU` must match
   (=`R×100`=1000).
8. **UE launch wrapper exits 0 instantly** (editor reparents). Confirm with `Get-Process
   UnrealEditor`; real logs in `Saved/Logs/`. (Direct `UnrealEditor.exe` invocations from a
   shell DO block until exit — the wrapper gotcha is about launcher/association launches.)
9. **Blender close-range perspective fakes tall walls** — verify with vertex Z or **orthographic**.
10. **glTF import re-orients meshes (handedness + offset).** Never trust the abstract Blender
    edge layout for in-engine placement. The generator **measures** each tile's true road edges
    from geometry (reads the `M_Road` section verts near each edge midpoint) and resolves
    rotation against that. **Physics line-traces were useless** in the editor (the spawned body
    isn't ready the same frame) — read **render-data vertices** instead.
11. **UE-Python `set_editor_property` on a nested struct array does NOT dirty the package**, so
    `EditorAssetLibrary.save_loaded_asset` silently no-ops (returns `True`, writes nothing). →
    save with **`only_if_is_dirty=False`**, edit struct arrays by **index** (`a[i]=e`, not
    mutating the loop var), and **verify the `.uasset` size/mtime actually changed**. Also: never
    `Stop-Process -Force` the editor right after a save — it eats the flush. Use a clean
    **commandlet** (`-run=pythonscript`) for asset edits/saves (exits cleanly, flushes).
12. **UE yaw convention:** world_angle = local_angle + yaw (positive yaw = +1 edge / rotate mask
    left). The generator's default is correct for our import; `bInvertYawShift` is the escape
    hatch if a future kit imports mirrored.
13. **Export tiles CENTERED, or UE double-offsets them.** An object's world location bakes into
    the glTF node transform, then UE bakes that into the mesh — so placing the actor at the same
    coord doubles the offset (tiles spread at 2× spacing with gaps). Set `object.location = 0`
    before export; position **only** via the actor/generator. (Mesh data stays bottom-center.)
14. **Self-intersecting boolean cutter eats the WHOLE target.** Overlapping carriageway arms (a
    junction cutter where arms meet at center) make the EXACT solver mis-evaluate and delete *all*
    the pavement, not just the channel. Fix: `modifier.use_self = True` + `use_hole_tolerant =
    True`. (`gen_curved_tiles.py` and `gen_pit_core.py` both carry the fix.)
15. **`-ExecutePythonScript` is one-shot:** the GUI editor runs the script and **exits** (a build
    step, like `setup_shuffle_lab.py`). The work persists; relaunch the editor normally to use
    the result.
16. **glTF import MIRRORS each tile across the X-axis** (edges 0↔3, 1↔2, 4↔5) — the concrete form
    of gotcha #10's "re-orientation." The frontier resolver absorbs it (matches measured→target
    mask by rotation; road geometry is per-edge symmetric). **Anything placed verbatim must do the
    same** — the Pit-core tiles were placed at a fixed yaw and came out mis-rotated (rings off the
    mirror axis wrong, *every roll*). Fix: `Build()` measures each core mesh's real mask and rotates
    it onto the authored `CC.RoadMask`. ⇒ **Never place an imported tile at a hardcoded yaw; always
    measure-and-rotate.** (Chiral *art* would also need authoring that accounts for the mirror.)
17. **glTF reimport (`replace_existing`) doesn't reliably update MATERIAL factors** — a colour/param
    change baked in Blender may not take on reimport. Force it in UE after import via
    `MaterialEditingLibrary.set_material_instance_vector_parameter_value(MIC, "baseColorFactor", …)`
    (glTF mats import as `MaterialInstanceConstant`; param is `baseColorFactor`). See
    `Tools/wire_core_into_shufflelab.py`.
18. **Procedural vs bespoke is FILE ownership, enforced by the manifest.** A tile is either
    generator-owned (rebuilt from code) or hand-owned (a `.blend` under `Source_Art/Blender/Tiles/`)
    — never both, or a regenerate clobbers hand work. `tile_manifest.json` is the contract; the
    generators skip `bespoke` tiles. ⚠️ **Don't hand-edit a tile inside the master `HexBase.blend`
    and Ctrl+S** — that bakes it into the master (hit twice now — see #30). Use the **Hex Tiles**
    panel's **Promote to Bespoke** instead; leaving the master via the panel never auto-saves it.
19. **glTF import mints per-mesh material dupes — consolidate to shared masters.** Each `.glb`
    import gives every tile its own `Materials/` folder, so ~30 tiles scattered **~130 copies** of
    really **4** materials. Canonical masters live in **`/Game/_project/HexTiles/Materials/`**;
    `Content/Python/hextile_materials.py` consolidates. Headless quirks learned the hard way:
    `EditorAssetLibrary.consolidate_assets` **replaces references but leaves the copies as
    `ObjectRedirector`s**; `delete_asset` **does not remove redirectors** headless and
    `AssetTools.fixup_referencers` **doesn't exist in 5.7 Python**. The working recipe: **force-
    rebind every static-mesh slot to the master path + save** (so no mesh depends on a redirector),
    then **delete the redirector `.uasset` files on disk** (editor closed; UE rescans on launch).
    `reimport_hextiles.py` calls `consolidate_to_masters()` after every reimport so the sprawl
    never comes back. (⚠️ UE's pythonscript commandlet does **not** reliably run a file's
    `if __name__=="__main__"` block — use an explicit entry script.)
20. **Close the UE editor before any git op that MOVES/DELETES `.uasset` files** (branch switch,
    merge, `checkout -f`, reset). The open editor **locks** the package files, so git can't unlink
    them → "unable to unlink … Invalid argument" and a **half-completed branch switch**. Recovery
    is clean once closed: `git checkout -f <branch>` restores the tree, then merge. (Same family
    as #4's DLL lock.) The work is never lost — it's in the commits; only the working tree gets
    stuck.
21. **A live Blender session caches imported pipeline modules.** After editing `tile_common.py` /
    the generators / the addon on disk, the **open** session keeps the OLD code, so "Export This
    Tile" can silently write to the **pre-edit path**. Fix: reload (`importlib.reload(...)`) or
    just **restart Blender**.
22. **`PythonScriptPlugin.AdditionalPaths` silently no-ops on relative paths.** A line like
    `+AdditionalPaths=(Path="Content/_project/Python")` is resolved against
    `Engine/Binaries/Win64/`, not the project root — so it points at a nonexistent dir, gets
    dropped without warning, and the directory never lands on `sys.path`. Symptoms: any module
    living there throws `ModuleNotFoundError`, and any `init_unreal.py` in there never runs. Fix:
    **keep editor Python under `Content/Python/`** — UE hard-codes that onto `sys.path`. (Also:
    every plugin can ship `init_unreal.py` under the same module name — keep real work in
    uniquely-named modules like `hexmap_menus.py`.)
23. **`BlueprintReadOnly` / `BlueprintReadWrite` is REJECTED on `private` UPROPERTYs by default.**
    Fix: add **`meta = (AllowPrivateAccess = "true")`** — keeps the field C++-private but opts
    past UE's BP-visibility gate. In-repo example: `AHexShuffleGenerator::LastNetwork`, which
    Python's roll diagnostics read.
24. **Live Coding (Ctrl+Alt+F11 / editor "Compile") CANNOT add new `UPROPERTY`/`UCLASS`/`USTRUCT`
    reflection.** It hot-patches *function* bodies; new reflected members look like they compiled
    but never reach the engine. **Diagnostic:** compare mtimes —
    `Plugins/<plugin>/Binaries/Win64/UnrealEditor-<plugin>.dll` older than your `.h` edit ⇒ Live
    Coding ran but didn't compile anything reflection-visible. **Fix:** close the editor (gotcha
    #4) and build via `Tools/Build.ps1`.
25. **Shapely returns CW polygons after `hex.difference(corridor).buffer(...)`.** With CW
    polygons, the standard `add_quad([v00,v10,v11,v01])` winding produces INWARD normals (every
    wall flips, renders as backfaces in UE). Shapely doesn't promise any orientation on output.
    **Fix:** call `shapely.geometry.polygon.orient(pc, sign=1.0)` before extracting
    `.exterior.coords` in every builder function. The working combo is `orient` ALONE — see #26.
26. **`bmesh.ops.recalc_face_normals` flips alternating panels on disconnected per-segment quads.**
    Per-segment quads share no edges/verts, so recalc has no neighbour-consistency anchor and
    flips every other face in any door-split run. **Fix:** with `orient(CCW)` (#25) the explicit
    winding is already correct — do NOT recalc the wall mesh. (Recalc on a CLOSED solid like the
    roof slab is fine — shared edges anchor it.)
27. **Blender 5.1's `bpy.ops.object.shade_smooth_by_angle()` no longer adds the Smooth-by-Angle
    GN modifier** — it only marks `use_edge_sharp` flags, which have **no visual effect** without
    the modifier. **Diagnostic:** `len(obj.modifiers)` unchanged after the call. **Fix:**
    `use_smooth = True` on every polygon + an angle-limited bevel modifier for visible hard
    corners (real chamfer geometry, not split-normal tricks).
28. **Per-segment door placement is wrong for tessellated curves.** Shapely's buffer tessellates
    an arc into many ~1.3 m sub-segments, so per-segment "does a door fit?" fails on curves while
    a single-segment straight gets too many. **Fix:** classify doors by **combined front-run arc
    length** (`doors_for_run`), distribute evenly along the run, and map each door span back to
    the segments it overlaps (multi-segment "banana lintel" follows the curve).
29. **NEVER use the VS 2022 Build menu on this UE project — it trips MSBuild's `SetEnv` task
    before any compile starts.** `$(IncludePath)` on a UE 5.7 project exceeds the **32 767-char**
    Windows env-var ceiling, so MSBuild dies with `MSB4018 … value is too long` on every machine.
    **Fix:** always compile via `Tools/Build.ps1` (UBT → `cl.exe` passes includes as `/I` args).
    The editor's "rebuild outdated modules?" prompt also works (it calls UBT).
30. **The master got polluted AND the pollution got committed — file ownership needs a guard,
    not just a rule.** During the buildings session (commit `8e7b862`), three generator-output
    objects (`T_bldg_penta/straight/tee_a` + 7 on-demand materials) were saved into
    `HexBase.blend` and shipped in the commit; nobody noticed for 3 days (fixed in `e63eb75`).
    #18's rule alone didn't prevent the second occurrence. **Cheap tell:** the master is
    LFS-tracked, so `git show HEAD:Source_Art/Blender/HexBase.blend` prints the pointer —
    expected size ≈ **101.5 KB**; a jump means stowaways. **Diagnostic in-session:** any object
    outside the canonical set (`Hex_Base`, 6 `RoadAnchor_*`, `Camera`, `Light`) or material
    beyond `M_HexGround`/`M_Road`/`M_Pavement` means the file is dirty in spirit even if
    `is_dirty` says False (#31). **Standing ToDo (Roadmap):** pre-commit LFS-size check and/or
    an addon guard that warns on non-CANON objects outside `TilePreview`.
31. **`bpy.data.*.remove()` does NOT set `is_dirty`.** Scripted datablock removals (objects,
    meshes, materials) leave Blender reporting "no unsaved changes" — the dirty flag tracks
    operator/undo pushes, not data-API edits. So "not dirty" can LIE after scripted surgery,
    and a Ctrl+S habit won't fire to persist it. **Fix:** after any scripted edit you intend to
    keep, save explicitly (`bpy.ops.wm.save_mainfile()`); after any you DON'T intend to keep,
    remember the session still holds the edits live (#21) even though the file looks clean.
32. **Every editor session OVERWRITES `Saved/Logs/ModularHexMap.log`** — the previous
    session's log rotates to `ModularHexMap-backup-<timestamp>.log`. Chained one-shot
    runs (gate → gate → census) leave only the LAST session in the main log; grepping
    it for an earlier gate's PASS line silently finds nothing. **Fix:** read the
    backups (`ls -t Saved/Logs/ModularHexMap-backup-*.log`) for all but the final
    session of a chain. *(Bit twice during the 2026-06-11 gate chains.)*
