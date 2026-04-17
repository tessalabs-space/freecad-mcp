"""Structural diff between two FreeCAD documents.

Compares object sets, typed properties, assigned materials, BC tags, and
bounding-box-level geometry changes. Does not do per-triangle mesh diff —
the output is a decision-making summary, not a patch.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import FreeCAD

from ..utils import ok, err


_SNAPSHOT_TAG = "FreeCADMCP"


def compare_documents(a_path: str, b_path: str) -> Dict[str, Any]:
    snap_a = _snapshot(a_path)
    snap_b = _snapshot(b_path)

    names_a = {o["name"] for o in snap_a["objects"]}
    names_b = {o["name"] for o in snap_b["objects"]}

    added = sorted(names_b - names_a)
    removed = sorted(names_a - names_b)
    common = names_a & names_b

    changes: List[Dict[str, Any]] = []
    a_by_name = {o["name"]: o for o in snap_a["objects"]}
    b_by_name = {o["name"]: o for o in snap_b["objects"]}
    for name in sorted(common):
        diff = _diff_object(a_by_name[name], b_by_name[name])
        if diff:
            changes.append({"name": name, **diff})
    return ok(
        a_path=a_path,
        b_path=b_path,
        objects_added=added,
        objects_removed=removed,
        objects_changed=changes,
    )


def _snapshot(path: str) -> Dict[str, Any]:
    doc = FreeCAD.openDocument(path, True)  # hidden
    objects = []
    try:
        for obj in doc.Objects:
            entry: Dict[str, Any] = {"name": obj.Name, "type": obj.TypeId, "label": obj.Label}
            if hasattr(obj, "Shape") and not obj.Shape.isNull():
                bb = obj.Shape.BoundBox
                entry["volume_mm3"] = float(obj.Shape.Volume)
                entry["area_mm2"] = float(obj.Shape.Area)
                entry["bbox"] = {
                    "xmin": bb.XMin, "ymin": bb.YMin, "zmin": bb.ZMin,
                    "xmax": bb.XMax, "ymax": bb.YMax, "zmax": bb.ZMax,
                }
            if "FreeCADMCP_Material" in obj.PropertiesList:
                entry["material"] = dict(obj.FreeCADMCP_Material)
            if "FreeCADMCP_BCTags" in obj.PropertiesList:
                entry["bc_tags"] = json.loads(obj.FreeCADMCP_BCTags)
            objects.append(entry)
    finally:
        FreeCAD.closeDocument(doc.Name)
    return {"path": path, "objects": objects}


def _diff_object(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    changes: Dict[str, Any] = {}
    if a.get("type") != b.get("type"):
        changes["type"] = {"before": a.get("type"), "after": b.get("type")}
    for key in ("volume_mm3", "area_mm2"):
        if a.get(key) is None or b.get(key) is None:
            continue
        delta = b[key] - a[key]
        if abs(delta) > 1e-3:
            changes[key] = {"before": a[key], "after": b[key], "delta": delta}
    bb_a, bb_b = a.get("bbox"), b.get("bbox")
    if bb_a and bb_b:
        for axis in ("xmin", "ymin", "zmin", "xmax", "ymax", "zmax"):
            d = bb_b[axis] - bb_a[axis]
            if abs(d) > 1e-3:
                changes.setdefault("bbox_shift", {})[axis] = d
    if a.get("material") != b.get("material"):
        changes["material"] = {"before": a.get("material"), "after": b.get("material")}
    if a.get("bc_tags") != b.get("bc_tags"):
        changes["bc_tags"] = {"before": a.get("bc_tags"), "after": b.get("bc_tags")}
    return changes


def register(r: Dict[str, Any]) -> None:
    r.update({"compare_documents": compare_documents})
