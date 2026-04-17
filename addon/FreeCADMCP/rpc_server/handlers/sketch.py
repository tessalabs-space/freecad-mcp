"""Sketch creation with basic geometry and constraints.

Scope note: FreeCAD's Sketcher is extremely feature-rich; we expose the
constructors that are stable across versions and most commonly used for
parametric CAD.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import FreeCAD
import Part
import Sketcher

from ..utils import apply_placement, get_document, ok, err


def create_sketch(
    name: str,
    plane: str = "XY",
    doc_name: Optional[str] = None,
    placement: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    sketch = doc.addObject("Sketcher::SketchObject", name)
    if placement:
        apply_placement(sketch, placement)
    else:
        presets = {
            "XY": FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(0, 0, 0, 1)),
            "XZ": FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(1, 0, 0, 1)),
            "YZ": FreeCAD.Placement(
                FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 90)
            ),
        }
        if plane.upper() not in presets:
            return err(f"Unknown sketch plane '{plane}' (XY, XZ, YZ)")
        sketch.Placement = presets[plane.upper()]
    doc.recompute()
    return ok(name=sketch.Name)


def add_line(
    sketch_name: str,
    start: Dict[str, float],
    end: Dict[str, float],
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    sk = doc.getObject(sketch_name)
    if sk is None:
        return err(f"Sketch '{sketch_name}' not found")
    p1 = FreeCAD.Vector(float(start["x"]), float(start["y"]), 0)
    p2 = FreeCAD.Vector(float(end["x"]), float(end["y"]), 0)
    idx = sk.addGeometry(Part.LineSegment(p1, p2))
    doc.recompute()
    return ok(geometry_index=idx)


def add_circle(
    sketch_name: str,
    center: Dict[str, float],
    radius: float,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    sk = doc.getObject(sketch_name)
    if sk is None:
        return err(f"Sketch '{sketch_name}' not found")
    c = FreeCAD.Vector(float(center["x"]), float(center["y"]), 0)
    idx = sk.addGeometry(Part.Circle(c, FreeCAD.Vector(0, 0, 1), float(radius)))
    doc.recompute()
    return ok(geometry_index=idx)


def add_rectangle(
    sketch_name: str,
    origin: Dict[str, float],
    width: float,
    height: float,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    sk = doc.getObject(sketch_name)
    if sk is None:
        return err(f"Sketch '{sketch_name}' not found")
    x0, y0 = float(origin["x"]), float(origin["y"])
    w, h = float(width), float(height)
    pts = [
        FreeCAD.Vector(x0, y0, 0),
        FreeCAD.Vector(x0 + w, y0, 0),
        FreeCAD.Vector(x0 + w, y0 + h, 0),
        FreeCAD.Vector(x0, y0 + h, 0),
    ]
    idxs = []
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        idxs.append(sk.addGeometry(Part.LineSegment(a, b)))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", idxs[i], 2, idxs[(i + 1) % 4], 1))
    doc.recompute()
    return ok(geometry_indices=idxs)


def add_constraint(
    sketch_name: str,
    kind: str,
    refs: List[Dict[str, Any]],
    value: Optional[float] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a Sketcher constraint.

    refs: list of {'geo': int, 'vertex': int} dicts. ``kind`` is one of
    ``Coincident``, ``Horizontal``, ``Vertical``, ``Parallel``,
    ``Perpendicular``, ``Tangent``, ``Equal``, ``Distance``, ``DistanceX``,
    ``DistanceY``, ``Radius``, ``Diameter``, ``Angle``.
    """
    doc = get_document(doc_name)
    sk = doc.getObject(sketch_name)
    if sk is None:
        return err(f"Sketch '{sketch_name}' not found")
    args: list = [kind]
    for r in refs:
        args.append(int(r["geo"]))
        if "vertex" in r:
            args.append(int(r["vertex"]))
    if value is not None:
        args.append(float(value))
    idx = sk.addConstraint(Sketcher.Constraint(*args))
    doc.recompute()
    return ok(constraint_index=idx)


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "create_sketch": create_sketch,
            "sketch_add_line": add_line,
            "sketch_add_circle": add_circle,
            "sketch_add_rectangle": add_rectangle,
            "sketch_add_constraint": add_constraint,
        }
    )
