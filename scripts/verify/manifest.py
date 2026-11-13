"""The job manifest `scripts/verify/jobs.toml`: test suites and lint checks with the globs that select them."""

import tomllib
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Literal, cast

LANGS = frozenset({"py", "bats", "ts", "sh", "md", "yaml", "toml", "json"})

type Runner = Literal["pytest", "bats", "mod"]

RUNNERS: tuple[Runner, ...] = ("pytest", "bats", "mod")

TEST_FILE_NAMES: dict[Runner, tuple[str, ...]] = {
    "pytest": ("test_*.py",),
    "bats": ("*.bats",),
    "mod": ("*.test.ts", "*.test.tsx"),
}


class ManifestError(Exception):
    """A job manifest entry the runner cannot use."""


@dataclass(frozen=True)
class Job:
    name: str
    sources: tuple[str, ...]
    langs: frozenset[str]

    def owns(self, path: str) -> bool:
        """Whether a repository-relative path matches one of the job's source globs."""
        pure = PurePosixPath(path)
        return any(pure.full_match(glob) for glob in self.sources)


@dataclass(frozen=True)
class Suite(Job):
    runner: Runner
    tests: tuple[str, ...]

    def holds_test_file(self, path: str) -> bool:
        """Whether a path is a test file of this suite: under its tests paths, named as its runner names tests."""
        name = PurePosixPath(path).name
        under = any(path.startswith(f"{test}/") for test in self.tests)
        return under and any(fnmatchcase(name, pattern) for pattern in TEST_FILE_NAMES[self.runner])


@dataclass(frozen=True)
class Files:
    """The command runs once over every in-scope file the job's sources match."""


@dataclass(frozen=True)
class Once:
    """The command runs as written when any in-scope file matches the job's sources."""


@dataclass(frozen=True)
class Dirs:
    """The command runs once per directory holding `marker` that holds an in-scope file."""

    marker: str


type LintMode = Files | Once | Dirs


@dataclass(frozen=True)
class Lint(Job):
    """A lint check; `fixes` marks a command that applies its tool's safe fixes to the files it is handed."""

    command: tuple[str, ...]
    mode: LintMode
    fixes: bool = False


@dataclass(frozen=True)
class Manifest:
    entries: tuple[dict, ...]
    suites: tuple[Suite, ...]
    lints: tuple[Lint, ...]


def strings(entry: dict, key: str) -> tuple[str, ...]:
    value = entry.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value):
        message = f"job {entry.get('name')!r}: {key} must be a non-empty list of strings"
        raise ManifestError(message)
    return tuple(value)


def parse_job(entry: dict) -> Suite | Lint:
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        message = f"every job needs a name, got {entry!r}"
        raise ManifestError(message)
    sources = strings(entry, "sources")
    langs = frozenset(strings(entry, "langs"))
    unknown = langs - LANGS
    if unknown:
        message = f"job {name!r}: unknown langs {sorted(unknown)}"
        raise ManifestError(message)
    kind = entry.get("kind")
    if kind in RUNNERS:
        return Suite(name, sources, langs, cast(Runner, kind), strings(entry, "tests"))
    if kind != "lint":
        message = f"job {name!r}: kind must be one of {[*RUNNERS, 'lint']}, got {kind!r}"
        raise ManifestError(message)
    command = strings(entry, "command")
    match entry.get("mode"):
        case "files":
            mode: LintMode = Files()
        case "once":
            mode = Once()
        case "dirs":
            marker = entry.get("marker")
            if not isinstance(marker, str) or not marker:
                message = f"job {name!r}: mode dirs needs a marker"
                raise ManifestError(message)
            mode = Dirs(marker)
        case other:
            message = f"job {name!r}: mode must be files, once, or dirs, got {other!r}"
            raise ManifestError(message)
    fixes = entry.get("fixes", False)
    if not isinstance(fixes, bool):
        message = f"job {name!r}: fixes must be true or false, got {fixes!r}"
        raise ManifestError(message)
    if fixes and not isinstance(mode, Files):
        message = f"job {name!r}: fixes needs mode files, which hands the command its files"
        raise ManifestError(message)
    return Lint(name, sources, langs, command, mode, fixes)


def load(path: Path) -> Manifest:
    try:
        entries = tomllib.loads(path.read_text(encoding="utf-8")).get("job", [])
    except (OSError, tomllib.TOMLDecodeError) as error:
        message = f"{path}: {error}"
        raise ManifestError(message) from error
    jobs = [parse_job(entry) for entry in entries]
    names = [job.name for job in jobs]
    duplicated = sorted({name for name in names if names.count(name) > 1})
    if duplicated:
        message = f"job names repeat: {duplicated}"
        raise ManifestError(message)
    return Manifest(
        entries=tuple(entries),
        suites=tuple(job for job in jobs if isinstance(job, Suite)),
        lints=tuple(job for job in jobs if isinstance(job, Lint)),
    )
