import FreeCAD
import FreeCADGui


class FreeCADMCPWorkbench(FreeCADGui.Workbench):
    MenuText = "FreeCAD MCP"
    ToolTip = "Engineering MCP server for FreeCAD"
    Icon = ""

    def Initialize(self):
        from rpc_server import commands  # noqa: F401 — registers Gui commands

        cmds = [
            "MCP_Start_RPC_Server",
            "MCP_Stop_RPC_Server",
            "MCP_Toggle_Auto_Start",
            "MCP_Toggle_Remote_Connections",
            "MCP_Configure_Allowed_IPs",
        ]
        self.appendToolbar("FreeCAD MCP", cmds)
        self.appendMenu("FreeCAD MCP", cmds)

    def Activated(self):
        FreeCAD.Console.PrintMessage("FreeCAD MCP workbench activated\n")

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(FreeCADMCPWorkbench())


def _auto_start_mcp():
    """If auto-start is enabled in settings, launch the RPC server."""
    try:
        from rpc_server.settings import load_settings
        from rpc_server.rpc_server import start_server

        settings = load_settings()
        if settings.get("auto_start", False):
            start_server()
            FreeCAD.Console.PrintMessage("FreeCAD MCP RPC server auto-started\n")
    except Exception as exc:
        FreeCAD.Console.PrintWarning(f"FreeCAD MCP auto-start failed: {exc}\n")


from rpc_server.qt_compat import QTimer  # type: ignore

QTimer.singleShot(0, _auto_start_mcp)
