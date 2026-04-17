from dataclasses import dataclass
from typing import Optional


@dataclass
class ServerState:
    rpc_host: str = "localhost"
    rpc_port: int = 9875
    only_text_feedback: bool = False
    screenshot_on_change: bool = True
    client: Optional["FreeCADClient"] = None  # noqa: F821 — forward ref
