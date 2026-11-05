"""The parent session of a forked session, found by the leading message identifiers its transcript copied."""

from __future__ import annotations

import dataclasses
import json
import pathlib


@dataclasses.dataclass(frozen=True)
class Parent:
    session_id: str


@dataclasses.dataclass(frozen=True)
class Unknown:
    """No single other transcript in the project directory is the one the fork copied."""


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


def _sequences(directory: pathlib.Path, excluded: pathlib.Path) -> dict[pathlib.Path, list[str]]:
    """The identifiers of each transcript in `directory` but `excluded`; an unreadable one holds none."""

    found: dict[pathlib.Path, list[str]] = {}
    for path in directory.glob("*.jsonl"):
        if path != excluded:
            try:
                found[path] = _identifiers(path)
            except OSError:
                continue
    return found


def _shared_prefix(left: list[str], right: list[str]) -> int:
    length = 0
    for one, other in zip(left, right, strict=False):
        if one != other:
            break
        length += 1
    return length


def fork_parent(transcript: pathlib.Path) -> ForkParent:
    """The transcript beside `transcript` that holds the longest run of entries it copied.

    A fork's transcript starts with its parent's message identifiers in order and then adds its
    own, so the parent shares the longest leading run with it; a sibling fork shares only the run
    up to where the parent stood at the sibling's fork. Where several transcripts share the
    longest run, the one that ends there is the parent, because a sibling goes on with entries of
    its own. Where that leaves no single transcript, the parent is not known.
    """

    try:
        identifiers = _identifiers(transcript)
    except OSError:
        return Unknown()
    sequences = _sequences(transcript.parent, transcript)
    shared = {path: _shared_prefix(identifiers, sequence) for path, sequence in sequences.items()}
    longest = max(shared.values(), default=0)
    if longest == 0:
        return Unknown()
    tied = [path for path, length in shared.items() if length == longest]
    ending_there = [path for path in tied if len(sequences[path]) == longest]
    candidates = ending_there or tied
    return Parent(candidates[0].stem) if len(candidates) == 1 else Unknown()
