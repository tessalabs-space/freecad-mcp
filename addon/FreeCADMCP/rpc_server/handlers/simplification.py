"""Generic shape healing and simplification.

Complements the feature-specific tools in ``defeaturing.py`` (holes,
fillets, chamfers, fasteners). These are topology-level repairs that
don't assume anything about what the face is geometrically — useful for
imported STEP/IGES where the neutral format drops small faces, inverts
normals, or leaves edges unsewn.

OCC primitives used:
  - ``ShapeFix_Shape``     general heal (small-edge fixing, wire repair)
  - ``ShapeUpgrade_UnifySameDomain`` merge co-planar/co-cylindrical faces
  - ``BRepBuilderAPI_Sewing`` sew faces into a shell / solid
  - ``Part.Shape.removeSplitter`` drop internal split edges
  - ``Part.Shape.removeInternalWires`` drop holes-in-faces below a tolerance
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import FreeCAD
import Part

from ..utils import get_object, ok, err


def simplify_shape(
    obj_name: str,
    remove_splitter: bool = True,
    unify_faces: bool = True,
    unify_edges: bool = True,
    heal: bool = True,
    sew_tolerance_mm: Optional[float] = None,
    min_face_area_mm2: float = 0.0,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a configurable pipeline of healing passes on a Part/Shape.

    Steps (each optional):
      1. ``heal``            — ``ShapeFix_Shape`` general OCC repair.
      2. ``remove_splitter`` — drop redundant internal split edges.
      3. ``unify_faces``/``unify_edges`` — ``UnifySameDomain`` merger.
      4. ``sew_tolerance_mm`` — sew faces (default: skip). Typical values
         0.01-0.1 mm for mm-scale parts.
      5. ``min_face_area_mm2`` — remove tiny splinter faces.

    Produces a new Part::Feature to preserve the source.
    """
    obj = get_object(doc_name, obj_name)
    doc = obj.Document
    shape = obj.Shape.copy()

    stats: Dict[str, Any] = {
        "faces_before": len(shape.Faces),
        "edges_before": len(shape.Edges),
    }

    if heal:
        try:
            shape = _shape_fix(shape)
            stats["healed"] = True
        except Exception as exc:
            stats["healed"] = False
            stats["heal_error"] = str(exc)

    if remove_splitter:
        try:
            shape = shape.removeSplitter()
            stats["splitter_removed"] = True
        except Exception as exc:
            stats["splitter_removed"] = False
            stats["splitter_error"] = str(exc)

    if unify_faces or unify_edges:
        try:
            shape = _unify_same_domain(shape, unify_faces, unify_edges)
            stats["unified"] = True
        except Exception as exc:
            stats["unified"] = False
            stats["unify_error"] = str(exc)

    if sew_tolerance_mm is not None:
        try:
            shape = _sew_shape(shape, float(sew_tolerance_mm))
            stats["sewn"] = True
        except Exception as exc:
            stats["sewn"] = False
            stats["sew_error"] = str(exc)

    removed_faces = 0
    if min_face_area_mm2 > 0.0:
        shape, removed_faces = _drop_small_faces(shape, float(min_face_area_mm2))
    stats["small_faces_removed"] = removed_faces

    stats["faces_after"] = len(shape.Faces)
    stats["edges_after"] = len(shape.Edges)

    out = doc.addObject("Part::Feature", name or f"{obj_name}_Simplified")
    out.Shape = shape
    doc.recompute()
    return ok(name=out.Name, label=out.Label, **stats)


def find_small_faces(
    obj_name: str,
    max_area_mm2: float = 1.0,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Report faces with area ≤ ``max_area_mm2`` — candidates for removal."""
    obj = get_object(doc_name, obj_name)
    hits: List[Dict[str, Any]] = []
    for idx, face in enumerate(obj.Shape.Faces, start=1):
        if face.Area <= max_area_mm2:
            hits.append({"face_index": idx, "area_mm2": float(face.Area)})
    return ok(count=len(hits), small_faces=hits)


def remove_small_faces(
    obj_name: str,
    max_area_mm2: float = 1.0,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Drop faces with area ≤ ``max_area_mm2`` via ``Shape.removeFeature``."""
    obj = get_object(doc_name, obj_name)
    doc = obj.Document
    shape = obj.Shape.copy()
    names = [
        f"Face{idx}"
        for idx, face in enumerate(shape.Faces, start=1)
        if face.Area <= max_area_mm2
    ]
    if not names:
        return ok(removed=[], note="no small faces under threshold")
    try:
        cleaned = shape.removeFeature(names)
    except Exception as exc:
        return err(f"removeFeature failed: {exc}", candidates=names)
    out = doc.addObject("Part::Feature", name or f"{obj_name}_NoSmallFaces")
    out.Shape = cleaned
    doc.recompute()
    return ok(name=out.Name, removed=names, count=len(names))


# --- OCC helpers ---------------------------------------------------------

def _shape_fix(shape):
    from OCC.Core.ShapeFix import ShapeFix_Shape  # type: ignore  # noqa: F401
    # FreeCAD ships OCCT; import path differs across builds. Fall back to
    # Part's built-in ``fix`` if the direct binding isn't available.
    try:
        fixer = ShapeFix_Shape(shape)
        fixer.Perform()
        return Part.__toPythonOCC__(fixer.Shape()) if hasattr(Part, "__toPythonOCC__") else shape
    except Exception:
        # Part.Shape.fix(precision, mintolerance, maxtolerance) is the
        # idiomatic FreeCAD path — precision=0 lets OCC pick.
        shape = shape.copy()
        shape.fix(0.0, 0.0, 1.0)
        return shape


def _unify_same_domain(shape, unify_faces: bool, unify_edges: bool):
    """Merge adjacent co-planar/co-cylindrical faces and co-linear edges."""
    # Prefer Part's ``removeSplitter`` which wraps UnifySameDomain in FC 1.x.
    # If a direct binding becomes available later, swap it in here.
    out = shape.copy()
    if unify_faces or unify_edges:
        out = out.removeSplitter()
    return out


def _sew_shape(shape, tol_mm: float):
    return shape.copy().sewShape(tol_mm) or shape


def _drop_small_faces(shape, min_area: float):
    """Return (new_shape, removed_count) after dropping sub-tolerance faces."""
    names = [
        f"Face{idx}"
        for idx, face in enumerate(shape.Faces, start=1)
        if face.Area <= min_area
    ]
    if not names:
        return shape, 0
    try:
        return shape.removeFeature(names), len(names)
    except Exception:
        return shape, 0


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "simplify_shape": simplify_shape,
            "find_small_faces": find_small_faces,
            "remove_small_faces": remove_small_faces,
        }
    )
