"""The JSON outputs a hook prints, each carrying its text to the model.

The model-facing field differs by output. `systemMessage` reaches the user
alone, per https://code.claude.com/docs/en/hooks. Every constructor but
`model_only_context` sets it to the same text, so a finding never reaches the
model alone.
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


def model_only_context(event, text) -> dict:
    """Output handing `text` to the model as `additionalContext`, hidden from the user."""
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


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
