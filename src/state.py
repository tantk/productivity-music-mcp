"""Shared state file between MCP server and TUI widget."""

import json
import time
from pathlib import Path

STATE_FILE = Path.home() / ".productivity-music" / "state.json"


def write(data: dict):
    """Write playback state atomically (temp file + rename)."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = time.time()
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.rename(STATE_FILE)


def read() -> dict:
    """Read current playback state."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def clear():
    """Clear state."""
    write({"playing": False, "track_name": "", "pomo_active": False})
