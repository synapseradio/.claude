"""The parent session of a forked session, found by the message identifiers its transcript copied."""

from __future__ import annotations

import dataclasses
import json
import pathlib


@dataclasses.dataclass(frozen=True)
class Parent:
    session_id: str


@dataclasses.dataclass(frozen=True)
class Unknown:
    """No other transcript in the project directory holds a message the fork copied."""


type ForkParent = Parent | Unknown


def _identifiers(transcript: pathlib.Path) -> list[str]:
    """The `uuid` of each entry of a transcript, in file order; lines that are no entry are skipped."""

    found: list[str] = []
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and isinstance(entry.get("uuid"), str):
            found.append(entry["uuid"])
    return found


def _texts(directory: pathlib.Path, excluded: pathlib.Path) -> dict[pathlib.Path, str]:
    """The text of each transcript in `directory` but `excluded`; an unreadable one holds nothing."""

    texts: dict[pathlib.Path, str] = {}
    for path in directory.glob("*.jsonl"):
        if path != excluded:
            try:
                texts[path] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return texts


def fork_parent(transcript: pathlib.Path) -> ForkParent:
    """The newest other transcript beside `transcript` that holds the last identifier it copied.

    A fork's transcript copies its parent's message identifiers and then adds its own, so its
    last identifier that another transcript of the project holds is the last one copied.
    """

    try:
        identifiers = _identifiers(transcript)
    except OSError:
        return Unknown()
    texts = _texts(transcript.parent, transcript)
    for identifier in reversed(identifiers):
        holders = [path for path, text in texts.items() if identifier in text]
        if holders:
            return Parent(max(holders, key=lambda path: path.stat().st_mtime_ns).stem)
    return Unknown()
