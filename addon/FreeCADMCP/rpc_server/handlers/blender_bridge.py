"""Export scenes into a format a Blender MCP can consume.

Writes one ``.glb`` for the geometry plus a sidecar ``scene.json`` listing
per-object transforms, materials (with the physical properties from the
materials library), and BC tags. The companion Blender MCP reads the
sidecar and applies PBR materials / creates custom collections named
after the BC tags.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils import get_document, ok, err


def export_for_blender(
    output_dir: str,
    objects: Optional[List[str]] = None,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    doc = get_document(doc_name)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    targets = objects or [o.Name for o in doc.Objects if hasattr(o, "Shape")]

    # glTF export via FreeCAD's ImportGui (falls back to per-object OBJ if glTF missing).
    gltf_path = out / "scene.glb"
    wrote_gltf = False
    try:
        import ImportGui  # type: ignore
        ImportGui.export([doc.getObject(n) for n in targets], str(gltf_path))
        wrote_gltf = True
    except Exception:
        try:
            import Mesh  # type: ignore
            for n in targets:
                Mesh.export([doc.getObject(n)], str(out / f"{n}.obj"))
        except Exception as exc:
            return err(f"geometry export failed: {exc}")

    sidecar = {
        "source": "freecad-mcp",
        "doc_name": doc.Name,
        "geometry": "scene.glb" if wrote_gltf else "per-object .obj files",
        "objects": [],
    }
    for n in targets:
        obj = doc.getObject(n)
        entry: Dict[str, Any] = {
            "name": n,
            "label": obj.Label,
            "type": obj.TypeId,
            "placement": _serialize_placement(obj.Placement),
        }
        if "FreeCADMCP_Material" in obj.PropertiesList:
            entry["material"] = dict(obj.FreeCADMCP_Material)
        if "FreeCADMCP_BCTags" in obj.PropertiesList:
            entry["bc_tags"] = json.loads(obj.FreeCADMCP_BCTags)
        sidecar["objects"].append(entry)

    (out / "scene.json").write_text(json.dumps(sidecar, indent=2))
    return ok(directory=str(out), geometry=str(gltf_path), sidecar=str(out / "scene.json"))


def _serialize_placement(p) -> Dict[str, Any]:
    return {
        "base": {"x": p.Base.x, "y": p.Base.y, "z": p.Base.z},
        "rotation_axis": {
            "x": p.Rotation.Axis.x,
            "y": p.Rotation.Axis.y,
            "z": p.Rotation.Axis.z,
        },
        "rotation_angle_rad": p.Rotation.Angle,
    }


def register(r: Dict[str, Any]) -> None:
    r.update({"export_for_blender": export_for_blender})
