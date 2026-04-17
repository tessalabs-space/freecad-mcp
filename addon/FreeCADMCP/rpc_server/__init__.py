"""FreeCAD addon RPC server package.

Layout:
    rpc_server.py   — XML-RPC server bootstrap + GUI task-queue pump.
    task_queue.py   — Thread-safe queue that shunts callables onto FreeCAD's
                      Qt main thread. All GUI / OCC / Coin3D work must go
                      through this.
    settings.py     — Persistent settings (JSON on disk).
    commands.py     — FreeCAD Gui commands wired into the workbench toolbar.
    utils.py        — Shared helpers (property setters, object lookup,
                      placement parsing, response envelopes).
    handlers/       — One module per feature domain (geometry, defeaturing,
                      materials, annotations, ...). Each exposes functions
                      that are registered on the RPC dispatcher.
"""
