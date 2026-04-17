"""Qt binding compatibility shim.

FreeCAD ships with different Qt bindings depending on version:
    * FreeCAD 1.1+   -> PySide6
    * FreeCAD 0.20 - 1.0 -> PySide2
    * Older builds / other distros -> PySide (FreeCAD's unified shim)

Import from this module instead of picking one directly.
"""

from __future__ import annotations


def _load():
    try:
        from PySide6 import QtCore, QtWidgets  # type: ignore
        return QtCore, QtWidgets
    except ImportError:
        pass
    try:
        from PySide2 import QtCore, QtWidgets  # type: ignore
        return QtCore, QtWidgets
    except ImportError:
        pass
    from PySide import QtCore, QtWidgets  # type: ignore
    return QtCore, QtWidgets


QtCore, QtWidgets = _load()
QTimer = QtCore.QTimer
QInputDialog = QtWidgets.QInputDialog
