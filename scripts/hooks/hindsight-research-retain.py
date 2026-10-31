#!/usr/bin/env python3
"""PostToolUse hook: retain each online research call into research::<repo>.

Covers WebFetch, WebSearch, the linkup, context7 and tavily MCP tools, and Bash
calls running the tvly CLI or fetching over http with curl. Outside a git
repository the bank is research::general. The hook never blocks the session: any
failure reaching the server exits 0 without output.
"""

import contextlib
import json
import re
import sys

from hindsight_retain import repo_name, retain

MAX_CHARS = 40_000
RESEARCH_TOOL = re.compile(
    r"^(WebFetch|WebSearch|mcp__linkup__.*|mcp__plugin_context7_.*|mcp__.*tavily.*)$"
)
RESEARCH_COMMAND = re.compile(r"(^|[\s;&|(])(tvly\s|curl\s[^|;&]*https?://)")


def is_research(tool, tool_input):
    if RESEARCH_TOOL.match(tool):
        return True
    return tool == "Bash" and bool(RESEARCH_COMMAND.search(tool_input.get("command", "")))


def response_text(response):
    if isinstance(response, str):
        return response
    return json.dumps(response, ensure_ascii=False)


def main():
    payload = json.load(sys.stdin)
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if not is_research(tool, tool_input):
        return
    repo = repo_name(payload.get("cwd") or ".")
    bank = f"research::{repo}" if repo else "research::general"
    content = (
        f"Online research through {tool}.\n"
        f"Request: {json.dumps(tool_input, ensure_ascii=False)}\n\n"
        f"Result:\n{response_text(payload.get('tool_response'))[:MAX_CHARS]}"
    )
    retain(
        bank,
        content,
        document_id=f"research:{payload.get('session_id', 'session')}:{payload.get('tool_use_id', tool)}",
        tags=["source:research", f"tool:{tool}", f"repo:{repo or 'none'}"],
        context=f"online research via {tool}",
    )


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        main()
