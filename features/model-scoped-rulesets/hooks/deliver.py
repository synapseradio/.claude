#!/usr/bin/env python3
"""Deliver a session's or a delegate's ruleset into its context.

Wired to `SessionStart`, `SubagentStart`, and `PostModelSwitch` to deliver,
and to `PreToolUse` on `Agent` to record the per-spawn model a later
`SubagentStart` reads. Nothing in the corpus auto-loads, so a failure here
leaves the session with no user rules. The resolver answers the `default`
tier's bodies wherever a tier, a manifest, or a body is unavailable, and it
answers a header naming the cause where even those are missing. What
escapes it is either a body the process could not read or a defect in this
plugin, and both leave the session without its rules, so both are announced
down the same channel a delivery uses: context naming the failure, exit 0
so the session still starts. A silent session with no rules is the outcome
this plugin exists to prevent; a session that says it has none can be
repaired.

The hook commands pass no flag, so the corpus and the state resolve the way
every other entry point resolves them. `--root` and `--state` name them
outright, which the forwarders at the old command paths use during the
migration and a test uses to keep off live state.
"""

import argparse
import json
import pathlib
import sys
import traceback
from collections.abc import Callable
from typing import TextIO

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets import resolve

FAILURE_TIER = "delivery failed"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None, help="the live corpus to read")
    parser.add_argument("--state", default=None, help="the state directory to write")
    return parser


def failure_output(event: str, reason: str, defect: bool) -> dict:
    """The context a failed delivery sends where the ruleset would have gone.

    The first line keeps the header's shape, with `delivery failed` where a
    tier would be and `0 stems`, so a reader who knows the header reads this
    one the same way. `defect` marks a failure the corpus owner cannot fix by
    editing the corpus, and points at the traceback on stderr.
    """

    hook = pathlib.Path(__file__).resolve()
    lines = [
        f"<!-- ruleset: {FAILURE_TIER}, from {hook.name}, 0 stems -->",
        f"<!-- note: {reason} -->",
        "",
        "Ruleset delivery failed, so this session is running without its user rules. "
        "Tell the user this before doing anything else.",
        "",
    ]
    if defect:
        lines.append(
            "The cause is a defect in the rulesets plugin, not in the corpus; the traceback "
            "went to the hook's stderr. Run the hook by hand to see it again:"
        )
    else:
        lines.append(
            "The cause is a file the hook could not read or write. Repair it, then run the "
            "hook by hand to confirm:"
        )
    lines += [
        "",
        f'    echo \'{{"hook_event_name":"{event}","session_id":"probe"}}\' | python3 {hook}',
        "",
        "A new session delivers the rules once that prints a header naming a tier.",
    ]
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": "\n".join(lines)}}


def main(
    argv: list[str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    deliver: Callable[..., dict] = resolve.deliver_payload,
) -> int:
    """Run the hook. The streams and the resolver are injectable for tests."""

    args = build_parser().parse_args(argv)
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    # With no readable payload there is no event to address an answer to, so
    # the only channel left is stderr. The harness always sends an object.
    try:
        payload = json.loads(stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        print(f"deliver.py: stdin was not JSON, so nothing was delivered: {exc}", file=stderr)
        return 0
    if not isinstance(payload, dict):
        print("deliver.py: stdin was not a JSON object, so nothing was delivered", file=stderr)
        return 0
    event = payload.get("hook_event_name") or "SessionStart"

    try:
        output = deliver(payload, root=args.root, state=args.state)
    except OSError as exc:
        # The one failure a sound plugin meets: a body it could not read, or a
        # state path it could not write. The message names the path.
        output = failure_output(event, f"{type(exc).__name__}: {exc}", defect=False)
    except Exception as exc:
        # A defect. The traceback is the finding; the context is what makes
        # the session say so rather than start quietly with no rules.
        traceback.print_exc(file=stderr)
        output = failure_output(event, f"{type(exc).__name__}: {exc}", defect=True)

    if output:
        print(json.dumps(output), file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
