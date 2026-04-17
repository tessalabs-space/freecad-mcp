"""Inspection: mass properties, centre of gravity, clash detection,
interference / dimension queries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, get_object, ok, err, serialize_vector, shape_center_of_mass


def mass_properties(
    obj_name: str,
    density_kg_m3: Optional[float] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    shape = obj.Shape
    volume_mm3 = shape.Volume
    volume_m3 = volume_mm3 * 1e-9
    surface_area_mm2 = shape.Area
    center = shape_center_of_mass(shape)
    result: Dict[str, Any] = {
        "volume_mm3": volume_mm3,
        "volume_m3": volume_m3,
        "surface_area_mm2": surface_area_mm2,
        "center_of_mass_mm": serialize_vector(center),
        "bbox": _bbox(shape),
    }
    # Try assigned material density if none given
    if density_kg_m3 is None and "FreeCADMCP_Material" in obj.PropertiesList:
        try:
            meta = dict(obj.FreeCADMCP_Material)
            density_kg_m3 = float(meta.get("density_kg_m3"))
        except Exception:
            pass
    if density_kg_m3 is not None:
        mass_kg = volume_m3 * float(density_kg_m3)
        result["density_kg_m3"] = float(density_kg_m3)
        result["mass_kg"] = mass_kg
        try:
            im = shape.MatrixOfInertia
            result["inertia_kg_mm2"] = [
                [im.A11 * (mass_kg / shape.Volume), im.A12, im.A13],
                [im.A21, im.A22 * (mass_kg / shape.Volume), im.A23],
                [im.A31, im.A32, im.A33 * (mass_kg / shape.Volume)],
            ]
        except Exception:
            pass
    return ok(**result)


def clash_detection(
    objects: Optional[List[str]] = None,
    tolerance: float = 0.0,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    if objects is None:
        objs = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
    else:
        objs = [doc.getObject(n) for n in objects]
        if any(o is None for o in objs):
            return err("Unknown object in clash list")
    clashes: List[Dict[str, Any]] = []
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            a, b = objs[i], objs[j]
            try:
                common = a.Shape.common(b.Shape)
            except Exception:
                continue
            vol = common.Volume
            if vol > tolerance:
                clashes.append(
                    {
                        "a": a.Name,
                        "b": b.Name,
                        "overlap_volume_mm3": float(vol),
                    }
                )
    return ok(count=len(clashes), clashes=clashes)


def distance_between(
    a: str,
    b: str,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    oa, ob = doc.getObject(a), doc.getObject(b)
    if oa is None or ob is None:
        return err("Unknown object(s)")
    dist, pairs, _ = oa.Shape.distToShape(ob.Shape)
    nearest = []
    for p1, p2 in (pairs or [])[:3]:
        nearest.append({"a": serialize_vector(p1), "b": serialize_vector(p2)})
    return ok(distance_mm=float(dist), nearest_pairs=nearest)


def expression_report(
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Dump all parametric expressions across the document.

    Useful to see what's driven from where before you rip out a dependency.
    """
    doc = get_document(doc_name)
    report = []
    for obj in doc.Objects:
        for prop in obj.PropertiesList:
            try:
                expr = obj.ExpressionEngine
            except Exception:
                continue
            for path, expression in expr or []:
                if path.endswith(prop):
                    report.append(
                        {"object": obj.Name, "property": prop, "expression": expression}
                    )
    return ok(count=len(report), expressions=report)


def _bbox(shape) -> Dict[str, float]:
    bb = shape.BoundBox
    return {
        "xmin": bb.XMin,
        "ymin": bb.YMin,
        "zmin": bb.ZMin,
        "xmax": bb.XMax,
        "ymax": bb.YMax,
        "zmax": bb.ZMax,
        "diag_mm": bb.DiagonalLength,
    }


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "mass_properties": mass_properties,
            "clash_detection": clash_detection,
            "distance_between": distance_between,
            "expression_report": expression_report,
        }
    )
