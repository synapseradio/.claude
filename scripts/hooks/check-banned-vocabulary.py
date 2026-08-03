#!/usr/bin/env python3
"""Stop hook: report banned vocabulary in the turn's final message.

Reads the Stop hook JSON envelope on stdin and inspects
`last_assistant_message`, which carries the text of the final response
without the lag that reading `transcript_path` would incur.

Coverage stays deliberately narrow. Returning `additionalContext` on Stop
continues the conversation for another turn, so every false positive costs a
turn. Only the two bans with no legitimate use are checked; looser patterns
("shape", emoji) would misfire on quotation and on user requests.

Enforces the Never section of rules/writing-prose.md.

Stdin:  Stop hook JSON envelope.
Stdout: hookSpecificOutput JSON when a ban is hit; nothing otherwise.
"""

import json
import re
import sys

BANS = (
    (re.compile("—"), "em dash"),
    (re.compile(r"load[-‑ ]bearing", re.IGNORECASE), '"load-bearing"'),
)

# Naming a banned term inside quotes or backticks mentions it rather than uses
# it, which is how the ban itself gets discussed. Quoted spans drop before the
# scan so writing about the rule never trips it.
QUOTED_SPAN = re.compile(
    r"`[^`]*`|\"[^\"\n]*\"|'[^'\n]*'|“[^”\n]*”|‘[^’\n]*’"
)

GUIDANCE = (
    "Banned vocabulary in your last message: {found}. "
    "See the Never section of rules/writing-prose.md. "
    "Rephrase going forward without announcing the correction."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    message = QUOTED_SPAN.sub(" ", payload.get("last_assistant_message") or "")
    found = [label for pattern, label in BANS if pattern.search(message)]
    if not found:
        return 0

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": GUIDANCE.format(found=", ".join(found)),
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
