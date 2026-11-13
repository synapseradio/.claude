"""The hook result type and the two recording hooks, which import nothing of the delivery stack.

`record-load.py` and `record-spawn.py` run on every instruction load and every `Agent` spawn, so
the interpreter loads this module alone for them. Like `hook_entry`, no function here reads
`sys.argv`, `sys.stdin`, or `os.environ`, and none writes to `sys.stdout` or `sys.stderr`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
from collections.abc import Callable, Mapping, Sequence

from rulesets import spawn_log
from rulesets.audit import log
from rulesets.audit.json_fields import UnreadableRecord
from rulesets.audit.load_record import LoadRecord
from rulesets.locations import Locations


def _hold_nothing() -> None:
    return None


@dataclasses.dataclass(frozen=True)
class HookResult:
    """What one hook run exits with and writes, as text its process encodes in UTF-8.

    `release` lets go of the part locks the run took, as the run's process exiting does, and
    the next part of the same delivery waits until then. Two results compare without it.
    """

    exit_code: int
    stdout: str
    stderr: str
    release: Callable[[], None] = dataclasses.field(
        default=_hold_nothing, compare=False, repr=False
    )


def record_load(argv: Sequence[str], stdin: bytes, environ: Mapping[str, str]) -> HookResult:
    """`record-load.py`: record each instruction file the harness loads; print nothing and exit 0."""
    with contextlib.suppress(Exception):
        _append_load(json.loads(_stdin_text(stdin)), Locations.from_environment(environ))
    return HookResult(0, "", "")


def record_spawn(argv: Sequence[str], stdin: bytes, environ: Mapping[str, str]) -> HookResult:
    """`record-spawn.py`: record one `Agent` spawn and the model its caller names, if any; print nothing and exit 0."""
    with contextlib.suppress(Exception):
        _append_spawn(json.loads(_stdin_text(stdin)), Locations.from_environment(environ))
    return HookResult(0, "", "")


def _stdin_text(stdin: bytes) -> str:
    r"""`stdin` as `sys.stdin.read()` returns it under the hooks' interpreter.

    Python 3.15 starts in UTF-8 mode, where stdin decodes as UTF-8 with `surrogateescape` and,
    in text mode, translates every line ending to `\n`:
    https://docs.python.org/3.15/library/os.html#utf8-mode
    """
    return io.TextIOWrapper(io.BytesIO(stdin), encoding="utf-8", errors="surrogateescape").read()


def _append_load(payload: object, locations: Locations) -> None:
    """Append the load to its session's log; skip a payload that names no file, reason, or session."""
    try:
        loaded = LoadRecord.from_payload(payload)
    except UnreadableRecord:
        return
    log.append(log.session_dir(locations, loaded.session_id) / log.LOADS_FILE, loaded.to_json())


def _append_spawn(payload: object, locations: Locations) -> None:
    """Append one record per spawn, joined on the prompt and the agent type.

    A spawn naming no model is recorded with no model, so it keeps its own place among the
    spawns a delegate start claims in order.
    """
    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input")
    session_id = payload.get("session_id")
    if not isinstance(tool_input, dict) or not isinstance(session_id, str) or not session_id:
        return
    model = tool_input.get("model")
    spawn_log.append_spawn(
        session_id,
        _text(payload.get("prompt_id")),
        _text(tool_input.get("subagent_type")),
        None if model == "" else model,
        locations.state,
    )


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
