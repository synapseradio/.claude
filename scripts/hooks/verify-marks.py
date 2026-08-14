#!/usr/bin/env python3
"""Stop hook: a verification pass for epistemic marks.

Scans the assistant text of the turn that just finished for the marks
`[?]` (a claim with no source on file) and `[.?]` (a claim that arrived
secondhand and stayed ungrounded), per core-rules.sudolang.md 8.GroundOrMark.
When either mark appears, the hook blocks the stop once and hands back
instructions: verify each marked claim through real lookups, then re-emit
the original reply verbatim with each mark replaced in place by its
inline citation, correcting or removing only the sentences that failed.

One pass per stop cycle: `stop_hook_active` means a Stop hook already
blocked this cycle, so the hook exits silently instead of looping. A mark
that survives its verification pass therefore stands as written.
"""

import json
import sys
from pathlib import Path

MARKS = ("[?]", "[.?]")


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


def marked_lines(blocks):
    """Lines carrying a mark, skipping fenced code (quoted rules, examples)."""
    lines = []
    for block in blocks:
        in_fence = False
        for line in block.splitlines():
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if any(mark in line for mark in MARKS):
                lines.append(line.strip())
    return lines


def build_reason(lines):
    listing = "\n".join(f"- {line}" for line in lines)
    return (
        "Your reply carries claims marked [?] or [.?] — unverified or "
        "uncited:\n"
        f"{listing}\n\n"
        "Run a verification pass, then re-emit the reply with the marks "
        "resolved.\n"
        "1. For each marked claim, gather the evidence that would ground "
        "it. External facts: use a purpose-built research tool (the "
        "linkup MCP tools, the tavily CLI, context7 for library docs). "
        "Claims about local code or files: read the actual source with "
        "Read/Grep.\n"
        "2. Re-emit the original reply verbatim, treating each mark as a "
        "template slot. A claim that verified keeps its exact sentence, "
        "with the mark replaced in place by the inline citation: a URL "
        "for an external fact, a path:line for local code. A claim that "
        "failed verification gets its sentence corrected to what the "
        "evidence supports, or removed if nothing supports it, with a "
        "parenthetical noting the point could not be verified.\n"
        "3. Change nothing outside the marked sentences: no added "
        "commentary, no report about the verification, no restructuring. "
        "The reader sees the same message they would have seen, with "
        "sources where the marks stood."
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
    lines = []
    for line in marked_lines(blocks):
        if line not in lines:
            lines.append(line)
    if not lines:
        sys.exit(0)
    json.dump({"decision": "block", "reason": build_reason(lines)}, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
