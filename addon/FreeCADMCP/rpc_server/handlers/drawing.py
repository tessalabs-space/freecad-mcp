"""TechDraw integration.

Two levels of API:

* Low-level: ``create_drawing_page`` + ``add_drawing_view`` +
  ``add_drawing_dimension`` for bespoke layouts.
* High-level: ``create_manufacturing_drawing`` produces a one-shot
  sheet with a proper third-angle projection group (Front + Top +
  Right, laid out by TechDraw itself — no more overlapping views),
  an optional isometric, auto-computed scale, title-block fields,
  overall extent dimensions, and a PDF export.
"""

from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, get_object, ok, err


# --- templates -------------------------------------------------------------

_TEMPLATE_CANDIDATES = {
    "A4_Landscape": ["A4_LandscapeTD.svg", "A4_Landscape_ISO7200TD.svg", "A4_LandscapeTD_EN.svg"],
    "A3_Landscape": ["A3_LandscapeTD.svg", "A3_Landscape_ISO7200TD.svg"],
    "A2_Landscape": ["A2_LandscapeTD.svg"],
    "A4_Portrait":  ["A4_PortraitTD.svg"],
    "A3_Portrait":  ["A3_PortraitTD.svg"],
}


def _find_template(name_or_path: Optional[str]) -> Optional[str]:
    if name_or_path and os.path.exists(name_or_path):
        return name_or_path
    resource = FreeCAD.getResourceDir()
    tdir = os.path.join(resource, "Mod", "TechDraw", "Templates")
    if not os.path.isdir(tdir):
        return None
    if name_or_path in _TEMPLATE_CANDIDATES:
        for fname in _TEMPLATE_CANDIDATES[name_or_path]:
            p = os.path.join(tdir, fname)
            if os.path.exists(p):
                return p
    for fname in _TEMPLATE_CANDIDATES["A3_Landscape"] + _TEMPLATE_CANDIDATES["A4_Landscape"]:
        p = os.path.join(tdir, fname)
        if os.path.exists(p):
            return p
    return None


def _sheet_dims_mm(template_path: str) -> tuple:
    """Best-effort sheet dimensions from the template name."""
    name = os.path.basename(template_path).lower()
    if "a2" in name:
        return (594, 420)
    if "a3" in name:
        return (420, 297)
    if "a4" in name:
        return (297, 210)
    return (420, 297)


# --- low-level primitives --------------------------------------------------


_VIEW_DIRECTIONS = {
    "Front":  (0, -1, 0),
    "Back":   (0,  1, 0),
    "Top":    (0,  0, 1),
    "Bottom": (0,  0,-1),
    "Right":  (1,  0, 0),
    "Left":   (-1, 0, 0),
    "Iso":    (1, -1, 1),
    "TrueIso": (1, -1, 1),
}


def create_drawing_page(
    template_path: Optional[str] = None,
    sheet: Optional[str] = None,
    name: Optional[str] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    try:
        import TechDraw  # noqa: F401
    except Exception as exc:
        return err(f"TechDraw workbench unavailable: {exc}")
    tpl = _find_template(template_path or sheet)
    if tpl is None:
        return err("No TechDraw template found", hint="pass template_path or set sheet to A3_Landscape / A4_Landscape")
    template = doc.addObject("TechDraw::DrawSVGTemplate", (name or "Page") + "_tmpl")
    template.Template = tpl
    page = doc.addObject("TechDraw::DrawPage", name or "Page")
    page.Template = template
    doc.recompute()
    return ok(page=page.Name, template=template.Name, template_path=tpl)


def add_drawing_view(
    page_name: str,
    source_objects: List[str],
    view_type: str = "Front",
    position: Optional[Dict[str, float]] = None,
    scale: float = 0.5,
    show_hidden: bool = False,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    page = doc.getObject(page_name)
    if page is None:
        return err(f"Page '{page_name}' not found")
    dir_vec = _VIEW_DIRECTIONS.get(view_type)
    if dir_vec is None:
        return err(f"Unknown view '{view_type}'", known=sorted(_VIEW_DIRECTIONS))
    sources = [doc.getObject(n) for n in source_objects]
    if any(s is None for s in sources):
        return err("Unknown source object in view list")
    view = doc.addObject("TechDraw::DrawViewPart", f"{page_name}_{view_type}")
    view.Source = sources
    view.Direction = FreeCAD.Vector(*dir_vec)
    view.Scale = float(scale)
    if show_hidden:
        view.HardHidden = True
        view.SmoothHidden = True
    if position:
        view.X = float(position.get("x", position.get("X", 150)))
        view.Y = float(position.get("y", position.get("Y", 130)))
    else:
        sheet_w, sheet_h = _sheet_dims_mm(page.Template.Template)
        view.X = sheet_w * 0.5
        view.Y = sheet_h * 0.5
    page.addView(view)
    doc.recompute()
    return ok(view=view.Name)


def add_drawing_dimension(
    view_name: str,
    kind: str,
    refs: List[Dict[str, Any]],
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    view = doc.getObject(view_name)
    if view is None:
        return err(f"View '{view_name}' not found")
    dim = doc.addObject("TechDraw::DrawViewDimension", f"{view_name}_dim_{kind}")
    dim.Type = kind
    dim.References2D = [(view, r["subname"]) for r in refs]
    doc.recompute()
    return ok(dimension=dim.Name)


def export_drawing_pdf(page_name: str, path: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
    doc = get_document(doc_name)
    page = doc.getObject(page_name)
    if page is None:
        return err(f"Page '{page_name}' not found")
    try:
        import TechDrawGui  # type: ignore
        TechDrawGui.exportPageAsPdf(page, path)
    except Exception as exc:
        return err(f"PDF export failed: {exc}")
    return ok(path=path)


def export_drawing_svg(page_name: str, path: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
    doc = get_document(doc_name)
    page = doc.getObject(page_name)
    if page is None:
        return err(f"Page '{page_name}' not found")
    try:
        import TechDrawGui  # type: ignore
        TechDrawGui.exportPageAsSvg(page, path)
    except Exception as exc:
        return err(f"SVG export failed: {exc}")
    return ok(path=path)


# --- projection group ------------------------------------------------------


def create_projection_group(
    page_name: str,
    source_objects: List[str],
    projections: Optional[List[str]] = None,
    scale: Optional[float] = None,
    position: Optional[Dict[str, float]] = None,
    name: Optional[str] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a proper third-angle projection group to a page.

    TechDraw handles the relative positioning of Front / Top / Right
    internally — no overlap, no manual X/Y juggling. ``scale`` is None
    -> automatic (``ScaleType = Page``); pass a value for a fixed scale.

    ``projections`` is the list of supplementary projections added
    around the anchor Front view. Valid: Top, Bottom, Left, Right,
    Rear, FrontTopLeft, FrontTopRight, FrontBottomLeft, FrontBottomRight.
    """
    doc = get_document(doc_name)
    page = doc.getObject(page_name)
    if page is None:
        return err(f"Page '{page_name}' not found")
    sources = [doc.getObject(n) for n in source_objects]
    if any(s is None for s in sources):
        return err("Unknown source object")

    pg = doc.addObject("TechDraw::DrawProjGroup", name or "ProjGroup")
    page.addView(pg)
    pg.Source = sources
    if scale:
        pg.ScaleType = "Custom"
        pg.Scale = float(scale)
    else:
        pg.ScaleType = "Page"
    pg.addProjection("Front")
    try:
        pg.Anchor = pg.getItemByLabel("Front")
    except Exception:
        pass
    for p in (projections or ["Top", "Right"]):
        if p == "Front":
            continue
        try:
            pg.addProjection(p)
        except Exception as exc:
            FreeCAD.Console.PrintWarning(f"projection {p}: {exc}\n")
    if position:
        pg.X = float(position.get("x", position.get("X", 150)))
        pg.Y = float(position.get("y", position.get("Y", 130)))
    else:
        sheet_w, sheet_h = _sheet_dims_mm(page.Template.Template)
        pg.X = sheet_w * 0.45
        pg.Y = sheet_h * 0.5
    doc.recompute()
    return ok(projection_group=pg.Name, members=[v.Name for v in pg.Views])


# --- high-level manufacturing drawing -------------------------------------


_STANDARD_SCALES = (10.0, 5.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01)


def _auto_scale(bbox_diag_mm: float, sheet_w_mm: int, sheet_h_mm: int) -> float:
    """Pick a standard scale so a projection group fits in ~60% of the
    short sheet dimension."""
    target = min(sheet_w_mm, sheet_h_mm) * 0.6
    ratio = target / max(bbox_diag_mm, 1e-6)
    for s in _STANDARD_SCALES:
        if s <= ratio:
            return s
    return _STANDARD_SCALES[-1]


def _format_scale(s: float) -> str:
    if s >= 1:
        return f"{int(s) if s.is_integer() else s}:1"
    inv = 1.0 / s
    return f"1:{int(inv) if inv.is_integer() else round(inv, 2)}"


def _set_template_fields(template, fields: Dict[str, str]) -> None:
    try:
        current = dict(template.EditableTexts)
    except Exception:
        return
    for key, val in fields.items():
        if not val:
            continue
        if key in current:
            current[key] = str(val)
        else:
            for k in list(current.keys()):
                if k.lower() == key.lower():
                    current[k] = str(val)
                    break
    try:
        template.EditableTexts = current
    except Exception:
        pass


def _add_extent_dimensions(doc, pg, source_obj) -> List[str]:
    """Best-effort overall-length + overall-height dimensions on the
    anchor (Front) view. Picks the 2D projected vertices farthest apart
    horizontally and vertically.
    """
    created: List[str] = []
    front = None
    try:
        front = pg.getItemByLabel("Front")
    except Exception:
        pass
    if front is None:
        return created
    verts = None
    for attr in ("Shape",):
        try:
            s = getattr(front, attr)
            verts = s.Vertexes
            break
        except Exception:
            continue
    if not verts or len(verts) < 2:
        return created

    def _extrema(idx: int):
        vals = [(v.Point.x if idx == 0 else v.Point.y) for v in verts]
        lo = vals.index(min(vals))
        hi = vals.index(max(vals))
        return lo, hi

    for label, axis in (("Length", 0), ("Height", 1)):
        try:
            lo, hi = _extrema(axis)
            if lo == hi:
                continue
            dim = doc.addObject("TechDraw::DrawViewDimension", f"Overall_{label}")
            dim.Type = "DistanceX" if axis == 0 else "DistanceY"
            dim.References2D = [(front, f"Vertex{lo+1}"), (front, f"Vertex{hi+1}")]
            created.append(dim.Name)
        except Exception as exc:
            FreeCAD.Console.PrintWarning(f"auto-extent {label}: {exc}\n")
    return created


def _material_of(obj) -> str:
    if "FreeCADMCP_Material" in obj.PropertiesList:
        try:
            return dict(obj.FreeCADMCP_Material).get("name", "")
        except Exception:
            pass
    return ""


def create_manufacturing_drawing(
    object_name: str,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    sheet: str = "A3_Landscape",
    projections: Optional[List[str]] = None,
    include_iso: bool = True,
    scale: Optional[float] = None,
    add_overall_dimensions: bool = True,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """One-shot manufacturing drawing.

    Creates a sheet (A3 landscape by default) with a standard template,
    a ``DrawProjGroup`` of third-angle views (Front + Top + Right by
    default), an optional isometric view, populated title-block fields,
    auto overall-length / overall-height dimensions on the front view,
    and (optionally) a PDF export.
    """
    try:
        import TechDraw  # noqa: F401
    except Exception as exc:
        return err(f"TechDraw workbench unavailable: {exc}")

    doc = get_document(doc_name)
    obj = doc.getObject(object_name)
    if obj is None:
        return err(f"object '{object_name}' not found")
    if not hasattr(obj, "Shape") or obj.Shape.isNull():
        return err(f"object '{object_name}' has no shape")

    tpl = _find_template(sheet)
    if tpl is None:
        return err(f"No TechDraw template for sheet '{sheet}'")
    sheet_w, sheet_h = _sheet_dims_mm(tpl)

    template = doc.addObject("TechDraw::DrawSVGTemplate", f"{object_name}_tmpl")
    template.Template = tpl
    page = doc.addObject("TechDraw::DrawPage", f"{object_name}_Page")
    page.Template = template

    chosen_scale = scale or _auto_scale(obj.Shape.BoundBox.DiagonalLength, sheet_w, sheet_h)

    pg = doc.addObject("TechDraw::DrawProjGroup", f"{object_name}_Projections")
    page.addView(pg)
    pg.Source = [obj]
    pg.ScaleType = "Custom"
    pg.Scale = float(chosen_scale)
    pg.addProjection("Front")
    try:
        pg.Anchor = pg.getItemByLabel("Front")
    except Exception:
        pass
    for p in (projections or ["Top", "Right"]):
        if p == "Front":
            continue
        try:
            pg.addProjection(p)
        except Exception:
            pass
    pg.X = sheet_w * 0.40
    pg.Y = sheet_h * 0.50

    iso_view = None
    if include_iso:
        try:
            iso_view = doc.addObject("TechDraw::DrawViewPart", f"{object_name}_Iso")
            iso_view.Source = [obj]
            iso_view.Direction = FreeCAD.Vector(1, -1, 1)
            iso_view.Scale = float(chosen_scale)
            iso_view.X = sheet_w * 0.82
            iso_view.Y = sheet_h * 0.78
            page.addView(iso_view)
        except Exception as exc:
            FreeCAD.Console.PrintWarning(f"iso view failed: {exc}\n")

    _set_template_fields(template, {
        "Title":           title or obj.Label,
        "Author":          author or "",
        "Scale":           _format_scale(chosen_scale),
        "Date":            _dt.date.today().isoformat(),
        "Sheet":           "1/1",
        "Material":        _material_of(obj),
        "DrawingNumber":   f"{obj.Label}-01",
        "PartName":        obj.Label,
    })

    doc.recompute()

    dims_created: List[str] = []
    if add_overall_dimensions:
        dims_created = _add_extent_dimensions(doc, pg, obj)
        doc.recompute()

    exported_path: Optional[str] = None
    if output_path:
        try:
            import TechDrawGui  # type: ignore
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            TechDrawGui.exportPageAsPdf(page, output_path)
            exported_path = output_path
        except Exception as exc:
            return err(f"PDF export failed: {exc}", page=page.Name, pdf_path=None)

    return ok(
        page=page.Name,
        projection_group=pg.Name,
        iso_view=iso_view.Name if iso_view else None,
        scale=chosen_scale,
        sheet=sheet,
        sheet_dims_mm=[sheet_w, sheet_h],
        dimensions=dims_created,
        pdf_path=exported_path,
    )


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "create_drawing_page": create_drawing_page,
            "add_drawing_view": add_drawing_view,
            "add_drawing_dimension": add_drawing_dimension,
            "export_drawing_pdf": export_drawing_pdf,
            "export_drawing_svg": export_drawing_svg,
            "create_projection_group": create_projection_group,
            "create_manufacturing_drawing": create_manufacturing_drawing,
        }
    )
