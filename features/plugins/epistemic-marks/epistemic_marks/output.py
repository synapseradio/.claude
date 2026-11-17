"""The JSON outputs a hook prints, each carrying its text to the model and the user.

The model-facing field differs by output. `systemMessage` reaches the user
alone, per https://code.claude.com/docs/en/hooks, so each constructor sets it
to the same text and no output reaches only one party.
"""


def block(reason) -> dict:
    """A Stop or SubagentStop block whose `reason` the model reads."""
    return {"decision": "block", "reason": reason, "systemMessage": reason}


def context(event, text) -> dict:
    """Output handing `text` to the model as `additionalContext` on `event`."""
    return {
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": text},
        "systemMessage": text,
    }


def deny(reason) -> dict:
    """A denied spawn call whose `reason` reaches the agent that composed it."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": reason,
    }
