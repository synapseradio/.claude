#!/usr/bin/env python3
"""PostToolUse and PostToolUseFailure hook: a lookup once a tool call fails.

Hands back the lookup that search-tools.sudolang.md AFailureBuysALookup
requires, reading the installed artifact and searching the live web
together rather than attempting again from the recollection that produced
the failure. A streak reports its length, and a streak whose failures carry
one error asks for that text verbatim.

Register the script on both events. PostToolUseFailure speaks; PostToolUse
clears the streak, so the count measures failures uninterrupted by success.
An abort carries no wrong model of the interface, so a payload whose
`is_interrupt` is true never counts.

Permission denials and validation rejections reach neither event, so the
count covers tools that started executing and then failed.
"""

import contextlib
import json
import os
import re
import sys
import time
from pathlib import Path

THRESHOLD = 1
RECENT = 3
STALE_SECONDS = 24 * 60 * 60
TARGET_KEYS = ("command", "file_path", "pattern", "url", "path", "query")


def state_dir():
    override = os.environ.get("CLAUDE_REPEAT_FAILURE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".claude" / ".tmp" / "repeat-failure"


def state_path(directory, session_id):
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return directory / f"{safe or 'session'}.json"


def prune(directory, now):
    for path in directory.glob("*.json"):
        try:
            if now - path.stat().st_mtime > STALE_SECONDS:
                path.unlink()
        except OSError:
            continue


def read_state(path):
    try:
        state = json.loads(path.read_text())
    except OSError, ValueError:
        return {"count": 0, "failures": []}
    if not isinstance(state, dict):
        return {"count": 0, "failures": []}
    return {"count": state.get("count", 0), "failures": state.get("failures", [])}


EXIT_CODE = re.compile(r"^exit code \d+\.?$", re.IGNORECASE)


def summarize(text):
    """The first line, plus the next one where the first is only a status.

    A bare `Exit code N` names no interface, so the line under it carries
    the text worth searching.
    """
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return "no error text"
    head = lines[0][:200]
    if EXIT_CODE.match(lines[0]) and len(lines) > 1:
        return f"{head} {lines[1][:200]}"
    return head


def target_of(tool_input):
    if not isinstance(tool_input, dict):
        return ""
    for key in TARGET_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().splitlines()[0][:120]
    return ""


def describe(failure):
    target = failure.get("target")
    head = f"{failure.get('tool', 'a tool')}"
    if target:
        head += f" `{target}`"
    return f"- {head}\n  {failure.get('error', '')}"


def build_context(failures, count):
    listing = "\n".join(describe(f) for f in failures)
    errors = [f.get("error") for f in failures]
    repeated = len(errors) > 1 and len(set(errors)) == 1
    if count > 1:
        lead = (
            f"{count} tool calls have failed in a row with no success between them:\n{listing}\n\n"
        )
        opening = (
            "Stop attempting. A failure that repeats reports a wrong model "
            "of the interface rather than a wrong keystroke, so another "
            "attempt from the same understanding fails the same way."
        )
    else:
        lead = f"A tool call failed:\n{listing}\n\n"
        opening = (
            "Read before attempting again. Where this failure names an "
            "interface, a flag, a signature, or a config key, your "
            "recollection of it is a guess until a source confirms it."
        )
    steps = [
        opening,
        "Name the interface in question and the version the lockfile resolves for it.",
        "In one response, read the installed artifact and search the live "
        "web: the package's own types, `--help` output, or bundled docs on "
        "one side, and a Tavily, linkup, or context7 lookup on the other. "
        "Neither waits on the other, and neither substitutes for the other.",
        "State what the sources settled and what they left open, then "
        "resume from that rather than from your recollection.",
    ]
    if repeated:
        steps.insert(
            1,
            "The failures carried one error, so search that error text "
            "verbatim before anything else.",
        )
    numbered = "\n".join(f"{n}. {s}" for n, s in enumerate(steps, start=1))
    closing = (
        "\n\nA test you wrote to fail has already done its job: where this "
        "failure is the red step you predicted, say so in one clause and "
        "carry on to the code that makes it pass."
    )
    return lead + numbered + closing


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    directory = state_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        sys.exit(0)
    path = state_path(directory, payload.get("session_id") or "session")
    if payload.get("hook_event_name") != "PostToolUseFailure":
        with contextlib.suppress(OSError):
            path.unlink()
        sys.exit(0)
    if payload.get("is_interrupt"):
        sys.exit(0)
    prune(directory, time.time())
    state = read_state(path)
    state["count"] += 1
    state["failures"].append(
        {
            "tool": payload.get("tool_name") or "a tool",
            "target": target_of(payload.get("tool_input")),
            "error": summarize(payload.get("error")),
        }
    )
    state["failures"] = state["failures"][-RECENT:]
    with contextlib.suppress(OSError):
        path.write_text(json.dumps(state))
    # Every THRESHOLD-th failure of one streak speaks, so a streak that runs
    # long repeats the demand instead of falling silent after the first.
    if state["count"] % THRESHOLD:
        sys.exit(0)
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUseFailure",
                "additionalContext": build_context(state["failures"], state["count"]),
            }
        },
        sys.stdout,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
