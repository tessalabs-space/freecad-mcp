"""Standalone mesh generation and mesh-format export.

Separate from ``fem_export`` (which builds full Elmer/CalculiX decks) —
these tools just produce a mesh from a Part/Shape, or export an existing
FemMesh to a neutral format, so users can feed the mesh into any
downstream solver or share it with collaborators.

Supported export formats:
  - ``.unv``   Ideas Universal — the Elmer / Code_Aster lingua franca
  - ``.inp``   Abaqus / CalculiX input deck (mesh only, no case data)
  - ``.med``   Salome MED (Code_Aster, ParaVis)
  - ``.vtk``   Legacy VTK (ParaView, visualization)
  - ``.dat``   FreeCAD mesh dump (debugging)
  - ``.stl``   Tessellated surface (Mesh module) — useful for 3D printing
               or handing to a meshing tool that wants a clean surface.

Mesh generation uses Gmsh through FreeCAD's FEM workbench; Gmsh must be
installed and discoverable (FreeCAD ships with a bundled copy on most
platforms).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import get_document, get_object, ok, err


_SUPPORTED_EXPORT_EXTS = {".unv", ".inp", ".med", ".vtk", ".dat", ".stl", ".bdf", ".z88"}


def generate_mesh(
    obj_name: str,
    mesh_size_mm: float = 5.0,
    min_size_mm: Optional[float] = None,
    order: int = 1,
    algorithm_2d: str = "Automatic",
    algorithm_3d: str = "Automatic",
    doc_name: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a Gmsh FEM mesh for a Part/Shape.

    ``order`` is element order (1 = linear, 2 = quadratic). Both 2D and 3D
    algorithm names follow FreeCAD's FemMeshGmsh vocabulary — common
    choices: ``Automatic``, ``Delaunay``, ``Frontal``, ``MeshAdapt`` (2D),
    ``Delaunay``, ``Frontal``, ``HXT`` (3D).
    """
    try:
        import ObjectsFem  # type: ignore
        from femmesh.gmshtools import GmshTools  # type: ignore
    except Exception as exc:
        return err(f"FEM workbench / Gmsh unavailable: {exc}")

    obj = get_object(doc_name, obj_name)
    doc = obj.Document

    mesh_obj = ObjectsFem.makeMeshGmsh(doc, name or f"Mesh_{obj_name}")
    mesh_obj.Part = obj
    mesh_obj.CharacteristicLengthMax = float(mesh_size_mm)
    if min_size_mm is not None:
        mesh_obj.CharacteristicLengthMin = float(min_size_mm)
    mesh_obj.ElementOrder = "2nd" if int(order) == 2 else "1st"
    try:
        mesh_obj.Algorithm2D = algorithm_2d
        mesh_obj.Algorithm3D = algorithm_3d
    except Exception:
        # Older FreeCAD builds expose different property names; best-effort.
        pass

    doc.recompute()
    try:
        GmshTools(mesh_obj).create_mesh()
    except Exception as exc:
        return err(f"Gmsh run failed: {exc}")
    doc.recompute()

    fem_mesh = mesh_obj.FemMesh
    return ok(
        mesh_object=mesh_obj.Name,
        mesh_label=mesh_obj.Label,
        node_count=int(fem_mesh.NodeCount),
        edge_count=int(fem_mesh.EdgeCount),
        face_count=int(fem_mesh.FaceCount),
        volume_count=int(fem_mesh.VolumeCount),
        element_order=int(order),
        characteristic_length_max_mm=float(mesh_size_mm),
    )


def list_meshes(doc_name: Optional[str] = None) -> Dict[str, Any]:
    """Return every FemMesh / Mesh::Feature in the document."""
    doc = get_document(doc_name)
    out: List[Dict[str, Any]] = []
    for o in doc.Objects:
        if _looks_like_fem_mesh(o):
            fm = o.FemMesh
            out.append(
                {
                    "name": o.Name,
                    "label": o.Label,
                    "kind": "FemMesh",
                    "nodes": int(fm.NodeCount),
                    "edges": int(fm.EdgeCount),
                    "faces": int(fm.FaceCount),
                    "volumes": int(fm.VolumeCount),
                }
            )
        elif _looks_like_surface_mesh(o):
            m = o.Mesh
            out.append(
                {
                    "name": o.Name,
                    "label": o.Label,
                    "kind": "SurfaceMesh",
                    "points": int(m.CountPoints),
                    "facets": int(m.CountFacets),
                }
            )
    return ok(meshes=out, count=len(out))


def export_mesh(
    mesh_name: str,
    path: str,
    doc_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Export a mesh object to ``path``. Format is chosen by extension.

    For FemMesh objects, FreeCAD's ``Fem.export`` handles UNV/INP/MED/VTK/DAT/BDF/Z88.
    For surface meshes (Mesh::Feature), ``Mesh.export`` handles STL/OBJ/PLY.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in _SUPPORTED_EXPORT_EXTS and ext not in {".obj", ".ply"}:
        return err(
            f"Unsupported mesh format '{ext}'",
            supported=sorted(_SUPPORTED_EXPORT_EXTS | {".obj", ".ply"}),
        )

    obj = get_object(doc_name, mesh_name)
    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)

    if _looks_like_fem_mesh(obj):
        if ext == ".stl":
            # Tessellate the FemMesh surface: write a temporary surface mesh.
            import Mesh  # type: ignore
            tri = _femmesh_to_surface(obj.FemMesh)
            Mesh.Mesh(tri).write(path)
        else:
            import Fem  # type: ignore
            try:
                Fem.export([obj], path)
            except Exception as exc:
                return err(f"Fem.export failed: {exc}")
    elif _looks_like_surface_mesh(obj):
        import Mesh  # type: ignore
        if ext in {".stl", ".obj", ".ply"}:
            Mesh.export([obj], path)
        else:
            return err(
                f"Surface mesh '{mesh_name}' cannot be exported as '{ext}' — "
                "only .stl/.obj/.ply are supported for surface meshes."
            )
    else:
        return err(f"Object '{mesh_name}' is not a mesh (type {obj.TypeId}).")

    size = os.path.getsize(path) if os.path.exists(path) else 0
    return ok(path=path, format=ext.lstrip("."), bytes=size)


def _looks_like_fem_mesh(obj) -> bool:
    return hasattr(obj, "FemMesh") and obj.FemMesh is not None


def _looks_like_surface_mesh(obj) -> bool:
    return obj.TypeId.startswith("Mesh::") and hasattr(obj, "Mesh")


def _femmesh_to_surface(fem_mesh):
    """Pull the face triangulation out of a FemMesh as a plain triangle list.

    Only exposes face elements; volume interiors aren't rendered. That's
    usually what you want for STL.
    """
    tris = []
    # FemMesh triangular faces come as (n1, n2, n3) node-id tuples.
    for fid in fem_mesh.Faces:
        nodes = fem_mesh.getElementNodes(fid)
        if len(nodes) < 3:
            continue
        # Fan-triangulate quads/higher-order faces.
        pts = [tuple(fem_mesh.Nodes[n]) for n in nodes[:4]]
        if len(pts) == 3:
            tris.append(pts)
        else:
            tris.append((pts[0], pts[1], pts[2]))
            if len(pts) >= 4:
                tris.append((pts[0], pts[2], pts[3]))
    return tris


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "generate_mesh": generate_mesh,
            "list_meshes": list_meshes,
            "export_mesh": export_mesh,
        }
    )
