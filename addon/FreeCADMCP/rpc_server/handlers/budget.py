"""Mass, centre-of-gravity, and moment-of-inertia budget tracker.

Rolls up per-object properties into aggregates, optionally grouped by a
label prefix or by a user-supplied grouping dict, using assigned-material
densities where present.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, ok, shape_center_of_mass


def mass_budget(
    doc_name: Optional[str] = None,
    default_density_kg_m3: Optional[float] = None,
    group_by_prefix: bool = False,
    grouping: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Return per-object and aggregate mass with weighted centre of gravity.

    If ``group_by_prefix`` is true, objects with a label like ``PCB_Top`` and
    ``PCB_Bottom`` are aggregated under ``PCB``. If ``grouping`` is given, it
    takes precedence — mapping group-name → list of object names.
    """
    doc = get_document(doc_name)
    rows: List[Dict[str, Any]] = []
    total_mass = 0.0
    weighted = FreeCAD.Vector(0, 0, 0)

    for obj in doc.Objects:
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        vol_m3 = float(obj.Shape.Volume) * 1e-9
        density = default_density_kg_m3
        material = None
        if "FreeCADMCP_Material" in obj.PropertiesList:
            meta = dict(obj.FreeCADMCP_Material)
            material = meta.get("name")
            try:
                density = float(meta.get("density_kg_m3", density))
            except (TypeError, ValueError):
                pass
        if density is None:
            rows.append({"name": obj.Name, "volume_m3": vol_m3, "mass_kg": None, "material": material})
            continue
        mass = vol_m3 * density
        cm = shape_center_of_mass(obj.Shape)
        rows.append(
            {
                "name": obj.Name,
                "label": obj.Label,
                "material": material,
                "volume_m3": vol_m3,
                "density_kg_m3": density,
                "mass_kg": mass,
                "cg_mm": {"x": cm.x, "y": cm.y, "z": cm.z},
            }
        )
        total_mass += mass
        weighted = weighted + FreeCAD.Vector(cm.x * mass, cm.y * mass, cm.z * mass)

    result: Dict[str, Any] = {
        "items": rows,
        "total_mass_kg": total_mass,
    }
    if total_mass > 0:
        cg = weighted.multiply(1.0 / total_mass)
        result["total_cg_mm"] = {"x": cg.x, "y": cg.y, "z": cg.z}

    groups = grouping or {}
    if group_by_prefix and not groups:
        groups = _auto_group_by_prefix(doc)
    if groups:
        group_rows = []
        for gname, members in groups.items():
            masses = [r["mass_kg"] for r in rows if r["name"] in members and r["mass_kg"]]
            group_rows.append({"group": gname, "member_count": len(members), "mass_kg": sum(masses)})
        result["groups"] = group_rows

    return ok(**result)


def _auto_group_by_prefix(doc) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {}
    for obj in doc.Objects:
        label = obj.Label
        prefix = label.split("_", 1)[0] if "_" in label else label
        groups.setdefault(prefix, []).append(obj.Name)
    return groups


def register(r: Dict[str, Any]) -> None:
    r.update({"mass_budget": mass_budget})
