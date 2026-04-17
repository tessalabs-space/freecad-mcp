"""XML-RPC server for the FreeCAD MCP addon.

Only this module touches networking. Handlers registered here all route
through ``task_queue.run_on_gui`` so GUI / OCC state is touched solely on
the Qt main thread.
"""

from __future__ import annotations

import ipaddress
import logging
import threading
from socketserver import ThreadingMixIn
from typing import Any, Callable, Dict, Optional
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

import FreeCAD

from .settings import load_settings
from .task_queue import run_on_gui, ensure_pump
from .handlers import registry


logger = logging.getLogger("FreeCADMCP.rpc")


class _IPFilterRequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/RPC2", "/")

    def _client_allowed(self) -> bool:
        cfg = load_settings()
        if not cfg.get("allow_remote", False):
            return self.client_address[0] in ("127.0.0.1", "::1", "localhost")
        try:
            client = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        for entry in cfg.get("allowed_ips", []):
            try:
                if "/" in entry:
                    if client in ipaddress.ip_network(entry, strict=False):
                        return True
                elif client == ipaddress.ip_address(entry):
                    return True
            except ValueError:
                continue
        return False

    def parse_request(self) -> bool:  # noqa: D401 — stdlib override
        if not SimpleXMLRPCRequestHandler.parse_request(self):
            return False
        if not self._client_allowed():
            self.send_error(403, "Forbidden")
            return False
        return True


class _ThreadingXMLRPC(ThreadingMixIn, SimpleXMLRPCServer):
    daemon_threads = True
    allow_reuse_address = True


_server: Optional[_ThreadingXMLRPC] = None
_thread: Optional[threading.Thread] = None


def _wrap_gui(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a handler so the RPC worker thread runs it on the GUI thread.

    XML-RPC only sends positional args; the MCP client sends a single dict
    positional when the caller used kwargs, so unpack that here.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
                return run_on_gui(fn, **args[0])
            return run_on_gui(fn, *args, **kwargs)
        except Exception as exc:  # surfaced as XML-RPC fault
            logger.exception("Handler %s failed", getattr(fn, "__name__", fn))
            return {"success": False, "error": str(exc)}

    wrapper.__name__ = getattr(fn, "__name__", "rpc_wrapper")
    return wrapper


def _register_handlers(server: _ThreadingXMLRPC) -> None:
    for name, fn in registry().items():
        server.register_function(_wrap_gui(fn), name)
    server.register_function(lambda: {"success": True, "pong": True}, "ping")
    server.register_function(
        lambda: {"success": True, "handlers": sorted(registry().keys())},
        "list_handlers",
    )
    server.register_introspection_functions()


def start_server(host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    global _server, _thread
    if _server is not None:
        return {"success": False, "error": "RPC server already running"}
    ensure_pump()
    cfg = load_settings()
    h = host or ("0.0.0.0" if cfg.get("allow_remote") else cfg.get("host", "localhost"))
    p = int(port or cfg.get("port", 9875))
    _server = _ThreadingXMLRPC((h, p), requestHandler=_IPFilterRequestHandler, logRequests=False)
    _register_handlers(_server)
    _thread = threading.Thread(target=_server.serve_forever, name="FreeCADMCP-RPC", daemon=True)
    _thread.start()
    FreeCAD.Console.PrintMessage(f"FreeCAD MCP RPC listening on {h}:{p}\n")
    return {"success": True, "host": h, "port": p}


def stop_server() -> Dict[str, Any]:
    global _server, _thread
    if _server is None:
        return {"success": False, "error": "RPC server is not running"}
    _server.shutdown()
    _server.server_close()
    _server = None
    _thread = None
    FreeCAD.Console.PrintMessage("FreeCAD MCP RPC stopped\n")
    return {"success": True}


def is_running() -> bool:
    return _server is not None
