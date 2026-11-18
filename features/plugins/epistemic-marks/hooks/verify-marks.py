#!/usr/bin/env python3
"""The verification pass for epistemic marks, run from four hook events.

Bare from Stop, blocking on a pass that finds a line still owed an act, up to
BLOCK_CAP blocks in a turn.
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

Once a turn holds BLOCK_CAP blocks, a Stop or SubagentStop pass that would
block returns the same findings as `additionalContext` and never blocks again
that turn, which keeps the hook under the harness's override after eight
consecutive continuations. Without a writable state directory the cap is one
block: the first pass blocks, and any pass the harness reports as continued
carries its findings as context.

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
    forget_turn,
    prepare,
    prune,
    read_reported,
    read_turn,
    state_dir,
    state_key,
    state_path,
    unrecorded,
    write_reported,
    write_turn,
)
from epistemic_marks.marks import RELAY_MARKS
from epistemic_marks.messages import Mode, build_context, build_denial, build_findings
from epistemic_marks.output import block, context, deny
from epistemic_marks.routes import denied_routes
from epistemic_marks.scan import batch_transcript, last_turn_entries, last_turn_text, text_blocks

# The most blocks one turn draws from this hook. The harness overrides the
# next block after eight consecutive continuations, per
# https://code.claude.com/docs/en/hooks, so the hook stops blocking well short.
BLOCK_CAP = 5

# Without a state directory no count survives a pass. The first pass blocks,
# and a pass arriving with stop_hook_active set counts as following that block.
UNRECORDED_CAP = 1


def emit(output) -> None:
    """Print one output from epistemic_marks/output.py and end the pass."""
    json.dump(output, sys.stdout)
    sys.exit(0)


def flat(*groups) -> list[str]:
    """Every line of every group, in order."""
    return [line for group in groups for lines in group.values() for line in lines]


def opens_on(reply, standing_lines, marked) -> bool:
    """Whether the reply puts every line in `standing_lines` ahead of every line with no mark.

    `marked` holds every line the scan found carrying a mark, any of which
    may sit in the opening. Blank lines, headings and labels ending in a
    colon are passed over, as STANDING_HEADING in messages.py tells the
    reader.
    """
    wanted = set(standing_lines)
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
    texts = [reply]
    # agent_transcript_path names the calling subagent's own transcript;
    # transcript_path names the session-level file every concurrent subagent
    # and the orchestrator write to.
    transcript = payload.get("agent_transcript_path") or payload.get("transcript_path", "")
    again = bool(payload.get("stop_hook_active"))
    # A later pass judges the reply rewritten after the block. The earlier
    # messages of the turn hold the superseded draft, whose lines the rewrite
    # already answered, so only the rewrite is read.
    entries = last_turn_entries(transcript) if transcript and Path(transcript).exists() else []
    if not again:
        drafted = [
            text
            for entry in entries
            if entry.get("type") == "assistant"
            for text in text_blocks(entry.get("message", {}))
        ]
        texts = drafted + texts
    # A fetch a permission check denied, where a mark followed with no other
    # route tried, blocks on every pass while it holds: trying a second route
    # is the one act that ends it, and the turn's block cap bounds the rest.
    routes = denied_routes(entries, reply, drafts=not again)
    lines_by_mark, wording, mentions = unchecked_claims(texts)
    carried = (
        {token: lines_by_mark.pop(token) for token in RELAY_MARKS if token in lines_by_mark}
        if delegate
        else {}
    )

    # The record holds every line a pass sent the model since the turn's
    # first pass, which starts it over: the harness sets stop_hook_active
    # only while it is "already continuing as a result of a stop hook", per
    # https://code.claude.com/docs/en/hooks. stop_hook_active says some hook
    # continued the turn, not that this one sent the model every line, so a
    # line first written after a block, or in a turn another plugin's Stop
    # hook continued, still goes out. The record also counts the blocks the
    # turn has drawn. Where no record can be kept, no line counts as sent, so
    # every pass sends every line, and UNRECORDED_CAP sets the block count.
    # A first pass has no record to read and draws no block yet, so only a
    # later pass asks whether the directory can be written.
    directory = state_dir()
    path = state_path(directory, f"{state_key(payload)}-stop-sent")
    recordable = False
    recorded, issued, cap = [], 0, BLOCK_CAP
    if again:
        recordable = prepare(directory)
        if recordable:
            recorded, issued = read_turn(path)
        else:
            issued, cap = 1, UNRECORDED_CAP
    sent = set(recorded)
    capped = issued >= cap

    fresh = unrecorded(lines_by_mark, sent)
    new_mentions = unrecorded(mentions, sent)
    new_relay = unrecorded(carried, sent)
    # A marked line already sent back for its check may stand, since the
    # check it waits on can be out of reach, but only at the head of the
    # reply, where the rule text tells the writer to put it. Wording never
    # has to stand: marking the claim or cutting it needs no tool. So the
    # loop ends when the reply does what the block asked; the harness's own
    # end is its override after eight consecutive continuations, per
    # https://code.claude.com/docs/en/hooks
    standing = {}
    if again:
        listed = {
            mark: kept
            for mark, lines in lines_by_mark.items()
            if (kept := [line for line in lines if line not in fresh.get(mark, [])])
        }
        marked = set(flat(lines_by_mark, carried))
        if not opens_on(reply, flat(listed), marked):
            standing = listed

    owed = bool(fresh or wording or standing or routes)
    newly = flat(fresh, new_mentions, new_relay)
    if newly or owed:
        if recordable or prepare(directory):
            write_turn(
                path,
                sorted(sent | {fingerprint(line) for line in newly}),
                issued + int(owed and not capped),
            )
    elif not again:
        forget_turn(path)

    event = "SubagentStop" if delegate else "Stop"
    if owed:
        mode = Mode.CAPPED if capped else Mode.BLOCK
        message = build_findings(
            mode, fresh, new_relay, delegate, wording, standing, new_mentions, routes
        )
        emit(context(event, message) if capped else block(message))
    # A mention claims nothing and a relayed line is the caller's to settle,
    # so neither blocks. additionalContext still hands each one to the model
    # and continues it, the one way a Stop or SubagentStop hook has to do
    # that without a block, per https://code.claude.com/docs/en/hooks. The
    # record keeps a line it carried from going out twice.
    if new_mentions or new_relay:
        emit(context(event, build_findings(Mode.NOTICE, {}, new_relay, mentions=new_mentions)))
    sys.exit(0)


def run_batch(payload) -> None:
    transcript = batch_transcript(payload)
    if not transcript or not Path(transcript).exists():
        sys.exit(0)
    lines_by_mark, wording, _ = unchecked_claims(last_turn_text(transcript))
    directory = state_dir()
    if not prepare(directory):
        sys.exit(0)
    prune(directory, time.time())
    path = state_path(directory, state_key(payload))
    reported = read_reported(path)
    seen = set(reported)
    fresh_marks, fresh_wording = unrecorded(lines_by_mark, seen), unrecorded(wording, seen)
    if not fresh_marks and not fresh_wording:
        sys.exit(0)
    for line in flat(fresh_marks, fresh_wording):
        fp = fingerprint(line)
        if fp not in seen:
            seen.add(fp)
            reported.append(fp)
    write_reported(path, reported)
    emit(context("PostToolBatch", build_context(fresh_marks, fresh_wording)))


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
    wording, _ = guessed_lines([prompt])
    if not wording:
        sys.exit(0)
    emit(deny(build_denial(wording)))


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
