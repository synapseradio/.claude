"""One unit of work the runner starts, and the command line each runner kind takes."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

type Kind = Literal["pytest", "bats", "mod", "lint"]


@dataclass(frozen=True)
class Task:
    """A suite or lint check ready to start, its command built from the workers it holds.

    `fixable` lists the repository-relative files a fixing command may rewrite.
    """

    name: str
    kind: Kind
    wants: int
    build: Callable[[int], list[str]] | None = None
    skip_exits: frozenset[int] = field(default_factory=frozenset)
    fixable: tuple[str, ...] = ()
    command: list[str] | None = None

    def argv(self, workers: int) -> list[str]:
        if self.command is not None:
            return list(self.command)
        return self.build(workers)

    @property
    def program(self) -> str:
        if self.command is not None:
            return self.command[0]
        return self.build(1)[0]


def pytest_command(paths: list[str], k: str | None, workers: int) -> list[str]:
    command = ["uv", "run", "--frozen", "pytest", *paths, "-p", "no:cacheprovider", "-rf"]
    if workers > 1:
        command += ["-n", str(workers)]
    if k is not None:
        command += ["-k", k]
    return command


def bats_command(paths: list[str], k: str | None, workers: int) -> list[str]:
    command = ["bats", "--formatter", "tap"]
    if workers > 1:
        command += ["--jobs", str(workers)]
    if k is not None:
        command += ["--filter", re.escape(k)]
    return [*command, *paths]


def mod_command(folder: str, _workers: int) -> list[str]:
    return ["claude", "plugin", "test", folder]
