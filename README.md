# freecad-mcp

*Published by **TESSA LABS**.*

An MCP server for FreeCAD. Claude drives the full CAD workflow:
parametric geometry, sketches, assemblies, drafting, annotation,
rendering, parametric studies, and export — with optional CAE side-tools
(defeaturing, material / boundary tagging, solver handoff) for when the
CAD feeds into thermal, CFD, or structural analysis.

Extends [neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp)
with a large, typed tool surface.

## Capabilities

**Parametric CAD**
- Primitives, booleans, fillet / chamfer / thickness / mirror, sketches
  with constraints, extrude / revolve / loft / sweep, transforms.
- `parametric_sweep` and `spreadsheet_sweep` iterate a property or cell
  through a list of values, optionally exporting each configuration.

**Drafting**
- TechDraw pages with orthographic + iso views, dimensions,
  PDF / SVG export.

**Import / export**
- STEP, IGES, STL, BREP, OBJ, FCStd — with optional round-trip
  tolerance reporting.

**Annotation and visuals**
- Leader callouts, Draft dimensions, section cuts, exploded views,
  screenshots, high-quality PNG renders, turntable + keyframe camera
  animations.

**Project management**
- `mass_budget` — per-object and aggregate mass + weighted CG using
  assigned-material densities.
- `generate_report` — Markdown project report with hero renders,
  object / material / BC / mass / clash tables.
- `compare_documents` — structural diff between two FCStd revisions.

**Analysis prep (when CAD feeds CAE)**
- Defeaturing: holes, fillets, chamfers, fasteners, thin bodies.
- Analysis prep: mid-surface extraction, symmetry detection, external
  shell, contact faces, imprint / merge.
- Materials: a curated library with density, conductivity, specific
  heat, Young's modulus, Poisson, CTE, emissivity.
- BC tagging: named face groups (inlet, outlet, wall, radiator,
  fixture, load, heat source, heat sink, ...) that flow through to
  solver exports.
- Load cases: `create_modal_analysis`, `create_static_acceleration_case`,
  `create_random_vibration_case`.
- Solver export: Elmer, CalculiX, OpenFOAM (tagged STL + manifest), DEM
  (Yade / LIGGGHTS / MFIX–ready STL + material manifest).
- Blender bridge: glTF + sidecar JSON so a companion Blender MCP can
  apply PBR materials and name collections automatically.

**Inspection**
- Mass properties, centre of gravity, clash detection, distance-to
  queries, parametric-expression dump.

**Headless mode**
- Optional: import FreeCAD as a Python module for batch geometry ops in
  CI / pipelines (no GUI features).

Full tool list: [docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md).

## Architecture

Two cooperating processes:

1. **FreeCAD addon** (`addon/FreeCADMCP/`) — workbench registered inside
   FreeCAD, serves XML-RPC on `localhost:9875`. GUI / OCC work runs on
   the Qt main thread via a task queue.
2. **MCP server** (`src/freecad_mcp/`) — stdio MCP built on `fastmcp`.
   Each tool call forwards to the addon.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design details.

## Install

```bash
# MCP server
git clone https://github.com/Tessalabs/freecad-mcp
cd freecad-mcp
uv sync

# FreeCAD addon (Windows)
xcopy /E /I addon\FreeCADMCP "%APPDATA%\FreeCAD\Mod\FreeCADMCP"
```

Claude Desktop config:

```jsonc
{
  "mcpServers": {
    "freecad": {
      "command": "<repo>/.venv/Scripts/freecad-mcp.exe"
    }
  }
}
```

Start FreeCAD → switch to the *FreeCAD MCP* workbench → click
**Start RPC Server**. First tool call connects.

Full install / macOS / Linux / headless instructions in
[docs/INSTALL.md](docs/INSTALL.md).

## Examples

- [Build a simple bracket](examples/01_build_simple_bracket.md)
- [Simplify a CAD import for analysis](examples/02_simplify_for_thermal.md)
- [Render with callouts](examples/03_render_with_callouts.md)
- [Elmer export](examples/04_elmer_export.md)
- [Parametric sweep](examples/05_parametric_sweep.md)
- [Drawings and a project report](examples/06_drawings_and_report.md)

## Credit

Addon shell, RPC pattern, and GUI task-queue design originate from
[neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp).

## License

MIT © 2026 TESSA LABS. See [LICENSE](LICENSE) for details.
