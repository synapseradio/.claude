"""The records of what the passes have reported, and of what a turn has blocked."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

STATE_ENV = "VERIFY_MARKS_STATE_DIR"
PLUGIN_DATA_ENV = "CLAUDE_PLUGIN_DATA"
STATE_DIR_NAME = "verify-marks"
STALE_SECONDS = 24 * 60 * 60
DIR_MODE = 0o700


def fingerprint(line) -> str:
    """An identity for a line, carrying none of its text."""
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def state_dir() -> Path:
    """The first location named: the override, the plugin's data directory, then temp.

    The harness sets PLUGIN_DATA_ENV to a directory that outlives a plugin
    update, per
    https://code.claude.com/docs/en/plugins-reference
    """
    override = os.environ.get(STATE_ENV)
    if override:
        return Path(override)
    plugin_data = os.environ.get(PLUGIN_DATA_ENV)
    if plugin_data:
        return Path(plugin_data) / STATE_DIR_NAME
    return Path(tempfile.gettempdir()) / f"epistemic-marks-{STATE_DIR_NAME}"


def state_path(directory, key) -> Path:
    safe = "".join(c for c in key if c.isalnum() or c in "-_")
    return directory / f"{safe or 'session'}.json"


def state_key(payload) -> str:
    """The identity whose reported lines this payload's record holds.

    The harness sends agent_id from within a subagent alone, per
    https://docs.claude.com/en/docs/claude-code/hooks
    """
    return payload.get("agent_id") or payload.get("session_id") or "session"


def prepare(directory) -> bool:
    """Make the directory, reporting whether it can be written."""
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=DIR_MODE)
    except OSError:
        return False
    return True


def prune(directory, now) -> None:
    for path in directory.glob("*.json"):
        try:
            if now - path.stat().st_mtime > STALE_SECONDS:
                path.unlink()
        except OSError:
            continue


def read_reported(path) -> list:
    try:
        reported = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    return reported if isinstance(reported, list) else []


def write_reported(path, reported) -> None:
    try:
        path.write_text(json.dumps(reported))
    except OSError:
        return


def read_turn(path) -> tuple[list, int]:
    """The lines a turn has sent the model and the blocks it has drawn, as (list, int)."""
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        return [], 0
    if not isinstance(record, dict):
        return [], 0
    sent, blocks = record.get("sent"), record.get("blocks")
    return (
        sent if isinstance(sent, list) else [],
        blocks if isinstance(blocks, int) and blocks > 0 else 0,
    )


def write_turn(path, sent, blocks) -> None:
    try:
        path.write_text(json.dumps({"sent": sent, "blocks": blocks}))
    except OSError:
        return
