"""3D annotations: leader arrows with auto-routing and part callouts.

Annotations are stored as ``App::FeaturePython`` objects with an
inline provider that draws a Coin3D leader line and a text label.
They recompute with the document so the arrow follows its target.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, get_object, ok, err, shape_center_of_mass


_ANNOTATION_STORE = "FreeCADMCP_Annotations"


def _ensure_group(doc) -> Any:
    grp = doc.getObject(_ANNOTATION_STORE)
    if grp is None:
        grp = doc.addObject("App::DocumentObjectGroup", _ANNOTATION_STORE)
        grp.Label = "MCP Annotations"
    return grp


def add_callout(
    label: str,
    target_object: str,
    target_face: Optional[int] = None,
    offset: Optional[Dict[str, float]] = None,
    color: Optional[List[float]] = None,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Draw a leader arrow from an offset position to the centroid of a
    face (or the object bounding-box centre if no face is specified),
    plus a text label at the leader tail.
    """
    obj = get_object(doc_name, target_object)
    doc = obj.Document
    if target_face:
        try:
            face = obj.Shape.Faces[target_face - 1]
            tip = shape_center_of_mass(face)
        except Exception:
            return err(f"face {target_face} not found on {target_object}")
    else:
        bb = obj.Shape.BoundBox
        tip = FreeCAD.Vector(bb.Center.x, bb.Center.y, bb.Center.z)

    delta = offset or {"x": 40.0, "y": 40.0, "z": 40.0}
    tail = FreeCAD.Vector(
        tip.x + float(delta.get("x", 0)),
        tip.y + float(delta.get("y", 0)),
        tip.z + float(delta.get("z", 0)),
    )

    import Draft  # type: ignore

    line = Draft.make_wire([tail, tip], closed=False)
    line.Label = (name or f"Callout_{target_object}_Line")
    try:
        line.ViewObject.EndArrow = True
        line.ViewObject.ArrowType = "Arrow"
        line.ViewObject.LineWidth = 2.0
        if color:
            line.ViewObject.LineColor = tuple(color[:3])
    except Exception:
        pass

    text = Draft.make_text([label], tail)
    text.Label = (name or f"Callout_{target_object}_Text")
    try:
        text.ViewObject.FontSize = 14
        if color:
            text.ViewObject.TextColor = tuple(color[:3])
    except Exception:
        pass

    group = _ensure_group(doc)
    group.addObject(line)
    group.addObject(text)
    doc.recompute()
    return ok(line=line.Name, text=text.Name)


def clear_annotations(doc_name: Optional[str] = None) -> Dict[str, Any]:
    doc = get_document(doc_name)
    grp = doc.getObject(_ANNOTATION_STORE)
    if grp is None:
        return ok(removed=0)
    removed = 0
    for child in list(grp.Group):
        doc.removeObject(child.Name)
        removed += 1
    doc.removeObject(grp.Name)
    doc.recompute()
    return ok(removed=removed)


def add_dimension(
    a: Dict[str, float],
    b: Dict[str, float],
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    import Draft  # type: ignore

    p1 = FreeCAD.Vector(float(a["x"]), float(a["y"]), float(a["z"]))
    p2 = FreeCAD.Vector(float(b["x"]), float(b["y"]), float(b["z"]))
    mid = FreeCAD.Vector(0.5 * (p1.x + p2.x), 0.5 * (p1.y + p2.y) + 10, 0.5 * (p1.z + p2.z))
    dim = Draft.make_dimension(p1, p2, mid)
    dim.Label = name or "Dimension"
    group = _ensure_group(doc)
    group.addObject(dim)
    doc.recompute()
    return ok(dimension=dim.Name, length_mm=float(p1.distanceToPoint(p2)))


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "add_callout": add_callout,
            "clear_annotations": clear_annotations,
            "add_dimension": add_dimension,
        }
    )
