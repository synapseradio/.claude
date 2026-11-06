"""The per-session log of the model a caller named for each spawn, and which start claimed it.

`SubagentStart` carries no per-spawn model, so a `PreToolUse` on `Agent` appends one
record per spawn and a delegate's start reads it back, joined on `(prompt_id, agent_type)`.
Where one prompt spawned several delegates of one type, each start claims the oldest
record no other start claimed, keyed by its `agent_id`. Both logs sit in a per-session
directory under the state directory.
"""

import dataclasses
import fcntl
import json
import pathlib

SPAWN = "spawn"
CLAIM = "claim"
SPAWNS_FILE = "spawns.jsonl"
CLAIMS_FILE = "claims.jsonl"
CLAIMS_LOCK = "claims.lock"


@dataclasses.dataclass(frozen=True)
class ClaimedSpawn:
    """The spawn record one start claimed: the model it names, None where the caller named none."""

    model: object


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
    """The models named for spawns matching one prompt and agent type, claimed or not.

    A record naming no model is left out. A line that does not parse is skipped, so a
    write that failed partway leaves the rest of the log readable.
    """

    try:
        records = _records(session_dir(session_id, state) / SPAWNS_FILE, SPAWN)
    except OSError:
        return []
    return [
        record["model"]
        for record in records.values()
        if _matches(record, prompt_id, agent_type) and record.get("model") not in (None, "")
    ]


def claim_spawn(
    session_id: str,
    prompt_id: str,
    agent_type: str,
    agent_id: str,
    state: pathlib.Path,
) -> ClaimedSpawn | None:
    """The spawn record `agent_id` holds among those matching the prompt and agent type.

    An `agent_id` that claimed before gets the record it claimed first. Otherwise it claims
    the oldest matching record no other `agent_id` claimed. A record is named by its line in
    the spawn log, which only grows. Starts run concurrently, so the read and the claim hold
    an exclusive lock together. None where every matching record is claimed, or where a log
    or the lock cannot be read or written.
    """

    directory = session_dir(session_id, state)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / CLAIMS_LOCK).open("a", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            spawns = _records(directory / SPAWNS_FILE, SPAWN)
            claimed = {
                claim["agent_id"]: claim["line"]
                for claim in _records(directory / CLAIMS_FILE, CLAIM).values()
                if isinstance(claim.get("agent_id"), str) and isinstance(claim.get("line"), int)
            }
            if agent_id in claimed:
                held = spawns.get(claimed[agent_id])
                return ClaimedSpawn(held.get("model")) if held is not None else None
            taken = set(claimed.values())
            free = [
                line
                for line, record in spawns.items()
                if line not in taken and _matches(record, prompt_id, agent_type)
            ]
            if not free:
                return None
            with (directory / CLAIMS_FILE).open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps({"kind": CLAIM, "agent_id": agent_id, "line": free[0]}) + "\n"
                )
            return ClaimedSpawn(spawns[free[0]].get("model"))
    except OSError:
        return None


def _records(path: pathlib.Path, kind: str) -> dict[int, dict]:
    """The records of `kind` in a JSON-lines log, keyed by line number; a line that does not parse is skipped."""

    records: dict[int, dict] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return records
    for number, line in enumerate(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("kind") == kind:
            records[number] = record
    return records


def _matches(record: dict, prompt_id: str | None, agent_type: str | None) -> bool:
    return record.get("prompt_id") == prompt_id and record.get("agent_type") == agent_type
