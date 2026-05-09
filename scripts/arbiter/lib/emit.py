"""Output emitters per `(event, action)`.

Translates the four-action vocabulary (deny, ask, block, inject)
into the JSON shape Claude Code expects for each hook event.

The `(event, action)` pairs are validated at config-load time, so
this module does not need to handle invalid combinations — the
defensive `RuntimeError` exists only to surface a programming
mistake if one ever slipped through.
"""
import json
from typing import IO


def _emit_pretooluse(reason: str, decision: str, output: IO[str]) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            },
            "systemMessage": reason,
        },
        output,
    )


def _emit_stop_block(reason: str, output: IO[str]) -> None:
    json.dump(
        {"decision": "block", "reason": reason, "systemMessage": reason},
        output,
    )


def _emit_inject(event: str, reason: str, output: IO[str]) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": reason,
            }
        },
        output,
    )


def emit(event: str, action: str, message: str, output: IO[str]) -> None:
    """Write the JSON shape Claude Code expects for this `(event, action)` pair."""
    if event == "PreToolUse" and action == "deny":
        _emit_pretooluse(message, "deny", output)
        return
    if event == "PreToolUse" and action == "ask":
        _emit_pretooluse(message, "ask", output)
        return
    if event in ("Stop", "SubagentStop") and action == "block":
        _emit_stop_block(message, output)
        return
    if event in ("PostToolUse", "UserPromptSubmit") and action == "inject":
        _emit_inject(event, message, output)
        return
    raise RuntimeError(f"no emitter for ({event}, {action})")
