#!/usr/bin/env python3
"""SubagentStop hook: retain a thinkies subagent's final report into Hindsight.

The report is retained to the global bank and, inside a git repository, to
coding-agent::<repo>, under one document id so recall from either bank finds it.
The id is thinkies:<skill>:<agent_id> when the report's opening lines name a
thinkies skill, and thinkies:<agent_id> otherwise. Any failure exits 0 silently.
"""

import contextlib
import json
import re
import sys
from pathlib import Path

# Run under `python -I`, which leaves the script's directory off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hindsight_retain import repo_name, retain

MAX_CHARS = 60_000
OPENING_LINES = 5
SKILL = re.compile(r"\bthinkies:([\w-]+)")


def skill_named(report):
    """The thinkies skill named in the report's first lines, or None."""
    match = SKILL.search("\n".join(report.splitlines()[:OPENING_LINES]))
    return f"thinkies:{match.group(1)}" if match else None


def main():
    payload = json.load(sys.stdin)
    report = payload.get("last_assistant_message") or ""
    if payload.get("agent_type") != "thinkies" or payload.get("stop_hook_active"):
        return
    if not report.strip():
        return
    agent_id = payload.get("agent_id") or "unknown"
    repo = repo_name(payload.get("cwd") or ".")
    skill = skill_named(report)
    document_id = f"thinkies:{skill}:{agent_id}" if skill else f"thinkies:{agent_id}"
    tags = ["source:thinkies", f"repo:{repo or 'none'}"]
    content = f"Output of a thinkies agent run.\n\n{report[:MAX_CHARS]}"
    banks = ["global"] + ([f"coding-agent::{repo}"] if repo else [])
    for bank in banks:
        with contextlib.suppress(Exception):
            retain(bank, content, document_id, tags, context="thinkies agent report")


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
