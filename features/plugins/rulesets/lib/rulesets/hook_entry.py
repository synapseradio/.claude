"""What each hook script does, as a function of the argv, stdin, and environment its process receives.

A script in `hooks/` calls the function here that bears its name with its own `sys.argv`, the bytes
of its stdin, and `os.environ`, then writes the result's stderr and stdout and exits with its
code. No function here reads `sys.argv`, `sys.stdin`, or `os.environ`, and none writes to
`sys.stdout` or `sys.stderr`.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import io
import json
import os
import pathlib
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import NoReturn, TextIO

from rulesets import ordering, spawn_log
from rulesets.audit import log
from rulesets.audit.json_fields import UnreadableRecord
from rulesets.audit.load_record import LoadRecord
from rulesets.delivery.failure import run_guarded
from rulesets.delivery.first_part import deliver_first
from rulesets.delivery.hook_output import PartOutput, hook_output
from rulesets.delivery.later_part import deliver_later
from rulesets.delivery.plan import Silent, new_generation, write_plan
from rulesets.delivery.replay import deliver_replay
from rulesets.delivery.request import (
    DeliveryStart,
    Forked,
    ModelSwitch,
    SessionEnd,
    SessionStart,
    SubagentStart,
    Unreadable,
    parse_request,
)
from rulesets.delivery.rerun import RERUN_FLAG
from rulesets.delivery.switch import deliver_switch
from rulesets.delivery.unreadable import report_unreadable
from rulesets.locations import Locations
from rulesets.session.lifecycle import on_session_end, on_session_start

DELIVER_DESCRIPTION = """One part of one delivery: `deliver.py --part K` reads a hook payload on stdin and prints the hook output.

`deliver.py --part 1 --rerun` runs the first part apart from any delivery, as a failure notice's command does.
`deliver.py --end` reads a session-end payload and ends the session's state. Every run exits 0.
"""


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


def deliver(argv: Sequence[str], stdin: bytes, environ: Mapping[str, str]) -> HookResult:
    """`deliver.py`: one part of one delivery, or with `--end`, the end of a session.

    `argv` is laid out as `sys.argv` is, the script's path first; a failure notice's rerun
    command names the scripts in that path's directory.
    """
    stdout, stderr = io.StringIO(), io.StringIO()
    parser = _Parser(
        stdout, stderr, prog=os.path.basename(argv[0]), description=DELIVER_DESCRIPTION
    )
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--part", type=int)
    which.add_argument("--end", action="store_true")
    parser.add_argument(
        RERUN_FLAG, action="store_true", help="run the first part apart from any delivery"
    )
    try:
        arguments = parser.parse_args(argv[1:])
    except _ParserExit as exited:
        return _result(exited.status, stdout, stderr)
    try:
        raw = stdin.decode("utf-8")
        request = parse_request(json.loads(raw))
    except UnicodeDecodeError, json.JSONDecodeError:
        raw, request = "", Unreadable("the payload is not UTF-8 JSON")
    if isinstance(request, Forked):
        return _result(0, stdout, stderr)
    locations = Locations.from_environment(environ)
    if isinstance(request, Unreadable):
        if arguments.end or arguments.part == 1:
            stdout.write(report_unreadable(request, locations, stderr))
        return _result(0, stdout, stderr)
    hooks = pathlib.Path(argv[0]).resolve().parent
    part = 0 if arguments.end else arguments.part
    locks = ordering.Locks()
    output = run_guarded(
        lambda: _output(
            request, arguments.end, part, arguments.rerun, raw, locations, environ, locks
        ),
        request=request,
        first_part=part == 1,
        raw_payload=raw,
        hooks=hooks,
        locations=locations,
        stderr=stderr,
    )
    stdout.write(output)
    return HookResult(0, stdout.getvalue(), stderr.getvalue(), locks.release)


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


def _result(exit_code: int, stdout: io.StringIO, stderr: io.StringIO) -> HookResult:
    return HookResult(exit_code, stdout.getvalue(), stderr.getvalue())


def _stdin_text(stdin: bytes) -> str:
    r"""`stdin` as `sys.stdin.read()` returns it under the hooks' interpreter.

    Python 3.15 starts in UTF-8 mode, where stdin decodes as UTF-8 with `surrogateescape` and,
    in text mode, translates every line ending to `\n`:
    https://docs.python.org/3.15/library/os.html#utf8-mode
    """
    return io.TextIOWrapper(io.BytesIO(stdin), encoding="utf-8", errors="surrogateescape").read()


class _ParserExit(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


class _Parser(argparse.ArgumentParser):
    """An argument parser that writes to the streams it holds and raises where argparse exits.

    argparse sends every message through `_print_message`, naming `sys.stdout` for help and
    `sys.stderr` for the rest, and leaves through `exit`; colour is still decided on the real
    stream, as the script's own parser decided it:
    https://github.com/python/cpython/blob/3.15/Lib/argparse.py
    """

    def __init__(self, stdout: TextIO, stderr: TextIO, **settings: object) -> None:
        super().__init__(**settings)
        self._stdout = stdout
        self._stderr = stderr

    def _print_message(self, message: str, file: object = None) -> None:
        if message:
            (self._stdout if file is sys.stdout else self._stderr).write(message)

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if message:
            self._stderr.write(message)
        raise _ParserExit(status)


def _output(
    request: DeliveryStart | SessionEnd,
    ending: bool,
    part: int,
    rerun: bool,
    raw: str,
    locations: Locations,
    environ: Mapping[str, str],
    locks: ordering.Locks,
) -> str:
    """The hook output of one run, or an empty string where the run has nothing to say.

    The run's part lock goes into `locks`.
    """
    if ending:
        if isinstance(request, SessionEnd):
            on_session_end(request, locations)
        return ""
    if isinstance(request, SessionEnd):
        return ""
    slot = (
        ordering.private_slot_dir(locations.state)
        if rerun
        else ordering.slot_dir(locations.state, raw)
    )
    if part != 1:
        return hook_output(request.event, deliver_later(request, locations, slot, part, locks))
    generation = new_generation()
    ordering.hold(slot, generation, 1, locks)
    try:
        return hook_output(
            request.event, _first_part(request, locations, environ, slot, generation)
        )
    except Exception:
        with contextlib.suppress(OSError):
            write_plan(slot, Silent(generation))
        raise


def _first_part(
    request: DeliveryStart,
    locations: Locations,
    environ: Mapping[str, str],
    slot: pathlib.Path,
    generation: str,
) -> PartOutput:
    match request:
        case ModelSwitch():
            return deliver_switch(request, locations, environ, slot, generation)
        case SessionStart():
            on_session_start(request, locations)
            return deliver_first(request, locations, environ, slot, generation)
        case SubagentStart():
            replayed = deliver_replay(request, locations, slot, generation)
            if replayed is not None:
                return replayed
            return deliver_first(request, locations, environ, slot, generation)


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
