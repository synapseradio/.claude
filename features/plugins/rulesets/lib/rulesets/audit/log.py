"""The per-session log directory: appending JSON lines to it, reading them back, and pruning it."""

from __future__ import annotations

import json
import pathlib
import shutil

from rulesets import spawn_log
from rulesets.locations import Locations

DELIVERIES_FILE = "deliveries.jsonl"
EMITTED_PATTERN = "emitted-*.jsonl"


def session_dir(locations: Locations, session_id: str) -> pathlib.Path:
    """The directory holding one session's records, the spawn log's among them."""

    return spawn_log.session_dir(session_id, locations.state)


def emitted_file(locations: Locations, session_id: str, part: int) -> pathlib.Path:
    """The file part `part` of a session's deliveries appends its records to."""

    return session_dir(locations, session_id) / f"emitted-{part}.jsonl"


def append(path: pathlib.Path, record: dict[str, object]) -> None:
    """Add one record as a line at the end of the file, creating the directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def read(path: pathlib.Path) -> list[dict[str, object]]:
    """The JSON objects of a file's lines in file order; a line that is no JSON object is skipped."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    found: list[dict[str, object]] = []
    for line in lines:
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            found.append(parsed)
    return found


def prune(locations: Locations, older_than: float) -> tuple[str, ...]:
    """Remove each session directory whose newest file was last written before `older_than`.

    `older_than` is a time in seconds since the epoch. The sessions removed come back sorted.
    A session's model record sits outside the log, so no removal touches it.
    """

    root = spawn_log.audit_dir(locations.state)
    if not root.is_dir():
        return ()
    removed: list[str] = []
    for directory in sorted(root.iterdir()):
        if directory.is_dir() and _last_written(directory) < older_than:
            shutil.rmtree(directory)
            removed.append(directory.name)
    return tuple(removed)


def _last_written(directory: pathlib.Path) -> float:
    return max(
        (entry.stat().st_mtime for entry in directory.iterdir()),
        default=directory.stat().st_mtime,
    )
