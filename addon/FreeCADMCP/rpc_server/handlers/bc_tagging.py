"""Boundary-condition face tagging.

Group faces on an object under a named tag (``inlet``, ``outlet``, ``wall``,
``radiator``, ``fixture``, ``load``, custom) and persist the mapping via an
``App::PropertyMap`` on the object. Tags are read back by the solver
exporters (Elmer / OpenFOAM / CalculiX) and the Blender bridge.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..utils import get_object, ok, err


_STANDARD_TAGS = {
    "inlet", "outlet", "wall", "symmetry", "radiator", "heat_source", "heat_sink",
    "fixture", "load", "contact", "interface", "free_surface", "periodic",
}


def _tag_property(obj):
    if "FreeCADMCP_BCTags" not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", "FreeCADMCP_BCTags", "MCP", "BC tag JSON")
        obj.FreeCADMCP_BCTags = "{}"
    return json.loads(obj.FreeCADMCP_BCTags)


def _write_tags(obj, tags: Dict[str, List[int]]) -> None:
    obj.FreeCADMCP_BCTags = json.dumps(tags)


def list_tags(obj_name: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    tags = _tag_property(obj)
    return ok(object=obj_name, tags=tags, standard=sorted(_STANDARD_TAGS))


def tag_faces(
    obj_name: str,
    tag: str,
    faces: List[int],
    doc_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    tags = _tag_property(obj)
    key = tag if tag in _STANDARD_TAGS else f"custom:{tag}"
    existing = set(tags.get(key, []))
    existing.update(int(f) for f in faces)
    tags[key] = sorted(existing)
    if metadata:
        tags[f"{key}__meta"] = metadata
    _write_tags(obj, tags)
    return ok(tag=key, faces=tags[key])


def untag_faces(
    obj_name: str,
    tag: str,
    faces: Optional[List[int]] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    tags = _tag_property(obj)
    key = tag if tag in tags else f"custom:{tag}"
    if key not in tags:
        return err(f"Tag '{tag}' not found on {obj_name}")
    if faces is None:
        tags.pop(key, None)
        tags.pop(f"{key}__meta", None)
    else:
        remaining = [f for f in tags[key] if f not in set(int(x) for x in faces)]
        tags[key] = remaining
    _write_tags(obj, tags)
    return ok(remaining=tags.get(key, []))


def tag_boundary_by_normal(
    obj_name: str,
    tag: str,
    direction: Dict[str, float],
    tolerance_deg: float = 15.0,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Auto-tag all faces whose outward normal is within ``tolerance_deg``
    of ``direction``. Handy for marking ``top`` / ``bottom`` / ``+Y wall``
    without picking faces manually.
    """
    import math
    import FreeCAD

    obj = get_object(doc_name, obj_name)
    target = FreeCAD.Vector(
        float(direction.get("x", 0)),
        float(direction.get("y", 0)),
        float(direction.get("z", 1)),
    )
    if target.Length == 0:
        return err("direction must be non-zero")
    target.normalize()
    picked: List[int] = []
    cos_tol = math.cos(math.radians(tolerance_deg))
    for idx, face in enumerate(obj.Shape.Faces, start=1):
        try:
            u0, u1, v0, v1 = face.ParameterRange
            n = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
            n.normalize()
            if n.dot(target) >= cos_tol:
                picked.append(idx)
        except Exception:
            continue
    if not picked:
        return ok(tag=tag, faces=[], note="no faces within tolerance")
    return tag_faces(obj_name, tag, picked, doc_name)


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "list_bc_tags": list_tags,
            "tag_faces": tag_faces,
            "untag_faces": untag_faces,
            "tag_boundary_by_normal": tag_boundary_by_normal,
        }
    )
