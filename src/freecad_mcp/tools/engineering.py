"""Engineering-specific tools: I/O, defeaturing, analysis prep, materials,
BC tagging, inspection, annotations, views, animation, render, FEM export,
Blender bridge, and the execute escape-hatch.

Kept in one file on purpose — each tool is a thin wrapper around a single
RPC call and grouping them by domain in comments makes the intent clear
without an extra module per group.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context


def register(mcp, get_client):  # noqa: C901 — one function, many tools
    # ---------------------------------------------------------------- I/O
    @mcp.tool()
    def import_file(ctx: Context, path: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """Import STEP/IGES/STL/BREP/OBJ/FCStd into a document."""
        return get_client().call("import_file", path=path, doc_name=doc_name)

    @mcp.tool()
    def export_file(
        ctx: Context,
        path: str,
        object_names: Optional[List[str]] = None,
        doc_name: Optional[str] = None,
        tolerance_report: bool = False,
    ) -> Dict[str, Any]:
        """Export to STEP/IGES/STL/BREP/OBJ/FCStd. ``tolerance_report``
        re-imports the exported file and diffs bounding boxes.
        """
        return get_client().call(
            "export_file", path=path, object_names=object_names,
            doc_name=doc_name, tolerance_report=tolerance_report,
        )

    @mcp.tool()
    def audit_units(ctx: Context, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """Report the unit system of a document."""
        return get_client().call("audit_units", doc_name=doc_name)

    # -------------------------------------------------------- defeaturing
    @mcp.tool()
    def find_holes(
        ctx: Context, obj_name: str, max_diameter: float = 10.0,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List cylindrical holes up to ``max_diameter`` mm."""
        return get_client().call(
            "find_holes", obj_name=obj_name, max_diameter=max_diameter, doc_name=doc_name,
        )

    @mcp.tool()
    def remove_holes(
        ctx: Context, obj_name: str, max_diameter: float = 10.0,
        doc_name: Optional[str] = None, name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fill cylindrical holes up to ``max_diameter`` mm."""
        return get_client().call(
            "remove_holes", obj_name=obj_name, max_diameter=max_diameter,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def find_fillets(
        ctx: Context, obj_name: str, max_radius: float = 5.0,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List likely fillet faces up to ``max_radius`` mm."""
        return get_client().call(
            "find_fillets", obj_name=obj_name, max_radius=max_radius, doc_name=doc_name,
        )

    @mcp.tool()
    def remove_fillets(
        ctx: Context, obj_name: str, max_radius: float = 5.0,
        doc_name: Optional[str] = None, name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Remove likely fillets up to ``max_radius`` mm."""
        return get_client().call(
            "remove_fillets", obj_name=obj_name, max_radius=max_radius,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def remove_chamfers(
        ctx: Context, obj_name: str, max_size: float = 5.0,
        doc_name: Optional[str] = None, name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Remove narrow planar faces likely to be chamfers."""
        return get_client().call(
            "remove_chamfers", obj_name=obj_name, max_size=max_size,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def find_fasteners(
        ctx: Context,
        doc_name: Optional[str] = None,
        name_patterns: Optional[List[str]] = None,
        max_length_mm: float = 200.0,
        diameter_range_mm: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """List probable bolts / screws / nuts by name AND shape heuristic."""
        return get_client().call(
            "find_fasteners", doc_name=doc_name, name_patterns=name_patterns,
            max_length_mm=max_length_mm,
            diameter_range_mm=tuple(diameter_range_mm or [1.5, 20.0]),
        )

    @mcp.tool()
    def remove_fasteners(
        ctx: Context,
        doc_name: Optional[str] = None,
        name_patterns: Optional[List[str]] = None,
        max_length_mm: float = 200.0,
        diameter_range_mm: Optional[List[float]] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Remove probable fasteners. ``dry_run`` defaults to True — set
        False explicitly to actually delete.
        """
        return get_client().call(
            "remove_fasteners", doc_name=doc_name, name_patterns=name_patterns,
            max_length_mm=max_length_mm,
            diameter_range_mm=tuple(diameter_range_mm or [1.5, 20.0]),
            dry_run=dry_run,
        )

    @mcp.tool()
    def find_thin_bodies(
        ctx: Context, doc_name: Optional[str] = None, min_thickness_mm: float = 0.5,
    ) -> Dict[str, Any]:
        """Flag bodies with bbox dimensions under ``min_thickness_mm``."""
        return get_client().call(
            "find_thin_bodies", doc_name=doc_name, min_thickness_mm=min_thickness_mm,
        )

    # ---------------------------------------------------- analysis prep
    @mcp.tool()
    def extract_midsurface(
        ctx: Context, obj_name: str, thickness: float,
        doc_name: Optional[str] = None, name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Best-effort mid-surface from a thin-walled part."""
        return get_client().call(
            "extract_midsurface", obj_name=obj_name, thickness=thickness,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def detect_symmetry(
        ctx: Context, obj_name: str, tolerance: float = 0.5,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check XY / XZ / YZ symmetry of a body by bbox vs mass centre."""
        return get_client().call(
            "detect_symmetry", obj_name=obj_name, tolerance=tolerance, doc_name=doc_name,
        )

    @mcp.tool()
    def keep_external_surfaces(
        ctx: Context, obj_name: str,
        doc_name: Optional[str] = None, name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract the outer shell only (for thermal radiation analyses)."""
        return get_client().call(
            "keep_external_surfaces", obj_name=obj_name,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def find_contact_faces(
        ctx: Context, a: str, b: str, tolerance: float = 0.1,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pairwise face distance between two bodies below ``tolerance``."""
        return get_client().call(
            "find_contact_faces", a=a, b=b, tolerance=tolerance, doc_name=doc_name,
        )

    @mcp.tool()
    def imprint_merge(
        ctx: Context, objects: List[str],
        doc_name: Optional[str] = None, name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """generalFuse-based imprint of mating faces."""
        return get_client().call(
            "imprint_merge", objects=objects, doc_name=doc_name, name=name,
        )

    # -------------------------------------------------------- materials
    @mcp.tool()
    def list_materials(ctx: Context) -> Dict[str, Any]:
        """List materials in the built-in library, grouped by category."""
        return get_client().call("list_materials")

    @mcp.tool()
    def get_material(ctx: Context, material: str) -> Dict[str, Any]:
        """Return a material's full property sheet."""
        return get_client().call("get_material", material=material)

    @mcp.tool()
    def assign_material(
        ctx: Context, obj_name: str, material: str, face: Optional[int] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Assign a material to an object (or a single face)."""
        return get_client().call(
            "assign_material", obj_name=obj_name, material=material,
            face=face, doc_name=doc_name,
        )

    @mcp.tool()
    def get_assigned_material(
        ctx: Context, obj_name: str, face: Optional[int] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Read back the material metadata from an object/face."""
        return get_client().call(
            "get_assigned_material", obj_name=obj_name, face=face, doc_name=doc_name,
        )

    # ------------------------------------------------------- BC tagging
    @mcp.tool()
    def list_bc_tags(ctx: Context, obj_name: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """List boundary-condition tags on an object."""
        return get_client().call("list_bc_tags", obj_name=obj_name, doc_name=doc_name)

    @mcp.tool()
    def tag_faces(
        ctx: Context, obj_name: str, tag: str, faces: List[int],
        doc_name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Tag the listed face indices. Standard tags: inlet, outlet, wall,
        symmetry, radiator, heat_source, heat_sink, fixture, load, contact,
        interface, free_surface, periodic. Any other tag is namespaced
        under ``custom:``.
        """
        return get_client().call(
            "tag_faces", obj_name=obj_name, tag=tag, faces=faces,
            doc_name=doc_name, metadata=metadata,
        )

    @mcp.tool()
    def untag_faces(
        ctx: Context, obj_name: str, tag: str, faces: Optional[List[int]] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Remove a tag, or only the listed faces from a tag."""
        return get_client().call(
            "untag_faces", obj_name=obj_name, tag=tag, faces=faces, doc_name=doc_name,
        )

    @mcp.tool()
    def tag_boundary_by_normal(
        ctx: Context, obj_name: str, tag: str,
        direction: Dict[str, float], tolerance_deg: float = 15.0,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Auto-tag faces whose outward normal is within ``tolerance_deg``
        of ``direction``.
        """
        return get_client().call(
            "tag_boundary_by_normal", obj_name=obj_name, tag=tag,
            direction=direction, tolerance_deg=tolerance_deg, doc_name=doc_name,
        )

    # -------------------------------------------------------- inspection
    @mcp.tool()
    def mass_properties(
        ctx: Context, obj_name: str, density_kg_m3: Optional[float] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Volume, surface area, centre of mass, bbox, and — if density is
        known (argument or assigned-material) — mass and inertia.
        """
        return get_client().call(
            "mass_properties", obj_name=obj_name, density_kg_m3=density_kg_m3,
            doc_name=doc_name,
        )

    @mcp.tool()
    def clash_detection(
        ctx: Context, objects: Optional[List[str]] = None, tolerance: float = 0.0,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pairwise boolean-intersection check. ``tolerance`` is minimum
        overlap volume to report (mm³).
        """
        return get_client().call(
            "clash_detection", objects=objects, tolerance=tolerance, doc_name=doc_name,
        )

    @mcp.tool()
    def distance_between(ctx: Context, a: str, b: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """Minimum distance between two objects with nearest-point pairs."""
        return get_client().call("distance_between", a=a, b=b, doc_name=doc_name)

    @mcp.tool()
    def expression_report(ctx: Context, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """Dump every parametric expression in the document."""
        return get_client().call("expression_report", doc_name=doc_name)

    # ------------------------------------------------------- annotations
    @mcp.tool()
    def add_callout(
        ctx: Context, label: str, target_object: str,
        target_face: Optional[int] = None,
        offset: Optional[Dict[str, float]] = None,
        color: Optional[List[float]] = None,
        doc_name: Optional[str] = None, name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Leader arrow + text label pointing at an object or face."""
        return get_client().call(
            "add_callout", label=label, target_object=target_object,
            target_face=target_face, offset=offset, color=color,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def add_dimension(
        ctx: Context, a: Dict[str, float], b: Dict[str, float],
        doc_name: Optional[str] = None, name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Draft dimension between two 3D points."""
        return get_client().call(
            "add_dimension", a=a, b=b, doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def clear_annotations(ctx: Context, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """Remove every annotation this tool has created in the document."""
        return get_client().call("clear_annotations", doc_name=doc_name)

    # ------------------------------------------------------------- views
    @mcp.tool()
    def set_view(
        ctx: Context, direction: str, focus_object: Optional[str] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Switch the 3D view. ``direction``: Isometric, Front, Top, Right,
        Back, Left, Bottom, Dimetric, Trimetric.
        """
        return get_client().call(
            "set_view", direction=direction, focus_object=focus_object, doc_name=doc_name,
        )

    @mcp.tool()
    def screenshot(
        ctx: Context, path: Optional[str] = None,
        width: int = 1600, height: int = 1000,
        background: str = "Current", return_bytes: bool = True,
    ) -> Dict[str, Any]:
        """Save a PNG of the active view; optionally return base64 bytes."""
        return get_client().call(
            "screenshot", path=path, width=width, height=height,
            background=background, return_bytes=return_bytes,
        )

    @mcp.tool()
    def section_cut(
        ctx: Context, objects: List[str],
        origin: Dict[str, float], normal: Dict[str, float],
        name: Optional[str] = None, doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Insert a Part::SectionCut through the listed objects."""
        return get_client().call(
            "section_cut", objects=objects, origin=origin, normal=normal,
            name=name, doc_name=doc_name,
        )

    @mcp.tool()
    def explode(
        ctx: Context, objects: List[str], factor: float = 1.5,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exploded view. ``factor=1.0`` restores original positions."""
        return get_client().call(
            "explode", objects=objects, factor=factor, doc_name=doc_name,
        )

    # -------------------------------------------------- animation / render
    @mcp.tool()
    def turntable(
        ctx: Context, output_dir: str, frames: int = 60, axis: str = "Z",
        width: int = 1600, height: int = 1000,
        background: str = "Current", focus_object: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Render a 360° turntable into PNG frames in ``output_dir``."""
        return get_client().call(
            "turntable", output_dir=output_dir, frames=frames, axis=axis,
            width=width, height=height, background=background,
            focus_object=focus_object,
        )

    @mcp.tool()
    def keyframe_camera(
        ctx: Context, output_dir: str,
        keyframes: List[Dict[str, Any]], frames_between: int = 30,
        width: int = 1600, height: int = 1000, background: str = "Current",
    ) -> Dict[str, Any]:
        """Render interpolated camera path frames.

        keyframes: [{"pos": {x,y,z}, "target": {x,y,z}}, ...]
        """
        return get_client().call(
            "keyframe_camera", output_dir=output_dir, keyframes=keyframes,
            frames_between=frames_between, width=width, height=height,
            background=background,
        )

    @mcp.tool()
    def render_png(
        ctx: Context, path: Optional[str] = None,
        width: int = 2400, height: int = 1600,
        background: str = "Transparent", quality: str = "high",
        return_bytes: bool = False,
    ) -> Dict[str, Any]:
        """High-quality PNG render. quality: 'low' | 'medium' | 'high'."""
        return get_client().call(
            "render_png", path=path, width=width, height=height,
            background=background, quality=quality, return_bytes=return_bytes,
        )

    # ------------------------------------------------------- FEM export
    @mcp.tool()
    def export_elmer(
        ctx: Context, output_dir: str, objects: List[str],
        analysis: str = "HeatTransfer", mesh_size_mm: float = 5.0,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write an Elmer sif case. analysis: 'HeatTransfer'|'Elasticity'|'Flow'."""
        return get_client().call(
            "export_elmer", output_dir=output_dir, objects=objects,
            analysis=analysis, mesh_size_mm=mesh_size_mm, doc_name=doc_name,
        )

    @mcp.tool()
    def export_calculix(
        ctx: Context, output_dir: str, objects: List[str],
        doc_name: Optional[str] = None, mesh_size_mm: float = 5.0,
    ) -> Dict[str, Any]:
        """Write a CalculiX .inp deck."""
        return get_client().call(
            "export_calculix", output_dir=output_dir, objects=objects,
            doc_name=doc_name, mesh_size_mm=mesh_size_mm,
        )

    @mcp.tool()
    def export_openfoam_stl(
        ctx: Context, output_dir: str, objects: List[str],
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write tagged STLs + manifest for snappyHexMesh ingestion."""
        return get_client().call(
            "export_openfoam_stl", output_dir=output_dir, objects=objects,
            doc_name=doc_name,
        )

    # -------------------------------------------------- Blender bridge
    @mcp.tool()
    def export_for_blender(
        ctx: Context, output_dir: str,
        objects: Optional[List[str]] = None, doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export scene.glb + scene.json (materials + BC tags) for a
        Blender MCP to pick up.
        """
        return get_client().call(
            "export_for_blender", output_dir=output_dir,
            objects=objects, doc_name=doc_name,
        )

    # -------------------------------------------------- escape hatch
    @mcp.tool()
    def execute_code(ctx: Context, code: str) -> Dict[str, Any]:
        """Run Python inside the FreeCAD GUI process. Use rarely — prefer
        the typed tools — but indispensable for one-off OCC tricks.
        """
        return get_client().call("execute_code", code=code)
