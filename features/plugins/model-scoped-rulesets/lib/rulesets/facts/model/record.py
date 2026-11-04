"""The per-session file that records the identifier a session runs on."""

import json
import os
import pathlib
import uuid


def _clean_key(session_id: str) -> str:
    """A session id cut to alphanumerics, hyphens, and underscores, as the log names its folders."""

    return "".join(c for c in session_id if c.isalnum() or c in "-_") or "session"


def model_record_path(session_id: str, state_dir: pathlib.Path) -> pathlib.Path:
    """Where a session's model record lives, apart from the log that pruning clears."""

    return state_dir / "models" / f"{_clean_key(session_id)}.json"


def write_model_record(session_id: str, identifier: str | None, state_dir: pathlib.Path) -> bool:
    """Record a session's identifier, or that none was available, answering whether it landed.

    The write goes to a temporary file in the same directory and reaches the target in
    one atomic replace, so a concurrent reader never meets a half-written record.
    """

    record = (
        {"identifier": identifier}
        if identifier is not None
        else {"identifier": None, "unavailable": "no model identifier was available"}
    )
    path = model_record_path(session_id, state_dir)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(record) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        return False
    return True


def read_model_record(session_id: str, state_dir: pathlib.Path) -> str | None:
    """The identifier recorded for a session, or None where none is recorded or readable."""

    try:
        record = json.loads(model_record_path(session_id, state_dir).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    identifier = record.get("identifier") if isinstance(record, dict) else None
    return identifier if isinstance(identifier, str) and identifier else None
