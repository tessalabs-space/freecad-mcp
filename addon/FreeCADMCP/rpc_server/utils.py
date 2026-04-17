"""Shared helpers used by handlers."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import FreeCAD


def get_document(name: Optional[str]) -> "FreeCAD.Document":
    """Resolve a document by name, falling back to the active document."""
    if name:
        doc = FreeCAD.getDocument(name) if name in FreeCAD.listDocuments() else None
        if doc is None:
            raise ValueError(f"Document '{name}' not found")
        return doc
    if FreeCAD.ActiveDocument is None:
        raise ValueError("No active FreeCAD document")
    return FreeCAD.ActiveDocument


def get_object(doc_name: Optional[str], obj_name: str):
    doc = get_document(doc_name)
    obj = doc.getObject(obj_name)
    if obj is None:
        raise ValueError(f"Object '{obj_name}' not found in document '{doc.Name}'")
    return obj


def apply_placement(obj, placement: Dict[str, Any]) -> None:
    """Apply a placement dict of the form {'Base': {x,y,z}, 'Rotation': {...}}."""
    if not placement:
        return
    base = placement.get("Base") or {}
    rot = placement.get("Rotation") or {}
    pos = FreeCAD.Vector(
        float(base.get("x", 0.0)),
        float(base.get("y", 0.0)),
        float(base.get("z", 0.0)),
    )
    if rot:
        axis_spec = rot.get("Axis") or {"x": 0, "y": 0, "z": 1}
        axis = FreeCAD.Vector(
            float(axis_spec.get("x", 0.0)),
            float(axis_spec.get("y", 0.0)),
            float(axis_spec.get("z", 1.0)),
        )
        angle = float(rot.get("Angle", 0.0))
        rotation = FreeCAD.Rotation(axis, angle)
    else:
        rotation = FreeCAD.Rotation()
    obj.Placement = FreeCAD.Placement(pos, rotation)


_SKIP_PROPERTIES = {"Placement", "ViewObject", "References"}


def apply_properties(obj, properties: Optional[Dict[str, Any]]) -> None:
    """Copy a dict of simple properties onto a FreeCAD object."""
    if not properties:
        return
    for key, value in properties.items():
        if key in _SKIP_PROPERTIES:
            continue
        try:
            setattr(obj, key, value)
        except Exception as exc:
            FreeCAD.Console.PrintWarning(
                f"Could not set {obj.Name}.{key}={value!r}: {exc}\n"
            )
    if "Placement" in properties:
        apply_placement(obj, properties["Placement"])
    if "ViewObject" in properties and getattr(obj, "ViewObject", None) is not None:
        for vkey, vval in properties["ViewObject"].items():
            try:
                setattr(obj.ViewObject, vkey, vval)
            except Exception as exc:
                FreeCAD.Console.PrintWarning(
                    f"Could not set ViewObject.{vkey}: {exc}\n"
                )


def ok(**payload) -> Dict[str, Any]:
    """Standard success envelope."""
    return {"success": True, **payload}


def err(message: str, **extra) -> Dict[str, Any]:
    return {"success": False, "error": message, **extra}


def serialize_vector(v) -> Dict[str, float]:
    return {"x": float(v.x), "y": float(v.y), "z": float(v.z)}


def shape_center_of_mass(shape):
    """Centre-of-mass that works across Part.Solid, Part.Compound, Part.Shell.

    FreeCAD 1.1's ``Part.Compound`` exposes ``CenterOfGravity`` but not
    ``CenterOfMass``; ``Part.Solid`` exposes both. Prefer ``CenterOfGravity``
    everywhere; fall back to a volume-weighted average of sub-solids, then
    the bounding-box centre.
    """
    if hasattr(shape, "CenterOfGravity"):
        try:
            return shape.CenterOfGravity
        except Exception:
            pass
    if hasattr(shape, "CenterOfMass"):
        try:
            return shape.CenterOfMass
        except Exception:
            pass
    solids = getattr(shape, "Solids", None) or []
    total = 0.0
    weighted = FreeCAD.Vector(0, 0, 0)
    for s in solids:
        try:
            v = float(s.Volume)
            c = getattr(s, "CenterOfGravity", None) or getattr(s, "CenterOfMass", None)
            if c is not None and v > 0:
                total += v
                weighted = weighted + FreeCAD.Vector(c.x * v, c.y * v, c.z * v)
        except Exception:
            continue
    if total > 0:
        return weighted.multiply(1.0 / total)
    return shape.BoundBox.Center


def serialize_placement(p) -> Dict[str, Any]:
    axis = p.Rotation.Axis
    return {
        "Base": serialize_vector(p.Base),
        "Rotation": {"Axis": serialize_vector(axis), "Angle": float(p.Rotation.Angle)},
    }


def collect_subshapes(references: Iterable[Dict[str, Any]]):
    """Turn [{'object_name': 'Pad', 'face': 'Face3'}] into OCC refs."""
    refs = []
    for ref in references or []:
        obj = get_object(ref.get("doc_name"), ref["object_name"])
        sub = ref.get("face") or ref.get("edge") or ref.get("vertex")
        if sub:
            refs.append((obj, sub))
        else:
            refs.append((obj, ""))
    return refs
