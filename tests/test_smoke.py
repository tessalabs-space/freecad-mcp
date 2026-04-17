"""Smoke tests that run without FreeCAD.

Validates the Python-only parts of the package: the client class builds,
the materials JSON parses, and the MCP server module imports without
connecting to anything.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "addon" / "FreeCADMCP" / "libs" / "materials.json"


def test_materials_library_parses():
    data = json.loads(MATERIALS.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert "materials" in data
    assert "Aluminum_6061_T6" in data["materials"]
    al = data["materials"]["Aluminum_6061_T6"]
    for key in ("density_kg_m3", "thermal_conductivity_W_mK", "emissivity"):
        assert key in al


def test_materials_categories_sane():
    data = json.loads(MATERIALS.read_text(encoding="utf-8"))
    categories = {m.get("category") for m in data["materials"].values()}
    expected = {"metal", "composite", "polymer", "thermal_coating", "fluid", "semiconductor"}
    assert categories <= expected, f"unexpected categories: {categories - expected}"


def test_client_constructs():
    from freecad_mcp.client import FreeCADClient

    c = FreeCADClient("localhost", 9875)
    assert c.url == "http://localhost:9875/RPC2"


def test_server_module_imports():
    # Must not connect to anything on import.
    import freecad_mcp.server as server  # noqa: F401

    assert server.mcp.name == "freecad-mcp"


def test_state_defaults():
    from freecad_mcp.state import ServerState

    s = ServerState()
    assert s.rpc_host == "localhost"
    assert s.rpc_port == 9875


@pytest.mark.parametrize(
    "module_name",
    [
        "freecad_mcp.tools.documents",
        "freecad_mcp.tools.geometry",
        "freecad_mcp.tools.sketch",
        "freecad_mcp.tools.parts",
        "freecad_mcp.tools.engineering",
        "freecad_mcp.tools.advanced",
    ],
)
def test_tool_modules_expose_register(module_name):
    import importlib

    mod = importlib.import_module(module_name)
    assert hasattr(mod, "register") and callable(mod.register)
