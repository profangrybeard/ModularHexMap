"""Explicit commandlet entry for the material consolidation (the __main__ guard is unreliable
under UE's pythonscript commandlet). Run:
  UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="Content/Python/_run_consolidate.py"
"""
import unreal
import hextile_materials

unreal.log("[_run_consolidate] force-rebind meshes to masters + save")
hextile_materials.consolidate_to_masters()     # force every slot to the master path, save meshes
unreal.log("[_run_consolidate] done (redirector files removed on disk by the caller)")
