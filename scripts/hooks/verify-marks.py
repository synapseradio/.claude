#!/usr/bin/env python3
"""Stop hook: a verification pass for epistemic marks.

Scans the assistant text of the turn that just finished for the marks
`[?]` (a claim with no source on file), `[.?]` (a claim that arrived
secondhand and stayed ungrounded), and `[^?]` (a premise only the user can
settle), per rules/core-rules.md, under "Evidence before claims". When any
mark appears, the hook blocks the stop once and hands back the resolution
each mark takes: verify a `[?]` or `[.?]` claim through real lookups and
re-emit the original reply verbatim with each mark replaced in place by its
inline citation, correcting or removing only the sentences that failed; put
the question a `[^?]` stands in for to the user through AskUserQuestion,
since in live conversation the question replaces the mark. A line that
refers to a mark rather than claiming under one takes a third resolution:
it names the mark in words and says what became of it.

One pass per stop cycle: `stop_hook_active` means a Stop hook already
blocked this cycle, so the hook reports the surviving marks through
`systemMessage` and lets the turn end, instead of looping. A mark that
survives its verification pass therefore stands as written, in front of the
user rather than silently. Stderr would not reach them: from a hook that
exits 0 it goes to the debug log alone, per
https://docs.claude.com/en/docs/claude-code/hooks

Run with `--delegate` from SubagentStop, where a `[^?]` rides up to the
caller untouched: a subagent reaches no user, so the question it stands in
for travels in the report rather than through AskUserQuestion.

Run with `--batch` from PostToolBatch, which fires after each batch of tool
calls resolves and hands back `additionalContext` before the next model
call. A turn that runs long writes a mark many tool calls before it ends, so
this pass reaches the claim while the turn can still act on it, where the
Stop pass reaches it only once the turn is over. It never blocks, since
stopping the agentic loop mid-task costs more than the claim it flags. A
per-session file under `~/.claude/.tmp/verify-marks` records the lines
already handed back, so a line draws one report instead of one per batch for
the rest of the session; a sentence repeated verbatim in a later turn
therefore reaches the user through the Stop pass alone. Point
VERIFY_MARKS_STATE_DIR elsewhere to keep a run out of that state.

PostToolBatch fires from within a subagent too, where it carries agent_id
and names the session-level transcript, which holds none of that subagent's
text. This pass scans the subagent's own file instead, derived from the
session transcript's stem, and keeps a ledger per agent, so a delegate is
flagged for its own marks alone.
"""

import contextlib
import json
import os
import re
import sys
import time
from pathlib import Path

MARKS = ("[?]", "[.?]", "[^?]")

MARK_MEANINGS = {
    "[?]": "no source on file",
    "[.?]": "secondhand and ungrounded",
    "[^?]": "awaits an answer only the user supplies",
}

STATE_ENV = "VERIFY_MARKS_STATE_DIR"
STALE_SECONDS = 24 * 60 * 60


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
    # Tool results also arrive as user entries; a real user turn carries
    # plain text content instead of tool_result blocks.
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return any(isinstance(block, dict) and block.get("type") == "text" for block in content)
    return False


def last_turn_text(transcript_path):
    """Assistant text blocks since the most recent real user message."""
    turn = []
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if is_real_user_entry(entry):
                    turn = []
                elif entry.get("type") == "assistant":
                    turn.extend(text_blocks(entry.get("message", {})))
    except OSError:
        return []
    return turn


INLINE_CODE = re.compile(r"`[^`\n]*`")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def fenced_line_numbers(lines):
    """Indices of the lines inside a fence that closes.

    A closing delimiter runs at least as long as the one that opened it and
    carries nothing after it, so a shorter run inside a longer fence leaves
    the fence open. A fence still open at the end of the turn excludes
    nothing, since a delimiter the author never closed would otherwise hide
    every claim that follows it.
    """
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


def strip_code_spans(line):
    """The line with its inline code removed, keeping a span that holds a
    mark and nothing else.

    A reply writes a mark in backticks as readily as bare, so the backticks
    settle nothing about whether the sentence claims or quotes. A longer
    span holds code or a quoted rule line, where the mark is a mention.
    """
    return INLINE_CODE.sub(
        lambda span: span.group(0) if span.group(0).strip("`").strip() in MARKS else "",
        line,
    )


def marked_lines(blocks):
    """Lines carrying a mark, keyed by mark, skipping fenced code, where a
    mark is a mention rather than a claim.

    The turn's blocks join into one line sequence, since a fence opened in
    one text block closes in a later one.

    A line carrying two marks lands under each of them.
    """
    lines = [line for block in blocks for line in block.splitlines()]
    fenced = fenced_line_numbers(lines)
    found = {mark: [] for mark in MARKS}
    for number, line in enumerate(lines):
        if number in fenced:
            continue
        prose = strip_code_spans(line)
        for mark in MARKS:
            if mark in prose and line.strip() not in found[mark]:
                found[mark].append(line.strip())
    return {mark: hits for mark, hits in found.items() if hits}


def build_reason(lines_by_mark, carried=()):
    found = ", ".join(lines_by_mark)
    listing = "\n\n".join(
        f"Marked {mark} ({MARK_MEANINGS[mark]}):\n" + "\n".join(f"- {line}" for line in lines)
        for mark, lines in lines_by_mark.items()
    )
    steps = []
    if "[?]" in lines_by_mark or "[.?]" in lines_by_mark:
        steps.append(
            "For each claim marked [?] or [.?], gather the evidence that "
            "would ground it. External facts: use a purpose-built research "
            "tool (the linkup MCP tools, the tavily CLI, context7 for "
            "library docs). Claims about local code or files: read the "
            "actual source with Read/Grep. Then re-emit the original reply "
            "verbatim, treating each mark as a template slot. A claim that "
            "verified keeps its exact sentence, with the mark replaced in "
            "place by the inline citation: a URL for an external fact, a "
            "path:line for local code. A claim that failed verification "
            "gets its sentence corrected to what the evidence supports, or "
            "removed if nothing supports it, with a parenthetical noting "
            "the point could not be verified."
        )
    if "[^?]" in lines_by_mark:
        steps.append(
            "For each line marked [^?], call AskUserQuestion with the "
            "question the mark stands in for and the options you would "
            "offer, then re-emit with the mark dropped, since a live "
            "question replaces it. Looking the premise up settles nothing: "
            "only the user's answer does."
        )
    if carried:
        steps.append(
            "Leave every line marked [^?] exactly where it stands, and open "
            "the report with UNANSWERED: the question each one carries and "
            "the options you would have offered, then what you did, then "
            "what you left undone. Calling AskUserQuestion settles nothing "
            "from here, since only whoever spawned you reaches the user. "
            "The lines that ride up:\n" + "\n".join(f"- {line}" for line in carried)
        )
    steps.append(
        "A flagged line that refers to a mark, rather than claiming under "
        "one, resolves a third way. Keep the reference, name the mark in "
        "words instead of writing the glyph, and say in the same sentence "
        'what you did about it or what you do next: "A subagent returned '
        "a mark handing a decision up to you, so I am putting that "
        'question through AskUserQuestion." A glyph left standing as a '
        "reference identifier reads as a claim awaiting its source, and "
        "this pass cannot tell the two apart."
    )
    steps.append(
        "Change nothing outside the marked sentences: no added commentary, "
        "no report about the verification, no restructuring. The reader "
        "sees the same message they would have seen, with sources where "
        "the marks stood."
    )
    numbered = "\n".join(f"{n}. {step}" for n, step in enumerate(steps, start=1))
    return (
        f"Your reply carries lines marked {found}, each awaiting resolution:\n\n"
        f"{listing}\n\n"
        "Resolve each mark, then re-emit the reply with the marks resolved.\n"
        f"{numbered}"
    )


def state_dir():
    override = os.environ.get(STATE_ENV)
    if override:
        return Path(override)
    return Path.home() / ".claude" / ".tmp" / "verify-marks"


def state_path(directory, key):
    safe = "".join(c for c in key if c.isalnum() or c in "-_")
    return directory / f"{safe or 'session'}.json"


def state_key(payload):
    """The identifier whose reported lines this payload's ledger holds.

    Every hook call in one session carries the same session_id. agent_id,
    which the harness sends only from within a subagent, is the field that
    distinguishes a subagent's call from a main-thread one, per
    https://docs.claude.com/en/docs/claude-code/hooks
    """
    return payload.get("agent_id") or payload.get("session_id") or "session"


def batch_transcript(payload):
    """The transcript holding text the agent this batch belongs to wrote.

    PostToolBatch carries session_id and transcript_path, and from within a
    subagent it adds agent_id; agent_transcript_path reaches SubagentStop
    alone. The harness writes a subagent's turns to
    `<session transcript stem>/subagents/agent-<agent_id>.jsonl`, putting a
    workflow agent's file one level deeper, and writes none of them into the
    session transcript. Where the derived file is absent, this returns
    nothing, so the pass stays silent instead of handing a delegate the
    marks another agent wrote.
    See test_batch_reports_a_delegates_own_mark_from_its_own_transcript.
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


def prune(directory, now):
    for path in directory.glob("*.json"):
        try:
            if now - path.stat().st_mtime > STALE_SECONDS:
                path.unlink()
        except OSError:
            continue


def read_reported(path):
    try:
        reported = json.loads(path.read_text())
    except OSError, ValueError:
        return []
    return reported if isinstance(reported, list) else []


def build_context(lines_by_mark):
    found = ", ".join(lines_by_mark)
    listing = "\n\n".join(
        f"Marked {mark} ({MARK_MEANINGS[mark]}):\n" + "\n".join(f"- {line}" for line in lines)
        for mark, lines in lines_by_mark.items()
    )
    steps = []
    if "[?]" in lines_by_mark or "[.?]" in lines_by_mark:
        steps.append(
            "Ground each claim marked [?] or [.?] while the turn is still "
            "open. External facts: use a purpose-built research tool (the "
            "tvly CLI, the linkup MCP tools, context7 for library docs). "
            "Claims about local code or files: read the actual source with "
            "Read/Grep. Then give the source in your next message, a URL "
            "for an external fact and a path:line for local code, and "
            "correct or withdraw any claim the evidence fails to support."
        )
    if "[^?]" in lines_by_mark:
        steps.append(
            "For each line marked [^?], call AskUserQuestion with the "
            "question the mark stands in for and the options you would "
            "offer, before further work rests on the answer. Looking the "
            "premise up settles nothing: only the user's answer does."
        )
    steps.append(
        "A flagged line that refers to a mark, rather than claiming under "
        "one, needs no lookup. Name the mark in words and say what became of it."
    )
    numbered = "\n".join(f"{n}. {step}" for n, step in enumerate(steps, start=1))
    return (
        f"Earlier in this turn you wrote lines marked {found}, each still "
        f"awaiting resolution:\n\n{listing}\n\n"
        "Resolve each one now, so the Stop pass at the end of the turn "
        f"finds nothing left standing.\n{numbered}"
    )


def build_notice(lines_by_mark):
    listing = "\n".join(f"{mark} {line}" for mark, lines in lines_by_mark.items() for line in lines)
    return (
        "These marks survived the verification pass and stand as written, "
        "each still awaiting what its mark names:\n" + listing
    )


def run_stop(payload, delegate):
    # The harness flushes the turn's assistant entries to the transcript
    # AFTER Stop hooks run, so the transcript alone always scans one turn
    # behind. The payload's last_assistant_message carries the final reply
    # race-free; the transcript parse supplements it with any earlier
    # messages of the same turn that did flush.
    blocks = [payload.get("last_assistant_message") or ""]
    # agent_transcript_path, present only on SubagentStop, names the calling
    # subagent's own transcript; transcript_path there is the shared
    # session-level file every concurrent subagent and the orchestrator
    # write to. See
    # test_a_delegate_report_scans_its_own_agent_transcript_not_the_shared_session_one.
    transcript = payload.get("agent_transcript_path") or payload.get("transcript_path", "")
    if transcript and Path(transcript).exists():
        blocks = last_turn_text(transcript) + blocks
    lines_by_mark = marked_lines(blocks)
    carried = lines_by_mark.pop("[^?]", []) if delegate else []
    if not lines_by_mark:
        sys.exit(0)
    if payload.get("stop_hook_active"):
        json.dump({"systemMessage": build_notice(lines_by_mark)}, sys.stdout)
        sys.exit(0)
    reason = build_reason(lines_by_mark, carried)
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.exit(0)


def run_batch(payload):
    # PostToolBatch carries no last_assistant_message, and it fires after a
    # tool result the harness has already written, so the turn's earlier
    # assistant text stands in the transcript by now.
    transcript = batch_transcript(payload)
    if not transcript or not Path(transcript).exists():
        sys.exit(0)
    lines_by_mark = marked_lines(last_turn_text(transcript))
    directory = state_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        sys.exit(0)
    prune(directory, time.time())
    path = state_path(directory, state_key(payload))
    reported = read_reported(path)
    fresh = {}
    for mark, lines in lines_by_mark.items():
        unseen = [line for line in lines if line not in reported]
        if unseen:
            fresh[mark] = unseen
    if not fresh:
        sys.exit(0)
    # A line carrying two marks lands under each of them, so the membership
    # check keeps it from entering the record twice.
    for lines in fresh.values():
        for line in lines:
            if line not in reported:
                reported.append(line)
    with contextlib.suppress(OSError):
        path.write_text(json.dumps(reported))
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolBatch",
                "additionalContext": build_context(fresh),
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    # argv carries the mode rather than the payload, so the wiring in
    # settings.json alone decides which event this run answers.
    args = sys.argv[1:]
    if "--batch" in args:
        run_batch(payload)
    run_stop(payload, delegate="--delegate" in args)


if __name__ == "__main__":
    main()
