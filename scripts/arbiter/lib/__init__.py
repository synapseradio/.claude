"""Arbiter — runs declared yes/no verdicts as Claude Code hook gates.

Public API: `dispatch(payload, output)`.

`bindings.yaml` (sibling of this `lib/`) is the single source of
truth for what verdicts run, where they bind, and what action fires
when they do. The engine here is a router: parse the YAML, derive
`(event, tool)` from the payload, judge the body, compose the
message, write the JSON shape Claude Code expects for the matched
hook event. Adding a verdict, wiring it to a new hook target, or
shipping a new action handler is an edit to the YAML or to one map
in `lib/`.
"""
from .config import Binding, Bindings, ConfigError, VerdictSpec, load_bindings
from .dispatcher import dispatch

__all__ = [
    "dispatch",
    "load_bindings",
    "ConfigError",
    "Bindings",
    "VerdictSpec",
    "Binding",
]
