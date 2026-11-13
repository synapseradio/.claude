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
    build: Callable[[int], list[str]]
    skip_exits: frozenset[int] = field(default_factory=frozenset)
    fixable: tuple[str, ...] = ()

    @property
    def program(self) -> str:
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


def fixed_command(command: list[str], _workers: int) -> list[str]:
    return list(command)
