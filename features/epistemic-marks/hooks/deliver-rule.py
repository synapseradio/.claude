#!/usr/bin/env python3
"""SessionStart and SubagentStart hook: teaches the marks the other hooks enforce.

The rule text and the verification hooks are one unit, and delivery is the
half that produces the signal. verify-marks.py matches literal tokens, so an
agent that was never taught the vocabulary writes no mark, the scan comes back
empty, and the verification pass is inert. A spawned agent needs the text for
the same reason a session does, which is why both start events fire this.

Runs on every SessionStart source, since additionalContext does not outlive a
compaction and each firing re-delivers the text, per
https://code.claude.com/docs/en/hooks
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from epistemic_marks.delivery import rule_text


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    # The echoed name has to be the event that fired, since the same script
    # serves both starts and the harness reads the answer against the event
    # it sent.
    event = payload.get("hook_event_name") or "SessionStart"
    text = rule_text()
    if not text:
        sys.exit(0)
    json.dump(
        {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}},
        sys.stdout,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
