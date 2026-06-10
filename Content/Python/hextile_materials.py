"""hextile_materials.py — collapse per-mesh glTF material dupes into a small set of masters.

glTF import mints a fresh Materials/ folder per mesh, so reimporting ~30 tiles scattered ~130
copies of what are really 4 materials. consolidate_to_masters() ensures one master each under
/Game/_project/HexTiles/Materials/ and uses EditorAssetLibrary.consolidate_assets to replace every
reference (on every mesh slot) with the master and delete the copy. Also deletes dead orphans
(M_Walk / M_Building_* from older kit versions) and prunes the emptied per-tile Materials folders.

Used two ways:
  * one-time headless cleanup: run as a commandlet (editor CLOSED, asset edits are commandlet-safe)
      UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="Content/Python/hextile_materials.py"
  * self-healing: reimport_hextiles.py calls consolidate_to_masters() after every reimport, so
    fresh dupes from a reimport get folded straight back into the masters.
"""
import unreal
from collections import defaultdict

ROOT = "/Game/_project/HexTiles"
MASTER_DIR = "/Game/_project/HexTiles/Materials"
CANON = ["M_Road", "M_Pavement", "M_HexGround", "M_TileBorder"]
ORPHAN_PREFIXES = ("M_Walk", "M_Building")

_eal = unreal.EditorAssetLibrary


def _pkg(path):
    return path.split(".")[0]


def _base(path):
    return _pkg(path).rsplit("/", 1)[-1]


def purge_redirectors():
    """Remove ObjectRedirectors under ROOT (left by an earlier consolidate_assets). delete_asset
    does NOT remove redirectors headless; AssetTools.fixup_referencers does (same as the editor's
    'Fix Up Redirectors' — resaves any referencers, then deletes the redirector)."""
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    datas = ar.get_assets_by_path(unreal.Name(ROOT), recursive=True,
                                  include_only_on_disk_assets=False)
    redirs = []
    for d in datas:
        try:
            cls = str(d.asset_class_path.asset_name)
        except Exception:
            cls = ""
        if cls == "ObjectRedirector":
            obj = d.get_asset()
            if obj:
                redirs.append(obj)
    if redirs:
        unreal.AssetToolsHelpers.get_asset_tools().fixup_referencers(redirs)
    unreal.log("[hextile_materials] fixed up + deleted %d redirectors" % len(redirs))
    return len(redirs)


def _canon_for(name):
    """Map a material asset name to its canonical master, or None. Per-tile glTF copies are
    named exactly (e.g. 'M_Road'); tolerate numeric dedupe suffixes ('M_Road_2')."""
    for c in CANON:
        if name == c or name.startswith(c + "_") or name.startswith(c + "."):
            return c
    return None


def consolidate_to_masters(delete_orphans=True, prune_folders=True):
    """Headless-safe: rebind every static-mesh material slot to one master per canonical name,
    then delete the now-unreferenced per-tile copies + orphans. Avoids consolidate_assets, which
    replaces references but does NOT delete the copies in a commandlet."""
    if not _eal.does_directory_exist(MASTER_DIR):
        _eal.make_directory(MASTER_DIR)

    all_assets = _eal.list_assets(ROOT, recursive=True, include_folder=False)

    # index material assets (skip the masters themselves)
    copies_by_canon = defaultdict(list)
    orphans, mat_dirs = [], set()
    for p in all_assets:
        obj = _eal.load_asset(p)
        if not isinstance(obj, unreal.MaterialInterface):
            continue
        parent = _pkg(p).rsplit("/", 1)[0]
        if parent == MASTER_DIR:
            continue
        mat_dirs.add(parent)
        bn = _base(p)
        if any(bn.startswith(pre) for pre in ORPHAN_PREFIXES):
            orphans.append(p)
        else:
            copies_by_canon[_canon_for(bn)].append(p)

    # 1) ensure one master per canonical name (duplicate a representative copy if missing)
    masters = {}
    for name in CANON:
        mp = "%s/%s" % (MASTER_DIR, name)
        if not _eal.does_asset_exist(mp):
            reps = copies_by_canon.get(name, [])
            if not reps:
                continue
            _eal.duplicate_asset(_pkg(reps[0]), mp)
            unreal.log("[hextile_materials] created master %s" % mp)
        masters[name] = _eal.load_asset(mp)

    # 2) rebind every static-mesh slot to the master for its canonical name
    rebound = 0
    for p in all_assets:
        sm = _eal.load_asset(p)
        if not isinstance(sm, unreal.StaticMesh):
            continue
        slots = sm.get_editor_property("static_materials")
        changed = False
        for i, slot in enumerate(slots):
            cur = slot.material_interface
            ref_name = cur.get_name() if cur else str(slot.material_slot_name)
            master = masters.get(_canon_for(ref_name))
            if master is not None:
                sm.set_material(i, master)   # force: rewrites the stored ref to the master PATH
                changed = True
        if changed:
            _eal.save_loaded_asset(sm)
            rebound += 1

    # 3) delete every non-master material copy (+ orphans) now that nothing references them
    deleted = 0
    victims = orphans if delete_orphans else []
    for lst in copies_by_canon.values():
        victims += lst
    for p in victims:
        try:
            if _eal.does_asset_exist(_pkg(p)) and _eal.delete_asset(_pkg(p)):
                deleted += 1
        except Exception as exc:
            unreal.log_warning("[hextile_materials] delete skipped %s: %s" % (p, exc))

    # 4) prune emptied per-tile Materials folders
    n_dirs = 0
    if prune_folders:
        for d in sorted(mat_dirs):
            try:
                if not _eal.list_assets(d, recursive=True, include_folder=False) \
                        and _eal.delete_directory(d):
                    n_dirs += 1
            except Exception as exc:
                unreal.log_warning("[hextile_materials] folder prune skipped %s: %s" % (d, exc))

    _eal.save_directory(MASTER_DIR, only_if_is_dirty=False, recursive=True)
    unreal.log("[hextile_materials] done: %d slots rebound, %d copies/orphans deleted, "
               "%d folders pruned (masters in %s)" % (rebound, deleted, n_dirs, MASTER_DIR))


if __name__ == "__main__":
    consolidate_to_masters()
