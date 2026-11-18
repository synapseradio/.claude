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

# What blanked text is filled with, so an offset into the raw line survives.
BLANK = "\x00"
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
BLOCKQUOTE = re.compile(r"^ {0,3}>")

# A quotation. Double quotes may run across the line ends of one paragraph,
# since prose wraps; a single quote also writes an apostrophe, so it pairs
# only within its line.
QUOTED = re.compile(
    r'"[^"]{0,600}"'
    r"|“[^”]{0,600}”"
    r"|\u2018[^\u2019\n]*\u2019"
    r"|(?<!\w)'[^'\n]*'(?!\w)"
)
NOT_A_LINE_END = re.compile(r"[^\n]")

# The list markers a line opens on. A notice lists each flagged line as an
# item, so a line copied from it arrives with one more of these than it had.
LEADING_MARKERS = re.compile(r"^(?:[-*+]\s+)+")


def claim_text(line) -> str:
    """The line trimmed, without the list markers it opens on.

    A flagged line is identified by this text, so the bullet the notice quotes
    it under, copied back ahead of the line's own, names the same line.
    """
    return LEADING_MARKERS.sub("", line.strip())


def text_blocks(message) -> list[str]:
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


def is_real_user_entry(entry) -> bool:
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


def _turn_state_path(directory, transcript_path) -> Path:
    """Where this transcript's turn-boundary offset lives, one file per file scanned."""
    resolved = str(Path(transcript_path).resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()
    return directory / f"{digest}{SCAN_STATE_SUFFIX}"


def _load_turn_start(path) -> int:
    try:
        data = json.loads(path.read_text())
    except OSError, ValueError:
        return 0
    offset = data.get("turn_start_offset") if isinstance(data, dict) else None
    return offset if isinstance(offset, int) and offset >= 0 else 0


def _save_turn_start(path, offset) -> None:
    # A state directory that cannot be written costs a rescan, never a
    # verification pass, so the failure is swallowed on purpose.
    with contextlib.suppress(OSError):
        path.write_text(json.dumps({"turn_start_offset": offset}))


def last_turn_text(transcript_path) -> list[str]:
    """Assistant text blocks since the most recent real user message."""
    return [
        text
        for entry in last_turn_entries(transcript_path)
        if entry.get("type") == "assistant"
        for text in text_blocks(entry.get("message", {}))
    ]


def last_turn_entries(transcript_path) -> list[dict]:
    """The assistant entries and tool results since the most recent real user message, in order.

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
                elif entry.get("type") in {"assistant", "user"}:
                    turn.append(entry)
    except OSError:
        return []

    if state_path is not None and boundary != start:
        _save_turn_start(state_path, boundary)
    return turn


def fenced_line_numbers(lines) -> set[int]:
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


def _span_token(span) -> str:
    """The mark a code span holds alone, or nothing where it holds anything else."""
    token = span.strip("`").strip()
    return token if token in MARKS else ""


def names_in_words(line, mark) -> bool:
    """Whether the line calls the mark by the name the vocabulary gives it.

    The discriminator comes from MARK_NAMES rather than from a list kept
    here, so a renamed mark renames what a mention has to say.
    """
    return MARK_NAMES[mark].lower() in line.lower()


def _mention_forms(mark) -> tuple[re.Pattern[str], re.Pattern[str]]:
    """How a glyph is written, outside a code span, on a line that only names it.

    In quotes of its own, or straight after its own name. Both read as
    pointing at the mark, the way the rule text itself introduces each one.
    """
    glyph = re.escape(mark)
    name = re.escape(MARK_NAMES[mark])
    return (
        re.compile(rf"""["“'\u2018](?P<glyph>{glyph})["”'\u2019]"""),
        re.compile(rf"{name}[\s,:;(—\u2013-]{{0,3}}(?P<glyph>{glyph})", re.IGNORECASE),
    )


MENTION_FORMS = {mark: _mention_forms(mark) for mark in MARKS}


def _read_line(line) -> tuple[str, set[str]]:
    """The line's claiming prose, and the marks the line only mentions.

    The prose is the line with its inline code and its mentioned glyphs
    blanked at equal length, so an offset into one is an offset into the
    other. A span holding a mark alone stays in the prose, so backticks
    around a mark leave it a claim. A glyph drops out only where the same
    line calls that mark by name and writes the glyph in a span of its own,
    in quotes of its own, or straight after the name, which reads as
    documenting the mark rather than claiming under it.
    """
    named = {mark for mark in MARKS if names_in_words(line, mark)}
    mentioned = set()
    chars = list(line)

    def blank(start, end) -> None:
        chars[start:end] = BLANK * (end - start)

    for span in INLINE_CODE.finditer(line):
        token = _span_token(span.group(0))
        if token and token not in named:
            continue
        if token:
            mentioned.add(token)
        blank(*span.span())
    outside_code = "".join(chars)
    for mark in named:
        for form in MENTION_FORMS[mark]:
            for match in form.finditer(outside_code):
                mentioned.add(mark)
                blank(*match.span("glyph"))
    return "".join(chars), mentioned


def _blank_quotation(match: re.Match[str]) -> str:
    """The quotation blanked at equal length, unless it holds a mark alone.

    Quotes around a bare mark leave it a claim, as backticks do.
    """
    quoted = match.group(0)
    if quoted[1:-1].strip() in MARKS:
        return quoted
    return NOT_A_LINE_END.sub(BLANK, quoted)


def claim_lines(lines) -> list[tuple[str, set[str]]]:
    """Per line, the prose a claim can sit in and the marks the line only mentions.

    The prose is the line with its code spans, its mentioned glyphs and
    its quotations blanked at equal length. A fenced line, a block-quoted
    line and a blank line hold no claim and come back empty: fenced text
    is code, and quotation is the form kept for someone else's words. A
    quotation is found across the wrapped lines of one paragraph.
    """
    fenced = fenced_line_numbers(lines)
    read = [
        ("", set())
        if number in fenced or BLOCKQUOTE.match(line) or not line.strip()
        else _read_line(line)
        for number, line in enumerate(lines)
    ]
    number = 0
    while number < len(read):
        end = number
        while end < len(read) and read[end][0]:
            end += 1
        paragraph = "\n".join(prose for prose, _ in read[number:end])
        for offset, prose in enumerate(QUOTED.sub(_blank_quotation, paragraph).split("\n")):
            if end > number:
                read[number + offset] = (prose, read[number + offset][1])
        number = end + 1
    return read


def marked_lines(blocks) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Lines claiming under a mark and lines merely naming one, each keyed by mark.

    Both mappings skip fenced code, block quotes and quotations. A line reaches the second by naming a
    mark in words and writing its glyph as a mention on the same line; it
    blocks nothing, and the Stop pass reports it so the exemption stays
    visible. One line can reach both mappings, by documenting one mark and
    claiming under another.
    """
    lines = [line for block in blocks for line in block.splitlines()]
    found = {mark: [] for mark in MARKS}
    named = {mark: [] for mark in MARKS}
    for line, (prose, mentioned) in zip(lines, claim_lines(lines), strict=True):
        stripped = claim_text(line)
        for mark in MARKS:
            if mark in prose and stripped not in found[mark]:
                found[mark].append(stripped)
        for mark in mentioned:
            if stripped not in named[mark]:
                named[mark].append(stripped)
    return (
        {mark: hits for mark, hits in found.items() if hits},
        {mark: hits for mark, hits in named.items() if hits},
    )


def batch_transcript(payload) -> str:
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
