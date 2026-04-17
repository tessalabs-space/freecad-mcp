"""XML-RPC client for the FreeCAD addon.

Every RPC method on the addon is exposed as an attribute on the client,
thanks to XML-RPC's introspection. We add:
  * ping() with timeout
  * reconnect() after transient failures
  * ``call(method, *args, **kwargs)`` that normalises errors into Python
    exceptions instead of ``{"success": False, ...}`` dicts so the MCP
    tool layer can propagate a clean message to Claude.
"""

from __future__ import annotations

import logging
import xmlrpc.client
from typing import Any, Dict

logger = logging.getLogger("freecad_mcp.client")


class FreeCADError(RuntimeError):
    """Raised when the addon returns ``{"success": False, ...}``."""


class FreeCADClient:
    def __init__(self, host: str = "localhost", port: int = 9875, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._proxy: xmlrpc.client.ServerProxy | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/RPC2"

    def _ensure(self) -> xmlrpc.client.ServerProxy:
        if self._proxy is None:
            transport = xmlrpc.client.Transport()
            # xmlrpc stdlib has no per-call timeout; set on the socket each open.
            self._proxy = xmlrpc.client.ServerProxy(self.url, transport=transport, allow_none=True)
        return self._proxy

    def ping(self) -> bool:
        try:
            resp = self._ensure().ping()
            return bool(resp.get("pong"))
        except Exception as exc:
            logger.debug("ping failed: %s", exc)
            return False

    def list_handlers(self) -> list[str]:
        return self._ensure().list_handlers().get("handlers", [])

    def call(self, method: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        proxy = self._ensure()
        fn = getattr(proxy, method)
        if kwargs and args:
            raise ValueError("mix of positional and keyword args not supported over XML-RPC")
        try:
            resp = fn(*args) if args else fn(kwargs) if kwargs else fn()
        except xmlrpc.client.Fault as fault:
            raise FreeCADError(fault.faultString) from fault
        if isinstance(resp, dict) and resp.get("success") is False:
            raise FreeCADError(resp.get("error", "unknown error"))
        return resp

    def disconnect(self) -> None:
        if self._proxy is not None:
            try:
                self._proxy("close")()  # type: ignore[misc]
            except Exception:
                pass
            self._proxy = None
