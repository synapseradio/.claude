#!/usr/bin/env python3
"""The verification pass for epistemic marks, run from three hook events.

Bare from Stop, blocking the stop once and asking for each mark's
resolution. With --delegate from SubagentStop, where a relaying mark is left
standing for the delegate's own report to carry, since nothing this hook
returns reaches the caller. With --batch from PostToolBatch, which never
blocks and reports a line once per session.

A mark surviving a top-level pass reaches the user through systemMessage,
since stderr from a hook exiting 0 goes to the debug log alone. The same
finding reaches a delegate through additionalContext, which is what a
SubagentStop hook has that carries text to the agent that just stopped, per
https://code.claude.com/docs/en/hooks

epistemic_marks/marks.py holds the vocabulary. The rule text teaching it ships under
rule-text/ and reaches a session through hooks/deliver-rule.py.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from epistemic_marks.citations import unopened
from epistemic_marks.ledger import (
    fingerprint,
    prepare,
    prune,
    read_reported,
    state_dir,
    state_key,
    state_path,
    write_reported,
)
from epistemic_marks.marks import RELAY_MARKS
from epistemic_marks.messages import build_context, build_notice, build_reason
from epistemic_marks.scan import batch_transcript, last_turn_text, marked_lines


def run_stop(payload, delegate):
    # The harness flushes the turn's assistant entries after Stop hooks run,
    # so last_assistant_message carries the final reply and the transcript
    # supplies the earlier messages of the same turn.
    blocks = [payload.get("last_assistant_message") or ""]
    # agent_transcript_path names the calling subagent's own transcript;
    # transcript_path names the session-level file every concurrent subagent
    # and the orchestrator write to.
    transcript = payload.get("agent_transcript_path") or payload.get("transcript_path", "")
    if transcript and Path(transcript).exists():
        blocks = last_turn_text(transcript) + blocks
    lines_by_mark, mentions = marked_lines(blocks)
    carried = (
        {token: lines_by_mark.pop(token) for token in RELAY_MARKS if token in lines_by_mark}
        if delegate
        else {}
    )
    if lines_by_mark and not payload.get("stop_hook_active"):
        json.dump(
            {"decision": "block", "reason": build_reason(lines_by_mark, carried, delegate)},
            sys.stdout,
        )
        sys.exit(0)
    # The reply stands from here, so the citation check runs only on a pass
    # that is not about to replace it, and its finding rides along with
    # whatever else this pass has to report.
    # additionalContext continues the subagent where systemMessage did not,
    # which is the point on a first pass: the delegate rewrites its report
    # with the question surfaced. On a second pass it is a loop, so the relay
    # group is withheld once stop_hook_active is set, per the Stop decision
    # control this event inherits at https://code.claude.com/docs/en/hooks
    notice = build_notice(
        lines_by_mark,
        mentions,
        unopened(blocks, transcript),
        carried if not payload.get("stop_hook_active") else None,
    )
    if notice and delegate:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStop",
                    "additionalContext": notice,
                }
            },
            sys.stdout,
        )
    elif notice:
        json.dump({"systemMessage": notice}, sys.stdout)
    sys.exit(0)


def run_batch(payload):
    transcript = batch_transcript(payload)
    if not transcript or not Path(transcript).exists():
        sys.exit(0)
    lines_by_mark, _mentions = marked_lines(last_turn_text(transcript))
    directory = state_dir()
    if not prepare(directory):
        sys.exit(0)
    prune(directory, time.time())
    path = state_path(directory, state_key(payload))
    reported = read_reported(path)
    seen = set(reported)
    fingerprints = {}
    fresh = {}
    for mark, lines in lines_by_mark.items():
        unseen = []
        for line in lines:
            fp = fingerprints.setdefault(line, fingerprint(line))
            if fp not in seen:
                unseen.append(line)
        if unseen:
            fresh[mark] = unseen
    if not fresh:
        sys.exit(0)
    for lines in fresh.values():
        for line in lines:
            fp = fingerprints[line]
            if fp not in seen:
                seen.add(fp)
                reported.append(fp)
    write_reported(path, reported)
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolBatch",
                "additionalContext": build_context(fresh),
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    args = sys.argv[1:]
    if "--batch" in args:
        run_batch(payload)
    run_stop(payload, delegate="--delegate" in args)


if __name__ == "__main__":
    main()
