"""Session transcripts shaped as the harness writes them, for finding a fork's parent.

A parent's transcript holds entries that carry a `uuid`, a `parentUuid`, and the parent's
`sessionId`, among bookkeeping lines (`session-owner`, `last-prompt`, `cost-state`) that carry
none. A fork's transcript holds copies of the parent's entries under the fork's `sessionId`,
the same `uuid`s intact, followed by entries of its own.
"""

import json
import pathlib
import uuid

_MESSAGE_KINDS = ("attachment", "attachment", "user", "assistant", "system")


def _bookkeeping(session_id: str, kind: str) -> dict[str, str]:
    return {"type": kind, "sessionId": session_id}


def _chain(session_id: str, after: str | None) -> list[dict[str, str | None]]:
    entries: list[dict[str, str | None]] = []
    for kind in _MESSAGE_KINDS:
        identity = str(uuid.uuid4())
        entries.append(
            {"type": kind, "uuid": identity, "parentUuid": after, "sessionId": session_id}
        )
        after = identity
    return entries


def write_transcript(
    directory: pathlib.Path, session_id: str, *, fork_of: pathlib.Path | None = None
) -> pathlib.Path:
    """The transcript of `session_id` in `directory`; a fork copies the entries of `fork_of`."""

    directory.mkdir(parents=True, exist_ok=True)
    inherited: list[dict] = []
    if fork_of is not None:
        parent_lines = [json.loads(line) for line in fork_of.read_text("utf-8").splitlines()]
        inherited = [{**e, "sessionId": session_id} for e in parent_lines if "uuid" in e]
    last_copied = inherited[-1]["uuid"] if inherited else None
    lines = [
        _bookkeeping(session_id, "session-owner"),
        *inherited,
        *_chain(session_id, last_copied),
        _bookkeeping(session_id, "last-prompt"),
        _bookkeeping(session_id, "cost-state"),
    ]
    path = directory / f"{session_id}.jsonl"
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path
