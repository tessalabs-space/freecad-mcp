# freecad-mcp

**A Model Context Protocol server that gives Claude a real CAD system to work with.**

Point Claude at FreeCAD and it stops pretending to reason about geometry
in prose — it builds parametric parts, runs design sweeps, produces
manufacturing-ready drawings, prepares models for simulation, and hands
finished scenes to downstream renderers. All the tools engineers already
use, driven by natural language.

Published by **[TESSA LABS](https://tessalabs.space)**. MIT licensed.
Extends the addon shell and RPC pattern from
[neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp) with a
large, typed tool surface purpose-built for engineering workflows.

---

## What you can ask Claude to do

Short answer: almost anything you'd do in FreeCAD, plus a lot that
would normally take hours of Python scripting. Here are five prompts —
paste any of them into Claude once the server is running and watch the
model appear.

### 1. Parametric CAD from scratch

> *Build me a 120×60×10 mm aluminium mounting bracket with four M4
> clearance holes (4.2 mm) 10 mm inset from the corners, 3 mm fillets
> on the outer edges. Assign Aluminium 6061-T6, give me mass properties,
> and an isometric render at 2400×1600.*

Claude creates a sketch, extrudes, adds the hole pattern with a
boolean cut, fillets the edges, assigns the material, computes the
mass from the library density, and drops a render PNG into your temp
folder. One prompt, done.

### 2. Design sweep + trade study

> *Sweep the bracket thickness from 4 to 14 mm in 2 mm steps. Export
> each configuration as STEP into `C:/sweeps/bracket`, capture mass at
> every step, and tell me which thickness hits a 150 g target.*

Uses `parametric_sweep` to vary the `Length` property of the extrude,
recompute the document, export each config, record mass, then presents
the trade-off table with a recommendation.

### 3. Manufacturing-ready drawing

> *Create a manufacturing drawing for the bracket titled "Bracket v1 —
> design review", A3 landscape, with a third-angle projection group,
> isometric view, overall dimensions on the front view, and export to
> `C:/out/bracket_drawing.pdf`.*

`create_manufacturing_drawing` creates the sheet with a standard ISO
template, lays out Front + Top + Right in correct third-angle
projection (no manual X/Y juggling), drops the iso in the top-right,
populates the title block (part name, scale, date, material, drawing
number), and writes the PDF. Auto-scales to fit the page.

### 4. Simplify a CAD import for analysis

> *Open `C:/cad/housing_v2.step`. Tell me what small features it has.
> Remove every cylindrical hole under 6 mm diameter, every fillet under
> 2 mm, and every bolt you can find. Keep the original intact. Then tag
> the `+Z` face as a radiator surface and export for Elmer thermal
> analysis.*

The defeaturing tools (`find_holes`, `find_fillets`, `find_fasteners`)
all preview first so nothing is destroyed silently. BC tags
(`tag_boundary_by_normal`) let you mark faces with a direction; the
tag survives through to the `.sif` Elmer case file.

### 5. Cinematic render with callouts

> *Position the view isometric on the assembly. Add yellow arrow
> callouts to the top cover, main board, and mounting bracket. Render
> a 4K hero shot, then a 180-frame turntable at 1080p.*

Leader arrows with auto-routing. Turntable frames go to a directory
as PNGs — feed them to `ffmpeg` for an MP4. For a truly cinematic
render, `export_for_blender` writes a glTF with a sidecar JSON
carrying materials and BC tags so a companion Blender MCP can apply
PBR shaders.

---

## Capability map

| Group | Tools |
| --- | --- |
| **Geometry** | primitives (box / cylinder / sphere / cone / torus / plane / wedge / ellipsoid / prism), booleans (fuse / cut / common), fillet, chamfer, thickness, draft, mirror, translate, rotate |
| **Sketches** | sketch creation on XY / XZ / YZ or custom placement, line / circle / rectangle, Sketcher constraints (coincident, horizontal, vertical, parallel, tangent, distance, radius, angle) |
| **Part** | extrude, revolve, loft, sweep |
| **I/O** | STEP, IGES, STL, BREP, OBJ, FCStd with optional round-trip tolerance reporting |
| **Parametric studies** | `parametric_sweep` (single property), `spreadsheet_sweep` (expression-linked) |
| **Drawings** | `create_manufacturing_drawing` (one-shot), `create_projection_group` (third-angle layout), `add_drawing_view`, `add_drawing_dimension`, PDF / SVG export |
| **Reports** | `generate_report` (Markdown with renders + tables), `mass_budget`, `compare_documents` (structural FCStd diff) |
| **Annotations** | leader callouts with auto-routing, Draft dimensions, section cuts, exploded views |
| **Renders** | screenshots, PNG renders at configurable quality, turntable animations, keyframe camera paths |
| **Materials** | curated library (aluminium, copper, stainless, Ti, Invar, Si, FR4, CFRP, Kapton, MLI, thermal coatings, fluids) with density / k / Cp / E / ν / CTE / emissivity — assignable per object or face |
| **BC tagging** | named face groups (inlet / outlet / wall / radiator / fixture / load / heat source / heat sink / ...) — carried through to solver exports |
| **Defeaturing** | find / remove holes, fillets, chamfers, fasteners (label + shape fingerprint), thin bodies |
| **Analysis prep** | mid-surface extraction, symmetry detection, external-shell extraction, contact-face identification, imprint / merge for conformal meshes |
| **Solvers** | Elmer (heat / flow / elasticity), CalculiX, OpenFOAM (tagged STL + snappyHexMesh manifest), DEM (Yade / LIGGGHTS / MFIX) |
| **Load cases** | modal analysis, quasi-static acceleration, random vibration (PSD sidecar) |
| **Bridges** | Blender (glTF + scene.json sidecar with materials and BC tags) |
| **Inspection** | mass properties, centre of gravity, clash detection, distance-to, parametric-expression dump |
| **Headless mode** | optional — import FreeCAD as a Python module for batch ops in CI, no GUI |

Full alphabetised tool reference: [docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md).

---

## Install

### 1. Install the MCP server

```bash
git clone https://github.com/tessalabs-space/freecad-mcp
cd freecad-mcp
uv sync
```

### 2. Install the FreeCAD addon

Copy `addon/FreeCADMCP/` into FreeCAD's user Mod folder. On **FreeCAD
1.x** this is a versioned path:

- **Windows**: `%APPDATA%\FreeCAD\v1-1\Mod\FreeCADMCP\`
- **macOS**: `~/Library/Application Support/FreeCAD/v1-1/Mod/FreeCADMCP/`
- **Linux**: `~/.local/share/FreeCAD/v1-1/Mod/FreeCADMCP/`

One-liner on Windows:

```powershell
xcopy /E /I addon\FreeCADMCP "$env:APPDATA\FreeCAD\v1-1\Mod\FreeCADMCP"
```

For FreeCAD 0.x the path is `%APPDATA%\FreeCAD\Mod\FreeCADMCP\` (no
`v1-1`). See [docs/INSTALL.md](docs/INSTALL.md) for every OS and for
the headless setup.

### 3. Wire Claude Desktop

The cleanest config pulls from GitHub via `uvx` — no working copy
needed, auto-updates on each Claude restart:

```jsonc
{
  "mcpServers": {
    "freecad": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/tessalabs-space/freecad-mcp",
        "freecad-mcp"
      ]
    }
  }
}
```

Or point at a local `.venv` if you prefer:

```jsonc
{
  "mcpServers": {
    "freecad": {
      "command": "/path/to/repo/.venv/bin/freecad-mcp"
    }
  }
}
```

### 4. Launch

1. Start FreeCAD.
2. Switch to the **FreeCAD MCP** workbench (top-left dropdown).
3. Click **Start RPC Server** — the Report view will show
   `FreeCAD MCP RPC listening on localhost:9875`.
4. Restart Claude Desktop so it picks up the new MCP entry.
5. Try `list_documents` in Claude.

---

## Architecture

```
┌──────────────────┐  stdio   ┌──────────────────────────┐  XML-RPC   ┌──────────────┐
│  Claude Desktop  │ ───────▶ │  freecad-mcp (FastMCP)   │ ────────▶ │  FreeCAD GUI │
│   (MCP client)   │          │  src/freecad_mcp         │ :9875      │  + addon     │
└──────────────────┘          └──────────────────────────┘            └──────────────┘
```

Two cooperating processes:

1. **FreeCAD addon** (`addon/FreeCADMCP/`) — a workbench that runs an
   XML-RPC server on `localhost:9875`. All GUI / OpenCASCADE /
   Coin3D work is dispatched to FreeCAD's Qt main thread through a
   task queue, so the RPC thread never touches thread-unsafe state.
2. **MCP server** (`src/freecad_mcp/`) — stdio MCP built on
   `fastmcp`. Each tool call forwards to the addon. Also supports a
   headless mode that imports FreeCAD as a Python module for batch
   geometry pipelines without a running GUI.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the detailed
design.

---

## Walkthroughs

| Topic | File |
| --- | --- |
| Build a simple bracket | [examples/01_build_simple_bracket.md](examples/01_build_simple_bracket.md) |
| Simplify a CAD import for analysis | [examples/02_simplify_for_thermal.md](examples/02_simplify_for_thermal.md) |
| Render with callouts and turntable | [examples/03_render_with_callouts.md](examples/03_render_with_callouts.md) |
| Export an Elmer thermal case | [examples/04_elmer_export.md](examples/04_elmer_export.md) |
| Parametric sweep | [examples/05_parametric_sweep.md](examples/05_parametric_sweep.md) |
| Drawings and a project report | [examples/06_drawings_and_report.md](examples/06_drawings_and_report.md) |

---

## Extending

Adding a new tool is a three-step recipe:

1. Implement the logic in
   `addon/FreeCADMCP/rpc_server/handlers/<domain>.py` and register it
   at the bottom of the module.
2. If it's a new domain, add it to the registry in
   `handlers/__init__.py`.
3. Add a thin wrapper in `src/freecad_mcp/tools/engineering.py` (or a
   sibling module in `tools/`) that forwards to the handler by name.

No protocol changes, no server restart needed (the MCP server reloads
per Claude session).

---

## Development

```bash
uv sync --extra dev
uv run pytest tests/
```

The smoke tests don't need FreeCAD running — they verify the client,
server, tool modules, and material library load cleanly.

---

## Credit

Addon shell, RPC pattern, and the Qt-main-thread task-queue design
originate from
[neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp).
Extended here with the full engineering tool surface described above.

Issues and pull requests welcome:
<https://github.com/tessalabs-space/freecad-mcp/issues>.

## License

MIT © 2026 TESSA LABS and contributors. See [LICENSE](LICENSE) for
details.
