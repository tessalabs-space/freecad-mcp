"""Turntable and keyframed camera animation.

Renders a sequence of PNG frames to a directory. Downstream, ffmpeg turns
them into an mp4 or webm — we keep encoding out of the addon to avoid a
hard ffmpeg dependency.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import FreeCAD

from ..utils import ok, err


def turntable(
    output_dir: str,
    frames: int = 60,
    axis: str = "Z",
    width: int = 1600,
    height: int = 1000,
    background: str = "Current",
    focus_object: Optional[str] = None,
) -> Dict[str, Any]:
    """Render ``frames`` images rotating the camera around ``axis`` through
    360°. Writes ``frame_0000.png`` … ``frame_NNNN.png`` to ``output_dir``.
    """
    import FreeCADGui
    view = FreeCADGui.ActiveDocument.ActiveView if FreeCADGui.ActiveDocument else None
    if view is None:
        return err("No active 3D view")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    axis_vec = {
        "X": FreeCAD.Vector(1, 0, 0),
        "Y": FreeCAD.Vector(0, 1, 0),
        "Z": FreeCAD.Vector(0, 0, 1),
    }.get(axis.upper())
    if axis_vec is None:
        return err(f"Unknown axis '{axis}'")

    if focus_object:
        import FreeCADGui as _Gui
        doc = FreeCAD.ActiveDocument
        if doc and doc.getObject(focus_object):
            _Gui.Selection.clearSelection()
            _Gui.Selection.addSelection(doc.getObject(focus_object))
            FreeCADGui.SendMsgToActiveView("ViewSelection")

    step = 360.0 / max(frames, 1)
    rendered = []
    for i in range(frames):
        try:
            cam = view.getCamera()
        except Exception:
            cam = None
        view.getCameraNode().orientation = view.getCameraNode().orientation  # keep binding alive
        view.getCameraNode().orientation.setValue(
            axis_vec.x, axis_vec.y, axis_vec.z, math.radians(i * step)
        )
        path = str(out / f"frame_{i:04d}.png")
        view.saveImage(path, int(width), int(height), background)
        rendered.append(path)

    return ok(frames_rendered=len(rendered), directory=str(out))


def keyframe_camera(
    output_dir: str,
    keyframes: List[Dict[str, Any]],
    frames_between: int = 30,
    width: int = 1600,
    height: int = 1000,
    background: str = "Current",
) -> Dict[str, Any]:
    """Interpolate the camera through a list of keyframes.

    Each keyframe is ``{"pos": {x,y,z}, "target": {x,y,z}}``. Linear
    interpolation only for v1 — swap in slerp + bezier later.
    """
    import FreeCADGui
    view = FreeCADGui.ActiveDocument.ActiveView if FreeCADGui.ActiveDocument else None
    if view is None:
        return err("No active 3D view")
    if len(keyframes) < 2:
        return err("at least two keyframes required")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rendered: List[str] = []
    idx = 0
    for a, b in zip(keyframes, keyframes[1:]):
        for step in range(frames_between):
            t = step / float(frames_between)
            pos = _lerp_vec(a["pos"], b["pos"], t)
            target = _lerp_vec(a["target"], b["target"], t)
            view.viewTop()
            try:
                view.setCameraOrientation(
                    FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0)
                )
                cam = view.getCameraNode()
                cam.position.setValue(pos.x, pos.y, pos.z)
                cam.pointAt(_coin_vec(target))
            except Exception:
                pass
            path = str(out / f"frame_{idx:04d}.png")
            view.saveImage(path, int(width), int(height), background)
            rendered.append(path)
            idx += 1
    return ok(frames_rendered=len(rendered), directory=str(out))


def _lerp_vec(a: Dict[str, float], b: Dict[str, float], t: float) -> FreeCAD.Vector:
    return FreeCAD.Vector(
        a["x"] + (b["x"] - a["x"]) * t,
        a["y"] + (b["y"] - a["y"]) * t,
        a["z"] + (b["z"] - a["z"]) * t,
    )


def _coin_vec(v: Dict[str, float]):
    from pivy import coin  # type: ignore
    return coin.SbVec3f(float(v["x"]), float(v["y"]), float(v["z"]))


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "turntable": turntable,
            "keyframe_camera": keyframe_camera,
        }
    )
