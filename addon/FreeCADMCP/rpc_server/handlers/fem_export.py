"""Exporters for Elmer, OpenFOAM, and CalculiX.

Strategy: FreeCAD has a decent FEM workbench with writers for Elmer and
CalculiX. For OpenFOAM we emit a minimal ``constant/polyMesh`` via
snappyHexMesh-ready STL per BC group — the user still needs to run
``snappyHexMesh`` themselves, but the tagged STL set means the dict's
``geometry`` block is trivial to write.

BC tags written by ``bc_tagging.py`` are read back here so the named
groups propagate into the solver case files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils import get_document, get_object, ok, err


def export_elmer(
    output_dir: str,
    objects: List[str],
    analysis: str = "HeatTransfer",
    mesh_size_mm: float = 5.0,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an Elmer FEM analysis in FreeCAD and dump the sif file.

    Uses FreeCAD's ``Fem`` workbench — the heavy lifting is delegated to
    ``ObjectsFem`` makers. We only wire material + BC groups.
    """
    try:
        import ObjectsFem  # type: ignore
        from femtools import ccxtools  # noqa: F401 — availability probe
    except Exception as exc:
        return err(f"FEM workbench unavailable: {exc}")

    doc = get_document(doc_name)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    analysis_obj = ObjectsFem.makeAnalysis(doc, "MCP_ElmerAnalysis")

    mesh_obj = ObjectsFem.makeMeshGmsh(doc, "MCP_Mesh")
    target = doc.getObject(objects[0])
    if target is None:
        return err("primary object not found")
    mesh_obj.Part = target
    mesh_obj.CharacteristicLengthMax = float(mesh_size_mm)
    analysis_obj.addObject(mesh_obj)

    solver = ObjectsFem.makeSolverElmer(doc, "MCP_Elmer")
    analysis_obj.addObject(solver)

    equation = {
        "HeatTransfer": "makeEquationHeat",
        "Elasticity": "makeEquationElasticity",
        "Flow": "makeEquationFlow",
    }.get(analysis, "makeEquationHeat")
    getattr(ObjectsFem, equation)(doc, solver)

    # Materials + BCs from tags
    bc_count = 0
    for name in objects:
        obj = doc.getObject(name)
        if obj is None:
            continue
        if "FreeCADMCP_Material" in obj.PropertiesList:
            meta = dict(obj.FreeCADMCP_Material)
            mat = ObjectsFem.makeMaterialSolid(doc, f"Mat_{name}")
            mat.Material = {
                "Name": meta.get("name", "Custom"),
                "Density": f"{meta.get('density_kg_m3', 7800)} kg/m^3",
                "YoungsModulus": f"{meta.get('youngs_modulus_GPa', 200)} GPa",
                "PoissonRatio": str(meta.get("poisson_ratio", 0.3)),
                "ThermalConductivity": f"{meta.get('thermal_conductivity_W_mK', 45)} W/m/K",
                "SpecificHeat": f"{meta.get('specific_heat_J_kgK', 500)} J/kg/K",
            }
            analysis_obj.addObject(mat)
        if "FreeCADMCP_BCTags" in obj.PropertiesList:
            tags = json.loads(obj.FreeCADMCP_BCTags)
            for tag, faces in tags.items():
                if tag.endswith("__meta") or not faces:
                    continue
                bc_count += 1
                refs = [(obj, f"Face{i}") for i in faces]
                if analysis == "HeatTransfer":
                    bc = ObjectsFem.makeConstraintTemperature(doc, f"BC_{tag}_{name}")
                else:
                    bc = ObjectsFem.makeConstraintFixed(doc, f"BC_{tag}_{name}")
                bc.References = refs
                analysis_obj.addObject(bc)

    doc.recompute()

    try:
        from femsolver.elmer.writer import Writer  # type: ignore
        writer = Writer(solver, str(out))
        writer.writeInputFiles()
    except Exception as exc:
        return err(f"Elmer writer failed: {exc}")

    return ok(directory=str(out), bc_constraints_created=bc_count)


def export_calculix(
    output_dir: str,
    objects: List[str],
    doc_name: Optional[str] = None,
    mesh_size_mm: float = 5.0,
) -> Dict[str, Any]:
    try:
        import ObjectsFem  # type: ignore
        from femtools import ccxtools  # type: ignore
    except Exception as exc:
        return err(f"FEM workbench unavailable: {exc}")

    doc = get_document(doc_name)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    analysis = ObjectsFem.makeAnalysis(doc, "MCP_CcxAnalysis")
    solver = ObjectsFem.makeSolverCalculixCcxTools(doc, "MCP_Ccx")
    analysis.addObject(solver)
    mesh = ObjectsFem.makeMeshGmsh(doc, "MCP_CcxMesh")
    mesh.Part = doc.getObject(objects[0])
    mesh.CharacteristicLengthMax = float(mesh_size_mm)
    analysis.addObject(mesh)

    doc.recompute()

    fea = ccxtools.FemToolsCcx(solver=solver)
    fea.setup_working_dir(str(out))
    fea.purge_results()
    try:
        fea.write_inp_file()
    except Exception as exc:
        return err(f"CalculiX writer failed: {exc}")
    return ok(directory=str(out))


def export_openfoam_stl(
    output_dir: str,
    objects: List[str],
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Write one STL per BC group per object so ``snappyHexMeshDict`` can
    reference them by name. Returns the mapping for downstream scripts.
    """
    import Mesh  # type: ignore
    doc = get_document(doc_name)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    mapping: Dict[str, str] = {}
    for name in objects:
        obj = doc.getObject(name)
        if obj is None or not hasattr(obj, "Shape"):
            continue
        path = out / f"{name}.stl"
        Mesh.export([obj], str(path))
        mapping[name] = str(path)
        if "FreeCADMCP_BCTags" in obj.PropertiesList:
            tags = json.loads(obj.FreeCADMCP_BCTags)
            for tag, faces in tags.items():
                if tag.endswith("__meta") or not faces:
                    continue
                import Part  # type: ignore
                sub = Part.makeCompound([obj.Shape.Faces[i - 1] for i in faces])
                scratch_obj = doc.addObject("Part::Feature", f"_tmp_{name}_{tag}")
                scratch_obj.Shape = sub
                doc.recompute()
                tag_path = out / f"{name}_{tag}.stl"
                Mesh.export([scratch_obj], str(tag_path))
                mapping[f"{name}/{tag}"] = str(tag_path)
                doc.removeObject(scratch_obj.Name)

    (out / "bc_manifest.json").write_text(json.dumps(mapping, indent=2))
    return ok(directory=str(out), files=mapping)


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "export_elmer": export_elmer,
            "export_calculix": export_calculix,
            "export_openfoam_stl": export_openfoam_stl,
        }
    )
