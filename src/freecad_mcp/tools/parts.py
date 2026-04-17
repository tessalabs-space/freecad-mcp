from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context


def register(mcp, get_client):
    @mcp.tool()
    def extrude(
        ctx: Context,
        profile: str,
        length: float,
        direction: Optional[Dict[str, float]] = None,
        symmetric: bool = False,
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extrude a sketch or face along its normal (or a custom direction)."""
        return get_client().call(
            "extrude", profile=profile, length=length, direction=direction,
            symmetric=symmetric, doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def revolve(
        ctx: Context,
        profile: str,
        axis_base: Dict[str, float],
        axis_dir: Dict[str, float],
        angle: float = 360.0,
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Revolve a profile around an axis."""
        return get_client().call(
            "revolve", profile=profile, axis_base=axis_base,
            axis_dir=axis_dir, angle=angle, doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def loft(
        ctx: Context,
        profiles: List[str],
        solid: bool = True,
        ruled: bool = False,
        closed: bool = False,
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Loft a solid through ordered profiles."""
        return get_client().call(
            "loft", profiles=profiles, solid=solid, ruled=ruled, closed=closed,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def sweep(
        ctx: Context,
        profile: str,
        path: str,
        solid: bool = True,
        frenet: bool = False,
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sweep a profile along a path."""
        return get_client().call(
            "sweep", profile=profile, path=path, solid=solid, frenet=frenet,
            doc_name=doc_name, name=name,
        )
