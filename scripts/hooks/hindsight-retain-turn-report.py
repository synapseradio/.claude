#!/usr/bin/env python3
"""Stop hook: retain the main session's closing message after a turn that did online research.

The PostToolUse research hook leaves a marker named for the session when the main session
makes an online research call; this hook retains the turn's last assistant message as
`research:report:<session_id>:<timestamp>` and removes the marker, so the next turn starts
unmarked.

The hook never blocks the session: any failure prints one line to stderr and exits 0.
"""

import json
import subprocess
import sys
import tempfile
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

# Run under `python -I`, which leaves the script's directory off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hindsight_research_bank import retain_report
from hindsight_retain import repo_name

TURN_MARKERS = Path(tempfile.gettempdir()) / "hindsight-research-turn"


def main():
    payload = json.load(sys.stdin)
    session = payload.get("session_id")
    if payload.get("stop_hook_active") or not session:
        return
    marker = TURN_MARKERS / session
    if not marker.exists():
        return
    marker.unlink()
    report = payload.get("last_assistant_message") or ""
    if not report.strip():
        return
    cwd = payload.get("cwd") or "."
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    metadata = {"agent_type": "main", "session_id": session}
    bank = retain_report(
        cwd, repo_name(cwd), f"research:report:{session}:{stamp}", report, metadata
    )
    print(f"Research turn report queued for Hindsight bank {bank}.", file=sys.stderr)


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
        print(f"hindsight-retain-turn-report: {error}", file=sys.stderr)
    sys.exit(0)
