"""Parametric sweep runner.

Iterate a property through a list of values, recompute the document at
each step, and optionally capture exports / mass / screenshots per
configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, get_object, ok, err


def parametric_sweep(
    obj_name: str,
    property_name: str,
    values: List[float],
    doc_name: Optional[str] = None,
    export_dir: Optional[str] = None,
    export_format: str = "step",
    capture_mass: bool = True,
    capture_screenshot: bool = False,
) -> Dict[str, Any]:
    """Set ``obj.property_name`` to each value, recompute, and record a row.

    Exported files are named ``<obj_name>_<property>_<value>.<ext>``.
    """
    obj = get_object(doc_name, obj_name)
    doc = obj.Document
    if property_name not in obj.PropertiesList:
        return err(f"{obj_name} has no property '{property_name}'", available=list(obj.PropertiesList))

    out = Path(export_dir) if export_dir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    original = getattr(obj, property_name)
    try:
        for value in values:
            setattr(obj, property_name, value)
            doc.recompute()
            row: Dict[str, Any] = {"value": value}
            if capture_mass and hasattr(obj, "Shape"):
                try:
                    row["volume_mm3"] = float(obj.Shape.Volume)
                    row["surface_area_mm2"] = float(obj.Shape.Area)
                except Exception:
                    pass
            if out:
                fname = f"{obj_name}_{property_name}_{value}".replace(".", "p")
                path = out / f"{fname}.{export_format}"
                _export_single(obj, str(path), export_format)
                row["path"] = str(path)
            if capture_screenshot:
                import FreeCADGui
                view = FreeCADGui.ActiveDocument.ActiveView if FreeCADGui.ActiveDocument else None
                if view and out:
                    shot = out / f"{fname}.png"
                    view.saveImage(str(shot), 1200, 800, "Current")
                    row["screenshot"] = str(shot)
            rows.append(row)
    finally:
        setattr(obj, property_name, original)
        doc.recompute()
    return ok(rows=rows, property=property_name, object=obj_name)


def spreadsheet_sweep(
    spreadsheet_name: str,
    cell: str,
    values: List[float],
    doc_name: Optional[str] = None,
    export_dir: Optional[str] = None,
    export_format: str = "step",
) -> Dict[str, Any]:
    """Sweep a Spreadsheet cell that drives other objects via expressions.

    Use this when the parameter feeds several sketches / bodies through
    FreeCAD expression bindings — one cell, many dependents.
    """
    doc = get_document(doc_name)
    sheet = doc.getObject(spreadsheet_name)
    if sheet is None:
        return err(f"Spreadsheet '{spreadsheet_name}' not found")
    out = Path(export_dir) if export_dir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    original = sheet.getContents(cell)
    try:
        for value in values:
            sheet.set(cell, str(value))
            doc.recompute()
            row: Dict[str, Any] = {"value": value, "cell": cell}
            if out:
                path = out / f"{spreadsheet_name}_{cell}_{value}".replace(".", "p")
                path = path.with_suffix(f".{export_format}")
                _export_document(doc, str(path), export_format)
                row["path"] = str(path)
            rows.append(row)
    finally:
        sheet.set(cell, str(original))
        doc.recompute()
    return ok(rows=rows)


def _export_single(obj, path: str, fmt: str) -> None:
    if fmt in ("step", "stp", "iges", "igs"):
        import Import  # type: ignore
        Import.export([obj], path)
    elif fmt == "stl":
        import Mesh  # type: ignore
        Mesh.export([obj], path)
    elif fmt == "brep":
        obj.Shape.exportBrep(path)
    else:
        raise ValueError(f"Unsupported format '{fmt}'")


def _export_document(doc, path: str, fmt: str) -> None:
    objects = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
    if fmt in ("step", "stp", "iges", "igs"):
        import Import  # type: ignore
        Import.export(objects, path)
    elif fmt == "stl":
        import Mesh  # type: ignore
        Mesh.export(objects, path)
    else:
        raise ValueError(f"Unsupported document-wide format '{fmt}'")


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "parametric_sweep": parametric_sweep,
            "spreadsheet_sweep": spreadsheet_sweep,
        }
    )
