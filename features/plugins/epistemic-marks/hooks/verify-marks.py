#!/usr/bin/env python3
"""The verification pass for epistemic marks, run from four hook events.

Bare from Stop, blocking the stop once and asking for each mark's
resolution. With --delegate from SubagentStop, where a relaying mark is left
standing for the delegate's own report to carry, since nothing this hook
returns reaches the caller. With --batch from PostToolBatch, which never
blocks and reports a line once per session. With --prompt from PreToolUse on
a spawn call, denying a prompt that hands its delegate a guess in words.

Every pass reads for two things: a mark, and a guess written in words where
a mark belongs. epistemic_marks/hedges.py holds the second scan.

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

from epistemic_marks.hedges import guessed_lines, unchecked_claims
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
from epistemic_marks.messages import build_context, build_denial, build_notice, build_reason
from epistemic_marks.scan import batch_transcript, last_turn_text


def already_sent(payload, notice) -> bool:
    """Whether this agent was already handed this notice, recording it where not.

    additionalContext continues the subagent, which stops again with
    stop_hook_active still set, so an unchanged notice sent every pass
    restarts it up to the harness's cap. The record sits apart from the
    batch pass's line fingerprints, which DESIGN.md explains would suppress
    a notice the batch pass had already reported mid-turn.
    """
    directory = state_dir()
    if not prepare(directory):
        return False
    path = state_path(directory, f"{state_key(payload)}-stop-notices")
    sent = read_reported(path)
    fp = fingerprint(notice)
    if fp in sent:
        return True
    write_reported(path, [*sent, fp])
    return False


def run_stop(payload, delegate) -> None:
    # The harness flushes the turn's assistant entries after Stop hooks run,
    # so last_assistant_message carries the final reply and the transcript
    # supplies the earlier messages of the same turn.
    blocks = [payload.get("last_assistant_message") or ""]
    # agent_transcript_path names the calling subagent's own transcript;
    # transcript_path names the session-level file every concurrent subagent
    # and the orchestrator write to.
    transcript = payload.get("agent_transcript_path") or payload.get("transcript_path", "")
    # A second pass judges the reply rewritten after the block. The earlier
    # messages of the turn hold the superseded draft, whose lines the rewrite
    # already answered, so only the rewrite is read.
    if transcript and Path(transcript).exists() and not payload.get("stop_hook_active"):
        blocks = last_turn_text(transcript) + blocks
    lines_by_mark, wording, mentions = unchecked_claims(blocks)
    carried = (
        {token: lines_by_mark.pop(token) for token in RELAY_MARKS if token in lines_by_mark}
        if delegate
        else {}
    )
    if (lines_by_mark or wording) and not payload.get("stop_hook_active"):
        json.dump(
            {
                "decision": "block",
                "reason": build_reason(lines_by_mark, carried, delegate, wording),
            },
            sys.stdout,
        )
        sys.exit(0)
    # additionalContext continues the subagent where systemMessage did not,
    # which is the point on a first pass: the delegate rewrites its report
    # with the question surfaced. On a second pass it is a loop, so the relay
    # group is withheld once stop_hook_active is set, per the Stop decision
    # control this event inherits at https://code.claude.com/docs/en/hooks
    notice = build_notice(
        lines_by_mark,
        mentions,
        carried if not payload.get("stop_hook_active") else None,
        wording,
    )
    if notice and delegate and payload.get("stop_hook_active") and already_sent(payload, notice):
        sys.exit(0)
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


def run_batch(payload) -> None:
    transcript = batch_transcript(payload)
    if not transcript or not Path(transcript).exists():
        sys.exit(0)
    lines_by_mark, wording, _mentions = unchecked_claims(last_turn_text(transcript))
    directory = state_dir()
    if not prepare(directory):
        sys.exit(0)
    prune(directory, time.time())
    path = state_path(directory, state_key(payload))
    reported = read_reported(path)
    seen = set(reported)
    fingerprints = {}

    def unseen(groups) -> dict[str, list[str]]:
        """The lines of each group no earlier batch reported, empty groups dropped."""
        fresh = {}
        for key, lines in groups.items():
            kept = [
                line
                for line in lines
                if fingerprints.setdefault(line, fingerprint(line)) not in seen
            ]
            if kept:
                fresh[key] = kept
        return fresh

    fresh_marks, fresh_wording = unseen(lines_by_mark), unseen(wording)
    if not fresh_marks and not fresh_wording:
        sys.exit(0)
    for lines in [*fresh_marks.values(), *fresh_wording.values()]:
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
                "additionalContext": build_context(fresh_marks, fresh_wording),
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def run_prompt(payload) -> None:
    """Deny a spawn call whose prompt guesses in words.

    A mark in the prompt passes, since a marked observation is what the rule
    asks a prompt to carry. Only the prompt is read: the description is a
    label for a transcript row. The denial travels as permissionDecision,
    whose reason reaches the agent that composed the prompt, per
    https://code.claude.com/docs/en/hooks
    """
    tool_input = payload.get("tool_input")
    prompt = tool_input.get("prompt") if isinstance(tool_input, dict) else None
    if not isinstance(prompt, str):
        sys.exit(0)
    wording, _mentions = guessed_lines([prompt])
    if not wording:
        sys.exit(0)
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": build_denial(wording),
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    args = sys.argv[1:]
    if "--batch" in args:
        run_batch(payload)
    if "--prompt" in args:
        run_prompt(payload)
    run_stop(payload, delegate="--delegate" in args)


if __name__ == "__main__":
    main()
