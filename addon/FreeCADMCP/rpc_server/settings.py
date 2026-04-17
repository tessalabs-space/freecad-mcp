import json
import os
from pathlib import Path
from typing import Any, Dict

import FreeCAD


_DEFAULTS: Dict[str, Any] = {
    "port": 9875,
    "host": "localhost",
    "auto_start": False,
    "allow_remote": False,
    "allowed_ips": ["127.0.0.1"],
}


def _settings_path() -> Path:
    user_dir = Path(FreeCAD.getUserAppDataDir())
    return user_dir / "FreeCADMCP" / "settings.json"


def load_settings() -> Dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update(data)
    return merged


def save_settings(settings: Dict[str, Any]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def update_setting(key: str, value: Any) -> Dict[str, Any]:
    s = load_settings()
    s[key] = value
    save_settings(s)
    return s
