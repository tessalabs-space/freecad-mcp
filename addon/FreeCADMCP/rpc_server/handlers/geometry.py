"""Primitives, booleans, and local feature ops (fillet / chamfer / draft /
thickness). Everything is done via the ``Part`` workbench so we stay in
pure BRep and avoid PartDesign body scoping unless explicitly asked for.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import FreeCAD
import Part

from ..utils import apply_placement, apply_properties, get_document, get_object, ok, err


_PRIMITIVES = {
    "box": "Part::Box",
    "cylinder": "Part::Cylinder",
    "sphere": "Part::Sphere",
    "cone": "Part::Cone",
    "torus": "Part::Torus",
    "plane": "Part::Plane",
    "wedge": "Part::Wedge",
    "ellipsoid": "Part::Ellipsoid",
    "prism": "Part::Prism",
}


def create_primitive(
    kind: str,
    name: str,
    properties: Optional[Dict[str, Any]] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    type_id = _PRIMITIVES.get(kind.lower())
    if type_id is None:
        return err(f"Unknown primitive kind '{kind}'", known=sorted(_PRIMITIVES))
    obj = doc.addObject(type_id, name)
    apply_properties(obj, properties)
    doc.recompute()
    return ok(name=obj.Name)


def boolean_op(
    op: str,
    bases: List[str],
    tools: List[str],
    name: Optional[str] = None,
    doc_name: Optional[str] = None,
    keep_inputs: bool = False,
) -> Dict[str, Any]:
    op = op.lower()
    doc = get_document(doc_name)
    type_map = {
        "fuse": "Part::MultiFuse",
        "union": "Part::MultiFuse",
        "cut": "Part::Cut",
        "difference": "Part::Cut",
        "common": "Part::MultiCommon",
        "intersection": "Part::MultiCommon",
    }
    tid = type_map.get(op)
    if tid is None:
        return err(f"Unknown boolean op '{op}'", known=sorted(set(type_map)))
    base_objs = [doc.getObject(n) for n in bases]
    tool_objs = [doc.getObject(n) for n in tools]
    if any(o is None for o in base_objs + tool_objs):
        return err("Unknown input object(s) in boolean")

    result_name = name or f"{op.capitalize()}"
    if tid == "Part::Cut":
        if len(base_objs) != 1:
            return err("cut requires exactly one base")
        obj = doc.addObject(tid, result_name)
        # Cut = Base - union(tools)
        if len(tool_objs) == 1:
            obj.Base = base_objs[0]
            obj.Tool = tool_objs[0]
        else:
            union = doc.addObject("Part::MultiFuse", f"{result_name}_tools")
            union.Shapes = tool_objs
            obj.Base = base_objs[0]
            obj.Tool = union
    else:
        obj = doc.addObject(tid, result_name)
        obj.Shapes = base_objs + tool_objs

    doc.recompute()
    if not keep_inputs:
        for o in base_objs + tool_objs:
            if o is not obj:
                o.ViewObject.Visibility = False
    return ok(name=obj.Name)


def fillet(
    obj_name: str,
    edges: List[int],
    radius: float,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    base = doc.getObject(obj_name)
    if base is None:
        return err(f"Object '{obj_name}' not found")
    fillet_obj = doc.addObject("Part::Fillet", name or f"{obj_name}_Fillet")
    fillet_obj.Base = base
    edge_specs = [(int(i), float(radius), float(radius)) for i in edges]
    fillet_obj.Edges = edge_specs
    doc.recompute()
    return ok(name=fillet_obj.Name, edges_filleted=len(edges))


def chamfer(
    obj_name: str,
    edges: List[int],
    size: float,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    base = doc.getObject(obj_name)
    if base is None:
        return err(f"Object '{obj_name}' not found")
    ch = doc.addObject("Part::Chamfer", name or f"{obj_name}_Chamfer")
    ch.Base = base
    ch.Edges = [(int(i), float(size), float(size)) for i in edges]
    doc.recompute()
    return ok(name=ch.Name, edges_chamfered=len(edges))


def thickness(
    obj_name: str,
    faces: List[int],
    value: float,
    mode: str = "Skin",
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    base = doc.getObject(obj_name)
    if base is None:
        return err(f"Object '{obj_name}' not found")
    thick = doc.addObject("Part::Thickness", name or f"{obj_name}_Shell")
    thick.Faces = (base, [f"Face{i}" for i in faces])
    thick.Value = float(value)
    thick.Mode = mode
    doc.recompute()
    return ok(name=thick.Name)


def draft(
    obj_name: str,
    faces: List[int],
    angle: float,
    neutral_plane: Optional[int] = None,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply a draft (taper) angle to the listed faces.

    FreeCAD lacks a first-class Part::Draft object; we call Part.makeOffset with
    a tapered profile per face. Returns the wrapper Part::Feature.
    """
    doc = get_document(doc_name)
    base = doc.getObject(obj_name)
    if base is None:
        return err(f"Object '{obj_name}' not found")
    shape = base.Shape.copy()
    # FreeCAD's OCC binding exposes makeDraft on TopoShape in some builds.
    if not hasattr(shape, "makeDraft"):
        return err("This FreeCAD build does not expose Shape.makeDraft; use MCP_execute_code for a manual implementation")
    face_refs = [shape.Faces[i - 1] for i in faces]
    plane = shape.Faces[neutral_plane - 1] if neutral_plane else face_refs[0]
    drafted = shape.makeDraft(
        face_refs,
        FreeCAD.Vector(0, 0, 1),
        float(angle),
        plane,
    )
    out = doc.addObject("Part::Feature", name or f"{obj_name}_Draft")
    out.Shape = drafted
    doc.recompute()
    return ok(name=out.Name)


def mirror(
    obj_name: str,
    base: Dict[str, float],
    normal: Dict[str, float],
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    source = doc.getObject(obj_name)
    if source is None:
        return err(f"Object '{obj_name}' not found")
    m = doc.addObject("Part::Mirroring", name or f"{obj_name}_Mirror")
    m.Source = source
    m.Base = FreeCAD.Vector(base.get("x", 0), base.get("y", 0), base.get("z", 0))
    m.Normal = FreeCAD.Vector(normal.get("x", 0), normal.get("y", 0), normal.get("z", 1))
    doc.recompute()
    return ok(name=m.Name)


def translate(
    obj_name: str,
    delta: Dict[str, float],
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    p = obj.Placement
    p.Base = p.Base + FreeCAD.Vector(
        float(delta.get("x", 0.0)),
        float(delta.get("y", 0.0)),
        float(delta.get("z", 0.0)),
    )
    obj.Placement = p
    return ok()


def rotate(
    obj_name: str,
    axis: Dict[str, float],
    angle: float,
    center: Optional[Dict[str, float]] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    obj = get_object(doc_name, obj_name)
    axis_v = FreeCAD.Vector(
        float(axis.get("x", 0.0)),
        float(axis.get("y", 0.0)),
        float(axis.get("z", 1.0)),
    )
    pivot = FreeCAD.Vector(
        float((center or {}).get("x", 0.0)),
        float((center or {}).get("y", 0.0)),
        float((center or {}).get("z", 0.0)),
    )
    rot = FreeCAD.Rotation(axis_v, float(angle))
    obj.Placement = FreeCAD.Placement(pivot, rot).multiply(obj.Placement)
    return ok()


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "create_primitive": create_primitive,
            "boolean_op": boolean_op,
            "fillet": fillet,
            "chamfer": chamfer,
            "thickness": thickness,
            "draft": draft,
            "mirror": mirror,
            "translate": translate,
            "rotate": rotate,
        }
    )
