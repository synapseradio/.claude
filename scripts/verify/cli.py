#!/usr/bin/env python3
"""Entry point behind `just test`, `lint`, `fmt`, `verify`, and `suites`.

    cli.py test|lint|fmt|verify [paths...] [--diff [BASE] | --prepush] [--lang L,...]
           [--file SUBSTR] [-k SUBSTR] [--list] [--json] [--jobs N] [--serial]
    cli.py list [--json]

Exit codes: 0 pass or nothing to do, 1 a check failed, 2 usage, 3 a program
is missing, 5 an explicit scope selected nothing.
"""

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import fmt
from manifest import LANGS, Manifest, ManifestError, load
from repo import GitError, Repo, child_env
from report import Outcome, Report, counted, emit_json, say, warn
from run import Finished, Runner, missing, run_dir
from scope import (
    Diff,
    Nothing,
    Prepush,
    Scope,
    Selection,
    resolve,
    select_format,
    select_lints,
    select_tests,
)
from slots import SlotPool, default_dir

COMMANDS = ("test", "lint", "fmt", "verify", "list")
NOUNS = {"lint": "lint job", "test": "suite"}


class Exit(Exception):
    """Ends the run with `code`, printing `message` to stderr."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def langs(value: str) -> list[str]:
    names = [name for name in value.split(",") if name]
    unknown = [name for name in names if name not in LANGS]
    if unknown:
        message = f"unknown language {', '.join(unknown)}; known: {','.join(sorted(LANGS))}"
        raise argparse.ArgumentTypeError(message)
    return names


def positive(value: str) -> int:
    if not value.isdigit() or int(value) < 1:
        message = f"wanted a whole number of at least 1, got {value}"
        raise argparse.ArgumentTypeError(message)
    return int(value)


def parser_for(command: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=f"cli.py {command}")
    if command == "list":
        parser.add_argument("--json", action="store_true", help="print the manifest as JSON")
        return parser
    parser.add_argument("paths", nargs="*", help="files or directories to scope to")
    change = parser.add_mutually_exclusive_group()
    change.add_argument("--diff", nargs="?", const="main", metavar="BASE")
    change.add_argument("--prepush", action="store_true")
    parser.add_argument("--lang", action="append", type=langs, default=[])
    parser.add_argument("--file", metavar="SUBSTR")
    parser.add_argument("-k", metavar="SUBSTR")
    parser.add_argument("--list", action="store_true", help="print the selection, run nothing")
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    parser.add_argument("--jobs", type=positive, help="cap the workers a suite takes")
    parser.add_argument("--serial", action="store_true", help="run one suite at a time")
    return parser


def repo_relative(repo: Repo, given: str) -> str:
    absolute = Path(os.path.abspath(given))
    if not os.path.lexists(absolute):
        raise Exit(2, f"verify: no such path: {given}")
    real = Path(os.path.realpath(absolute.parent)) / absolute.name
    if real == repo.root:
        return "."
    if not real.is_relative_to(repo.root):
        raise Exit(2, f"verify: {given} is outside the repository at {repo.root}")
    return real.relative_to(repo.root).as_posix()


@dataclass(frozen=True)
class Context:
    repo: Repo
    manifest: Manifest
    scope: Scope
    args: argparse.Namespace
    env: dict[str, str]


def slot_pool() -> SlotPool:
    configured = os.environ.get("VERIFY_SLOTS", "")
    if configured and (not configured.isdigit() or int(configured) < 1):
        raise Exit(
            2, f"verify: VERIFY_SLOTS must be a whole number of at least 1, got {configured}"
        )
    size = int(configured) if configured else os.cpu_count() or 1
    return SlotPool(default_dir(), size)


def log_root() -> Path:
    return Path(os.environ.get("VERIFY_LOG_DIR") or "/tmp/claude-verify")


def planned_rows(selection: Selection) -> list[dict]:
    rows = [
        {"name": task.name, "runner": task.kind, "command": task.build(task.wants)}
        for task in selection.tasks
    ]
    return rows + [
        {"name": skip.name, "runner": skip.kind, "command": None, "skip": skip.reason}
        for skip in selection.skipped
    ]


def print_planned(rows: list[dict], notes: list[str]) -> None:
    for row in rows:
        detail = f"skip, {row['skip']}" if row["command"] is None else shlex.join(row["command"])
        say(f"{row['name']} ({row['runner']}): {detail}")
    for note in notes:
        say(f"note: {note}")


def run_parts(ctx: Context, planned: dict[str, Selection | Nothing]) -> dict[str, Report]:
    """Run every selected task of every part in one batch; returns one report per part."""
    reports: dict[str, Report] = {}
    parts: dict[str, Selection] = {}
    for part, selection in planned.items():
        if isinstance(selection, Nothing):
            reports[part] = Report(None, [*selection.notes, selection.message], exit=selection.exit)
            if not ctx.args.json:
                (say if selection.exit == 0 else warn)(f"verify: {selection.message}")
        else:
            parts[part] = selection
    if not parts:
        return reports
    if ctx.args.list:
        for part, selection in parts.items():
            reports[part] = Report(None, list(selection.notes), planned=planned_rows(selection))
            if not ctx.args.json:
                print_planned(reports[part].planned or [], reports[part].notes)
        return reports

    tasks = [task for selection in parts.values() for task in selection.tasks]
    absent = missing(ctx.repo.root, [task.program for task in tasks], ctx.env)
    if absent:
        raise Exit(3, "\n".join(item.message() for item in absent))

    logs = run_dir(log_root(), ctx.repo.log_name(), os.getpid())
    owner = {task.name: part for part, selection in parts.items() for task in selection.tasks}
    for part, selection in parts.items():
        reports[part] = Report(str(logs), list(selection.notes))
    if not ctx.args.json:
        sizes = [
            counted(len(selection.tasks) + len(selection.skipped), NOUNS[part])
            for part, selection in parts.items()
        ]
        say(f"verify: {', '.join(sizes)}, logs in {logs}")
        for part in parts:
            for note in reports[part].notes:
                say(f"note: {note}")

    def record(outcome: Outcome, part: str) -> None:
        reports[part].outcomes.append(outcome)
        if not ctx.args.json:
            say(outcome.line())

    for part, selection in parts.items():
        for skip in selection.skipped:
            record(Outcome.skipped(skip), part)

    def done(finished: Finished) -> None:
        record(Outcome.of(finished), owner[finished.task.name])

    runner = Runner(ctx.repo.root, ctx.env, slot_pool(), logs, ctx.args.jobs)
    runner.run_all(tasks, ctx.args.serial, done)

    for part, report in reports.items():
        if part not in parts:
            continue
        statuses = {outcome.status for outcome in report.outcomes}
        if "fail" in statuses:
            report.exit = 1
        elif statuses == {"skip"}:
            report.exit = 5
            report.notes.append(f"no test matches {ctx.scope.describe()}")
    if not ctx.args.json:
        outcomes = [outcome for part in parts for outcome in reports[part].outcomes]
        say(Report(str(logs), [], outcomes).tally())
        for part in parts:
            if reports[part].exit == 5:
                warn(f"verify: {reports[part].notes[-1]}")
    return reports


def plan_test(ctx: Context) -> Selection | Nothing:
    return select_tests(ctx.repo, ctx.manifest, ctx.scope, resolve(ctx.repo, ctx.scope))


def plan_lint(ctx: Context) -> Selection | Nothing:
    if ctx.scope.k is not None:
        raise Exit(2, "verify: lint takes no -k; -k selects test cases by name")
    return select_lints(ctx.repo, ctx.manifest, ctx.scope, resolve(ctx.repo, ctx.scope))


@dataclass(frozen=True)
class Formatted:
    exit: int
    command: list[str] | None

    def as_json(self) -> dict:
        return {"exit": self.exit, "command": self.command}


def run_fmt(ctx: Context) -> Formatted:
    """Run treefmt over the scope: exit 0, 1 for a treefmt failure, or 5 for an empty explicit scope."""
    if ctx.scope.k is not None:
        raise Exit(2, "verify: fmt takes no -k; -k selects test cases by name")
    try:
        formatters = fmt.formatters(ctx.repo.root / "treefmt.toml")
    except ManifestError as error:
        raise Exit(2, f"verify: {error}") from error
    names = [f.name for f in formatters if any(f.covers(lang) for lang in ctx.scope.langs)]
    if ctx.scope.langs and not names:
        warn(f"verify: no formatter matches {ctx.scope.describe()}")
        return Formatted(5, None)
    files = select_format(ctx.repo, ctx.scope, resolve(ctx.repo, ctx.scope))
    if isinstance(files, Nothing):
        if not ctx.args.json:
            (say if files.exit == 0 else warn)(f"verify: {files.message}")
        return Formatted(files.exit, None)
    command = fmt.command(files, names)
    if ctx.args.list:
        if not ctx.args.json:
            say(f"fmt (treefmt): {shlex.join(command)}")
        return Formatted(0, command)
    absent = missing(ctx.repo.root, ["treefmt", *(f.command for f in formatters)], ctx.env)
    if absent:
        raise Exit(3, "\n".join(item.message() for item in absent))
    result = subprocess.run(
        command,
        cwd=ctx.repo.root,
        env=ctx.env,
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr if ctx.args.json else None,
        check=False,
    )
    return Formatted(0 if result.returncode == 0 else 1, command)


def worst(codes: list[int]) -> int:
    """A failure outranks a pass; 5 stands only where every part selected nothing."""
    if 1 in codes:
        return 1
    if codes and all(code == 5 for code in codes):
        return 5
    return 0


def verify(ctx: Context) -> int:
    formatted = run_fmt(ctx)
    planned = {"lint": plan_lint(ctx), "test": plan_test(ctx)}
    reports = run_parts(ctx, planned)
    code = worst([formatted.exit, reports["lint"].exit, reports["test"].exit])
    if ctx.args.json:
        emit_json(
            {
                "fmt": formatted.as_json(),
                "lint": reports["lint"].as_json(),
                "test": reports["test"].as_json(),
                "exit": code,
            }
        )
    return code


def single(ctx: Context, part: str) -> int:
    selection = plan_test(ctx) if part == "test" else plan_lint(ctx)
    report = run_parts(ctx, {part: selection})[part]
    if ctx.args.json:
        emit_json(report.as_json())
    return report.exit


def dispatch(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        raise Exit(2, f"usage: cli.py {{{'|'.join(COMMANDS)}}} [scope] [flags]")
    command, rest = argv[0], argv[1:]
    args = parser_for(command).parse_intermixed_args(rest)
    try:
        repo = Repo.at(Path.cwd())
        manifest = load(repo.root / "scripts" / "verify" / "jobs.toml")
    except (GitError, ManifestError) as error:
        raise Exit(2, f"verify: {error}") from error
    if command == "list":
        if args.json:
            emit_json({"jobs": list(manifest.entries)})
        else:
            for job in manifest.entries:
                say(f"{job['name']} ({job['kind']}): {', '.join(job['sources'])}")
        return 0
    scope = Scope(
        paths=tuple(dict.fromkeys(repo_relative(repo, path) for path in args.paths)),
        change=Prepush() if args.prepush else Diff(args.diff) if args.diff is not None else None,
        langs=frozenset(lang for group in args.lang for lang in group),
        file=args.file,
        k=args.k,
    )
    ctx = Context(repo, manifest, scope, args, child_env())
    try:
        match command:
            case "fmt":
                formatted = run_fmt(ctx)
                if ctx.args.json:
                    emit_json(formatted.as_json())
                return formatted.exit
            case "verify":
                return verify(ctx)
            case _:
                return single(ctx, command)
    except GitError as error:
        raise Exit(2, f"verify: {error}") from error


def main() -> int:
    try:
        return dispatch(sys.argv[1:])
    except Exit as stop:
        warn(stop.message)
        return stop.code


if __name__ == "__main__":
    sys.exit(main())
