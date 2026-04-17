from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context


def register(mcp, get_client):
    @mcp.tool()
    def create_document(ctx: Context, name: str) -> Dict[str, Any]:
        """Create a new empty FreeCAD document."""
        return get_client().call("create_document", name=name)

    @mcp.tool()
    def list_documents(ctx: Context) -> Dict[str, Any]:
        """List names of open FreeCAD documents."""
        return get_client().call("list_documents")

    @mcp.tool()
    def open_document(ctx: Context, path: str) -> Dict[str, Any]:
        """Open an .FCStd file."""
        return get_client().call("open_document", path=path)

    @mcp.tool()
    def save_document(ctx: Context, doc_name: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
        """Save a document, optionally as a new file."""
        return get_client().call("save_document", doc_name=doc_name, path=path)

    @mcp.tool()
    def close_document(ctx: Context, doc_name: str) -> Dict[str, Any]:
        """Close a document."""
        return get_client().call("close_document", doc_name=doc_name)

    @mcp.tool()
    def recompute(ctx: Context, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """Force a dependency-graph recompute on the document."""
        return get_client().call("recompute", doc_name=doc_name)

    @mcp.tool()
    def get_objects(ctx: Context, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """List all objects in a document with type and visibility."""
        return get_client().call("get_objects", doc_name=doc_name)

    @mcp.tool()
    def get_object(ctx: Context, obj_name: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """Get full properties of a single object."""
        return get_client().call("get_object", obj_name=obj_name, doc_name=doc_name)

    @mcp.tool()
    def delete_object(ctx: Context, obj_name: str, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """Delete an object and recompute."""
        return get_client().call("delete_object", obj_name=obj_name, doc_name=doc_name)

    @mcp.tool()
    def rename_object(
        ctx: Context, obj_name: str, new_label: str,
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rename an object's user-facing Label. The internal Name is
        immutable; FreeCAD auto-suffixes Label collisions (e.g. Bracket001).
        """
        return get_client().call(
            "rename_object", obj_name=obj_name, new_label=new_label, doc_name=doc_name,
        )

    @mcp.tool()
    def rename_objects(
        ctx: Context, renames: List[Dict[str, str]],
        doc_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Batch-rename multiple objects. ``renames`` items: ``{"name": "<id>", "label": "<new>"}``."""
        return get_client().call(
            "rename_objects", renames=renames, doc_name=doc_name,
        )
