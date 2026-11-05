"""The per-session log of the model a caller named for each spawn.

`SubagentStart` carries no per-spawn model, so a `PreToolUse` on `Agent` appends the
model the caller named and a delegate's start reads it back, joined on
`(prompt_id, agent_type)`. The log sits in a per-session directory under the state
directory.
"""

import json
import pathlib

SPAWN = "spawn"
SPAWNS_FILE = "spawns.jsonl"


def _safe(key: str) -> str:
    cleaned = "".join(c for c in str(key) if c.isalnum() or c in "-_")
    return cleaned or "session"


def audit_dir(state: pathlib.Path) -> pathlib.Path:
    """The directory holding one directory of records for each session."""

    return state / "audit"


def session_dir(session_id: str, state: pathlib.Path) -> pathlib.Path:
    """The directory holding one session's records."""

    return audit_dir(state) / _safe(session_id)


def append_spawn(
    session_id: str,
    prompt_id: str | None,
    agent_type: str | None,
    model: str | None,
    state: pathlib.Path,
) -> bool:
    """Record the model a caller named for one spawn, answering whether the write landed.

    A caller runs inside a hook, so an unwritable log answers False and raises nothing.
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
    state: pathlib.Path,
) -> list[object]:
    """The models named for spawns matching one prompt and agent type.

    More than one match means one prompt spawned two delegates of the same
    type, where the per-spawn model is ambiguous and the caller falls
    through to the next source. A line that does not parse is skipped, so a
    write that failed partway leaves the rest of the log readable.
    """

    try:
        lines = (
            (session_dir(session_id, state) / SPAWNS_FILE).read_text(encoding="utf-8").splitlines()
        )
    except OSError:
        return []

    models: list[object] = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(record, dict)
            and record.get("kind") == SPAWN
            and record.get("prompt_id") == prompt_id
            and record.get("agent_type") == agent_type
            and record.get("model") not in (None, "")
        ):
            models.append(record["model"])
    return models
