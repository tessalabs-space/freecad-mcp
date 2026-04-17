"""Escape-hatch: execute arbitrary Python inside the FreeCAD GUI process.

Use this sparingly — prefer a typed handler when the pattern recurs.
"""

from __future__ import annotations

import contextlib
import io
import traceback
from typing import Any, Dict

import FreeCAD

from ..utils import ok, err


def execute_code(code: str) -> Dict[str, Any]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    ns: Dict[str, Any] = {"FreeCAD": FreeCAD, "App": FreeCAD}
    try:
        import FreeCADGui
        ns["FreeCADGui"] = FreeCADGui
        ns["Gui"] = FreeCADGui
    except Exception:
        pass
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(compile(code, "<mcp-exec>", "exec"), ns)
    except Exception as exc:
        return err(str(exc), traceback=traceback.format_exc(), stdout=stdout.getvalue(), stderr=stderr.getvalue())
    return ok(stdout=stdout.getvalue(), stderr=stderr.getvalue())


def register(r: Dict[str, Any]) -> None:
    r.update({"execute_code": execute_code})
