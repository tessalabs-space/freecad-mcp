"""Workflow and CAE extensions: parametric sweep, report generation,
mass/CG budget, TechDraw drawings, document diff, structural load cases,
DEM geometry export.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context


def register(mcp, get_client):  # noqa: C901
    # -------------------------------------------------------- parametric
    @mcp.tool()
    def parametric_sweep(
        ctx: Context,
        obj_name: str,
        property_name: str,
        values: List[float],
        doc_name: Optional[str] = None,
        export_dir: Optional[str] = None,
        export_format: str = "step",
        capture_mass: bool = True,
        capture_screenshot: bool = False,
    ) -> Dict[str, Any]:
        """Sweep an object's property through values and record / export
        each configuration. Property restored at the end.
        """
        return get_client().call(
            "parametric_sweep", obj_name=obj_name, property_name=property_name,
            values=values, doc_name=doc_name, export_dir=export_dir,
            export_format=export_format, capture_mass=capture_mass,
            capture_screenshot=capture_screenshot,
        )

    @mcp.tool()
    def spreadsheet_sweep(
        ctx: Context,
        spreadsheet_name: str,
        cell: str,
        values: List[float],
        doc_name: Optional[str] = None,
        export_dir: Optional[str] = None,
        export_format: str = "step",
    ) -> Dict[str, Any]:
        """Sweep a Spreadsheet cell that drives downstream objects via
        expression bindings.
        """
        return get_client().call(
            "spreadsheet_sweep", spreadsheet_name=spreadsheet_name, cell=cell,
            values=values, doc_name=doc_name, export_dir=export_dir,
            export_format=export_format,
        )

    # ----------------------------------------------------------- report
    @mcp.tool()
    def generate_report(
        ctx: Context,
        output_dir: str,
        title: str,
        sections: Optional[List[str]] = None,
        render_views: Optional[List[str]] = None,
        doc_name: Optional[str] = None,
        author: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write a Markdown project report (plus PNG renders) to
        ``output_dir``. Sections default to cover/renders/objects/
        materials/bc_tags/mass_budget/clashes.
        """
        return get_client().call(
            "generate_report", output_dir=output_dir, title=title,
            sections=sections, render_views=render_views,
            doc_name=doc_name, author=author,
        )

    # ---------------------------------------------------------- budget
    @mcp.tool()
    def mass_budget(
        ctx: Context,
        doc_name: Optional[str] = None,
        default_density_kg_m3: Optional[float] = None,
        group_by_prefix: bool = False,
        grouping: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Per-object mass + weighted CG, using assigned-material densities
        (with an optional default fallback). Groups by label prefix or an
        explicit grouping dict.
        """
        return get_client().call(
            "mass_budget", doc_name=doc_name,
            default_density_kg_m3=default_density_kg_m3,
            group_by_prefix=group_by_prefix, grouping=grouping,
        )

    # --------------------------------------------------------- drawings
    @mcp.tool()
    def create_drawing_page(
        ctx: Context,
        template_path: Optional[str] = None,
        name: Optional[str] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a TechDraw page. Falls back to a bundled template if
        ``template_path`` is not given.
        """
        return get_client().call(
            "create_drawing_page", template_path=template_path,
            name=name, doc_name=doc_name,
        )

    @mcp.tool()
    def add_drawing_view(
        ctx: Context,
        page_name: str,
        source_objects: List[str],
        view_type: str = "Front",
        position: Optional[Dict[str, float]] = None,
        scale: float = 0.5,
        show_hidden: bool = False,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add an orthographic or iso view to a drawing page.

        view_type: Front | Back | Top | Bottom | Right | Left | Iso
        """
        return get_client().call(
            "add_drawing_view", page_name=page_name,
            source_objects=source_objects, view_type=view_type,
            position=position, scale=scale, show_hidden=show_hidden,
            doc_name=doc_name,
        )

    @mcp.tool()
    def add_drawing_dimension(
        ctx: Context,
        view_name: str,
        kind: str,
        refs: List[Dict[str, Any]],
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a dimension in a drawing view.

        kind: Distance | DistanceX | DistanceY | Radius | Diameter | Angle
        refs: [{"subname": "Edge1"}, {"subname": "Vertex2"}]
        """
        return get_client().call(
            "add_drawing_dimension", view_name=view_name, kind=kind,
            refs=refs, doc_name=doc_name,
        )

    @mcp.tool()
    def export_drawing_pdf(
        ctx: Context, page_name: str, path: str, doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export a drawing page to PDF."""
        return get_client().call(
            "export_drawing_pdf", page_name=page_name, path=path, doc_name=doc_name,
        )

    @mcp.tool()
    def export_drawing_svg(
        ctx: Context, page_name: str, path: str, doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export a drawing page to SVG."""
        return get_client().call(
            "export_drawing_svg", page_name=page_name, path=path, doc_name=doc_name,
        )

    # ------------------------------------------------------------ diff
    @mcp.tool()
    def compare_documents(ctx: Context, a_path: str, b_path: str) -> Dict[str, Any]:
        """Structural diff between two .FCStd documents. Reports objects
        added / removed / changed with dimension, material, and BC-tag
        deltas.
        """
        return get_client().call("compare_documents", a_path=a_path, b_path=b_path)

    # --------------------------------------------------- load cases
    @mcp.tool()
    def create_modal_analysis(
        ctx: Context,
        objects: List[str],
        mode_count: int = 10,
        mesh_size_mm: float = 5.0,
        fixture_face_tags: Optional[List[str]] = None,
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set up a CalculiX eigenmode analysis with material + fixture
        BCs pulled from assigned materials and tag groups.
        """
        return get_client().call(
            "create_modal_analysis", objects=objects, mode_count=mode_count,
            mesh_size_mm=mesh_size_mm, fixture_face_tags=fixture_face_tags,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def create_static_acceleration_case(
        ctx: Context,
        objects: List[str],
        accel_g: Dict[str, float],
        fixture_face_tags: Optional[List[str]] = None,
        mesh_size_mm: float = 5.0,
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Quasi-static acceleration load case. ``accel_g`` is in units of g."""
        return get_client().call(
            "create_static_acceleration_case", objects=objects, accel_g=accel_g,
            fixture_face_tags=fixture_face_tags, mesh_size_mm=mesh_size_mm,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def create_random_vibration_case(
        ctx: Context,
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
        """Set up a companion modal analysis and write a PSD sidecar JSON.

        PSD entries: [[freq_hz, g2_per_hz], ...]
        """
        return get_client().call(
            "create_random_vibration_case", output_dir=output_dir, objects=objects,
            psd_x=psd_x, psd_y=psd_y, psd_z=psd_z,
            fixture_face_tags=fixture_face_tags, q_factor=q_factor,
            mesh_size_mm=mesh_size_mm, doc_name=doc_name,
        )

    # --------------------------------------------------- granular / DEM
    @mcp.tool()
    def export_for_dem(
        ctx: Context,
        output_dir: str,
        objects: List[str],
        roughness_um: Optional[float] = None,
        friction_coefficient: Optional[float] = None,
        surface_energy_mJ_m2: Optional[float] = None,
        restitution_coefficient: Optional[float] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export STL geometry + a DEM metadata manifest for solvers like
        Yade, LIGGGHTS, MFIX. Physical parameters are optional — pass the
        ones relevant to your DEM contact model.
        """
        return get_client().call(
            "export_for_dem", output_dir=output_dir, objects=objects,
            roughness_um=roughness_um,
            friction_coefficient=friction_coefficient,
            surface_energy_mJ_m2=surface_energy_mJ_m2,
            restitution_coefficient=restitution_coefficient,
            doc_name=doc_name,
        )
