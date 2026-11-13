"""What a scope selects: the in-scope files, then the suites, lint checks, or files to format they reach."""

import re
from dataclasses import dataclass
from functools import partial
from pathlib import PurePosixPath

from manifest import Dirs, Files, Lint, Manifest, Once, Suite
from repo import Changes, Repo
from tasks import Task, bats_command, fixed_command, mod_command, pytest_command


@dataclass(frozen=True)
class Diff:
    base: str


@dataclass(frozen=True)
class Prepush:
    pass


type Change = Diff | Prepush


@dataclass(frozen=True)
class Scope:
    paths: tuple[str, ...]
    change: Change | None
    langs: frozenset[str]
    file: str | None
    k: str | None

    def describe(self) -> str:
        parts = list(self.paths)
        match self.change:
            case Diff(base):
                parts.append(f"--diff {base}")
            case Prepush():
                parts.append("--prepush")
        if self.langs:
            parts.append(f"--lang {','.join(sorted(self.langs))}")
        if self.file is not None:
            parts.append(f"--file {self.file}")
        if self.k is not None:
            parts.append(f"-k {self.k}")
        return " ".join(parts) or "(no scope)"


@dataclass(frozen=True)
class InScope:
    """The files a scope's paths and change reach; `files` is None when neither narrows the tree."""

    files: frozenset[str] | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Skipped:
    """A selected suite the scope leaves nothing to run in, known before anything starts."""

    name: str
    kind: str
    reason: str


@dataclass(frozen=True)
class Selection:
    tasks: tuple[Task, ...]
    skipped: tuple[Skipped, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Nothing:
    """A scope that selects no work, with the exit code and message that says so."""

    exit: int
    message: str
    notes: tuple[str, ...]


def under(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(p == "." or path == p or path.startswith(f"{p}/") for p in prefixes)


def resolve(repo: Repo, scope: Scope) -> InScope:
    changes: Changes | None
    match scope.change:
        case Diff(base):
            changes = repo.changed_since(base)
        case Prepush():
            changes = repo.unpushed()
        case None:
            changes = None
    notes = (changes.note,) if changes is not None and changes.note else ()
    if changes is not None:
        files = changes.paths
        if scope.paths:
            files = frozenset(path for path in files if under(path, scope.paths))
        return InScope(files, notes)
    if scope.paths:
        listed: set[str] = set()
        for path in scope.paths:
            if (repo.root / path).is_dir():
                listed.update(repo.listed_under(path))
            else:
                listed.add(path)
        return InScope(frozenset(listed), notes)
    return InScope(None, notes)


TEST_LITERAL = re.compile(r"""\btest\(\s*(["'`])((?:\\.|(?!\1).)*)\1""", re.DOTALL)


def mod_names_hold(repo: Repo, suite: Suite, k: str) -> bool:
    """Whether a `test("...")` literal in the mod suite's files holds `k`."""
    for path in repo.tracked:
        if not under(path, suite.tests) or not repo.exists(path):
            continue
        text = (repo.root / path).read_text(encoding="utf-8", errors="replace")
        if any(k in match[2] for match in TEST_LITERAL.finditer(text)):
            return True
    return False


def count_test_files(repo: Repo, suite: Suite) -> int:
    found = set()
    for test in suite.tests:
        for path in (repo.root / test).rglob("*"):
            relative = path.relative_to(repo.root).as_posix()
            if path.is_file() and suite.holds_test_file(relative):
                found.add(relative)
    return len(found)


@dataclass(frozen=True)
class Whole:
    """The suite runs every test under its tests paths."""


@dataclass(frozen=True)
class Alone:
    """The suite runs these test files and no other."""

    paths: tuple[str, ...]


@dataclass(frozen=True)
class Unselected:
    """The scope reaches none of the suite."""


type Pick = Whole | Alone | Unselected


def suite_task(repo: Repo, suite: Suite, pick: Whole | Alone, k: str | None) -> Task:
    if suite.runner == "mod":
        return Task(suite.name, "mod", 1, partial(mod_command, suite.tests[0]))
    match pick:
        case Alone(paths):
            run, wants = list(paths), len(paths)
        case Whole():
            run, wants = list(suite.tests), count_test_files(repo, suite)
    if suite.runner == "bats":
        return Task(suite.name, "bats", max(wants, 1), partial(bats_command, run, k))
    # pytest exits 5 when it collects no test, which under -k means no name matched.
    # https://docs.pytest.org/en/stable/reference/exit-codes.html
    skips = frozenset({5}) if k is not None else frozenset()
    return Task(suite.name, "pytest", max(wants, 1), partial(pytest_command, run, k), skips)


def pick_for(repo: Repo, suite: Suite, scope: Scope, inscope: InScope) -> Pick:
    """A suite's test files run alone where its share of the scope is only existing test files."""
    if scope.file is not None:
        candidates = set(repo.tracked) | set(repo.untracked)
        if inscope.files is not None:
            candidates &= inscope.files
        chosen = sorted(
            path
            for path in candidates
            if scope.file in path and suite.holds_test_file(path) and repo.exists(path)
        )
        return Alone(tuple(chosen)) if chosen else Unselected()
    if inscope.files is None:
        return Whole()
    share = sorted(path for path in inscope.files if suite.owns(path))
    if not share:
        return Unselected()
    if all(suite.holds_test_file(path) and repo.exists(path) for path in share):
        return Alone(tuple(share))
    return Whole()


def select_tests(
    repo: Repo, manifest: Manifest, scope: Scope, inscope: InScope
) -> Selection | Nothing:
    tasks: list[Task] = []
    skipped: list[Skipped] = []
    notes = list(inscope.notes)
    for suite in manifest.suites:
        if scope.langs and not scope.langs & suite.langs:
            continue
        pick = pick_for(repo, suite, scope, inscope)
        if isinstance(pick, Unselected):
            continue
        if suite.runner == "mod":
            if scope.k is not None:
                if not mod_names_hold(repo, suite, scope.k):
                    skipped.append(
                        Skipped(suite.name, "mod", f'no test("...") name holds {scope.k}')
                    )
                    continue
                notes.append(
                    f"{suite.name}: the mod runner cannot narrow to -k {scope.k}; it runs the whole suite"
                )
            elif isinstance(pick, Alone):
                notes.append(
                    f"{suite.name}: the mod runner cannot narrow to files; it runs the whole suite"
                )
        tasks.append(suite_task(repo, suite, pick, scope.k))
    if tasks or skipped:
        return Selection(tuple(tasks), tuple(skipped), tuple(notes))
    if scope.change is not None:
        return Nothing(0, "no suite maps to the changed files", tuple(notes))
    return Nothing(5, f"no test matches {scope.describe()}", tuple(notes))


def marked_dir(repo: Repo, path: str, marker: str) -> str | None:
    """The nearest directory at or above a file's own that holds `marker`, repository-relative."""
    for directory in PurePosixPath(path).parents:
        if (repo.root / directory / marker).is_file():
            return directory.as_posix()
    return None


def lint_tasks(repo: Repo, job: Lint, hits: list[str]) -> list[Task]:
    command = list(job.command)
    match job.mode:
        case Files():
            present = sorted(path for path in hits if repo.exists(path))
            if not present:
                return []
            fixable = tuple(present) if job.fixes else ()
            build = partial(fixed_command, [*command, *present])
            return [Task(job.name, "lint", 1, build, fixable=fixable)]
        case Once():
            return [Task(job.name, "lint", 1, partial(fixed_command, command))] if hits else []
        case Dirs(marker):
            dirs = sorted({d for path in hits if (d := marked_dir(repo, path, marker)) is not None})
            return [
                Task(f"{job.name}:{d}", "lint", 1, partial(fixed_command, [*command, d]))
                for d in dirs
            ]


def select_lints(
    repo: Repo, manifest: Manifest, scope: Scope, inscope: InScope
) -> Selection | Nothing:
    files = sorted(inscope.files if inscope.files is not None else repo.tracked)
    if scope.file is not None:
        files = [path for path in files if scope.file in path]
    tasks: list[Task] = []
    for job in manifest.lints:
        if scope.langs and not scope.langs & job.langs:
            continue
        tasks += lint_tasks(repo, job, [path for path in files if job.owns(path)])
    notes = inscope.notes
    if tasks:
        return Selection(tuple(tasks), (), notes)
    if scope.langs or scope.file is not None:
        return Nothing(5, f"no lint job matches {scope.describe()}", notes)
    if scope.change is not None:
        return Nothing(0, "no lint job covers the changed files", notes)
    return Nothing(0, "no lint job covers the given files", notes)


def select_format(repo: Repo, scope: Scope, inscope: InScope) -> list[str] | Nothing:
    """The existing files `fmt` hands treefmt, an empty list meaning the whole tree."""
    if not scope.paths and scope.change is None and scope.file is None:
        return []
    files = inscope.files if inscope.files is not None else frozenset(repo.tracked)
    if scope.file is not None:
        files = frozenset(path for path in files if scope.file in path)
    present = sorted(path for path in files if repo.exists(path))
    if present:
        return present
    if scope.change is not None:
        return Nothing(0, "no changed file to format", inscope.notes)
    return Nothing(5, f"no file matches {scope.describe()}", inscope.notes)
