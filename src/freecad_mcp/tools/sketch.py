from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context


def register(mcp, get_client):
    @mcp.tool()
    def create_sketch(
        ctx: Context,
        name: str,
        plane: str = "XY",
        doc_name: Optional[str] = None,
        placement: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a sketch on XY, XZ, YZ, or a custom placement."""
        return get_client().call(
            "create_sketch", name=name, plane=plane,
            doc_name=doc_name, placement=placement,
        )

    @mcp.tool()
    def sketch_add_line(
        ctx: Context,
        sketch_name: str,
        start: Dict[str, float],
        end: Dict[str, float],
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a line segment to a sketch."""
        return get_client().call(
            "sketch_add_line", sketch_name=sketch_name, start=start, end=end,
            doc_name=doc_name,
        )

    @mcp.tool()
    def sketch_add_circle(
        ctx: Context,
        sketch_name: str,
        center: Dict[str, float],
        radius: float,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a circle to a sketch."""
        return get_client().call(
            "sketch_add_circle", sketch_name=sketch_name, center=center,
            radius=radius, doc_name=doc_name,
        )

    @mcp.tool()
    def sketch_add_rectangle(
        ctx: Context,
        sketch_name: str,
        origin: Dict[str, float],
        width: float,
        height: float,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add an axis-aligned rectangle (with coincident constraints)."""
        return get_client().call(
            "sketch_add_rectangle", sketch_name=sketch_name, origin=origin,
            width=width, height=height, doc_name=doc_name,
        )

    @mcp.tool()
    def sketch_add_constraint(
        ctx: Context,
        sketch_name: str,
        kind: str,
        refs: List[Dict[str, Any]],
        value: Optional[float] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a Sketcher constraint.

        kind: 'Coincident' | 'Horizontal' | 'Vertical' | 'Parallel' |
              'Perpendicular' | 'Tangent' | 'Equal' | 'Distance' |
              'DistanceX' | 'DistanceY' | 'Radius' | 'Diameter' | 'Angle'
        refs: [{'geo': i, 'vertex': v}, ...]
        """
        return get_client().call(
            "sketch_add_constraint", sketch_name=sketch_name, kind=kind,
            refs=refs, value=value, doc_name=doc_name,
        )
