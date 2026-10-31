"""Reading a transcript and finding the marked lines in it."""

import contextlib
import hashlib
import json
import os
import re
from pathlib import Path

from .ledger import prepare, state_dir
from .marks import MARK_NAMES, MARKS

SCAN_STATE_SUFFIX = ".scan-offset.json"

INLINE_CODE = re.compile(r"`[^`\n]*`")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def text_blocks(message):
    content = message.get("content")
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
    return []


def is_real_user_entry(entry):
    # Tool results reach the transcript as user entries too, carrying
    # tool_result blocks where a typed turn carries text.
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return any(isinstance(block, dict) and block.get("type") == "text" for block in content)
    return False


def _turn_state_path(directory, transcript_path):
    """Where this transcript's turn-boundary offset lives, one file per file scanned."""
    resolved = str(Path(transcript_path).resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()
    return directory / f"{digest}{SCAN_STATE_SUFFIX}"


def _load_turn_start(path):
    try:
        data = json.loads(path.read_text())
    except OSError, ValueError:
        return 0
    offset = data.get("turn_start_offset") if isinstance(data, dict) else None
    return offset if isinstance(offset, int) and offset >= 0 else 0


def _save_turn_start(path, offset):
    # A state directory that cannot be written costs a rescan, never a
    # verification pass, so the failure is swallowed on purpose.
    with contextlib.suppress(OSError):
        path.write_text(json.dumps({"turn_start_offset": offset}))


def last_turn_text(transcript_path):
    """Assistant text blocks since the most recent real user message.

    Rescans only the bytes written since the transcript's last confirmed
    turn boundary, not the whole file. That boundary is a byte offset
    persisted to the same per-session state directory ledger.py already
    writes its fingerprint-dedup record to, holding one integer and no
    conversation text.

    The offset only ever advances to a position this function itself found
    by parsing a real user entry there, so resuming the scan from it and
    resuming from byte 0 replay the identical sequence of resets on
    everything from that point forward and land on the same accumulator.
    Nothing before the boundary can still affect the answer: the last reset
    at or before it already discarded it. tests/test_scan_incremental.py
    pins this against the prior full-rescan implementation.
    """
    try:
        size = os.path.getsize(transcript_path)
    except OSError:
        return []

    directory = state_dir()
    state_path = _turn_state_path(directory, transcript_path) if prepare(directory) else None
    start = _load_turn_start(state_path) if state_path else 0
    if start > size:
        start = 0  # the file shrank or was replaced; the old boundary no longer applies

    turn = []
    boundary = start
    try:
        with open(transcript_path, "rb") as f:
            f.seek(start)
            position = start
            for raw_line in f:
                position += len(raw_line)
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if is_real_user_entry(entry):
                    turn = []
                    boundary = position
                elif entry.get("type") == "assistant":
                    turn.extend(text_blocks(entry.get("message", {})))
    except OSError:
        return []

    if state_path is not None and boundary != start:
        _save_turn_start(state_path, boundary)
    return turn


def fenced_line_numbers(lines):
    """Indices of the lines inside a fence that closes."""
    fenced = set()
    opened_at = None
    opener = ""
    for number, line in enumerate(lines):
        match = FENCE.match(line)
        if not match:
            continue
        run, rest = match.group(1), match.group(2)
        if opened_at is None:
            if run.startswith("`") and "`" in rest:
                continue
            opened_at, opener = number, run
        elif run[0] == opener[0] and len(run) >= len(opener) and not rest.strip():
            fenced.update(range(opened_at, number + 1))
            opened_at = None
    return fenced


def _span_token(span):
    """The mark a code span holds alone, or None where it holds anything else."""
    token = span.strip("`").strip()
    return token if token in MARKS else None


def names_in_words(line, mark):
    """Whether the line calls the mark by the name the vocabulary gives it.

    The discriminator comes from MARK_NAMES rather than from a list kept
    here, so a renamed mark renames what a mention has to say.
    """
    return MARK_NAMES[mark].lower() in line.lower()


def mentioned_marks(line):
    """The marks the line writes in a span of their own and names in words beside."""
    return {
        token
        for span in INLINE_CODE.findall(line)
        if (token := _span_token(span)) and names_in_words(line, token)
    }


def strip_code_spans(line):
    """The line without its inline code, keeping a mark the line never names.

    A span holding a mark alone stays in the prose, so backticks around a
    mark leave it a claim. It drops out only where the same line calls that
    mark by name, which reads as documenting the mark rather than claiming
    under it.
    """

    def keep(span):
        token = _span_token(span.group(0))
        return span.group(0) if token and not names_in_words(line, token) else ""

    return INLINE_CODE.sub(keep, line)


def marked_lines(blocks):
    """Lines claiming under a mark and lines merely naming one, each keyed by mark.

    Both mappings skip fenced code. A line reaches the second by writing a
    mark inside a code span and naming that mark in words on the same line;
    it blocks nothing, and the Stop pass reports it so the exemption stays
    visible. One line can reach both mappings, by documenting one mark and
    claiming under another.
    """
    lines = [line for block in blocks for line in block.splitlines()]
    fenced = fenced_line_numbers(lines)
    found = {mark: [] for mark in MARKS}
    named = {mark: [] for mark in MARKS}
    for number, line in enumerate(lines):
        if number in fenced:
            continue
        prose = strip_code_spans(line)
        stripped = line.strip()
        for mark in MARKS:
            if mark in prose and stripped not in found[mark]:
                found[mark].append(stripped)
        for mark in mentioned_marks(line):
            if stripped not in named[mark]:
                named[mark].append(stripped)
    return (
        {mark: hits for mark, hits in found.items() if hits},
        {mark: hits for mark, hits in named.items() if hits},
    )


def batch_transcript(payload):
    """The transcript holding text the agent this batch belongs to wrote.

    A subagent's turns go to `<session transcript stem>/subagents/agent-<id>.jsonl`,
    with a workflow agent's file one level deeper, and reach the session
    transcript never.
    """
    session = payload.get("transcript_path", "")
    agent = payload.get("agent_id")
    if not agent:
        return session
    if not session:
        return ""
    stem = session[: -len(".jsonl")] if session.endswith(".jsonl") else session
    try:
        for found in sorted(Path(stem, "subagents").rglob(f"agent-{agent}.jsonl")):
            return str(found)
    except OSError:
        return ""
    return ""
