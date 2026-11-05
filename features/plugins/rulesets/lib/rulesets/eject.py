"""Eject: the base context written as one plain file per rule, with a report of what plain files cannot carry."""

from __future__ import annotations

import dataclasses
import pathlib

from rulesets.compose.base_context import base_composition
from rulesets.compose.composition import WithheldRule
from rulesets.delivery.rule_bodies import bodies_of
from rulesets.source.directory import Present, RulesetsDirectory

_VARIANT_FILE_LINE = 1


@dataclasses.dataclass(frozen=True)
class Uncarried:
    """A block or a variant that plain files cannot carry, at the file and line that holds it."""

    file: pathlib.Path
    line: int
    subject: str

    def line_text(self) -> str:
        return f"{self.file}:{self.line}: {self.subject} is not carried by plain files"


@dataclasses.dataclass(frozen=True)
class EjectReport:
    written: tuple[pathlib.Path, ...]
    withheld: tuple[WithheldRule, ...]
    uncarried: tuple[Uncarried, ...]

    def lines(self) -> list[str]:
        return [
            *(f"wrote {path}" for path in self.written),
            *(f"withheld {held.rule}: {held.error}" for held in self.withheld),
            *(item.line_text() for item in self.uncarried),
        ]


def _uncarried(directory: RulesetsDirectory, ejected: set[tuple[str, str | None]]):
    if isinstance(directory.manifest, Present):
        manifest = directory.manifest.manifest
        for block in manifest.items:
            yield Uncarried(manifest.path, block.line, f"block `{block.condition}`")
    for rule in directory.pool.rules.values():
        for name, file in rule.variants.items():
            if (rule.name, name) not in ejected:
                yield Uncarried(
                    file.path, _VARIANT_FILE_LINE, f"variant `{name}` of rule `{rule.name}`"
                )


def eject(directory: RulesetsDirectory, out: pathlib.Path) -> EjectReport:
    """Write `<rule>.md` into `out` for each rule `defaults` gives, at the variant it names."""

    composition = base_composition(directory)
    out.mkdir(parents=True, exist_ok=True)
    written: list[pathlib.Path] = []
    for body in bodies_of(composition, directory.pool):
        path = out / f"{body.rule}.md"
        path.write_bytes(body.text.encode("utf-8"))
        written.append(path)
    ejected = {(delivered.rule, delivered.variant) for delivered in composition.rules}
    return EjectReport(tuple(written), composition.withheld, tuple(_uncarried(directory, ejected)))
