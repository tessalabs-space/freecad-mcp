"""Encode a directory of PNG frames into a video via ffmpeg.

ffmpeg is a soft dependency — it's not bundled with FreeCAD. If the
binary isn't on PATH (or at ``ffmpeg_path``), we return an error with a
pointer to installation docs instead of raising. Keeps the rest of the
addon usable on a fresh machine.

Output format is chosen by the extension of ``output_path``:
  - ``.mp4``    H.264 via libx264 (yuv420p, faststart) — default.
  - ``.webm``   VP9 via libvpx-vp9.
  - ``.gif``    palette-generated GIF for small previews.
  - ``.mov``    ProRes-friendly container.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils import ok, err


_SUPPORTED_EXTS = {".mp4", ".webm", ".gif", ".mov", ".mkv"}


def encode_video(
    frames_dir: str,
    output_path: str,
    fps: int = 30,
    pattern: str = "frame_%04d.png",
    crf: int = 18,
    ffmpeg_path: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run ffmpeg on a frame directory.

    Defaults produce a visually lossless H.264 mp4 (crf=18, yuv420p,
    faststart). Override ``extra_args`` for custom filters / codecs.
    """
    ext = os.path.splitext(output_path)[1].lower()
    if ext not in _SUPPORTED_EXTS:
        return err(
            f"Unsupported video extension '{ext}'",
            supported=sorted(_SUPPORTED_EXTS),
        )

    ffmpeg = ffmpeg_path or shutil.which("ffmpeg")
    if not ffmpeg:
        return err(
            "ffmpeg binary not found on PATH",
            hint="install ffmpeg (apt/brew/winget/scoop) or pass ffmpeg_path explicitly",
        )

    src_dir = Path(frames_dir)
    if not src_dir.is_dir():
        return err(f"Frames directory not found: {frames_dir}")
    # Sanity check: at least one PNG must exist matching the pattern.
    if not any(src_dir.glob(pattern.replace("%04d", "[0-9][0-9][0-9][0-9]"))):
        # Fallback: accept any .png in the directory.
        pngs = sorted(src_dir.glob("*.png"))
        if not pngs:
            return err(f"No PNG frames found in {frames_dir}")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if ext == ".gif":
        cmd = _build_gif_cmd(ffmpeg, src_dir, pattern, fps, out_path)
    else:
        cmd = _build_video_cmd(
            ffmpeg, src_dir, pattern, fps, ext, int(crf), out_path, extra_args or [],
        )

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False,
        )
    except Exception as exc:
        return err(f"ffmpeg invocation failed: {exc}", cmd=cmd)
    if proc.returncode != 0:
        return err(
            f"ffmpeg exited {proc.returncode}",
            cmd=cmd,
            stderr_tail=proc.stderr[-1500:] if proc.stderr else "",
        )
    size = out_path.stat().st_size if out_path.exists() else 0
    return ok(
        path=str(out_path),
        format=ext.lstrip("."),
        bytes=size,
        fps=int(fps),
        frames_glob=pattern,
    )


def ffmpeg_available(ffmpeg_path: Optional[str] = None) -> Dict[str, Any]:
    """Probe for ffmpeg — useful to gate workflows in callers."""
    ffmpeg = ffmpeg_path or shutil.which("ffmpeg")
    if not ffmpeg:
        return ok(available=False, path=None)
    try:
        proc = subprocess.run(
            [ffmpeg, "-version"], capture_output=True, text=True, check=False, timeout=10,
        )
        first_line = (proc.stdout or "").splitlines()[0] if proc.stdout else ""
        return ok(available=True, path=ffmpeg, version=first_line)
    except Exception as exc:
        return ok(available=False, path=ffmpeg, error=str(exc))


def _build_video_cmd(
    ffmpeg: str, src_dir: Path, pattern: str, fps: int,
    ext: str, crf: int, out_path: Path, extra_args: List[str],
) -> List[str]:
    codec_args: List[str]
    if ext == ".webm":
        codec_args = ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(crf), "-pix_fmt", "yuv420p"]
    elif ext == ".mov":
        codec_args = ["-c:v", "prores_ks", "-profile:v", "3"]
    else:  # .mp4, .mkv
        codec_args = [
            "-c:v", "libx264", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        ]
    return [
        ffmpeg, "-y",
        "-framerate", str(int(fps)),
        "-i", str(src_dir / pattern),
        *codec_args,
        *extra_args,
        str(out_path),
    ]


def _build_gif_cmd(
    ffmpeg: str, src_dir: Path, pattern: str, fps: int, out_path: Path,
) -> List[str]:
    """Single-pass palette-use filter graph. Quality < two-pass but good enough."""
    vf = (
        f"fps={int(fps)},"
        "split[a][b];"
        "[a]palettegen=stats_mode=diff[p];"
        "[b][p]paletteuse=dither=bayer:bayer_scale=5"
    )
    return [
        ffmpeg, "-y",
        "-i", str(src_dir / pattern),
        "-filter_complex", vf,
        str(out_path),
    ]


def register(r: Dict[str, Any]) -> None:
    r.update(
        {
            "encode_video": encode_video,
            "ffmpeg_available": ffmpeg_available,
        }
    )
