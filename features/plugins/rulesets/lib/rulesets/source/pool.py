"""Read the pool: the rule files of one rulesets directory, by rule and by variant.

The reader extracts what each file says (its text, first-line marker, frontmatter keys,
cited paths, and where its body begins) and judges none of it. A file that cannot be read
carries the cause in `problem`.
"""

from __future__ import annotations

import dataclasses
import pathlib
import re
from collections.abc import Mapping

import yaml

from rulesets.documents import split_frontmatter
from rulesets.source.text_file import UnreadableFile, read_text_file

_POOL_DIRECTORY = "rules"
REFERENCES_DIRECTORY = "references"
_RENDER_DIRECTORY = "-render"

_MARKER = re.compile(r"<!-- rule: (?P<rule>[^\s@]+)(?: variant: (?P<variant>\S+))? -->")

_REFERENCE_CITATION = re.compile(
    rf"`(?P<path>~/[^`\s]+|/[^`\s/]+/[^`\s]+|{REFERENCES_DIRECTORY}/[^`\s]+)`"
)


@dataclasses.dataclass(frozen=True)
class Marker:
    """What a body's first line says it is: a rule's default form, or one of its variants."""

    rule: str
    variant: str | None


@dataclasses.dataclass(frozen=True)
class FrontmatterKey:
    """A top-level frontmatter key with the file line it sits on."""

    key: str
    line: int


@dataclasses.dataclass(frozen=True)
class Frontmatter:
    """The frontmatter block of a file. `keys` is empty where the block is not YAML."""

    keys: tuple[FrontmatterKey, ...]
    parsed: bool


@dataclasses.dataclass(frozen=True)
class Citation:
    """A path a body cites in backticks, as written, with the file line it sits on.

    A path opens on `~/`, on `/` and a second segment, or on `references/`, and holds no
    whitespace. A bare `/`, a slash command such as `/clear`, any other relative path, and a
    URL are no citation.
    """

    text: str
    line: int


@dataclasses.dataclass(frozen=True)
class PoolFile:
    """One rule file as read. `problem` names why the file could not be read.

    A file with a problem holds no text, marker, frontmatter, or citation.
    """

    path: pathlib.Path
    rule: str
    variant: str | None
    text: str
    marker: Marker | None
    frontmatter: Frontmatter | None
    citations: tuple[Citation, ...]
    body_start: int
    problem: str | None

    @property
    def frontmatter_keys(self) -> tuple[FrontmatterKey, ...]:
        return self.frontmatter.keys if self.frontmatter else ()

    def line_of(self, index: int) -> int:
        """The 1-based file line of the character at `index` in the text."""

        return _line_of(self.text, index)


@dataclasses.dataclass(frozen=True)
class Rule:
    """A rule's files. `default` is None for a variant that sits beside no default form."""

    name: str
    default: PoolFile | None
    variants: Mapping[str, PoolFile]

    def files(self) -> tuple[PoolFile, ...]:
        """The default form first, then the variants by name."""

        return ((self.default,) if self.default else ()) + tuple(self.variants.values())

    @property
    def path(self) -> pathlib.Path:
        """The path of the first file: the default form, else the first variant."""

        return self.files()[0].path


@dataclasses.dataclass(frozen=True)
class Pool:
    """Every rule file of one rulesets directory, by rule name in sorted order."""

    root: pathlib.Path
    rules: Mapping[str, Rule]
    stray_directories: tuple[pathlib.Path, ...]

    def variants_by_rule(self) -> dict[str, tuple[str, ...]]:
        return {name: tuple(rule.variants) for name, rule in self.rules.items()}

    def has_reference(self, name: str) -> bool:
        """Whether `references/` holds a file at `name`."""

        return (self.root / REFERENCES_DIRECTORY / name).is_file()


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _parse_marker(line: str) -> Marker | None:
    found = _MARKER.fullmatch(line.rstrip())
    if found is None:
        return None
    return Marker(rule=found["rule"], variant=found["variant"])


def _frontmatter(text: str) -> Frontmatter | None:
    split = split_frontmatter(text)
    if split is None:
        return None
    block, first_line = split
    try:
        node = yaml.compose(block)
    except yaml.YAMLError:
        return Frontmatter(keys=(), parsed=False)
    if not isinstance(node, yaml.MappingNode):
        return Frontmatter(keys=(), parsed=True)
    keys = tuple(
        FrontmatterKey(key=key.value, line=key.start_mark.line + first_line)
        for key, _ in node.value
        if isinstance(key, yaml.ScalarNode)
    )
    return Frontmatter(keys=keys, parsed=True)


def _citations(text: str) -> tuple[Citation, ...]:
    return tuple(
        Citation(text=found["path"], line=_line_of(text, found.start()))
        for found in _REFERENCE_CITATION.finditer(text)
    )


def _read_file(path: pathlib.Path, rule: str, variant: str | None) -> PoolFile:
    try:
        text = read_text_file(path)
    except UnreadableFile as failure:
        return PoolFile(path, rule, variant, "", None, None, (), 0, failure.cause)
    first_line, newline, _ = text.partition("\n")
    marker = _parse_marker(first_line)
    return PoolFile(
        path=path,
        rule=rule,
        variant=variant,
        text=text,
        marker=marker,
        frontmatter=_frontmatter(text),
        citations=_citations(text),
        body_start=len(first_line) + len(newline) if marker else 0,
        problem=None,
    )


def read_pool(root: pathlib.Path) -> Pool:
    """Read `rules/` of one rulesets directory.

    A file's rule is its stem up to the first `@`, and the rest of the stem is its variant.
    The `references/` and `-render/` folders beside the pool are reserved and read as nothing.
    """

    pool_directory = root / _POOL_DIRECTORY
    stray = [
        entry
        for entry in (sorted(root.iterdir()) if root.is_dir() else ())
        if entry.is_dir()
        and entry.name not in (_POOL_DIRECTORY, REFERENCES_DIRECTORY, _RENDER_DIRECTORY)
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
