"""Material assignment with a curated JSON library.

Materials are stored as a FreeCAD ``App::MaterialObject`` (when available)
plus a parallel ``App::PropertyMap`` named ``FreeCADMCP_Material`` on the
target object so the metadata round-trips through save/load regardless of
FreeCAD version.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, get_object, ok, err


_LIBRARY_PATH = Path(__file__).resolve().parent.parent.parent / "libs" / "materials.json"


def _load_library() -> Dict[str, Any]:
    return json.loads(_LIBRARY_PATH.read_text(encoding="utf-8"))


def list_materials() -> Dict[str, Any]:
    lib = _load_library()
    return ok(
        count=len(lib["materials"]),
        materials=sorted(lib["materials"].keys()),
        by_category=_group_by_category(lib),
    )


def _group_by_category(lib) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for name, data in lib["materials"].items():
        out.setdefault(data.get("category", "other"), []).append(name)
    return out


def get_material(material: str) -> Dict[str, Any]:
    lib = _load_library()
    data = lib["materials"].get(material)
    if data is None:
        return err(f"Unknown material '{material}'", known=sorted(lib["materials"]))
    return ok(name=material, **data)


def assign_material(
    obj_name: str,
    material: str,
    face: Optional[int] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    lib = _load_library()
    data = lib["materials"].get(material)
    if data is None:
        return err(f"Unknown material '{material}'", known=sorted(lib["materials"]))
    obj = get_object(doc_name, obj_name)

    tag_key = "FreeCADMCP_Material" if face is None else f"FreeCADMCP_Material_Face{face}"
    prop_name = tag_key
    if prop_name not in obj.PropertiesList:
        obj.addProperty("App::PropertyMap", prop_name, "MCP", "Material metadata")
    obj.setPropertyStatus(prop_name, "UserEdit")
    mapping = {"name": material}
    for k, v in data.items():
        mapping[k] = str(v)
    setattr(obj, prop_name, mapping)

    if face is None and hasattr(obj, "ViewObject"):
        try:
            obj.ViewObject.ShapeColor = _color_for(data)
        except Exception:
            pass

    return ok(object=obj_name, material=material, face=face)


def get_assigned_material(
    obj_name: str,
    face: Optional[int] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    key = "FreeCADMCP_Material" if face is None else f"FreeCADMCP_Material_Face{face}"
    if key not in obj.PropertiesList:
        return err(f"No material assigned to {obj_name}" + (f" face {face}" if face else ""))
    return ok(object=obj_name, face=face, material=dict(getattr(obj, key)))


def _color_for(data: Dict[str, Any]) -> tuple:
    cat = data.get("category", "")
    palette = {
        "metal": (0.75, 0.75, 0.78, 1.0),
        "composite": (0.30, 0.30, 0.30, 1.0),
        "polymer": (0.90, 0.70, 0.30, 1.0),
        "thermal_coating": (0.20, 0.20, 0.20, 1.0),
        "fluid": (0.40, 0.60, 0.95, 1.0),
        "semiconductor": (0.60, 0.40, 0.20, 1.0),
    }
    return palette.get(cat, (0.60, 0.60, 0.60, 1.0))


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "list_materials": list_materials,
            "get_material": get_material,
            "assign_material": assign_material,
            "get_assigned_material": get_assigned_material,
        }
    )
