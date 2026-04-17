# Architecture

```
┌──────────────────────┐     stdio        ┌──────────────────────────┐
│  Claude Desktop      │ ◀───────────▶    │  freecad-mcp (FastMCP)   │
│  (MCP client)        │                  │  src/freecad_mcp         │
└──────────────────────┘                  └────────────┬─────────────┘
                                                       │ XML-RPC
                                                       │ (localhost:9875)
                                          ┌────────────▼─────────────┐
                                          │  FreeCADMCP addon         │
                                          │  addon/FreeCADMCP         │
                                          │   ├─ rpc_server.py        │
                                          │   ├─ task_queue.py        │
                                          │   └─ handlers/…           │
                                          └────────────┬─────────────┘
                                                       │ Qt signal
                                                       │ (main thread)
                                          ┌────────────▼─────────────┐
                                          │  FreeCAD GUI              │
                                          │  (OCC + Coin3D)           │
                                          └──────────────────────────┘
```

## Why two processes?

FreeCAD's OpenCASCADE and Coin3D are not thread-safe. Any call that
touches geometry, the document tree, or the 3D view must execute on the
Qt main thread. Running the MCP server *inside* FreeCAD would block the
GUI event loop while tool calls are in flight — so instead we keep the
MCP server standalone (one process per Claude session) and drive FreeCAD
over XML-RPC.

## GUI-thread safety

The XML-RPC server runs on a worker thread. Every registered handler is
wrapped so its actual body runs through `task_queue.run_on_gui`, which:

1. Enqueues the callable.
2. Wakes a `QTimer.singleShot(0, _pump)` on the main thread.
3. Blocks the worker thread on a `threading.Event` until the pump
   completes the callable.
4. Returns the result (or re-raises the exception) on the worker thread.

Net effect: callers see a synchronous RPC call, FreeCAD sees all work
arriving serially on the main thread.

## Handler layout

`addon/FreeCADMCP/rpc_server/handlers/` has one module per domain:

| Module | Purpose |
| --- | --- |
| `documents.py` | doc create / open / save / close / list |
| `geometry.py` | primitives, booleans, fillet / chamfer / thickness / mirror / transforms |
| `sketch.py` | sketches + constraints |
| `parts.py` | extrude, revolve, loft, sweep |
| `io.py` | STEP / IGES / STL / BREP / OBJ / FCStd |
| `defeaturing.py` | holes, fillets, chamfers, fasteners, thin bodies |
| `analysis_prep.py` | mid-surface, symmetry, external shell, contact, imprint |
| `materials.py` | curated library + assignment |
| `bc_tagging.py` | named face groups for solvers |
| `inspection.py` | mass / CoG / clash / distances / expressions |
| `annotations.py` | leader callouts + dimensions |
| `views.py` | view direction, screenshot, section cut, explode |
| `animation.py` | turntable + keyframe camera |
| `render.py` | PNG render |
| `fem_export.py` | Elmer, CalculiX, OpenFOAM STL |
| `blender_bridge.py` | glTF + sidecar JSON for downstream Blender MCP |
| `execute.py` | arbitrary Python escape hatch |

Each module exposes a `register(r)` function that adds its callables to
the shared handler registry. `handlers/__init__.py:registry()` returns
the combined dict, which `rpc_server.py` serves as XML-RPC methods.

## MCP tool layout

`src/freecad_mcp/tools/` mirrors the above, but most tools are thin
wrappers — see `engineering.py` for the one-file grouping of non-basic
tools. Each tool forwards to exactly one handler over XML-RPC.

## Extending

Add a new tool in three steps:

1. Implement the logic in `addon/FreeCADMCP/rpc_server/handlers/<domain>.py`,
   and register it at the bottom of the module.
2. Add it to the imports / loop in `handlers/__init__.py` if you created
   a new module.
3. Add a thin wrapper in `src/freecad_mcp/tools/engineering.py` (or a
   sibling module) that forwards to the handler by name.

No protocol changes, no server restart needed (MCP servers reload per
Claude session).
