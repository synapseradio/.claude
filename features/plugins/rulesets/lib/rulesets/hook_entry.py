"""What each hook script does, as a function of the argv, stdin, and environment its process receives.

A script in `hooks/` passes the function here that bears its name to `script_process.run_script`,
which calls it with the process's `sys.argv`, the bytes of its stdin, and `os.environ`, writes the
result's stderr and stdout, and returns its code. No function here reads `sys.argv`, `sys.stdin`,
or `os.environ`, and none writes to `sys.stdout` or `sys.stderr`. The two recording hooks live in
`record_entry`, which the record scripts import without the delivery stack.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import NoReturn, TextIO

from rulesets import ordering
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
from rulesets.record_entry import HookResult, record_load, record_spawn
from rulesets.session.lifecycle import on_session_end, on_session_start

__all__ = ["HookResult", "deliver", "record_load", "record_spawn"]

DELIVER_DESCRIPTION = """One part of one delivery: `deliver.py --part K` reads a hook payload on stdin and prints the hook output.

`deliver.py --part 1 --rerun` runs the first part apart from any delivery, as a failure notice's command does.
`deliver.py --end` reads a session-end payload and ends the session's state. Every run exits 0.
"""


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


def _result(exit_code: int, stdout: io.StringIO, stderr: io.StringIO) -> HookResult:
    return HookResult(exit_code, stdout.getvalue(), stderr.getvalue())


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
