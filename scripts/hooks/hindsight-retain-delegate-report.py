#!/usr/bin/env python3
"""SubagentStop hook: retain a delegate's research report into the session's Hindsight bank.

A spider or perspectives:consultant report always counts as research. Any other delegate's
report counts when its transcript holds an online research call, by the same test the
PostToolUse research hook applies. The report is retained as `research:report:<agent_id>`.

The hook never blocks the session: any failure prints one line to stderr and exits 0.
"""

import importlib.util
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

# Run under `python -I`, which leaves the script's directory off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hindsight_research_bank import retain_report
from hindsight_retain import repo_name

HERE = Path(__file__).resolve().parent
RESEARCH_AGENTS = {"spider", "perspectives:consultant"}


def load_is_research():
    spec = importlib.util.spec_from_file_location(
        "hindsight_research_retain", HERE / "hindsight-research-retain.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.is_research


def tool_calls(transcript_path):
    with open(transcript_path, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") != "assistant":
                continue
            for block in entry.get("message", {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    yield block.get("name", ""), block.get("input") or {}


def did_research(payload):
    if payload.get("agent_type") in RESEARCH_AGENTS:
        return True
    transcript = payload.get("agent_transcript_path")
    if not transcript:
        return False
    is_research = load_is_research()
    return any(is_research(tool, tool_input) for tool, tool_input in tool_calls(transcript))


def main():
    payload = json.load(sys.stdin)
    report = payload.get("last_assistant_message") or ""
    if payload.get("stop_hook_active") or not report.strip():
        return
    if not did_research(payload):
        return
    cwd = payload.get("cwd") or "."
    agent_type = payload.get("agent_type") or "unknown"
    agent_id = payload.get("agent_id") or "unknown"
    metadata = {
        "agent_type": agent_type,
        "agent_id": agent_id,
        "session_id": payload.get("session_id") or "",
    }
    bank = retain_report(cwd, repo_name(cwd), f"research:report:{agent_id}", report, metadata)
    print(f"Research report from {agent_type} queued for Hindsight bank {bank}.", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
        urllib.error.URLError,
    ) as error:
        print(f"hindsight-retain-delegate-report: {error}", file=sys.stderr)
    sys.exit(0)
