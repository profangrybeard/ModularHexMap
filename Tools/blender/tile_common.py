"""tile_common.py — shared plumbing for the iterative tile pipeline.

Low-level helpers used by tile_registry.py and the tile_pipeline addon:
  * repo/path resolution (robust: walks up to ModularHexMap.uproject)
  * the ONE canonical glTF export (so GUI + headless runs can't drift)
  * tile_manifest.json read/write (the git-tracked export-toggle / bespoke state)
  * a grid-layout helper for the in-scene preview

Deliberately knows nothing about how a tile is *built* (that's the registry) — it only
moves bytes, files, and JSON. Safe to import in any .blend; never saves the master.
"""
import os
import json
import math

import bpy

# Canonical glTF export flags — MUST match gen_curved_tiles.py / gen_pit_core.py.
_GLTF_KW = dict(export_format='GLB', use_selection=True, export_apply=True,
                export_yup=True, export_materials='EXPORT')

TILE_SPACING = 24.0   # preview grid pitch (m); > hex width-across-corners (2R=20) + gap
PREVIEW_COLL = "TilePreview"   # transient build-preview objects live here


# ---- paths ----
def repo_root():
    """Repo root = nearest ancestor holding ModularHexMap.uproject (robust to which
    .blend is open). Falls back to 3 dirs up from Source_Art/Blender/<file>.blend."""
    p = bpy.data.filepath
    start = os.path.dirname(p) if p else os.getcwd()
    cur = start
    for _ in range(10):
        if os.path.exists(os.path.join(cur, "ModularHexMap.uproject")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.dirname(os.path.dirname(os.path.dirname(p))) if p else start


def source_glb_dir():
    d = os.path.join(repo_root(), "Content", "_project", "HexTiles", "Source")
    os.makedirs(d, exist_ok=True)
    return d


def bespoke_dir():
    d = os.path.join(repo_root(), "Source_Art", "Blender", "Tiles")
    os.makedirs(d, exist_ok=True)
    return d


def hexbase_path():
    return os.path.join(repo_root(), "Source_Art", "Blender", "HexBase.blend")


def manifest_path():
    return os.path.join(repo_root(), "Tools", "blender", "tile_manifest.json")


def glb_path(tile_name):
    return os.path.join(source_glb_dir(), tile_name + ".glb")


def bespoke_blend_path(tile_name):
    return os.path.join(bespoke_dir(), tile_name + ".blend")


def rel_to_repo(abs_path):
    """Repo-relative POSIX path for storing in the manifest (git-stable)."""
    return os.path.relpath(abs_path, repo_root()).replace(os.sep, "/")


# ---- export ----
def export_glb(obj, path):
    """Export a single object to <path>.glb with the canonical flags. Temporarily zeroes
    the object's location first (gotcha #13: UE double-offsets a baked node transform),
    then restores it so the preview layout is untouched. Returns the written file size."""
    prev = tuple(obj.location)
    obj.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, **_GLTF_KW)
    obj.location = prev
    bpy.context.view_layer.update()
    return os.path.getsize(path)


# ---- manifest ----
def load_manifest():
    p = manifest_path()
    if os.path.exists(p):
        with open(p, "r") as f:
            return json.load(f)
    return {"version": 1, "tiles": {}}


def save_manifest(data):
    with open(manifest_path(), "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def tile_state(data, name):
    """Per-tile state with defaults (enabled procedural). Never raises on a missing tile."""
    t = data.get("tiles", {}).get(name, {})
    return {
        "enabled": t.get("enabled", True),
        "bespoke": t.get("bespoke", False),
        "blend": t.get("blend", None),
    }


def set_tile_state(data, name, **kw):
    tiles = data.setdefault("tiles", {})
    entry = tiles.setdefault(name, {"enabled": True, "bespoke": False, "blend": None})
    entry.update(kw)
    return entry


def bespoke_tile_names():
    """Names the manifest marks bespoke (owned by a .blend). Standalone generators skip
    these so a headless regenerate never clobbers a hand-authored tile."""
    man = load_manifest()
    return {n for n, t in man.get("tiles", {}).items() if t.get("bespoke")}


def reconcile_manifest(data, all_names):
    """Ensure every registry tile has an entry (default enabled/procedural); leave
    existing toggles untouched. Returns True if anything was added."""
    tiles = data.setdefault("tiles", {})
    changed = False
    for n in all_names:
        if n not in tiles:
            tiles[n] = {"enabled": True, "bespoke": False, "blend": None}
            changed = True
    return changed


# ---- preview layout ----
def preview_collection():
    c = bpy.data.collections.get(PREVIEW_COLL)
    if c is None:
        c = bpy.data.collections.new(PREVIEW_COLL)
        bpy.context.scene.collection.children.link(c)
    return c


def grid_location(index, cols=5, spacing=TILE_SPACING):
    row, col = divmod(index, cols)
    return (col * spacing, -row * spacing, 0.0)


def clear_preview():
    """Remove every transient preview object (tagged on build). Leaves the master clean."""
    n = 0
    for o in list(bpy.data.objects):
        if o.get("_tile_preview"):
            bpy.data.objects.remove(o, do_unlink=True)
            n += 1
    c = bpy.data.collections.get(PREVIEW_COLL)
    if c is not None and not c.objects:
        bpy.data.collections.remove(c)
    return n
