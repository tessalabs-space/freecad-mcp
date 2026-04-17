"""Auto-generate a project report: hero render, object / material / BC
tables, mass and clash summaries. Emits Markdown + companion PNGs into a
directory. Convert to PDF externally (pandoc / weasyprint) as needed.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils import get_document, ok


_DEFAULT_SECTIONS = [
    "cover",
    "renders",
    "objects",
    "materials",
    "bc_tags",
    "mass_budget",
    "clashes",
]


def generate_report(
    output_dir: str,
    title: str,
    sections: Optional[List[str]] = None,
    render_views: Optional[List[str]] = None,
    doc_name: Optional[str] = None,
    author: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    sections = sections or _DEFAULT_SECTIONS
    render_views = render_views or ["Isometric", "Front", "Top", "Right"]

    lines: List[str] = []
    lines.append(f"# {title}\n")
    lines.append(f"*Generated {datetime.now().isoformat(timespec='seconds')}"
                 + (f" — {author}" if author else "") + "*\n")
    lines.append(f"*Document:* `{doc.Name}`\n")

    if "renders" in sections:
        lines.append("\n## Views\n")
        try:
            import FreeCADGui  # type: ignore
            view = FreeCADGui.ActiveDocument.ActiveView if FreeCADGui.ActiveDocument else None
            for direction in render_views:
                try:
                    FreeCADGui.runCommand(f"Std_View{direction}", 0)
                except Exception:
                    pass
                FreeCADGui.SendMsgToActiveView("ViewFit")
                path = out / f"view_{direction.lower()}.png"
                if view:
                    view.saveImage(str(path), 1600, 1000, "White")
                    lines.append(f"### {direction}\n![{direction}]({path.name})\n")
        except Exception:
            lines.append("_Render views unavailable in this session._\n")

    if "objects" in sections:
        lines.append("\n## Objects\n\n| Name | Type | Volume (mm³) | Area (mm²) |\n| --- | --- | ---: | ---: |\n")
        for obj in doc.Objects:
            if not hasattr(obj, "Shape") or obj.Shape.isNull():
                continue
            lines.append(f"| {obj.Name} | {obj.TypeId} | {obj.Shape.Volume:.1f} | {obj.Shape.Area:.1f} |\n")

    if "materials" in sections:
        lines.append("\n## Materials\n\n| Object | Material | Density (kg/m³) | k (W/mK) | E (GPa) |\n| --- | --- | ---: | ---: | ---: |\n")
        for obj in doc.Objects:
            if "FreeCADMCP_Material" in obj.PropertiesList:
                m = dict(obj.FreeCADMCP_Material)
                lines.append(
                    "| {n} | {name} | {d} | {k} | {e} |\n".format(
                        n=obj.Name,
                        name=m.get("name", "?"),
                        d=m.get("density_kg_m3", "—"),
                        k=m.get("thermal_conductivity_W_mK", "—"),
                        e=m.get("youngs_modulus_GPa", "—"),
                    )
                )

    if "bc_tags" in sections:
        lines.append("\n## Boundary-condition tags\n\n| Object | Tag | Face count |\n| --- | --- | ---: |\n")
        for obj in doc.Objects:
            if "FreeCADMCP_BCTags" in obj.PropertiesList:
                tags = json.loads(obj.FreeCADMCP_BCTags)
                for tag, faces in tags.items():
                    if tag.endswith("__meta") or not faces:
                        continue
                    lines.append(f"| {obj.Name} | {tag} | {len(faces)} |\n")

    if "mass_budget" in sections:
        lines.append("\n## Mass budget\n\n| Object | Material | Volume (mm³) | Density (kg/m³) | Mass (kg) |\n| --- | --- | ---: | ---: | ---: |\n")
        total = 0.0
        for obj in doc.Objects:
            if not hasattr(obj, "Shape") or obj.Shape.isNull():
                continue
            vol_mm3 = float(obj.Shape.Volume)
            density = None
            mat_name = "—"
            if "FreeCADMCP_Material" in obj.PropertiesList:
                meta = dict(obj.FreeCADMCP_Material)
                mat_name = meta.get("name", "—")
                try:
                    density = float(meta.get("density_kg_m3"))
                except (TypeError, ValueError):
                    density = None
            mass = (vol_mm3 * 1e-9) * density if density else None
            if mass:
                total += mass
            density_cell = f"{density:.1f}" if density else "—"
            mass_cell = f"{mass:.3f}" if mass else "—"
            lines.append(
                f"| {obj.Name} | {mat_name} | {vol_mm3:.1f} | "
                f"{density_cell} | {mass_cell} |\n"
            )
        lines.append(f"\n**Total (from assigned materials):** {total:.3f} kg\n")

    if "clashes" in sections:
        lines.append("\n## Clash check\n\n")
        from . import inspection
        clashes = inspection.clash_detection(doc_name=doc.Name).get("clashes", [])
        if not clashes:
            lines.append("_No clashes above zero-volume tolerance._\n")
        else:
            lines.append("| A | B | Overlap (mm³) |\n| --- | --- | ---: |\n")
            for c in clashes:
                lines.append(f"| {c['a']} | {c['b']} | {c['overlap_volume_mm3']:.2f} |\n")

    report_path = out / "report.md"
    report_path.write_text("".join(lines), encoding="utf-8")
    return ok(path=str(report_path), sections=sections)


def register(r: Dict[str, Any]) -> None:
    r.update({"generate_report": generate_report})
