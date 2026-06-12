"""tile_registry.py — the single source of "what tiles exist and how to build one".

Pulls the procedural definitions straight from the existing generators so there's no
second list to keep in sync:
  * gen_curved_tiles.EDGE_SETS  -> the 14 T_street_* configs
  * gen_pit_core.core_specs()   -> the 7 T_core_* fixed-core tiles

Each registry entry exposes build() -> a freshly built tile object in the current scene
(no export, no cleanup). The pipeline addon lays those out for preview and exports them;
tile_common owns the actual glTF write.

Materials (M_Road / M_Pavement / M_HexGround) must already exist in the open .blend — they
do in HexBase.blend (the master) and in any bespoke tile that links them.
"""
import os
import sys

# Make sibling modules importable whether we're run as an addon or from the Text Editor.
_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
if _HERE and _HERE not in sys.path:
    sys.path.append(_HERE)

import gen_curved_tiles as _street
import gen_pit_core as _core
import gen_buildings as _bldg
import gen_river_tiles as _river
import gen_blank_variants as _blank
import gen_rim_tiles as _rim


class TileEntry:
    __slots__ = ("name", "kind", "_build")

    def __init__(self, name, kind, build):
        self.name = name      # final tile name == built object name == <name>.glb
        self.kind = kind      # "street" | "core"
        self._build = build

    def build(self):
        """Build the tile into the current scene and return its object."""
        return self._build()


def _registry():
    reg = {}
    # street kit (curved): tile name is "T_street_<key>"
    for key, edges in _street.EDGE_SETS.items():
        name = "T_street_%s" % key
        reg[name] = TileEntry(
            name, "street",
            (lambda k=key, e=list(edges): _street.build_tile_obj(k, e)),
        )
    # building kit (single-story facades + corner gardens): tile name is "T_bldg_<key>"
    for key, edges in _bldg.EDGE_SETS.items():
        name = "T_bldg_%s" % key
        reg[name] = TileEntry(
            name, "building",
            (lambda k=key, e=list(edges): _bldg.build_tile_obj(k, e)),
        )
    # blank variants (tended open ground; weighted siblings of T_street_blank)
    for key in _blank.VARIANTS:
        name = "T_blank_%s" % key
        reg[name] = TileEntry(
            name, "street",
            (lambda k=key: _blank.build_tile_obj(k)),
        )
    # rim kit (ring 7 — the bowl; Docs/Rim.md)
    for key in _rim.VARIANTS:
        name = "T_rim_%s" % key
        reg[name] = TileEntry(
            name, "rim",
            (lambda k=key: _rim.build_tile_obj(k)),
        )
    # fixed core: core_specs() keys are already "T_core_*"
    for name, (road, _qr, is_pit) in _core.core_specs().items():
        reg[name] = TileEntry(
            name, "core",
            (lambda n=name, r=dict(road), p=is_pit: _core.build_tile(n, r, p)),
        )
    return reg


REGISTRY = _registry()


def all_names():
    """Stable display order: street kit, blank variants, rim, buildings, core."""
    street = ["T_street_%s" % k for k in _street.EDGE_SETS]
    blank  = ["T_blank_%s"  % k for k in _blank.VARIANTS]
    rim    = ["T_rim_%s"    % k for k in _rim.VARIANTS]
    bldg   = ["T_bldg_%s"   % k for k in _bldg.EDGE_SETS]
    core   = [n for n in REGISTRY if n.startswith("T_core_")]
    return street + blank + rim + bldg + sorted(core)


def get(name):
    return REGISTRY.get(name)
