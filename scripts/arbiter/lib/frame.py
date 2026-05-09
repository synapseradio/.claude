"""System-prompt framings keyed on hook event.

The framing prefixes each verdict prompt sent to the model. It tells
the model what kind of body it is reading — a structured plan body
versus a turn-ending message — so phrasing in the verdict itself can
stay general.

Built-in map. Ships a framing for every event referenced by
`bindings.yaml`. Adding a new event binding without a matching
framing causes the dispatcher to skip — see `extract.py` for the same
shape.
"""

_FRAMING_PLAN = (
    "You judge an `ExitPlanMode` plan body for one specific issue. "
    "The body is between BEGIN and END markers.\n\n"
)

_FRAMING_TURN = (
    "You judge an assistant's turn-ending message for one specific "
    "issue. The body is between BEGIN and END markers.\n\n"
)

_FRAMINGS: dict[str, str] = {
    "PreToolUse": _FRAMING_PLAN,
    "Stop": _FRAMING_TURN,
    "SubagentStop": _FRAMING_TURN,
}


def get_framing(event: str) -> str | None:
    return _FRAMINGS.get(event)
