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


def keyframe_parts(
    output_dir: str,
    tracks: List[Dict[str, Any]],
    frames_between: int = 30,
    width: int = 1600,
    height: int = 1000,
    background: str = "Current",
    restore_on_finish: bool = True,
) -> Dict[str, Any]:
    """Animate one or more objects' Placements across keyframes.

    Each track describes one animated object:

        {
          "object": "Bracket",
          "keyframes": [
            {"pos": {x,y,z}, "rot": {axis:{x,y,z}, angle_deg: 0.0}},
            {"pos": {x,y,z}, "rot": {axis:{x,y,z}, angle_deg: 90.0}},
            ...
          ]
        }

    All tracks must have the same number of keyframes. For each pair of
    keyframes, ``frames_between`` interpolated frames are rendered — so
    N keyframes produce ``(N-1) * frames_between`` PNG frames.

    Rotation is linearly interpolated on axis + angle (no slerp yet;
    adequate for small-rotation previews). Starting placements are
    restored at the end when ``restore_on_finish`` is true.
    """
    import FreeCADGui
    view = FreeCADGui.ActiveDocument.ActiveView if FreeCADGui.ActiveDocument else None
    if view is None:
        return err("No active 3D view")
    if not tracks:
        return err("at least one track required")

    doc = FreeCAD.ActiveDocument
    if doc is None:
        return err("No active document")

    # Resolve all objects once, validate keyframe counts match.
    resolved: List[Dict[str, Any]] = []
    expected_kf = None
    for tr in tracks:
        obj = doc.getObject(tr.get("object", ""))
        if obj is None:
            return err(f"Track object not found: {tr.get('object')}")
        kfs = tr.get("keyframes") or []
        if expected_kf is None:
            expected_kf = len(kfs)
        elif len(kfs) != expected_kf:
            return err("All tracks must have the same number of keyframes")
        if len(kfs) < 2:
            return err(f"Track '{obj.Name}' needs ≥ 2 keyframes")
        resolved.append({"obj": obj, "keyframes": kfs, "original": obj.Placement})

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rendered: List[str] = []
    idx = 0
    segments = expected_kf - 1
    try:
        for seg in range(segments):
            for step in range(frames_between):
                t = step / float(frames_between)
                for tr in resolved:
                    a = tr["keyframes"][seg]
                    b = tr["keyframes"][seg + 1]
                    tr["obj"].Placement = _interp_placement(a, b, t)
                doc.recompute()
                path = str(out / f"frame_{idx:04d}.png")
                view.saveImage(path, int(width), int(height), background)
                rendered.append(path)
                idx += 1
        # Always render the final keyframe as the last frame.
        for tr in resolved:
            tr["obj"].Placement = _placement_from_kf(tr["keyframes"][-1])
        doc.recompute()
        final_path = str(out / f"frame_{idx:04d}.png")
        view.saveImage(final_path, int(width), int(height), background)
        rendered.append(final_path)
    finally:
        if restore_on_finish:
            for tr in resolved:
                tr["obj"].Placement = tr["original"]
            doc.recompute()

    return ok(
        frames_rendered=len(rendered),
        directory=str(out),
        tracks=[tr["obj"].Name for tr in resolved],
    )


def _lerp_vec(a: Dict[str, float], b: Dict[str, float], t: float) -> FreeCAD.Vector:
    return FreeCAD.Vector(
        a["x"] + (b["x"] - a["x"]) * t,
        a["y"] + (b["y"] - a["y"]) * t,
        a["z"] + (b["z"] - a["z"]) * t,
    )


def _coin_vec(v: Dict[str, float]):
    from pivy import coin  # type: ignore
    return coin.SbVec3f(float(v["x"]), float(v["y"]), float(v["z"]))


def _placement_from_kf(kf: Dict[str, Any]) -> FreeCAD.Placement:
    pos = kf.get("pos") or {"x": 0, "y": 0, "z": 0}
    rot = kf.get("rot") or {}
    axis = rot.get("axis") or {"x": 0, "y": 0, "z": 1}
    angle = float(rot.get("angle_deg", 0.0))
    return FreeCAD.Placement(
        FreeCAD.Vector(float(pos["x"]), float(pos["y"]), float(pos["z"])),
        FreeCAD.Rotation(
            FreeCAD.Vector(float(axis["x"]), float(axis["y"]), float(axis["z"])),
            angle,
        ),
    )


def _interp_placement(a: Dict[str, Any], b: Dict[str, Any], t: float) -> FreeCAD.Placement:
    """Linear blend of two keyframe placements at parameter ``t`` ∈ [0,1]."""
    pos = _lerp_vec(a.get("pos") or {"x": 0, "y": 0, "z": 0},
                    b.get("pos") or {"x": 0, "y": 0, "z": 0}, t)
    a_rot = a.get("rot") or {}
    b_rot = b.get("rot") or {}
    axis_a = a_rot.get("axis") or {"x": 0, "y": 0, "z": 1}
    axis_b = b_rot.get("axis") or {"x": 0, "y": 0, "z": 1}
    axis = _lerp_vec(axis_a, axis_b, t)
    if axis.Length < 1e-9:
        axis = FreeCAD.Vector(0, 0, 1)
    ang_a = float(a_rot.get("angle_deg", 0.0))
    ang_b = float(b_rot.get("angle_deg", 0.0))
    angle = ang_a + (ang_b - ang_a) * t
    return FreeCAD.Placement(pos, FreeCAD.Rotation(axis, angle))


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "turntable": turntable,
            "keyframe_camera": keyframe_camera,
            "keyframe_parts": keyframe_parts,
        }
    )
