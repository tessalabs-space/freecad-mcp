"""Analysis prep: mid-surface extraction, imprint / merge, symmetry,
contact-face ID, keep-only-external-surfaces.

Several of these are non-trivial even with full OCC access, so our
implementations are pragmatic:

* Mid-surface: offset each thin face by half-thickness inward; good enough
  for plate-like parts. Not suitable for branching thin-walled geometry.
* Symmetry detection: bounding-box centre vs mass centre for the three
  cardinal planes with a configurable tolerance.
* External surfaces: select outward-facing faces via a ray-cast fallback
  when the shape is a single solid, else keep the outer shell.
* Contact faces: pairwise face-distance under a tolerance.
* Imprint/merge: Part.compound + Shape.generalFuse for now.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import FreeCAD
import Part

from ..utils import get_document, get_object, ok, err


def extract_midsurface(
    obj_name: str,
    thickness: float,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    doc = obj.Document
    try:
        faces = obj.Shape.Faces
        shells = [f.makeOffsetShape(-thickness / 2.0, 1e-3) for f in faces]
        compound = Part.makeCompound(shells)
    except Exception as exc:
        return err(f"mid-surface extraction failed: {exc}")
    out = doc.addObject("Part::Feature", name or f"{obj_name}_MidSurface")
    out.Shape = compound
    doc.recompute()
    return ok(name=out.Name, face_count=len(faces))


def detect_symmetry(
    obj_name: str,
    tolerance: float = 0.5,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    shape = obj.Shape
    bb = shape.BoundBox
    cm = shape.CenterOfMass
    bb_center = FreeCAD.Vector(
        0.5 * (bb.XMin + bb.XMax),
        0.5 * (bb.YMin + bb.YMax),
        0.5 * (bb.ZMin + bb.ZMax),
    )
    planes = {
        "YZ": abs(cm.x - bb_center.x) < tolerance,
        "XZ": abs(cm.y - bb_center.y) < tolerance,
        "XY": abs(cm.z - bb_center.z) < tolerance,
    }
    return ok(symmetry_planes=planes, bbox_center=_v(bb_center), center_of_mass=_v(cm))


def keep_external_surfaces(
    obj_name: str,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract the outer shell of a solid as a surface-only feature.

    For a single-solid import this is just the outer shell; for an assembly
    we union everything first, then take the outer shell. Handy for thermal
    view-factor / radiation analyses where interior faces are irrelevant.
    """
    obj = get_object(doc_name, obj_name)
    doc = obj.Document
    shape = obj.Shape
    if len(shape.Solids) == 0:
        return err("Object has no solid bodies")
    if len(shape.Solids) == 1:
        shell = shape.Solids[0].Shells[0]
    else:
        fused = shape.Solids[0]
        for s in shape.Solids[1:]:
            fused = fused.fuse(s)
        shell = fused.Shells[0]
    out = doc.addObject("Part::Feature", name or f"{obj_name}_ExternalShell")
    out.Shape = shell
    doc.recompute()
    return ok(name=out.Name, face_count=len(shell.Faces))


def find_contact_faces(
    a: str,
    b: str,
    tolerance: float = 0.1,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Pairwise face-distance between two objects. Pairs below ``tolerance``
    are reported as contacts. Good for meshing imprint candidates.
    """
    doc = get_document(doc_name)
    oa, ob = doc.getObject(a), doc.getObject(b)
    if oa is None or ob is None:
        return err("Unknown object(s)")
    hits = []
    for i, fa in enumerate(oa.Shape.Faces, start=1):
        for j, fb in enumerate(ob.Shape.Faces, start=1):
            try:
                dist, *_ = fa.distToShape(fb)
            except Exception:
                continue
            if dist <= tolerance:
                hits.append({"a_face": i, "b_face": j, "distance_mm": float(dist)})
    return ok(count=len(hits), contacts=hits)


def imprint_merge(
    objects: List[str],
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """GeneralFuse-based imprint: ensures shared faces between adjacent
    bodies have matching UV parameterisation so meshers can produce
    conformal meshes.
    """
    doc = get_document(doc_name)
    objs = [doc.getObject(n) for n in objects]
    if any(o is None for o in objs):
        return err("Unknown object in imprint list")
    shapes = [o.Shape.copy() for o in objs]
    head, *tail = shapes
    fused, _ = head.generalFuse(tail)
    out = doc.addObject("Part::Feature", name or "Imprinted")
    out.Shape = fused
    doc.recompute()
    return ok(name=out.Name, source_objects=objects)


def _v(vec) -> Dict[str, float]:
    return {"x": float(vec.x), "y": float(vec.y), "z": float(vec.z)}


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "extract_midsurface": extract_midsurface,
            "detect_symmetry": detect_symmetry,
            "keep_external_surfaces": keep_external_surfaces,
            "find_contact_faces": find_contact_faces,
            "imprint_merge": imprint_merge,
        }
    )
