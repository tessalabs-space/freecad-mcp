"""PNG rendering via FreeCAD's built-in view or the optional Render
workbench. We keep it simple: quality-tier presets that tune anti-alias
and background.
"""

from __future__ import annotations

import base64
import os
import tempfile
from typing import Any, Dict, Optional

from ..utils import ok, err


def render_png(
    path: Optional[str] = None,
    width: int = 2400,
    height: int = 1600,
    background: str = "Transparent",
    quality: str = "high",
    return_bytes: bool = False,
) -> Dict[str, Any]:
    import FreeCADGui
    view = FreeCADGui.ActiveDocument.ActiveView if FreeCADGui.ActiveDocument else None
    if view is None:
        return err("No active 3D view")

    # Quality tiers nudge the Coin3D antialias count through the preferences.
    prefs = FreeCADGui.getMainWindow().findChild(object, "MainWindow")
    try:
        import FreeCAD
        params = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View")
        aa = {"low": 0, "medium": 4, "high": 16}.get(quality, 16)
        params.SetInt("SampleBuffers", 1)
        params.SetInt("Samples", aa)
    except Exception:
        pass

    if path is None:
        path = os.path.join(tempfile.gettempdir(), "freecadmcp_render.png")
    view.saveImage(path, int(width), int(height), background)
    result: Dict[str, Any] = {"path": path, "width": width, "height": height, "quality": quality}
    if return_bytes:
        with open(path, "rb") as f:
            result["image_base64"] = base64.b64encode(f.read()).decode("ascii")
    return ok(**result)


def register(r: Dict[str, Any]) -> None:
    r.update({"render_png": render_png})
