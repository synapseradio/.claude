#!/usr/bin/env python3
"""SessionStart hook: teaches the session the marks the other hooks enforce.

The rule text and the verification hooks are one unit. Enforcement reaching a
session that was never taught the marks would correct a model against nothing.

Runs on every SessionStart source, since additionalContext does not outlive a
compaction and each firing re-delivers the text, per
https://code.claude.com/docs/en/hooks
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from epistemic_marks.delivery import rule_text

EVENT = "SessionStart"


def main():
    try:
        json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    text = rule_text()
    if not text:
        sys.exit(0)
    json.dump(
        {"hookSpecificOutput": {"hookEventName": EVENT, "additionalContext": text}},
        sys.stdout,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
