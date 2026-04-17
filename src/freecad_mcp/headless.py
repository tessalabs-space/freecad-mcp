"""Headless FreeCAD mode — import FreeCAD as a Python module and run
geometry ops without a running GUI. Only a subset of the handler surface
works headless (no views, no annotations, no renders).

Usage:
    from freecad_mcp import headless
    headless.ensure_available()
    doc = headless.new_document("batch")
    headless.run_handler("create_primitive", kind="box", name="Box",
                         properties={"Length": 30, "Width": 20, "Height": 10})
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


_IMPORTED = False


def ensure_available(freecad_bin_dir: Optional[str] = None) -> None:
    """Make FreeCAD's Python bindings importable in this process."""
    global _IMPORTED
    if _IMPORTED:
        return
    if freecad_bin_dir:
        sys.path.insert(0, freecad_bin_dir)
    try:
        import FreeCAD  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "FreeCAD's Python bindings were not found. Set freecad_bin_dir to "
            "the FreeCAD install 'bin' directory or run the addon via the GUI."
        ) from exc
    _IMPORTED = True


def new_document(name: str):
    ensure_available()
    import FreeCAD
    return FreeCAD.newDocument(name)


def run_handler(method: str, **kwargs: Any) -> Dict[str, Any]:
    """Call the named handler directly (same code path as the RPC server)
    but without the Qt GUI thread. Raises if the handler touches the GUI.
    """
    ensure_available()
    addon_path = _find_addon_path()
    if str(addon_path) not in sys.path:
        sys.path.insert(0, str(addon_path))
    from rpc_server.handlers import registry  # type: ignore
    reg = registry()
    if method not in reg:
        raise KeyError(f"Unknown handler '{method}'; have {sorted(reg)}")
    return reg[method](**kwargs)


def _find_addon_path() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        candidate = parent / "addon" / "FreeCADMCP"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("addon/FreeCADMCP not found relative to freecad_mcp package")
