"""Part workbench operations: extrude, revolve, loft, sweep."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, ok, err


def extrude(
    profile: str,
    length: float,
    direction: Optional[Dict[str, float]] = None,
    symmetric: bool = False,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    src = doc.getObject(profile)
    if src is None:
        return err(f"Profile '{profile}' not found")
    ext = doc.addObject("Part::Extrusion", name or f"{profile}_Extrude")
    ext.Base = src
    ext.LengthFwd = float(length)
    ext.Symmetric = bool(symmetric)
    if direction:
        ext.DirMode = "Custom"
        ext.Dir = FreeCAD.Vector(
            float(direction.get("x", 0)),
            float(direction.get("y", 0)),
            float(direction.get("z", 1)),
        )
    else:
        ext.DirMode = "Normal"
    ext.Solid = True
    doc.recompute()
    return ok(name=ext.Name)


def revolve(
    profile: str,
    axis_base: Dict[str, float],
    axis_dir: Dict[str, float],
    angle: float = 360.0,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    src = doc.getObject(profile)
    if src is None:
        return err(f"Profile '{profile}' not found")
    rev = doc.addObject("Part::Revolution", name or f"{profile}_Revolve")
    rev.Source = src
    rev.Base = FreeCAD.Vector(
        float(axis_base.get("x", 0)),
        float(axis_base.get("y", 0)),
        float(axis_base.get("z", 0)),
    )
    rev.Axis = FreeCAD.Vector(
        float(axis_dir.get("x", 0)),
        float(axis_dir.get("y", 0)),
        float(axis_dir.get("z", 1)),
    )
    rev.Angle = float(angle)
    rev.Solid = True
    doc.recompute()
    return ok(name=rev.Name)


def loft(
    profiles: List[str],
    solid: bool = True,
    ruled: bool = False,
    closed: bool = False,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    lofted = doc.addObject("Part::Loft", name or "Loft")
    sections = [doc.getObject(p) for p in profiles]
    if any(s is None for s in sections):
        return err("Unknown profile in loft")
    lofted.Sections = sections
    lofted.Solid = bool(solid)
    lofted.Ruled = bool(ruled)
    lofted.Closed = bool(closed)
    doc.recompute()
    return ok(name=lofted.Name)


def sweep(
    profile: str,
    path: str,
    solid: bool = True,
    frenet: bool = False,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    swp = doc.addObject("Part::Sweep", name or f"{profile}_Sweep")
    prof = doc.getObject(profile)
    spine = doc.getObject(path)
    if prof is None or spine is None:
        return err("Unknown profile or path")
    swp.Sections = [prof]
    swp.Spine = spine
    swp.Solid = bool(solid)
    swp.Frenet = bool(frenet)
    doc.recompute()
    return ok(name=swp.Name)


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "extrude": extrude,
            "revolve": revolve,
            "loft": loft,
            "sweep": sweep,
        }
    )
