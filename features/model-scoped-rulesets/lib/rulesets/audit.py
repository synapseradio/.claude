#!/usr/bin/env python3.14
"""Append and read the per-session record of loads and deliveries.

Records partition by writer. A delegate can carry its parent's session
identifier and two delegates can run at once, so a session's own records
go to `session.jsonl` under a per-session directory and each delegate's
to `<agent_id>.jsonl` beside it. Reading one session means reading that
directory, which leaves every other session's records unscanned.
"""

import json
import pathlib

from . import resolve

LOAD = "load"
DELIVERY = "delivery"
SPAWN = "spawn"

SESSION_FILE = "session.jsonl"
SPAWNS_FILE = "spawns.jsonl"


def _safe(key: str) -> str:
    cleaned = "".join(c for c in str(key) if c.isalnum() or c in "-_")
    return cleaned or "session"


def _state(state: pathlib.Path | str | None) -> pathlib.Path:
    return pathlib.Path(state) if state is not None else resolve.state_dir()


def session_dir(session_id: str, state: pathlib.Path | str | None = None) -> pathlib.Path:
    """The directory holding one session's records and its delegates'."""

    return _state(state) / "audit" / _safe(session_id)


def record_path(
    session_id: str,
    agent_id: str | None = None,
    state: pathlib.Path | str | None = None,
) -> pathlib.Path:
    """The file one writer appends to."""

    directory = session_dir(session_id, state)
    if agent_id:
        return directory / f"{_safe(agent_id)}.jsonl"
    return directory / SESSION_FILE


def append_record(
    record: dict,
    session_id: str,
    agent_id: str | None = None,
    state: pathlib.Path | str | None = None,
) -> bool:
    """Append one JSON line, answering whether the write landed.

    A caller runs inside a hook, so an unwritable log answers False and
    raises nothing.
    """

    try:
        path = record_path(session_id, agent_id, state)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
    except OSError:
        return False
    return True


def read_records(session_id: str, state: pathlib.Path | str | None = None) -> list[dict]:
    """Every complete record for a session and its delegates.

    A line that does not parse gets skipped, so a write that failed
    partway leaves the rest of the log readable.
    """

    directory = session_dir(session_id, state)
    if not directory.is_dir():
        return []

    records = []
    for path in sorted(directory.glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                records.append(parsed)
    return records


def load_record(payload: dict) -> dict:
    """The record one `InstructionsLoaded` payload produces."""

    record = {
        "kind": LOAD,
        "file_path": payload.get("file_path"),
        "load_reason": payload.get("load_reason"),
        "session_id": payload.get("session_id"),
    }
    for optional in ("trigger_file_path", "parent_file_path"):
        if payload.get(optional):
            record[optional] = payload[optional]
    return record


def delivery_record(
    session_id: str,
    tier: str,
    source: str,
    stems: tuple[str, ...],
    scope: str,
    agent_id: str | None = None,
    superseded: bool = False,
    prompt_id: str | None = None,
    root: pathlib.Path | str | None = None,
) -> dict:
    """The record one delivery produces.

    `root` names the corpus the delivery read. A flag, a variable, and the
    configuration directory each name one, so a record naming none leaves a
    reader unable to tell which bodies reached the context.
    """

    record = {
        "kind": DELIVERY,
        "session_id": session_id,
        "tier": tier,
        "tier_source": source,
        "stems": list(stems),
        "scope": scope,
        "superseded": superseded,
    }
    if agent_id:
        record["agent_id"] = agent_id
    if prompt_id:
        record["prompt_id"] = prompt_id
    if root is not None:
        record["root"] = str(root)
    return record


def tier_record_path(session_id: str, state: pathlib.Path | str | None = None) -> pathlib.Path:
    """The file holding one session's resolved tier."""

    return _state(state) / "tiers" / _safe(session_id)


def write_tier(session_id: str, tier: str, state: pathlib.Path | str | None = None) -> bool:
    """Record a session's tier so a later delivery with no model can read it."""

    try:
        path = tier_record_path(session_id, state)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(tier + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


def read_tier(session_id: str, state: pathlib.Path | str | None = None) -> str | None:
    """The tier recorded for a session, or None where none is."""

    try:
        path = tier_record_path(session_id, state)
        if path.is_file():
            return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        pass
    return None


def append_spawn(
    session_id: str,
    prompt_id: str | None,
    agent_type: str | None,
    model: str | None,
    state: pathlib.Path | str | None = None,
) -> bool:
    """Record the model a caller named for one spawn, keyed for later read.

    `SubagentStart` carries no per-spawn model, and the spike found the
    join is `(prompt_id, agent_type)` rather than `tool_use_id`. A
    `PreToolUse` on `Agent` writes this, and a delegate's start reads it.
    """

    record = {
        "kind": SPAWN,
        "session_id": session_id,
        "prompt_id": prompt_id,
        "agent_type": agent_type,
        "model": model,
    }
    try:
        path = session_dir(session_id, state) / SPAWNS_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
    except OSError:
        return False
    return True


def read_spawns(
    session_id: str,
    prompt_id: str | None,
    agent_type: str | None,
    state: pathlib.Path | str | None = None,
) -> list[str]:
    """The models named for spawns matching one prompt and agent type.

    More than one match means one prompt spawned two delegates of the same
    type, where the per-spawn model is ambiguous and the caller falls
    through to the next source.
    """

    models = []
    for record in read_records(session_id, state):
        if (
            record.get("kind") == SPAWN
            and record.get("prompt_id") == prompt_id
            and record.get("agent_type") == agent_type
            and record.get("model")
        ):
            models.append(record["model"])
    return models
