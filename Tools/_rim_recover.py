"""_rim_recover.py — one-shot GUI editor recovery chain (2026-06-12 water-mask hunt):

  1. PROBE the rim assets AS-IS (the corrupted state the flip session saved —
     forensic evidence, captured before reimport overwrites it),
  2. Tools ▸ Reimport Hex Tiles (fresh import of the v2.2 GLBs + material heal),
  3. PROBE again (post-reimport state),
  4. the full four-layer rim gate (verify_rim_b1: counts / calibration trust /
     ring identity / per-instance orientation, 30 seeds).

  UnrealEditor.exe <uproject> -ExecutePythonScript="<repo>/Tools/_rim_recover.py"

Then grep the log:  Saved/Logs/ModularHexMap.log  for [RimRecover], probe
output, 'calibration', and the [RimB1] verdict lines.
"""
import os
import unreal

ROOT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())


def _probe(tag):
    unreal.log("[RimRecover] ======== probe: %s ========" % tag)
    path = os.path.join(ROOT, "Tools", "probe_rim_materials.py")
    exec(compile(open(path).read(), path, "exec"), {})


unreal.log("[RimRecover] start (project=%s)" % ROOT)
_probe("PRE-reimport (assets as the flip session left them)")

import reimport_hextiles
reimport_hextiles.run()

_probe("POST-reimport (fresh v2.2 import + material heal)")

gate = os.path.join(ROOT, "Tools", "verify_rim_b1.py")
unreal.log("[RimRecover] ======== running the rim gate ========")
exec(compile(open(gate).read(), gate, "exec"), {})
