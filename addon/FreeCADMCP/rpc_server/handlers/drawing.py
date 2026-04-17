"""TechDraw integration: create 2D drawing pages with orthographic views
and export to SVG / PDF.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, get_object, ok, err


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


def _default_template() -> Optional[str]:
    resource = FreeCAD.getResourceDir()
    candidates = [
        os.path.join(resource, "Mod", "TechDraw", "Templates", "A4_LandscapeTD.svg"),
        os.path.join(resource, "Mod", "TechDraw", "Templates", "A3_LandscapeTD.svg"),
        os.path.join(resource, "Mod", "TechDraw", "Templates", "ANSI_B_Landscape.svg"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def create_drawing_page(
    template_path: Optional[str] = None,
    name: Optional[str] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    try:
        import TechDraw  # noqa: F401
    except Exception as exc:
        return err(f"TechDraw workbench unavailable: {exc}")
    tpl_path = template_path or _default_template()
    if tpl_path is None or not os.path.exists(tpl_path):
        return err("No TechDraw template found — pass template_path explicitly")
    template = doc.addObject("TechDraw::DrawSVGTemplate", (name or "Template") + "_tmpl")
    template.Template = tpl_path
    page = doc.addObject("TechDraw::DrawPage", name or "Page")
    page.Template = template
    doc.recompute()
    return ok(page=page.Name, template=template.Name, template_path=tpl_path)


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
    pos = position or _auto_position(page, view_type)
    view.X = float(pos.get("x", pos.get("X", 150)))
    view.Y = float(pos.get("y", pos.get("Y", 150)))
    page.addView(view)
    doc.recompute()
    return ok(view=view.Name)


def _auto_position(page, view_type: str) -> Dict[str, float]:
    # Rough layout: put Front centre, Top above, Right to the right, Iso upper-right.
    layout = {
        "Front": {"X": 150, "Y": 130},
        "Top":   {"X": 150, "Y": 220},
        "Right": {"X": 240, "Y": 130},
        "Left":  {"X":  60, "Y": 130},
        "Bottom":{"X": 150, "Y":  40},
        "Iso":   {"X": 240, "Y": 220},
        "TrueIso":{"X": 240, "Y": 220},
        "Back":  {"X":  60, "Y":  40},
    }
    return layout.get(view_type, {"X": 150, "Y": 130})


def add_drawing_dimension(
    view_name: str,
    kind: str,
    refs: List[Dict[str, Any]],
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """kind: 'Distance' | 'DistanceX' | 'DistanceY' | 'Radius' | 'Diameter' | 'Angle'.

    ``refs`` is a list of dicts pointing at sub-elements:
      [{"subname": "Edge1"}, {"subname": "Vertex2"}]
    """
    doc = get_document(doc_name)
    view = doc.getObject(view_name)
    if view is None:
        return err(f"View '{view_name}' not found")
    dim = doc.addObject("TechDraw::DrawViewDimension", f"{view_name}_dim_{kind}")
    dim.Type = kind
    dim.References2D = [(view, r["subname"]) for r in refs]
    doc.recompute()
    return ok(dimension=dim.Name)


def export_drawing_pdf(
    page_name: str,
    path: str,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
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


def export_drawing_svg(
    page_name: str,
    path: str,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
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


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "create_drawing_page": create_drawing_page,
            "add_drawing_view": add_drawing_view,
            "add_drawing_dimension": add_drawing_dimension,
            "export_drawing_pdf": export_drawing_pdf,
            "export_drawing_svg": export_drawing_svg,
        }
    )
