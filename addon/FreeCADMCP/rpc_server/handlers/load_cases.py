"""Structural load-case templates: modal, quasi-static acceleration,
and random vibration.

Modal and quasi-static set up real FreeCAD FEM analyses that export to
CalculiX. Random vibration is emitted as a PSD metadata file (+ the
modal case that feeds it) because FreeCAD's built-in solvers do not
support PSD natively — downstream tools consume the JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, ok, err


def create_modal_analysis(
    objects: List[str],
    mode_count: int = 10,
    mesh_size_mm: float = 5.0,
    fixture_face_tags: Optional[List[str]] = None,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        import ObjectsFem  # type: ignore
    except Exception as exc:
        return err(f"FEM workbench unavailable: {exc}")
    doc = get_document(doc_name)
    analysis = ObjectsFem.makeAnalysis(doc, name or "MCP_Modal")
    solver = ObjectsFem.makeSolverCalculixCcxTools(doc, "MCP_ModalSolver")
    solver.AnalysisType = "frequency"
    solver.EigenmodesCount = int(mode_count)
    analysis.addObject(solver)

    primary = doc.getObject(objects[0])
    if primary is None:
        return err(f"primary object '{objects[0]}' not found")
    mesh = ObjectsFem.makeMeshGmsh(doc, "MCP_ModalMesh")
    mesh.Part = primary
    mesh.CharacteristicLengthMax = float(mesh_size_mm)
    analysis.addObject(mesh)

    _attach_materials(doc, analysis, objects, ObjectsFem)
    bc_count = _attach_fixtures(doc, analysis, objects, ObjectsFem, fixture_face_tags)
    doc.recompute()
    return ok(analysis=analysis.Name, solver=solver.Name, mesh=mesh.Name, fixtures=bc_count)


def create_static_acceleration_case(
    objects: List[str],
    accel_g: Dict[str, float],
    fixture_face_tags: Optional[List[str]] = None,
    mesh_size_mm: float = 5.0,
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Quasi-static load case (e.g. launch loads). ``accel_g`` is the
    constant acceleration vector in units of g.
    """
    try:
        import ObjectsFem  # type: ignore
    except Exception as exc:
        return err(f"FEM workbench unavailable: {exc}")
    doc = get_document(doc_name)
    analysis = ObjectsFem.makeAnalysis(doc, name or "MCP_Static")
    solver = ObjectsFem.makeSolverCalculixCcxTools(doc, "MCP_StaticSolver")
    solver.AnalysisType = "static"
    analysis.addObject(solver)

    primary = doc.getObject(objects[0])
    if primary is None:
        return err(f"primary object '{objects[0]}' not found")
    mesh = ObjectsFem.makeMeshGmsh(doc, "MCP_StaticMesh")
    mesh.Part = primary
    mesh.CharacteristicLengthMax = float(mesh_size_mm)
    analysis.addObject(mesh)

    _attach_materials(doc, analysis, objects, ObjectsFem)
    _attach_fixtures(doc, analysis, objects, ObjectsFem, fixture_face_tags)

    g_ms2 = 9.80665
    grav = ObjectsFem.makeConstraintSelfWeight(doc, "MCP_Accel")
    grav.Gravity = abs(_magnitude(accel_g)) * g_ms2
    mag = max(_magnitude(accel_g), 1e-9)
    grav.GravityDirection = FreeCAD.Vector(
        -accel_g.get("x", 0) / mag,
        -accel_g.get("y", 0) / mag,
        -accel_g.get("z", 0) / mag,
    )
    analysis.addObject(grav)
    doc.recompute()
    return ok(analysis=analysis.Name, acceleration_vector_g=accel_g)


def create_random_vibration_case(
    output_dir: str,
    objects: List[str],
    psd_x: Optional[List[List[float]]] = None,
    psd_y: Optional[List[List[float]]] = None,
    psd_z: Optional[List[List[float]]] = None,
    fixture_face_tags: Optional[List[str]] = None,
    q_factor: float = 10.0,
    mesh_size_mm: float = 5.0,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Write a random-vibration case: a companion modal analysis plus a
    sidecar JSON describing the PSD per axis. Downstream solvers (pyNastran
    / custom Python) ingest the JSON together with the modes.
    """
    doc = get_document(doc_name)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    modal = create_modal_analysis(
        objects, mode_count=30, mesh_size_mm=mesh_size_mm,
        fixture_face_tags=fixture_face_tags,
        doc_name=doc.Name, name="MCP_RandomModal",
    )
    if not modal.get("success", True):
        return modal

    sidecar = {
        "case_type": "random_vibration",
        "q_factor": q_factor,
        "psd_axes": {
            "x": psd_x,
            "y": psd_y,
            "z": psd_z,
        },
        "fixture_tags": fixture_face_tags,
        "mode_count": 30,
        "notes": (
            "PSD entries are [[freq_hz, g2_per_hz], ...]. Feed the modal "
            "results from the companion analysis plus this PSD into your "
            "downstream random-vibration solver."
        ),
    }
    sidecar_path = out / "random_vibration_case.json"
    sidecar_path.write_text(json.dumps(sidecar, indent=2))
    return ok(sidecar=str(sidecar_path), modal_analysis=modal.get("analysis"))


def _attach_materials(doc, analysis, objects, ObjectsFem) -> None:
    for name in objects:
        obj = doc.getObject(name)
        if obj is None or "FreeCADMCP_Material" not in obj.PropertiesList:
            continue
        meta = dict(obj.FreeCADMCP_Material)
        mat = ObjectsFem.makeMaterialSolid(doc, f"Mat_{name}")
        mat.Material = {
            "Name": meta.get("name", "Custom"),
            "Density": f"{meta.get('density_kg_m3', 7800)} kg/m^3",
            "YoungsModulus": f"{meta.get('youngs_modulus_GPa', 200)} GPa",
            "PoissonRatio": str(meta.get("poisson_ratio", 0.3)),
        }
        analysis.addObject(mat)


def _attach_fixtures(doc, analysis, objects, ObjectsFem, fixture_face_tags):
    count = 0
    tags = set(fixture_face_tags or ["fixture"])
    for name in objects:
        obj = doc.getObject(name)
        if obj is None or "FreeCADMCP_BCTags" not in obj.PropertiesList:
            continue
        obj_tags = json.loads(obj.FreeCADMCP_BCTags)
        for tag, faces in obj_tags.items():
            if tag.endswith("__meta") or not faces:
                continue
            bare = tag.replace("custom:", "")
            if bare not in tags:
                continue
            bc = ObjectsFem.makeConstraintFixed(doc, f"Fixed_{name}_{bare}")
            bc.References = [(obj, f"Face{i}") for i in faces]
            analysis.addObject(bc)
            count += 1
    return count


def _magnitude(v: Dict[str, float]) -> float:
    x = float(v.get("x", 0)); y = float(v.get("y", 0)); z = float(v.get("z", 0))
    return (x * x + y * y + z * z) ** 0.5


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "create_modal_analysis": create_modal_analysis,
            "create_static_acceleration_case": create_static_acceleration_case,
            "create_random_vibration_case": create_random_vibration_case,
        }
    )
