"""FreeCAD MCP stdio server.

Registers tool groups against a shared FastMCP instance and proxies each
call to the FreeCAD addon over XML-RPC.
"""

from __future__ import annotations

import argparse
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from mcp.server.fastmcp import FastMCP

from .client import FreeCADClient
from .prompts import ENGINEERING_WORKFLOW
from .state import ServerState
from .tools import documents as tools_documents
from .tools import geometry as tools_geometry
from .tools import sketch as tools_sketch
from .tools import parts as tools_parts
from .tools import engineering as tools_engineering
from .tools import advanced as tools_advanced


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("freecad_mcp.server")


state = ServerState()


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    logger.info("freecad-mcp starting up")
    try:
        client = _get_client()
        if client.ping():
            logger.info("Connected to FreeCAD RPC at %s:%s", state.rpc_host, state.rpc_port)
        else:
            logger.warning(
                "FreeCAD RPC is not answering yet at %s:%s — start the "
                "FreeCAD MCP workbench server.",
                state.rpc_host, state.rpc_port,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not probe FreeCAD on startup: %s", exc)
    try:
        yield {}
    finally:
        if state.client is not None:
            state.client.disconnect()
            state.client = None
        logger.info("freecad-mcp shut down")


mcp = FastMCP(
    "freecad-mcp",
    instructions=(
        "Engineering-focused FreeCAD integration. Geometry, defeaturing, "
        "materials, BC tagging, annotations, animation, and solver export."
    ),
    lifespan=server_lifespan,
)


def _get_client() -> FreeCADClient:
    if state.client is None:
        state.client = FreeCADClient(state.rpc_host, state.rpc_port)
    return state.client


def _register_all() -> None:
    for module in (
        tools_documents,
        tools_geometry,
        tools_sketch,
        tools_parts,
        tools_engineering,
        tools_advanced,
    ):
        module.register(mcp, _get_client)


_register_all()


@mcp.prompt()
def engineering_workflow() -> str:
    """Opinionated workflow for using these tools end-to-end."""
    return ENGINEERING_WORKFLOW


def _validate_host(value: str) -> str:
    import argparse as _a

    import validators

    if validators.ipv4(value) or validators.ipv6(value) or validators.hostname(value):
        return value
    raise _a.ArgumentTypeError(f"Invalid host: {value!r}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="freecad-mcp")
    parser.add_argument("--host", type=_validate_host, default="localhost")
    parser.add_argument("--port", type=int, default=9875)
    parser.add_argument("--only-text-feedback", action="store_true")
    args = parser.parse_args()
    state.rpc_host = args.host
    state.rpc_port = args.port
    state.only_text_feedback = args.only_text_feedback
    logger.info("RPC target: %s:%s", state.rpc_host, state.rpc_port)
    mcp.run()


if __name__ == "__main__":
    main()
