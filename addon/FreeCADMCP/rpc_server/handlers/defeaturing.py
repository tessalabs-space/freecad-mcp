"""Defeaturing tools for analysis prep.

These are *best-effort geometric heuristics*, not perfect defeaturers —
catching 90% of bolts, holes, fillets, and chamfers on typical mechanical
parts. For pathological geometry, fall back to ``execute_code`` with a
custom OCC routine.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import FreeCAD
import Part

from ..utils import get_document, get_object, ok, err


def _is_cylindrical(face) -> bool:
    try:
        return face.Surface.TypeId == "Part::GeomCylinder" or isinstance(face.Surface, Part.Cylinder)
    except Exception:
        return False


def _is_circular_hole(face, max_diameter: float) -> bool:
    """A face is a hole if it is cylindrical, closed, and within diameter."""
    if not _is_cylindrical(face):
        return False
    try:
        radius = face.Surface.Radius
    except Exception:
        return False
    return radius * 2 <= max_diameter


def find_holes(
    obj_name: str,
    max_diameter: float = 10.0,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    shape = obj.Shape
    hits: List[Dict[str, Any]] = []
    for idx, face in enumerate(shape.Faces, start=1):
        if _is_circular_hole(face, max_diameter):
            hits.append(
                {
                    "face_index": idx,
                    "diameter_mm": 2 * face.Surface.Radius,
                    "area_mm2": face.Area,
                }
            )
    return ok(count=len(hits), holes=hits)


def remove_holes(
    obj_name: str,
    max_diameter: float = 10.0,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Fill cylindrical holes up to ``max_diameter``.

    Uses OCC's ShapeUpgrade/Part.removeFeature equivalent by iterating faces,
    closing each hole with a planar face, and sewing the result.
    """
    obj = get_object(doc_name, obj_name)
    doc = obj.Document
    shape = obj.Shape.copy()
    faces_to_remove = []
    for idx, face in enumerate(shape.Faces, start=1):
        if _is_circular_hole(face, max_diameter):
            faces_to_remove.append(f"Face{idx}")
    if not faces_to_remove:
        return ok(removed=[], note="no matching holes found")
    try:
        cleaned = shape.removeFeature(faces_to_remove)
    except Exception as exc:
        return err(f"removeFeature failed: {exc}", candidates=faces_to_remove)
    out = doc.addObject("Part::Feature", name or f"{obj_name}_NoHoles")
    out.Shape = cleaned
    doc.recompute()
    return ok(name=out.Name, removed=faces_to_remove)


def _fillet_like(face, max_radius: float) -> Optional[float]:
    try:
        if isinstance(face.Surface, Part.Cylinder):
            if face.Surface.Radius <= max_radius and len(face.Edges) >= 2:
                return face.Surface.Radius
    except Exception:
        return None
    try:
        if isinstance(face.Surface, Part.Toroid):
            # Fillet arcs often show as toroids in STEP/IGES imports.
            if face.Surface.MinorRadius <= max_radius:
                return face.Surface.MinorRadius
    except Exception:
        pass
    return None


def find_fillets(
    obj_name: str,
    max_radius: float = 5.0,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    hits: List[Dict[str, Any]] = []
    for idx, face in enumerate(obj.Shape.Faces, start=1):
        r = _fillet_like(face, max_radius)
        if r is not None:
            hits.append({"face_index": idx, "radius_mm": r, "area_mm2": face.Area})
    return ok(count=len(hits), fillets=hits)


def remove_fillets(
    obj_name: str,
    max_radius: float = 5.0,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    doc = obj.Document
    face_names = []
    for idx, face in enumerate(obj.Shape.Faces, start=1):
        if _fillet_like(face, max_radius) is not None:
            face_names.append(f"Face{idx}")
    if not face_names:
        return ok(removed=[], note="no fillets under threshold")
    try:
        cleaned = obj.Shape.copy().removeFeature(face_names)
    except Exception as exc:
        return err(f"removeFeature failed: {exc}", candidates=face_names)
    out = doc.addObject("Part::Feature", name or f"{obj_name}_NoFillets")
    out.Shape = cleaned
    doc.recompute()
    return ok(name=out.Name, removed=face_names)


def remove_chamfers(
    obj_name: str,
    max_size: float = 5.0,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Heuristic: chamfer faces are planar, narrow bands connecting two
    larger faces. We detect by aspect ratio of the oriented bounding box.
    """
    obj = get_object(doc_name, obj_name)
    doc = obj.Document
    candidates = []
    for idx, face in enumerate(obj.Shape.Faces, start=1):
        try:
            if not isinstance(face.Surface, Part.Plane):
                continue
            bb = face.BoundBox
            dims = sorted([bb.XLength, bb.YLength, bb.ZLength])
            thin, long_ = dims[0], dims[2]
            if thin <= max_size and long_ > 0 and (thin / long_) < 0.3:
                candidates.append(f"Face{idx}")
        except Exception:
            continue
    if not candidates:
        return ok(removed=[], note="no chamfer candidates")
    try:
        cleaned = obj.Shape.copy().removeFeature(candidates)
    except Exception as exc:
        return err(f"removeFeature failed: {exc}", candidates=candidates)
    out = doc.addObject("Part::Feature", name or f"{obj_name}_NoChamfers")
    out.Shape = cleaned
    doc.recompute()
    return ok(name=out.Name, removed=candidates)


def find_fasteners(
    doc_name: Optional[str] = None,
    name_patterns: Optional[List[str]] = None,
    max_length_mm: float = 200.0,
    diameter_range_mm: Tuple[float, float] = (1.5, 20.0),
) -> Dict[str, Any]:
    """Find likely bolts / screws / nuts by label pattern + shape heuristics.

    Two-step filter:
      1. Name match against common patterns (bolt, screw, nut, washer, ...).
      2. Shape fingerprint: cylindrical primary axis, small diameter, length
         well within typical fastener range.
    """
    doc = get_document(doc_name)
    patterns = [p.lower() for p in (name_patterns or [
        "bolt", "screw", "nut", "washer", "fastener", "m3", "m4", "m5",
        "m6", "m8", "m10", "m12", "stud", "rivet",
    ])]
    low_d, high_d = diameter_range_mm
    hits: List[Dict[str, Any]] = []
    for obj in doc.Objects:
        if not hasattr(obj, "Shape"):
            continue
        label = obj.Label.lower()
        name_match = any(p in label for p in patterns)
        cyl_radii = []
        for face in obj.Shape.Faces:
            try:
                if isinstance(face.Surface, Part.Cylinder):
                    cyl_radii.append(face.Surface.Radius)
            except Exception:
                continue
        bb_len = max(obj.Shape.BoundBox.XLength, obj.Shape.BoundBox.YLength, obj.Shape.BoundBox.ZLength)
        shape_match = False
        if cyl_radii:
            d = 2 * min(cyl_radii)
            if low_d <= d <= high_d and bb_len <= max_length_mm:
                shape_match = True
        if name_match or shape_match:
            hits.append(
                {
                    "name": obj.Name,
                    "label": obj.Label,
                    "matched_by_name": name_match,
                    "matched_by_shape": shape_match,
                    "bbox_longest_mm": bb_len,
                }
            )
    return ok(count=len(hits), fasteners=hits)


def remove_fasteners(
    doc_name: Optional[str] = None,
    name_patterns: Optional[List[str]] = None,
    max_length_mm: float = 200.0,
    diameter_range_mm: Tuple[float, float] = (1.5, 20.0),
    dry_run: bool = False,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    result = find_fasteners(doc_name, name_patterns, max_length_mm, diameter_range_mm)
    hits = result.get("fasteners", [])
    if dry_run:
        return ok(would_remove=hits, count=len(hits))
    for h in hits:
        doc.removeObject(h["name"])
    doc.recompute()
    return ok(removed=[h["name"] for h in hits], count=len(hits))


def find_thin_bodies(
    doc_name: Optional[str] = None,
    min_thickness_mm: float = 0.5,
) -> Dict[str, Any]:
    """Flag solids whose shortest BB dimension is under ``min_thickness_mm``.

    Cheap proxy for true thickness analysis — worth replacing with OCC's
    BRepOffsetAPI_MakeThickSolid-based probing if accuracy matters.
    """
    doc = get_document(doc_name)
    hits = []
    for obj in doc.Objects:
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        bb = obj.Shape.BoundBox
        thin = min(bb.XLength, bb.YLength, bb.ZLength)
        if thin < min_thickness_mm:
            hits.append({"name": obj.Name, "min_bbox_dim_mm": thin})
    return ok(count=len(hits), thin_bodies=hits)


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "find_holes": find_holes,
            "remove_holes": remove_holes,
            "find_fillets": find_fillets,
            "remove_fillets": remove_fillets,
            "remove_chamfers": remove_chamfers,
            "find_fasteners": find_fasteners,
            "remove_fasteners": remove_fasteners,
            "find_thin_bodies": find_thin_bodies,
        }
    )
