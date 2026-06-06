"""tile_pipeline.py — Blender addon: the iterative Hex-tile manager.

A "Hex Tiles" N-panel (View3D sidebar) that drives the per-tile workflow:
  * a checkbox list of every tile (export ON/OFF, persisted to tile_manifest.json)
  * "Build Enabled -> Preview & Export": lays the enabled PROCEDURAL tiles out in a
    grid as transient preview objects and writes their .glb (never saves the master)
  * per row: "Promote to Bespoke" (procedural) or "Open Bespoke" (already bespoke)
  * inside a bespoke .blend: "Export This Tile" + "Return to Master"

Promote spawns a headless Blender (_make_bespoke.py) to build the bespoke file in
isolation, flips the tile OFF in the manifest, then opens it (with a save prompt).
Leaving the MASTER never auto-saves it (keeps HexBase.blend byte-identical, gotcha #2).

Install via Preferences > Add-ons, OR just open this file in the Text Editor and Run
(the __main__ tail registers it for the session).
"""
bl_info = {
    "name": "Hex Tile Pipeline",
    "author": "ModularHexMap",
    "version": (1, 0, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar > Hex Tiles",
    "description": "Per-tile export toggles + bespoke .blend handoff for the hex kit",
    "category": "Pipeline",
}

import os
import sys
import subprocess
import importlib

import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty
from bpy.types import Operator, Panel, PropertyGroup, AddonPreferences


# ---- locate sibling modules (addon dir on sys.path) ----
def _addon_dir():
    if "__file__" in globals():
        return os.path.dirname(os.path.abspath(__file__))
    for p in sys.path:                                   # Text-Editor run: search sys.path
        if os.path.exists(os.path.join(p, "tile_common.py")):
            return p
    cur = os.path.dirname(bpy.data.filepath)             # last resort: walk up to the repo
    for _ in range(10):
        if os.path.exists(os.path.join(cur, "ModularHexMap.uproject")):
            return os.path.join(cur, "Tools", "blender")
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return cur


_HERE = _addon_dir()
if _HERE not in sys.path:
    sys.path.append(_HERE)

import tile_common
import tile_registry
importlib.reload(tile_common)
importlib.reload(tile_registry)

_SUPPRESS = False   # guard: don't write the manifest while populating the UI list


# ---- context helpers ----
def _norm(p):
    return os.path.normcase(os.path.normpath(p)) if p else ""


def _in_bespoke_file():
    fp = bpy.data.filepath
    return bool(fp) and _norm(os.path.dirname(fp)) == _norm(tile_common.bespoke_dir())


def _is_master_file():
    return _norm(bpy.data.filepath) == _norm(tile_common.hexbase_path())


def _current_tile_name():
    return os.path.splitext(os.path.basename(bpy.data.filepath))[0]


# ---- property group + populate ----
def _on_enabled(self, context):
    if _SUPPRESS:
        return
    man = tile_common.load_manifest()
    tile_common.set_tile_state(man, self.name, enabled=self.enabled)
    tile_common.save_manifest(man)


class HexTileItem(PropertyGroup):
    name: StringProperty()
    enabled: BoolProperty(default=True, update=_on_enabled)
    bespoke: BoolProperty(default=False)
    blend: StringProperty(default="")


def _populate(scene):
    global _SUPPRESS
    man = tile_common.load_manifest()
    if tile_common.reconcile_manifest(man, tile_registry.all_names()):
        tile_common.save_manifest(man)
    _SUPPRESS = True
    try:
        coll = scene.hextile_list
        coll.clear()
        for name in tile_registry.all_names():
            st = tile_common.tile_state(man, name)
            it = coll.add()
            it.name = name
            it.enabled = st["enabled"]
            it.bespoke = st["bespoke"]
            it.blend = st["blend"] or ""
    finally:
        _SUPPRESS = False


# ---- operators ----
class HEXTILE_OT_refresh(Operator):
    bl_idname = "hextile.refresh"
    bl_label = "Refresh Tile List"
    bl_description = "Re-read the registry + manifest and rebuild the list"

    def execute(self, context):
        _populate(context.scene)
        self.report({'INFO'}, "Tile list refreshed")
        return {'FINISHED'}


class HEXTILE_OT_clear_preview(Operator):
    bl_idname = "hextile.clear_preview"
    bl_label = "Clear Preview"
    bl_description = "Remove the transient preview tiles laid out by Build Enabled"

    def execute(self, context):
        n = tile_common.clear_preview()
        self.report({'INFO'}, "Cleared %d preview tiles" % n)
        return {'FINISHED'}


class HEXTILE_OT_build_enabled(Operator):
    bl_idname = "hextile.build_enabled"
    bl_label = "Build Enabled -> Preview & Export"
    bl_description = ("Build every enabled procedural tile, lay it out in a grid for preview, "
                      "and export its .glb. Bespoke tiles are skipped (they own their own .blend)")

    def execute(self, context):
        if not _is_master_file():
            self.report({'WARNING'}, "Build Enabled runs from the master (HexBase.blend)")
        tile_common.clear_preview()
        man = tile_common.load_manifest()
        names = [n for n in tile_registry.all_names()
                 if tile_common.tile_state(man, n)["enabled"]
                 and not tile_common.tile_state(man, n)["bespoke"]]
        coll = tile_common.preview_collection()
        built = exported = 0
        errs = []
        for i, name in enumerate(names):
            try:
                obj = tile_registry.get(name).build()
            except Exception as e:
                errs.append("build %s: %s" % (name, e))
                continue
            obj["_tile_preview"] = True
            for c in list(obj.users_collection):
                c.objects.unlink(obj)
            coll.objects.link(obj)
            obj.location = tile_common.grid_location(i)
            built += 1
            try:
                tile_common.export_glb(obj, tile_common.glb_path(name))
                exported += 1
            except Exception as e:
                errs.append("export %s: %s" % (name, e))
        msg = "Built %d, exported %d of %d enabled" % (built, exported, len(names))
        if errs:
            self.report({'WARNING'}, msg + " | %d errors: %s" % (len(errs), errs[0]))
        else:
            self.report({'INFO'}, msg)
        return {'FINISHED'}


class _FileSwitch:
    """Mixin: confirm dialog before a file switch. Leaving the master never auto-saves it."""
    save_current: BoolProperty(name="Save current file first", default=True)

    def invoke(self, context, event):
        self._master = _is_master_file()
        self.save_current = (not self._master) and bool(bpy.data.filepath)
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        col = self.layout.column()
        col.label(text=self.confirm_text())
        if bpy.data.is_dirty:
            if self._master:
                col.label(text="Master has unsaved edits — they will be DISCARDED", icon='ERROR')
                col.label(text="(keeps HexBase.blend byte-identical)")
            else:
                col.prop(self, "save_current")

    def maybe_save(self):
        if self.save_current and not self._master and bpy.data.filepath:
            bpy.ops.wm.save_mainfile()


class HEXTILE_OT_promote(_FileSwitch, Operator):
    bl_idname = "hextile.promote"
    bl_label = "Promote to Bespoke"
    bl_description = ("Spin this tile into its own editable .blend (linked master materials + "
                      "reference hex), toggle it OFF for procedural export, and open it")
    tile_name: StringProperty()

    def confirm_text(self):
        return "Create bespoke '%s.blend' and switch to it?" % self.tile_name

    def execute(self, context):
        out_blend = tile_common.bespoke_blend_path(self.tile_name)
        if os.path.exists(out_blend):
            self.report({'ERROR'}, "Bespoke file already exists — use Open Bespoke")
            return {'CANCELLED'}
        script = os.path.join(_HERE, "_make_bespoke.py")
        proc = subprocess.run(
            [bpy.app.binary_path, "--background", "--factory-startup", "--python", script,
             "--", self.tile_name, out_blend, tile_common.hexbase_path()],
            capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(out_blend):
            tail = (proc.stderr or proc.stdout or "")[-400:]
            self.report({'ERROR'}, "Bespoke build failed: %s" % tail)
            return {'CANCELLED'}
        man = tile_common.load_manifest()
        tile_common.set_tile_state(man, self.tile_name, enabled=False, bespoke=True,
                                   blend=tile_common.rel_to_repo(out_blend))
        tile_common.save_manifest(man)
        self.maybe_save()
        bpy.ops.wm.open_mainfile(filepath=out_blend)
        return {'FINISHED'}


class HEXTILE_OT_open_bespoke(_FileSwitch, Operator):
    bl_idname = "hextile.open_bespoke"
    bl_label = "Open Bespoke"
    bl_description = "Open this tile's bespoke .blend to edit it"
    tile_name: StringProperty()

    def confirm_text(self):
        return "Open bespoke '%s.blend'?" % self.tile_name

    def execute(self, context):
        out_blend = tile_common.bespoke_blend_path(self.tile_name)
        if not os.path.exists(out_blend):
            self.report({'ERROR'}, "Bespoke file missing: %s" % out_blend)
            return {'CANCELLED'}
        self.maybe_save()
        bpy.ops.wm.open_mainfile(filepath=out_blend)
        return {'FINISHED'}


class HEXTILE_OT_return_master(_FileSwitch, Operator):
    bl_idname = "hextile.return_master"
    bl_label = "Return to Master"
    bl_description = "Save (optional) and reopen HexBase.blend"

    def confirm_text(self):
        return "Return to the master HexBase.blend?"

    def execute(self, context):
        self.maybe_save()
        bpy.ops.wm.open_mainfile(filepath=tile_common.hexbase_path())
        return {'FINISHED'}


class HEXTILE_OT_export_this(Operator):
    bl_idname = "hextile.export_this"
    bl_label = "Export This Tile"
    bl_description = "Export this bespoke tile's local mesh to its .glb (Complex-As-Simple in UE)"

    def _tile_object(self, tile):
        obj = bpy.data.objects.get(tile)
        if obj is not None:
            return obj
        locals_ = [o for o in bpy.data.objects
                   if o.type == 'MESH' and o.library is None
                   and "Reference" not in [c.name for c in o.users_collection]]
        return locals_[0] if len(locals_) == 1 else None

    def execute(self, context):
        tile = _current_tile_name()
        obj = self._tile_object(tile)
        if obj is None:
            self.report({'ERROR'}, "Couldn't resolve the tile mesh to export for '%s'" % tile)
            return {'CANCELLED'}
        size = tile_common.export_glb(obj, tile_common.glb_path(tile))
        self.report({'INFO'}, "Exported %s.glb (%d bytes) — reimport in UE" % (tile, size))
        return {'FINISHED'}


# ---- panel ----
class HEXTILE_PT_panel(Panel):
    bl_label = "Hex Tiles"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hex Tiles"

    def draw(self, context):
        layout = self.layout

        if _in_bespoke_file():
            tile = _current_tile_name()
            box = layout.box()
            box.label(text="Bespoke tile", icon='MESH_DATA')
            box.label(text=tile)
            col = box.column(align=True)
            col.operator("hextile.export_this", icon='EXPORT')
            col.operator("hextile.return_master", icon='LOOP_BACK')
            return

        if not _is_master_file():
            layout.label(text="Open HexBase.blend to manage tiles", icon='INFO')

        col = layout.column(align=True)
        col.operator("hextile.build_enabled", icon='MOD_BUILD')
        row = col.row(align=True)
        row.operator("hextile.clear_preview", icon='TRASH')
        row.operator("hextile.refresh", text="", icon='FILE_REFRESH')

        layout.separator()
        scn = context.scene
        if not len(scn.hextile_list):
            layout.label(text="(click Refresh to load the list)")
            return
        box = layout.box()
        for item in scn.hextile_list:
            r = box.row(align=True)
            r.prop(item, "enabled", text="")
            r.label(text=item.name)
            if item.bespoke:
                r.label(text="", icon='LOCKED')
                op = r.operator("hextile.open_bespoke", text="", icon='FILE_BLEND')
                op.tile_name = item.name
            else:
                op = r.operator("hextile.promote", text="", icon='FILE_NEW')
                op.tile_name = item.name


# ---- (re)populate the list whenever a .blend loads ----
from bpy.app.handlers import persistent


@persistent
def _on_load(dummy):
    try:
        _populate(bpy.context.scene)
    except Exception:
        pass


_CLASSES = (
    HexTileItem,
    HEXTILE_OT_refresh, HEXTILE_OT_clear_preview, HEXTILE_OT_build_enabled,
    HEXTILE_OT_promote, HEXTILE_OT_open_bespoke, HEXTILE_OT_return_master,
    HEXTILE_OT_export_this,
    HEXTILE_PT_panel,
)


def register():
    for c in _CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.hextile_list = CollectionProperty(type=HexTileItem)
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    try:
        _populate(bpy.context.scene)
    except Exception:
        pass


def unregister():
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    del bpy.types.Scene.hextile_list
    for c in reversed(_CLASSES):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
