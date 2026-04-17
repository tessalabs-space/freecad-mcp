"""Document-level RPC handlers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, ok, err


def create_document(name: str) -> Dict[str, Any]:
    doc = FreeCAD.newDocument(name)
    return ok(name=doc.Name, label=doc.Label)


def list_documents() -> Dict[str, Any]:
    return ok(documents=list(FreeCAD.listDocuments().keys()))


def open_document(path: str) -> Dict[str, Any]:
    doc = FreeCAD.openDocument(path)
    return ok(name=doc.Name)


def save_document(doc_name: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
    doc = get_document(doc_name)
    if path:
        doc.saveAs(path)
    else:
        doc.save()
    return ok(name=doc.Name, path=doc.FileName)


def close_document(doc_name: str) -> Dict[str, Any]:
    if doc_name not in FreeCAD.listDocuments():
        return err(f"Document '{doc_name}' not found")
    FreeCAD.closeDocument(doc_name)
    return ok()


def recompute(doc_name: Optional[str] = None) -> Dict[str, Any]:
    doc = get_document(doc_name)
    doc.recompute()
    return ok()


def get_objects(doc_name: Optional[str] = None) -> Dict[str, Any]:
    doc = get_document(doc_name)
    entries: List[Dict[str, Any]] = []
    for obj in doc.Objects:
        entries.append(
            {
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId,
                "visible": bool(obj.ViewObject.Visibility) if obj.ViewObject else None,
            }
        )
    return ok(objects=entries)


def get_object(obj_name: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
    doc = get_document(doc_name)
    obj = doc.getObject(obj_name)
    if obj is None:
        return err(f"Object '{obj_name}' not found")
    props: Dict[str, Any] = {}
    for prop in obj.PropertiesList:
        try:
            val = getattr(obj, prop)
            props[prop] = _jsonify(val)
        except Exception:
            continue
    return ok(name=obj.Name, type=obj.TypeId, label=obj.Label, properties=props)


def delete_object(obj_name: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
    doc = get_document(doc_name)
    if doc.getObject(obj_name) is None:
        return err(f"Object '{obj_name}' not found")
    doc.removeObject(obj_name)
    doc.recompute()
    return ok()


def rename_object(
    obj_name: str,
    new_label: str,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Set an object's Label. Name (internal id) is immutable in FreeCAD;
    Label is the user-facing string shown in the tree and in assemblies.
    FreeCAD auto-suffixes duplicates (``Bracket001``) so we just read back
    the final Label.
    """
    doc = get_document(doc_name)
    obj = doc.getObject(obj_name)
    if obj is None:
        return err(f"Object '{obj_name}' not found")
    old_label = obj.Label
    obj.Label = str(new_label)
    doc.recompute()
    return ok(name=obj.Name, old_label=old_label, label=obj.Label)


def rename_objects(
    renames: List[Dict[str, str]],
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Batch rename. ``renames`` is a list of ``{name, label}`` dicts.

    Useful after importing a STEP file where OCC generates opaque labels
    like ``Solid`` / ``Solid001`` and you want one round-trip to fix them.
    """
    doc = get_document(doc_name)
    results: List[Dict[str, Any]] = []
    for entry in renames or []:
        nm = entry.get("name")
        lbl = entry.get("label")
        if not nm or lbl is None:
            results.append({"name": nm, "success": False, "error": "missing name or label"})
            continue
        obj = doc.getObject(nm)
        if obj is None:
            results.append({"name": nm, "success": False, "error": "not found"})
            continue
        old = obj.Label
        obj.Label = str(lbl)
        results.append({"name": nm, "old_label": old, "label": obj.Label, "success": True})
    doc.recompute()
    return ok(renamed=results, count=sum(1 for r in results if r.get("success")))


def _jsonify(value: Any) -> Any:
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    try:
        return str(value)
    except Exception:
        return None


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "create_document": create_document,
            "list_documents": list_documents,
            "open_document": open_document,
            "save_document": save_document,
            "close_document": close_document,
            "recompute": recompute,
            "get_objects": get_objects,
            "get_object": get_object,
            "delete_object": delete_object,
            "rename_object": rename_object,
            "rename_objects": rename_objects,
        }
    )
