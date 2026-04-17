"""Handler registry.

Each domain module exposes a ``register(r)`` function that adds its RPC
methods to the shared dict. ``registry()`` builds and returns that dict.

Note: the handler named ``annotations`` collides with
``__future__.annotations`` if ``from __future__ import annotations``
sits at module scope — Python resolves the tuple entry to the
``_Feature`` object instead of the submodule. So we don't use that
future import here and we load submodules by string name instead of
unpacked ``from . import …``.
"""

from typing import Callable, Dict


_MODULE_NAMES = (
    "documents",
    "geometry",
    "sketch",
    "parts",
    "io",
    "defeaturing",
    "simplification",
    "analysis_prep",
    "materials",
    "bc_tagging",
    "inspection",
    "annotations",
    "views",
    "animation",
    "video",
    "render",
    "fem_export",
    "meshing",
    "blender_bridge",
    "execute",
    "parametric",
    "report",
    "budget",
    "drawing",
    "diff",
    "load_cases",
    "granular",
)


def registry() -> Dict[str, Callable]:
    import importlib

    r: Dict[str, Callable] = {}
    for name in _MODULE_NAMES:
        mod = importlib.import_module(f".{name}", package=__name__)
        mod.register(r)
    return r
