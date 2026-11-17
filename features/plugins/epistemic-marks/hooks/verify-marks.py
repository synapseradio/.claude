#!/usr/bin/env python3
"""The verification pass for epistemic marks, run from four hook events.

Bare from Stop, blocking on every pass that finds a line still owed an act.
With --delegate from SubagentStop, where a relaying mark is left standing for
the delegate's own report to carry, since nothing this hook returns reaches
the caller. With --batch from PostToolBatch, which never blocks and reports a
line once per session. With --prompt from PreToolUse on a spawn call, denying
a prompt that hands its delegate a guess in words.

Every pass reads for two things: a mark, and a guess written in words where
a mark belongs. epistemic_marks/hedges.py holds the second scan.

Every output reaches the model, and the user sees the same text beside it.
The model-facing field is `decision` with `reason` on Stop and SubagentStop,
`additionalContext` where a pass reports without blocking, and
`permissionDecisionReason` on a denied spawn call. Each output also carries
that text as `systemMessage`, which reaches the user alone, per
https://code.claude.com/docs/en/hooks, so no output is a `systemMessage`
alone. A pass stays silent only about lines the model was already sent.

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


def emit(output, text) -> None:
    """Print one output whose model-facing field holds `text`, shown to the user too."""
    json.dump({**output, "systemMessage": text}, sys.stdout)
    sys.exit(0)


def opens_on(reply, standing, marked) -> bool:
    """Whether the reply puts every standing line ahead of every line with no mark.

    `marked` holds every line the scan found carrying a mark, any of which
    may sit in the opening. Blank lines, headings and labels ending in a
    colon are passed over, as STANDING_HEADING in messages.py tells the
    reader.
    """
    wanted = {line for lines in standing.values() for line in lines}
    for raw in reply.splitlines():
        if not wanted:
            break
        line = raw.strip()
        if not line or line.startswith("#") or line.rstrip("*_ ").endswith(":"):
            continue
        if line not in marked:
            return False
        wanted.discard(line)
    return not wanted


def run_stop(payload, delegate) -> None:
    # The harness flushes the turn's assistant entries after Stop hooks run,
    # so last_assistant_message carries the final reply and the transcript
    # supplies the earlier messages of the same turn.
    reply = payload.get("last_assistant_message") or ""
    blocks = [reply]
    # agent_transcript_path names the calling subagent's own transcript;
    # transcript_path names the session-level file every concurrent subagent
    # and the orchestrator write to.
    transcript = payload.get("agent_transcript_path") or payload.get("transcript_path", "")
    again = bool(payload.get("stop_hook_active"))
    # A later pass judges the reply rewritten after the block. The earlier
    # messages of the turn hold the superseded draft, whose lines the rewrite
    # already answered, so only the rewrite is read.
    if transcript and Path(transcript).exists() and not again:
        blocks = last_turn_text(transcript) + blocks
    lines_by_mark, wording, mentions = unchecked_claims(blocks)
    carried = (
        {token: lines_by_mark.pop(token) for token in RELAY_MARKS if token in lines_by_mark}
        if delegate
        else {}
    )
    marked = {
        line for group in (lines_by_mark, carried) for lines in group.values() for line in lines
    }

    # The record holds every line a pass sent the model since the turn's
    # first pass, which starts it over: the harness sets stop_hook_active
    # only while it is "already continuing as a result of a stop hook", per
    # https://code.claude.com/docs/en/hooks. stop_hook_active says some hook
    # continued the turn, not that this one sent the model every line, so a
    # line first written after a block, or in a turn another plugin's Stop
    # hook continued, still goes out. Where no record can be kept, no line
    # counts as sent, so every pass sends every line until the harness's
    # cap ends the turn.
    directory = state_dir()
    path = state_path(directory, f"{state_key(payload)}-stop-sent") if prepare(directory) else None
    sent = set(read_reported(path)) if path and again else set()

    def unsent(groups) -> dict[str, list[str]]:
        fresh = {}
        for key, lines in groups.items():
            kept = [line for line in lines if fingerprint(line) not in sent]
            if kept:
                fresh[key] = kept
        return fresh

    fresh = unsent(lines_by_mark)
    new_mentions = unsent(mentions)
    new_relay = unsent(carried)
    # A marked line already sent back for its check may stand, since the
    # check it waits on can be out of reach, but only at the head of the
    # reply, where the rule text tells the writer to put it. Wording never
    # has to stand: marking the claim or cutting it needs no tool. So the
    # loop ends when the reply does what the block asked; the harness's own
    # end is its override after eight consecutive continuations, per
    # https://code.claude.com/docs/en/hooks
    listed = {
        mark: kept
        for mark, lines in lines_by_mark.items()
        if (kept := [line for line in lines if line not in fresh.get(mark, [])])
    }
    standing = listed if again and not opens_on(reply, listed, marked) else {}

    if path is not None:
        newly = [
            line
            for group in (fresh, new_mentions, new_relay)
            for lines in group.values()
            for line in lines
        ]
        write_reported(path, sorted(sent | {fingerprint(line) for line in newly}))

    if fresh or wording or standing:
        reason = build_reason(fresh, new_relay, delegate, wording, standing, new_mentions)
        emit({"decision": "block", "reason": reason}, reason)
    # A mention claims nothing and a relayed line is the caller's to settle,
    # so neither blocks. additionalContext still hands each one to the model
    # and continues it, the one way a Stop or SubagentStop hook has to do
    # that without a block, per https://code.claude.com/docs/en/hooks. The
    # record keeps a line it carried from going out twice.
    if new_mentions or new_relay:
        notice = build_notice({}, new_mentions, new_relay)
        event = "SubagentStop" if delegate else "Stop"
        emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": notice}}, notice)
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
    context = build_context(fresh_marks, fresh_wording)
    emit(
        {"hookSpecificOutput": {"hookEventName": "PostToolBatch", "additionalContext": context}},
        context,
    )


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
    denial = build_denial(wording)
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": denial,
            }
        },
        denial,
    )


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
