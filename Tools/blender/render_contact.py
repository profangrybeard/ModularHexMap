"""render_contact.py — headless contact-sheet renders of staged tile .glbs.

    blender --background --factory-startup \
            --python Tools/blender/render_contact.py -- [substring ...]

Renders every Content/_project/HexTiles/Source/*.glb whose name contains any given
substring (no args = all) to Docs/Images/ContactSheets/<tile>.png — a quick visual
diff artifact after each bake (Roadmap ToDo). One tile per frame, 3/4 orbit view,
EEVEE with a workbench fallback so it renders on any machine. Reads ONLY the staged
.glbs; touches no .blend.
"""
import math
import os
import sys

import bpy


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def out_dir():
    d = os.path.join(repo_root(), "Docs", "Images", "ContactSheets")
    os.makedirs(d, exist_ok=True)
    return d


def src_dir():
    return os.path.join(repo_root(), "Content", "_project", "HexTiles", "Source")


def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def light_and_camera():
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(135))
    bpy.context.scene.collection.objects.link(sun)

    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    # 3/4 orbit: high enough to read the plan, low enough to read the masses
    dist, alt = 30.0, math.radians(38)
    az = math.radians(-60)
    cam.location = (dist * math.cos(alt) * math.cos(az),
                    dist * math.cos(alt) * math.sin(az),
                    dist * math.sin(alt) + 0.5)
    cam.rotation_euler = (math.radians(90) - alt, 0.0, az + math.radians(90))
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam


def render(glb, png):
    clean_scene()
    bpy.ops.import_scene.gltf(filepath=glb)
    light_and_camera()
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = 640
    sc.render.filepath = png
    sc.render.image_settings.file_format = 'PNG'
    try:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception:
        sc.render.engine = 'BLENDER_WORKBENCH'
    try:
        bpy.ops.render.render(write_still=True)
    except Exception as exc:
        print("  EEVEE failed (%s) -> workbench" % exc)
        sc.render.engine = 'BLENDER_WORKBENCH'
        bpy.ops.render.render(write_still=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    names = sorted(f for f in os.listdir(src_dir()) if f.endswith(".glb"))
    if args:
        names = [f for f in names if any(a in f for a in args)]
    print("=== render_contact: %d tiles -> %s ===" % (len(names), out_dir()))
    for f in names:
        png = os.path.join(out_dir(), f.replace(".glb", ".png"))
        render(os.path.join(src_dir(), f), png)
        print("  %-28s -> %s" % (f, os.path.basename(png)))
    print("=== render_contact: done ===")


main()
