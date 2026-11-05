"""A plain rules folder read as rule files, with the path-scoped ones set aside."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Mapping

from rulesets.adopt.path_scope import is_path_scoped
from rulesets.adopt.skipped import PATH_SCOPED, Skipped


@dataclasses.dataclass(frozen=True)
class RulesFolder:
    """The rule files by stem, and the files left out."""

    rules: Mapping[str, pathlib.Path]
    skipped: tuple[Skipped, ...]


def read_rules_folder(path: pathlib.Path) -> RulesFolder:
    """Read every `*.md` file directly inside `path`."""

    rules: dict[str, pathlib.Path] = {}
    skipped: list[Skipped] = []
    for file in sorted(path.glob("*.md")):
        if not file.is_file():
            continue
        if is_path_scoped(file):
            skipped.append(Skipped(file.name, PATH_SCOPED))
        else:
            rules[file.stem] = file
    return RulesFolder(rules, tuple(skipped))
