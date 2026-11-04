"""The per-session log directory, and appending one JSON line to a file in it."""

from __future__ import annotations

import json
import pathlib

from rulesets import spawn_log
from rulesets.locations import Locations

DELIVERIES_FILE = "deliveries.jsonl"


def session_dir(locations: Locations, session_id: str) -> pathlib.Path:
    """The directory holding one session's records, the spawn log's among them."""

    return spawn_log.session_dir(session_id, locations.state)


def append(path: pathlib.Path, record: dict[str, object]) -> None:
    """Add one record as a line at the end of the file, creating the directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
