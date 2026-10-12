"""Read the pool: the rule files of one rulesets directory, by rule and by variant."""

from __future__ import annotations

import dataclasses
import pathlib
import re
from collections.abc import Mapping

import yaml

POOL_DIRECTORY = "rules"
REFERENCES_DIRECTORY = "references"

# A frontmatter key scopes a rule file when it is the harness's path scope, the manifest's
# `when` key, or a fact kind a condition tests, singular or plural.
CONDITION_KEYS = frozenset(
    {
        "paths",
        "when",
        "model",
        "models",
        "agent",
        "agents",
        "kind",
        "kinds",
        "flag",
        "flags",
    }
)

MARKER = re.compile(r"<!-- rule: (?P<rule>[^\s@]+)(?: variant: (?P<variant>\S+))? -->")


@dataclasses.dataclass(frozen=True)
class Marker:
    """What a body's first line says it is: a rule's default form, or one of its variants."""

    rule: str
    variant: str | None


@dataclasses.dataclass(frozen=True)
class FrontmatterCondition:
    """A frontmatter key that scopes a rule file, with the file line it sits on."""

    key: str
    line: int


@dataclasses.dataclass(frozen=True)
class PoolFile:
    path: pathlib.Path
    rule: str
    variant: str | None
    text: str
    marker: Marker | None
    condition: FrontmatterCondition | None

    def line_of(self, index: int) -> int:
        """The 1-based file line of the character at `index` in the text."""

        return self.text.count("\n", 0, index) + 1


@dataclasses.dataclass(frozen=True)
class Rule:
    """A rule's files. `default` is None for a variant that sits beside no default form."""

    name: str
    default: PoolFile | None
    variants: Mapping[str, PoolFile]

    def files(self) -> tuple[PoolFile, ...]:
        """The default form first, then the variants by name."""

        return ((self.default,) if self.default else ()) + tuple(self.variants.values())


@dataclasses.dataclass(frozen=True)
class Pool:
    """Every rule file of one rulesets directory, by rule name in sorted order."""

    root: pathlib.Path
    rules: Mapping[str, Rule]
    stray_directories: tuple[pathlib.Path, ...]

    def variants_by_rule(self) -> dict[str, tuple[str, ...]]:
        return {name: tuple(rule.variants) for name, rule in self.rules.items()}


def parse_marker(line: str) -> Marker | None:
    found = MARKER.fullmatch(line.rstrip())
    if found is None:
        return None
    return Marker(rule=found["rule"], variant=found["variant"])


def _frontmatter_condition(text: str) -> FrontmatterCondition | None:
    lines = text.split("\n")
    if lines[0].rstrip() != "---":
        return None
    closing = next((n for n, line in enumerate(lines[1:], 1) if line.rstrip() == "---"), None)
    if closing is None:
        return None
    try:
        block = yaml.compose("\n".join(lines[1:closing]))
    except yaml.YAMLError:
        return None
    if not isinstance(block, yaml.MappingNode):
        return None
    for key, _ in block.value:
        if isinstance(key, yaml.ScalarNode) and key.value in CONDITION_KEYS:
            return FrontmatterCondition(key=key.value, line=key.start_mark.line + 2)
    return None


def _read_file(path: pathlib.Path, rule: str, variant: str | None) -> PoolFile:
    text = path.read_text(encoding="utf-8")
    return PoolFile(
        path=path,
        rule=rule,
        variant=variant,
        text=text,
        marker=parse_marker(text.split("\n", 1)[0]),
        condition=_frontmatter_condition(text),
    )


def read_pool(root: pathlib.Path) -> Pool:
    """Read `rules/` of one rulesets directory.

    A file's rule is its stem up to the first `@`, and the rest of the stem is its variant.
    The `references/` folder beside the pool is reserved and read as nothing.
    """

    pool_directory = root / POOL_DIRECTORY
    stray = [
        entry
        for entry in (sorted(root.iterdir()) if root.is_dir() else ())
        if entry.is_dir() and entry.name not in (POOL_DIRECTORY, REFERENCES_DIRECTORY)
    ]
    defaults: dict[str, PoolFile] = {}
    variants: dict[str, dict[str, PoolFile]] = {}
    if pool_directory.is_dir():
        for entry in sorted(pool_directory.iterdir()):
            if entry.is_dir():
                stray.append(entry)
                continue
            if entry.suffix != ".md":
                continue
            rule, at, variant = entry.stem.partition("@")
            if not rule or (at and not variant):
                continue
            file = _read_file(entry, rule, variant or None)
            if at:
                variants.setdefault(rule, {})[variant] = file
            else:
                defaults[rule] = file
    rules = {
        name: Rule(name=name, default=defaults.get(name), variants=variants.get(name, {}))
        for name in sorted(defaults.keys() | variants.keys())
    }
    return Pool(root=root, rules=rules, stray_directories=tuple(sorted(stray)))
