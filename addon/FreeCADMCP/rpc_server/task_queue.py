"""Dispatch RPC work onto FreeCAD's Qt main thread.

FreeCAD's OpenCASCADE and Coin3D objects are not thread-safe; any tool that
touches geometry, the document, or the 3D view must execute on the GUI
thread. The XML-RPC server runs on a worker thread, so each RPC method
submits a callable here and blocks on a result.
"""

from __future__ import annotations

import threading
import traceback
from queue import Queue
from typing import Any, Callable, Tuple

from .qt_compat import QTimer


_tasks: "Queue[Tuple[Callable[..., Any], tuple, dict, threading.Event, list]]" = Queue()
_pump_started = False


def _pump() -> None:
    """Drain any ready tasks; re-arm the timer if more remain."""
    while not _tasks.empty():
        fn, args, kwargs, done, slot = _tasks.get_nowait()
        try:
            slot.append(("ok", fn(*args, **kwargs)))
        except Exception as exc:  # noqa: BLE001 — surface to caller thread
            slot.append(("err", f"{exc}\n{traceback.format_exc()}"))
        finally:
            done.set()
    QTimer.singleShot(10, _pump)


def ensure_pump() -> None:
    """Start the main-thread pump exactly once."""
    global _pump_started
    if _pump_started:
        return
    _pump_started = True
    QTimer.singleShot(0, _pump)


def run_on_gui(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Submit ``fn`` to the GUI thread and block until it completes.

    Re-raises any exception thrown inside ``fn`` on the caller's thread so
    the RPC dispatcher can turn it into a fault.
    """
    ensure_pump()
    done = threading.Event()
    slot: list = []
    _tasks.put((fn, args, kwargs, done, slot))
    done.wait()
    kind, payload = slot[0]
    if kind == "err":
        raise RuntimeError(payload)
    return payload
