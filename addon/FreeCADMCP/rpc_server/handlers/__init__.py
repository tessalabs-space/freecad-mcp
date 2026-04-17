"""Handler registry.

Each domain module exposes a ``register(r)`` function that adds its RPC
methods to the shared dict. ``registry()`` builds and returns that dict.
"""

from __future__ import annotations

from typing import Callable, Dict


def registry() -> Dict[str, Callable]:
    r: Dict[str, Callable] = {}
    from . import (
        documents,
        geometry,
        sketch,
        parts,
        io,
        defeaturing,
        analysis_prep,
        materials,
        bc_tagging,
        inspection,
        annotations,
        views,
        animation,
        render,
        fem_export,
        blender_bridge,
        execute,
        parametric,
        report,
        budget,
        drawing,
        diff,
        load_cases,
        granular,
    )

    for mod in (
        documents,
        geometry,
        sketch,
        parts,
        io,
        defeaturing,
        analysis_prep,
        materials,
        bc_tagging,
        inspection,
        annotations,
        views,
        animation,
        render,
        fem_export,
        blender_bridge,
        execute,
        parametric,
        report,
        budget,
        drawing,
        diff,
        load_cases,
        granular,
    ):
        mod.register(r)
    return r
