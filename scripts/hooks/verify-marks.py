#!/usr/bin/env python3
"""Stop hook: a verification pass for epistemic marks.

Scans the assistant text of the turn that just finished for the marks
`[?]` (a claim with no source on file), `[.?]` (a claim that arrived
secondhand and stayed ungrounded), and `[^?]` (a premise only the user can
settle), per core-rules.sudolang.md 8.GroundOrMark. When any mark appears,
the hook blocks the stop once and hands back the resolution each mark
takes: verify a `[?]` or `[.?]` claim through real lookups and re-emit the
original reply verbatim with each mark replaced in place by its inline
citation, correcting or removing only the sentences that failed; put the
question a `[^?]` stands in for to the user through AskUserQuestion, since
in live conversation the question replaces the mark.

One pass per stop cycle: `stop_hook_active` means a Stop hook already
blocked this cycle, so the hook exits silently instead of looping. A mark
that survives its verification pass therefore stands as written.

Run with `--delegate` from SubagentStop, where a `[^?]` rides up to the
caller untouched: a subagent reaches no user, so the question it stands in
for travels in the report rather than through AskUserQuestion.
"""

import json
import re
import sys
from pathlib import Path

MARKS = ("[?]", "[.?]", "[^?]")

MARK_MEANINGS = {
    "[?]": "no source on file",
    "[.?]": "secondhand and ungrounded",
    "[^?]": "awaits an answer only the user supplies",
}


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


def marked_lines(blocks):
    """Lines carrying a mark, keyed by mark, skipping fenced code and inline
    code spans, where a mark is a mention rather than a claim.

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
        prose = INLINE_CODE.sub("", line)
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


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    if payload.get("stop_hook_active"):
        sys.exit(0)
    # The harness flushes the turn's assistant entries to the transcript
    # AFTER Stop hooks run, so the transcript alone always scans one turn
    # behind. The payload's last_assistant_message carries the final reply
    # race-free; the transcript parse supplements it with any earlier
    # messages of the same turn that did flush.
    blocks = [payload.get("last_assistant_message") or ""]
    transcript = payload.get("transcript_path", "")
    if transcript and Path(transcript).exists():
        blocks = last_turn_text(transcript) + blocks
    lines_by_mark = marked_lines(blocks)
    # argv carries the mode rather than the payload, so the wiring in
    # settings.json alone decides which event this run answers.
    delegate = "--delegate" in sys.argv[1:]
    carried = lines_by_mark.pop("[^?]", []) if delegate else []
    if not lines_by_mark:
        sys.exit(0)
    reason = build_reason(lines_by_mark, carried)
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
