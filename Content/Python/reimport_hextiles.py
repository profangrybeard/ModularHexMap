"""reimport_hextiles.py — one-click batch reimport of the hex-tile static meshes.

Reimports every StaticMesh under /Game/_project/HexTiles from its recorded .glb source (the files the
Blender "Build Enabled" / "Export This Tile" pipeline writes to Content/_project/HexTiles/Source/), then
re-asserts Collision Complexity = Use Complex As Simple (gotcha #5) so tiles stay walkable.

Run it three ways:
  * Tools menu -> "Reimport Hex Tiles" (registered by Content/Python/init_unreal.py)
  * Output Log (Python):  import reimport_hextiles; reimport_hextiles.run()
  * GUI editor:  UnrealEditor.exe <uproject> -ExecutePythonScript="Content/Python/reimport_hextiles.py"

Must run in a GUI editor — headless glTF import crashes on Slate (gotcha #1).
"""
import os
import unreal

TILE_ROOT = "/Game/_project/HexTiles"


def _source_dir():
    # <project>/Content/_project/HexTiles/Source — where the Blender pipeline writes the .glb kit
    return os.path.join(unreal.Paths.project_content_dir(), "_project", "HexTiles", "Source")


def _glb_sourced_static_meshes():
    """Match each tile mesh to <Source>/<MeshName>.glb (not the mesh's RECORDED source path), so
    reimport repoints automatically after the Source folder moves and survives stale sources."""
    eal = unreal.EditorAssetLibrary
    sdir = _source_dir()
    found = []
    for p in eal.list_assets(TILE_ROOT, recursive=True, include_folder=False):
        obj = eal.load_asset(p)
        if not isinstance(obj, unreal.StaticMesh):
            continue
        glb = os.path.join(sdir, obj.get_name() + ".glb")
        if os.path.exists(glb):
            found.append((p, obj, glb))
    return found


def run():
    eal = unreal.EditorAssetLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    meshes = _glb_sourced_static_meshes()
    if not meshes:
        unreal.log_warning("[ReimportHexTiles] no .glb-sourced StaticMeshes under %s" % TILE_ROOT)
        return

    tasks = []
    for asset_path, obj, src in meshes:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", src)
        t.set_editor_property("destination_path", asset_path.rsplit("/", 1)[0])
        t.set_editor_property("destination_name", obj.get_name())
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("automated", True)         # no per-file import dialog
        t.set_editor_property("save", True)
        tasks.append(t)

    unreal.log("[ReimportHexTiles] reimporting %d tiles from %s..." % (len(tasks), TILE_ROOT))
    tools.import_asset_tasks(tasks)

    # re-assert Complex-As-Simple so reimported tiles stay walkable (gotcha #5)
    fixed = 0
    for asset_path, _obj, _src in meshes:
        sm = eal.load_asset(asset_path)
        if not isinstance(sm, unreal.StaticMesh):
            continue
        bs = sm.get_editor_property("body_setup")
        if bs is not None:
            bs.set_editor_property("collision_trace_flag",
                                   unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            eal.save_loaded_asset(sm)
            fixed += 1

    # self-heal materials: glTF reimport re-mints per-tile material dupes; fold them back into
    # the /Game/_project/HexTiles/Materials masters so the project never re-accumulates the sprawl.
    try:
        import hextile_materials
        hextile_materials.consolidate_to_masters()
    except Exception as exc:
        unreal.log_warning("[ReimportHexTiles] material consolidate skipped: %s" % exc)

    unreal.log("[ReimportHexTiles] done: reimported %d, collision asserted on %d"
               % (len(tasks), fixed))


if __name__ == "__main__":
    run()
