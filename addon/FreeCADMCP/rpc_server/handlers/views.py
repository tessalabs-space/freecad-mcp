"""View controls, screenshots, section cuts, exploded views."""

from __future__ import annotations

import base64
import io
import os
import tempfile
from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, get_object, ok, err, shape_center_of_mass


_VIEW_DIRECTIONS = {
    "Isometric": "ViewIsometric",
    "Front": "ViewFront",
    "Top": "ViewTop",
    "Right": "ViewRight",
    "Back": "ViewRear",
    "Left": "ViewLeft",
    "Bottom": "ViewBottom",
    "Dimetric": "ViewDimetric",
    "Trimetric": "ViewTrimetric",
}


def _active_view():
    import FreeCADGui
    mw = FreeCADGui.getMainWindow()
    view = FreeCADGui.ActiveDocument.ActiveView if FreeCADGui.ActiveDocument else None
    return view, mw


def set_view(direction: str, focus_object: Optional[str] = None, doc_name: Optional[str] = None) -> Dict[str, Any]:
    import FreeCADGui
    cmd = _VIEW_DIRECTIONS.get(direction)
    if cmd is None:
        return err(f"Unknown view '{direction}'", known=sorted(_VIEW_DIRECTIONS))
    FreeCADGui.runCommand(cmd, 0)
    if focus_object:
        doc = get_document(doc_name)
        obj = doc.getObject(focus_object)
        if obj is not None and hasattr(obj, "ViewObject"):
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(obj)
            FreeCADGui.SendMsgToActiveView("ViewSelection")
    else:
        FreeCADGui.SendMsgToActiveView("ViewFit")
    return ok(direction=direction)


def screenshot(
    path: Optional[str] = None,
    width: int = 1600,
    height: int = 1000,
    background: str = "Current",
    return_bytes: bool = True,
) -> Dict[str, Any]:
    import FreeCADGui
    view = FreeCADGui.ActiveDocument.ActiveView if FreeCADGui.ActiveDocument else None
    if view is None:
        return err("No active 3D view")
    if path is None:
        path = os.path.join(tempfile.gettempdir(), "freecadmcp_screenshot.png")
    view.saveImage(path, int(width), int(height), background)
    result: Dict[str, Any] = {"path": path, "width": width, "height": height}
    if return_bytes:
        with open(path, "rb") as f:
            result["image_base64"] = base64.b64encode(f.read()).decode("ascii")
    return ok(**result)


def section_cut(
    objects: List[str],
    origin: Dict[str, float],
    normal: Dict[str, float],
    name: Optional[str] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a FreeCAD ``Part::SectionCut`` across the listed objects."""
    doc = get_document(doc_name)
    objs = [doc.getObject(n) for n in objects]
    if any(o is None for o in objs):
        return err("Unknown object in section list")
    try:
        sc = doc.addObject("Part::SectionCut", name or "SectionCut")
        sc.Objects = objs
        sc.Placement = FreeCAD.Placement(
            FreeCAD.Vector(
                float(origin.get("x", 0)),
                float(origin.get("y", 0)),
                float(origin.get("z", 0)),
            ),
            FreeCAD.Rotation(
                FreeCAD.Vector(
                    float(normal.get("x", 0)),
                    float(normal.get("y", 0)),
                    float(normal.get("z", 1)),
                ),
                0,
            ),
        )
        doc.recompute()
        return ok(name=sc.Name)
    except Exception as exc:
        return err(f"Part::SectionCut unavailable ({exc}); enable the Part workbench section cut feature")


def explode(
    objects: List[str],
    factor: float = 1.5,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Move every object radially outward from the assembly centroid by
    ``factor`` × its own distance from centroid. Reversible — call with
    ``factor=1.0`` to restore.
    """
    doc = get_document(doc_name)
    objs = [doc.getObject(n) for n in objects]
    if any(o is None for o in objs):
        return err("Unknown object in explode list")
    centres = []
    for o in objs:
        try:
            centres.append(shape_center_of_mass(o.Shape))
        except Exception:
            centres.append(o.Placement.Base)
    centroid = FreeCAD.Vector(
        sum(c.x for c in centres) / len(centres),
        sum(c.y for c in centres) / len(centres),
        sum(c.z for c in centres) / len(centres),
    )
    for o, c in zip(objs, centres):
        offset = (c - centroid) * (factor - 1.0)
        p = o.Placement
        p.Base = p.Base + offset
        o.Placement = p
    doc.recompute()
    return ok(center=_v(centroid), factor=factor)


def _v(vec) -> Dict[str, float]:
    return {"x": float(vec.x), "y": float(vec.y), "z": float(vec.z)}


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "set_view": set_view,
            "screenshot": screenshot,
            "section_cut": section_cut,
            "explode": explode,
        }
    )
