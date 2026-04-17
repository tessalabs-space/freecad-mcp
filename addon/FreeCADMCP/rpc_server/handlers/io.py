"""Import / export handlers with tolerance reporting and unit audit.

Supported formats: STEP, IGES, STL, BREP, OBJ, FCStd. Round-trip tolerance
is computed by diffing bounding boxes between the source and reloaded
shape; better-than-nothing until we hook into OCC's GeomAPI_ProjectPointOnSurf
for true Hausdorff distance.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, ok, err


_IMPORT_BY_EXT = {
    ".step": "Import",
    ".stp": "Import",
    ".iges": "Import",
    ".igs": "Import",
    ".brep": "Part",
    ".stl": "Mesh",
    ".obj": "Mesh",
    ".fcstd": None,  # handled directly by FreeCAD.openDocument
}


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def import_file(path: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
    ext = _ext(path)
    if not os.path.exists(path):
        return err(f"File does not exist: {path}")
    if ext == ".fcstd":
        doc = FreeCAD.openDocument(path)
        return ok(doc=doc.Name, imported_objects=[o.Name for o in doc.Objects])

    doc = get_document(doc_name) if doc_name else (FreeCAD.ActiveDocument or FreeCAD.newDocument("Import"))
    before = set(o.Name for o in doc.Objects)

    if ext in (".step", ".stp", ".iges", ".igs"):
        import Import  # type: ignore
        Import.insert(path, doc.Name)
    elif ext == ".brep":
        import Part  # type: ignore
        shape = Part.Shape()
        shape.read(path)
        obj = doc.addObject("Part::Feature", os.path.splitext(os.path.basename(path))[0])
        obj.Shape = shape
    elif ext in (".stl", ".obj"):
        import Mesh  # type: ignore
        Mesh.insert(path, doc.Name)
    else:
        return err(f"Unsupported import extension '{ext}'")

    doc.recompute()
    new_objects = [o.Name for o in doc.Objects if o.Name not in before]
    units = doc.UnitSystem if hasattr(doc, "UnitSystem") else None
    return ok(doc=doc.Name, imported_objects=new_objects, units=str(units))


def export_file(
    path: str,
    object_names: Optional[List[str]] = None,
    doc_name: Optional[str] = None,
    tolerance_report: bool = False,
) -> Dict[str, Any]:
    ext = _ext(path)
    doc = get_document(doc_name)
    if object_names is None:
        object_names = [o.Name for o in doc.Objects]
    objs = [doc.getObject(n) for n in object_names]
    if any(o is None for o in objs):
        return err("Unknown object in export list")

    if ext == ".fcstd":
        doc.saveAs(path)
        return ok(path=path)

    if ext in (".step", ".stp", ".iges", ".igs"):
        import Import  # type: ignore
        Import.export(objs, path)
    elif ext == ".brep":
        import Part  # type: ignore
        combined = objs[0].Shape if len(objs) == 1 else _compound([o.Shape for o in objs])
        combined.exportBrep(path)
    elif ext in (".stl", ".obj"):
        import Mesh  # type: ignore
        Mesh.export(objs, path)
    else:
        return err(f"Unsupported export extension '{ext}'")

    result: Dict[str, Any] = {"path": path, "objects": object_names}
    if tolerance_report and ext in (".step", ".stp", ".iges", ".igs", ".brep"):
        result["tolerance_report"] = _roundtrip_report(objs, path)
    return ok(**result)


def _compound(shapes):
    import Part  # type: ignore
    return Part.makeCompound(shapes)


def _bbox(shape) -> Dict[str, float]:
    bb = shape.BoundBox
    return {
        "xmin": bb.XMin,
        "ymin": bb.YMin,
        "zmin": bb.ZMin,
        "xmax": bb.XMax,
        "ymax": bb.YMax,
        "zmax": bb.ZMax,
        "diag": bb.DiagonalLength,
    }


def _roundtrip_report(objs, path: str) -> Dict[str, Any]:
    """Import the exported file back and compare bounding boxes."""
    import Part  # type: ignore
    scratch = FreeCAD.newDocument("_roundtrip")
    try:
        ext = _ext(path)
        if ext == ".brep":
            shape = Part.Shape()
            shape.read(path)
        else:
            import Import  # type: ignore
            Import.insert(path, scratch.Name)
            shape = _compound([o.Shape for o in scratch.Objects if hasattr(o, "Shape")])
        reloaded_bb = _bbox(shape)
        original_bb = _bbox(_compound([o.Shape for o in objs]))
        diag_delta = abs(reloaded_bb["diag"] - original_bb["diag"])
        return {
            "original_bbox": original_bb,
            "reloaded_bbox": reloaded_bb,
            "bbox_diag_delta_mm": diag_delta,
        }
    finally:
        FreeCAD.closeDocument(scratch.Name)


def audit_units(doc_name: Optional[str] = None) -> Dict[str, Any]:
    doc = get_document(doc_name)
    schema = doc.UnitSystem if hasattr(doc, "UnitSystem") else "unknown"
    return ok(unit_system=str(schema), file_name=doc.FileName)


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "import_file": import_file,
            "export_file": export_file,
            "audit_units": audit_units,
        }
    )
