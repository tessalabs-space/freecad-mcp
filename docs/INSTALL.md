# Install

## 1. Install the MCP server

```bash
git clone https://github.com/Tessalabs/freecad-mcp
cd freecad-mcp
uv sync
```

## 2. Install the FreeCAD addon

Copy `addon/FreeCADMCP/` into your FreeCAD `Mod/` directory:

- **Windows**: `%APPDATA%\FreeCAD\Mod\FreeCADMCP\`
- **macOS**: `~/Library/Application Support/FreeCAD/Mod/FreeCADMCP/`
- **Linux**: `~/.local/share/FreeCAD/Mod/FreeCADMCP/` (or `~/.FreeCAD/Mod/FreeCADMCP/` on older builds)

One-liners:

```bash
# Windows (PowerShell)
xcopy /E /I addon\FreeCADMCP "$env:APPDATA\FreeCAD\Mod\FreeCADMCP"

# macOS / Linux
cp -R addon/FreeCADMCP "$HOME/Library/Application Support/FreeCAD/Mod/FreeCADMCP"
# or on Linux:
cp -R addon/FreeCADMCP "$HOME/.local/share/FreeCAD/Mod/FreeCADMCP"
```

## 3. Start FreeCAD and the server

1. Launch FreeCAD.
2. Switch to the **FreeCAD MCP** workbench (dropdown at the top of the
   toolbar).
3. Click **Start RPC Server** (or enable **Toggle Auto-Start** to launch on
   each FreeCAD start).

The server listens on `localhost:9875` by default. To change port or allow
remote connections, edit `%APPDATA%\FreeCAD\FreeCADMCP\settings.json`.

## 4. Configure Claude Desktop

```jsonc
{
  "mcpServers": {
    "freecad": {
      "command": "uvx",
      "args": ["--from", "C:/Users/<you>/Documents/projects/freecad-mcp", "freecad-mcp"]
    }
  }
}
```

If `uvx` isn't on PATH, use the absolute path to the `uv` binary.

## 5. Verify

In Claude, call:

```
list_documents
```

You should get `{"documents": []}` (or whatever FreeCAD has open). Then:

```
create_document name=Test
create_primitive kind=box name=Block properties={"Length": 50, "Width": 30, "Height": 10}
screenshot
```

## Headless mode (optional)

Install FreeCAD and make its `bin/` directory importable from Python:

```bash
uv sync --extra headless
export PYTHONPATH="/path/to/FreeCAD/bin:$PYTHONPATH"  # or use headless.ensure_available()
```

Then in your own script:

```python
from freecad_mcp import headless
headless.ensure_available()
doc = headless.new_document("batch")
headless.run_handler(
    "create_primitive",
    kind="box", name="Box", doc_name=doc.Name,
    properties={"Length": 50, "Width": 30, "Height": 10},
)
```

Not all handlers work headless — anything that touches the 3D view
(`set_view`, `screenshot`, `render_png`, `turntable`, `add_callout`, ...)
requires the GUI.
