"""FreeCAD Gui commands wired into the workbench toolbar."""

from __future__ import annotations

import FreeCAD
import FreeCADGui

from .settings import load_settings, save_settings
from . import rpc_server as _rpc


class _StartServer:
    def GetResources(self):
        return {"MenuText": "Start RPC Server", "ToolTip": "Start FreeCAD MCP RPC server"}

    def IsActive(self):
        return not _rpc.is_running()

    def Activated(self):
        result = _rpc.start_server()
        if not result.get("success"):
            FreeCAD.Console.PrintError(result.get("error", "unknown error") + "\n")


class _StopServer:
    def GetResources(self):
        return {"MenuText": "Stop RPC Server", "ToolTip": "Stop FreeCAD MCP RPC server"}

    def IsActive(self):
        return _rpc.is_running()

    def Activated(self):
        _rpc.stop_server()


class _ToggleAutoStart:
    def GetResources(self):
        return {"MenuText": "Toggle Auto-Start", "ToolTip": "Auto-start the RPC server on launch"}

    def IsActive(self):
        return True

    def Activated(self):
        s = load_settings()
        s["auto_start"] = not s.get("auto_start", False)
        save_settings(s)
        FreeCAD.Console.PrintMessage(f"Auto-start: {s['auto_start']}\n")


class _ToggleRemote:
    def GetResources(self):
        return {
            "MenuText": "Toggle Remote Connections",
            "ToolTip": "Allow connections from non-localhost clients",
        }

    def IsActive(self):
        return True

    def Activated(self):
        s = load_settings()
        s["allow_remote"] = not s.get("allow_remote", False)
        save_settings(s)
        FreeCAD.Console.PrintMessage(f"Remote connections: {s['allow_remote']}\n")


class _ConfigureIPs:
    def GetResources(self):
        return {"MenuText": "Configure Allowed IPs", "ToolTip": "Edit the allowed-IP list"}

    def IsActive(self):
        return True

    def Activated(self):
        from .qt_compat import QInputDialog
        s = load_settings()
        current = ",".join(s.get("allowed_ips", []))
        text, ok_pressed = QInputDialog.getText(
            None, "Allowed IPs", "Comma-separated IPs / CIDR blocks:", text=current
        )
        if ok_pressed:
            s["allowed_ips"] = [p.strip() for p in text.split(",") if p.strip()]
            save_settings(s)


FreeCADGui.addCommand("MCP_Start_RPC_Server", _StartServer())
FreeCADGui.addCommand("MCP_Stop_RPC_Server", _StopServer())
FreeCADGui.addCommand("MCP_Toggle_Auto_Start", _ToggleAutoStart())
FreeCADGui.addCommand("MCP_Toggle_Remote_Connections", _ToggleRemote())
FreeCADGui.addCommand("MCP_Configure_Allowed_IPs", _ConfigureIPs())
