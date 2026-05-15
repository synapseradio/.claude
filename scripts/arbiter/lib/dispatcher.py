"""Dispatch entrypoint.

Resolves `(event, tool)` from the hook payload, finds the matching
binding, judges the body via the local `mlx_lm.server`, applies any
suppressions declared in `bindings.yaml`, composes the block message,
and writes the JSON shape Claude Code expects for the matched
`(event, action)` pair to the output stream.
"""

import os
import re
from pathlib import Path
from typing import IO

from . import client, compose, config, emit, extract, frame, state

_BINDINGS_PATH = Path(__file__).resolve().parent.parent / "bindings.yaml"

# Per-process cache. Hook processes are short-lived, so this just
# avoids re-reading the YAML when something inside the same process
# calls dispatch more than once. Across processes the file is read
# fresh — no daemon, no live-reload to worry about.
_CACHED_BINDINGS: config.Bindings | None = None


def _load() -> config.Bindings:
    global _CACHED_BINDINGS
    if _CACHED_BINDINGS is None:
        _CACHED_BINDINGS = config.load_bindings(_BINDINGS_PATH)
    return _CACHED_BINDINGS


def _resolve_event_tool(payload: dict) -> tuple[str, str | None]:
    """Map a Claude Code hook payload to `(event, tool_or_None)`.

    PreToolUse / PostToolUse payloads carry `tool_name`. Stop /
    SubagentStop / UserPromptSubmit carry `hook_event_name` only. If
    `hook_event_name` is missing, the presence of `tool_name` falls
    back to PreToolUse (the historical handler behavior); otherwise
    Stop.
    """
    event = payload.get("hook_event_name")
    tool = payload.get("tool_name")
    if event is None:
        event = "PreToolUse" if tool is not None else "Stop"
    return event, tool


def _quick_exit_pattern(verdict_specs) -> re.Pattern[str]:
    """Match a verdict token literal anywhere in the body.

    When the body literally contains a verdict name, the assistant is
    discussing the rules (meta-discussion) and the model should not be
    asked. Built fresh per dispatch since the verdict list comes from
    the matched binding, not a global registry.
    """
    names = "|".join(spec.name for spec in verdict_specs)
    return re.compile(rf"\b({names})\b")


def _find_binding(bindings: config.Bindings, event: str, tool: str | None) -> config.Binding | None:
    """First binding whose event matches and whose tool either equals
    `tool` or is unspecified."""
    for b in bindings.bindings:
        if b.event != event:
            continue
        if b.tool is not None and b.tool != tool:
            continue
        return b
    return None


def _is_suppressed(spec: config.VerdictSpec, turn_tools: set[str]) -> bool:
    """True when any tool named in `suppress_when.tools_in_turn` shows up
    in the latest turn's tool uses."""
    if not spec.suppress_tools_in_turn:
        return False
    return any(t in turn_tools for t in spec.suppress_tools_in_turn)


def dispatch(payload: dict, output: IO[str]) -> None:
    """Run the full hook pipeline: resolve → extract → judge → compose → emit."""
    bindings = _load()
    event, tool = _resolve_event_tool(payload)
    binding = _find_binding(bindings, event, tool)
    if binding is None:
        return

    body = extract.extract_body(event, tool, payload)
    if body is None or not body.strip():
        return

    framing = frame.get_framing(event)
    if framing is None:
        return

    verdict_specs = [bindings.verdicts[v] for v in binding.verdict_ids]
    scrubbed = extract.strip_code(body)

    if _quick_exit_pattern(verdict_specs).search(scrubbed):
        client.log_call(event, 0, "CLEAR:quick-exit")
        return

    if os.environ.get("BLOCK_PLAN_NO_JUDGE") == "1":
        emit.emit(event, binding.action, compose.FALLBACK_REPLAN_SLIM, output)
        return

    transcript_path = payload.get("transcript_path", "") or ""
    is_plan_flow = event == "PreToolUse" and tool == "ExitPlanMode"
    has_prior_block = (
        state.has_first_block(transcript_path, tool)
        if is_plan_flow and transcript_path and tool
        else False
    )

    fired_keys = client.judge_many(scrubbed, framing, verdict_specs, event)
    if fired_keys is None:
        # Fail-closed deny. The judge could not render a verdict, so
        # this does not count as the flow's first block — state is
        # not written. A subsequent re-emission with a healthy judge
        # will run the first-block logic fresh.
        emit.emit(event, binding.action, compose.FALLBACK_REPLAN_SLIM, output)
        return

    turn_tools: set[str] = (
        extract.latest_turn_tool_uses(transcript_path) if transcript_path else set()
    )
    fired_keys = [k for k in fired_keys if not _is_suppressed(bindings.verdicts[k], turn_tools)]

    if is_plan_flow and has_prior_block:
        # Block-once policy: the assistant has already absorbed one
        # deny on this transcript's plan flow within the last 24h.
        # Lift the deny on the second pass and emit allow with an
        # injected sentence the assistant can quote into a sub-agent
        # brief verbatim.
        if not fired_keys:
            emit.emit("PreToolUse", "allow", compose.REEVAL_APPROVED, output)
            return
        fired_specs = [bindings.verdicts[k] for k in fired_keys]
        message = compose.reeval_remaining_message(fired_specs)
        emit.emit("PreToolUse", "allow", message, output)
        return

    if not fired_keys:
        return

    fired_specs = [bindings.verdicts[k] for k in fired_keys]
    message = compose.compose_message(fired_specs, bindings.remediation, event)
    if not message:
        return
    emit.emit(event, binding.action, message, output)
    if is_plan_flow and transcript_path and tool:
        state.record_first_block(transcript_path, tool)
