"""Export geometry for discrete-element (DEM) and particulate-flow
workflows. Writes one STL per object plus a metadata JSON describing
per-surface roughness, friction, and surface-energy properties that
DEM engines (Yade, LIGGGHTS, MFIX) consume.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils import get_document, ok, err


def export_for_dem(
    output_dir: str,
    objects: List[str],
    roughness_um: Optional[float] = None,
    friction_coefficient: Optional[float] = None,
    surface_energy_mJ_m2: Optional[float] = None,
    restitution_coefficient: Optional[float] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        import Mesh  # type: ignore
    except Exception as exc:
        return err(f"Mesh workbench unavailable: {exc}")
    doc = get_document(doc_name)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    files: Dict[str, str] = {}
    metadata: List[Dict[str, Any]] = []
    for name in objects:
        obj = doc.getObject(name)
        if obj is None or not hasattr(obj, "Shape"):
            continue
        path = out / f"{name}.stl"
        Mesh.export([obj], str(path))
        files[name] = str(path)
        entry: Dict[str, Any] = {"name": name, "stl": str(path)}
        if "FreeCADMCP_Material" in obj.PropertiesList:
            entry["material"] = dict(obj.FreeCADMCP_Material)
        if roughness_um is not None:
            entry["roughness_um"] = float(roughness_um)
        if friction_coefficient is not None:
            entry["friction_coefficient"] = float(friction_coefficient)
        if surface_energy_mJ_m2 is not None:
            entry["surface_energy_mJ_m2"] = float(surface_energy_mJ_m2)
        if restitution_coefficient is not None:
            entry["restitution_coefficient"] = float(restitution_coefficient)
        metadata.append(entry)

    manifest = {
        "source": "freecad-mcp",
        "objects": metadata,
        "schema": {
            "roughness_um": "Ra-style surface roughness in micrometres.",
            "friction_coefficient": "Static friction (particle on surface).",
            "surface_energy_mJ_m2": "Surface energy in mJ/m² for JKR-type cohesion models.",
            "restitution_coefficient": "Coefficient of restitution (0 = perfectly plastic, 1 = elastic).",
        },
    }
    (out / "dem_manifest.json").write_text(json.dumps(manifest, indent=2))
    return ok(directory=str(out), files=files, manifest=str(out / "dem_manifest.json"))


def register(r: Dict[str, Any]) -> None:
    r.update({"export_for_dem": export_for_dem})
