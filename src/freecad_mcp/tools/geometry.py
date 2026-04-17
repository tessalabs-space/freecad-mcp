from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context


def register(mcp, get_client):
    @mcp.tool()
    def create_primitive(
        ctx: Context,
        kind: str,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a primitive solid.

        kind: 'box' | 'cylinder' | 'sphere' | 'cone' | 'torus' | 'plane' |
              'wedge' | 'ellipsoid' | 'prism'

        properties: dict matching FreeCAD's property names for the type,
        e.g. {'Length': 30, 'Width': 20, 'Height': 10,
              'Placement': {'Base': {'x': 0, 'y': 0, 'z': 0},
                            'Rotation': {'Axis': {'x': 0, 'y': 0, 'z': 1},
                                         'Angle': 0}}}
        """
        return get_client().call(
            "create_primitive",
            kind=kind, name=name, properties=properties, doc_name=doc_name,
        )

    @mcp.tool()
    def boolean_op(
        ctx: Context,
        op: str,
        bases: List[str],
        tools: List[str],
        name: Optional[str] = None,
        doc_name: Optional[str] = None,
        keep_inputs: bool = False,
    ) -> Dict[str, Any]:
        """Boolean op. ``op`` is 'fuse'|'union'|'cut'|'difference'|'common'|'intersection'."""
        return get_client().call(
            "boolean_op",
            op=op, bases=bases, tools=tools, name=name,
            doc_name=doc_name, keep_inputs=keep_inputs,
        )

    @mcp.tool()
    def fillet(
        ctx: Context,
        obj_name: str,
        edges: List[int],
        radius: float,
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fillet the listed edge indices (1-based) with a constant radius."""
        return get_client().call(
            "fillet", obj_name=obj_name, edges=edges, radius=radius,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def chamfer(
        ctx: Context,
        obj_name: str,
        edges: List[int],
        size: float,
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Chamfer the listed edge indices (1-based) with a constant size."""
        return get_client().call(
            "chamfer", obj_name=obj_name, edges=edges, size=size,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def thickness(
        ctx: Context,
        obj_name: str,
        faces: List[int],
        value: float,
        mode: str = "Skin",
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Hollow out a solid leaving the listed faces open. ``mode``: 'Skin'|'Pipe'|'RectoVerso'."""
        return get_client().call(
            "thickness", obj_name=obj_name, faces=faces, value=value,
            mode=mode, doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def mirror(
        ctx: Context,
        obj_name: str,
        base: Dict[str, float],
        normal: Dict[str, float],
        doc_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mirror an object across a plane defined by (base, normal)."""
        return get_client().call(
            "mirror", obj_name=obj_name, base=base, normal=normal,
            doc_name=doc_name, name=name,
        )

    @mcp.tool()
    def translate(
        ctx: Context,
        obj_name: str,
        delta: Dict[str, float],
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Translate an object by ``delta`` (mm)."""
        return get_client().call(
            "translate", obj_name=obj_name, delta=delta, doc_name=doc_name,
        )

    @mcp.tool()
    def rotate(
        ctx: Context,
        obj_name: str,
        axis: Dict[str, float],
        angle: float,
        center: Optional[Dict[str, float]] = None,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rotate an object by ``angle`` deg around ``axis`` through ``center``."""
        return get_client().call(
            "rotate", obj_name=obj_name, axis=axis, angle=angle,
            center=center, doc_name=doc_name,
        )
