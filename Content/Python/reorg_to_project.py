"""reorg_to_project.py — move our authored content under /Game/_project so it stops comingling
with the imported Epic template assets.

RUN IN THE OPEN GUI EDITOR (Tools > Execute Python Script, or the Output Log), THEN:
  right-click the new /Game/_project folder -> Fix Up Redirectors -> Save All.
EditorAssetLibrary.rename_* updates every reference and leaves redirectors at the old paths;
Fix Up Redirectors (GUI only — gotcha #19) removes them cleanly.

Moves:
  /Game/HexTiles  -> /Game/_project/HexTiles   (tile meshes + Materials masters)
  /Game/Data      -> /Game/_project/Data       (DA_HexTileSet_Streets, DA_HexCoreLayout)
  our lab maps    -> /Game/_project/Maps        (template TestMap stays in /Game/Maps)
NOTE: loose .glb files under Content/HexTiles/Source are NOT UE assets and are moved on disk
separately (the Blender pipeline now targets Content/_project/HexTiles/Source).
"""
import unreal

eal = unreal.EditorAssetLibrary

DIR_MOVES = [
    ("/Game/HexTiles", "/Game/_project/HexTiles"),
    ("/Game/Data", "/Game/_project/Data"),
]
OUR_MAPS = ["ShuffleLab", "PitCoreLab", "CoreGenLab", "SplineLab"]


def main():
    for src, dst in DIR_MOVES:
        if eal.does_directory_exist(src):
            ok = eal.rename_directory(src, dst)
            unreal.log("[reorg] dir %s -> %s : %s" % (src, dst, ok))
        else:
            unreal.log("[reorg] skip (missing) %s" % src)

    eal.make_directory("/Game/_project/Maps")
    for m in OUR_MAPS:
        src = "/Game/Maps/%s" % m
        dst = "/Game/_project/Maps/%s" % m
        if eal.does_asset_exist(src):
            ok = eal.rename_asset(src, dst)
            unreal.log("[reorg] map %s -> %s : %s" % (src, dst, ok))
        else:
            unreal.log("[reorg] skip (missing) %s" % src)

    unreal.log("[reorg] DONE. Now: right-click /Game/_project -> Fix Up Redirectors -> Save All.")


main()
