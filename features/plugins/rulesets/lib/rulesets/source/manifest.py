"""Read `manifest.yaml` into its four keys, keeping the file line of everything check points at.

A key of the wrong shape holds nothing and comes back as a shape problem. This module
records each problem as data and words none of them.
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Iterator, Mapping
from typing import Literal, get_args

import yaml

from rulesets.source.reference import (
    RESERVED_RULESETS,
    EntryForm,
    Reference,
    parse_reference,
    unquoted_reference,
)
from rulesets.source.text_file import UnreadableFile, read_text_file

_MANIFEST_FILE = "manifest.yaml"
_MISSING_MANIFEST = "defaults: ['all:*']\n"
_QUOTE_STYLES = ("'", '"')
_QUOTE_ADVICE = "write every list entry as a quoted string"

type ManifestKey = Literal["models", "defaults", "rulesets", "when"]

MANIFEST_KEYS: tuple[str, ...] = get_args(ManifestKey.__value__)


@dataclasses.dataclass(frozen=True)
class Ruleset:
    name: str
    line: int
    references: tuple[Reference, ...]


@dataclasses.dataclass(frozen=True)
class WhenItem:
    """A `when` item whose shape is legal. `index` counts every item written, legal or not."""

    index: int
    line: int
    condition: str
    references: tuple[Reference, ...]


@dataclasses.dataclass(frozen=True)
class UnknownKey:
    """A top-level key other than the four."""

    name: str
    line: int


@dataclasses.dataclass(frozen=True)
class WrongKeyShape:
    """A top-level key whose value is not the shape the key holds."""

    key: ManifestKey
    line: int


@dataclasses.dataclass(frozen=True)
class WrongRulesetShape:
    """A ruleset whose value is not a list of references."""

    ruleset: str
    line: int


@dataclasses.dataclass(frozen=True)
class ReservedRulesetDeclared:
    """A reserved ruleset name declared under `rulesets`."""

    ruleset: str
    line: int


@dataclasses.dataclass(frozen=True)
class MalformedItem:
    """A `when` item that is no one-key mapping from a condition to a list."""

    index: int
    line: int


@dataclasses.dataclass(frozen=True)
class UnquotedModel:
    """An entry of `models` that is no quoted string. `text` is the entry as written."""

    text: str
    line: int
    form: EntryForm


type ShapeProblem = (
    UnknownKey
    | WrongKeyShape
    | WrongRulesetShape
    | ReservedRulesetDeclared
    | MalformedItem
    | UnquotedModel
)


class ManifestParseError(Exception):
    """The manifest cannot be read as text, is not YAML, or is not a mapping of keys."""

    def __init__(self, path: pathlib.Path, line: int | None, reason: str):
        where = f"{path}:{line}" if line is not None else str(path)
        super().__init__(f"{where}: {reason}")
        self.path = path
        self.line = line
        self.reason = reason


@dataclasses.dataclass(frozen=True)
class Manifest:
    """The four keys of a manifest. A key that is missing or the wrong shape holds nothing.

    `problems` holds the shape problems found while reading. `defaults` is None where
    the key holds nothing.
    """

    path: pathlib.Path
    models: tuple[str, ...]
    defaults: Ruleset | None
    rulesets: Mapping[str, Ruleset]
    items: tuple[WhenItem, ...]
    problems: tuple[ShapeProblem, ...]

    def spreadable(self) -> dict[str, tuple[Reference, ...]]:
        """Each list a spread can name, by name: the declared rulesets and `defaults`."""

        named = {name: ruleset.references for name, ruleset in self.rulesets.items()}
        if self.defaults is not None:
            named["defaults"] = self.defaults.references
        return named

    def written_lists(self) -> Iterator[tuple[Reference, ...]]:
        """Every list the manifest writes, in file order: defaults, each ruleset, each item."""

        if self.defaults is not None:
            yield self.defaults.references
        for ruleset in self.rulesets.values():
            yield ruleset.references
        for item in self.items:
            yield item.references


def _line(node: yaml.Node) -> int:
    return node.start_mark.line + 1


def _written(node: yaml.Node, text: str) -> str:
    if isinstance(node, yaml.ScalarNode):
        return node.value
    return text[node.start_mark.index : node.end_mark.index]


def _quoted_value(node: yaml.Node) -> str | None:
    """The string of a quoted scalar, and None for every other way to write an entry."""

    if isinstance(node, yaml.ScalarNode) and node.style in _QUOTE_STYLES:
        return node.value
    return None


def _form(node: yaml.Node) -> EntryForm:
    if isinstance(node, yaml.MappingNode):
        return "mapping"
    if isinstance(node, yaml.SequenceNode):
        return "list"
    return "plain"


def _reference(node: yaml.Node, text: str) -> Reference:
    if (value := _quoted_value(node)) is not None:
        return parse_reference(value, _line(node))
    return unquoted_reference(_written(node, text), _line(node), _form(node))


def _references(node: yaml.Node, text: str) -> tuple[Reference, ...] | None:
    if not isinstance(node, yaml.SequenceNode):
        return None
    return tuple(_reference(element, text) for element in node.value)


def _is_item(node: yaml.Node) -> bool:
    if not isinstance(node, yaml.MappingNode) or len(node.value) != 1:
        return False
    condition, references = node.value[0]
    return isinstance(condition, yaml.ScalarNode) and isinstance(references, yaml.SequenceNode)


def _read_models(
    value: yaml.Node, text: str, line: int
) -> tuple[tuple[str, ...], tuple[ShapeProblem, ...]]:
    if not isinstance(value, yaml.SequenceNode):
        return (), (WrongKeyShape("models", line),)
    models: list[str] = []
    problems: list[ShapeProblem] = []
    for element in value.value:
        if (name := _quoted_value(element)) is not None:
            models.append(name)
        else:
            problems.append(UnquotedModel(_written(element, text), _line(element), _form(element)))
    return tuple(models), tuple(problems)


def _read_defaults(
    value: yaml.Node, text: str, line: int
) -> tuple[Ruleset | None, tuple[ShapeProblem, ...]]:
    references = _references(value, text)
    if references is None:
        return None, (WrongKeyShape("defaults", line),)
    return Ruleset("defaults", line, references), ()


def _read_rulesets(
    value: yaml.Node, text: str, line: int
) -> tuple[dict[str, Ruleset], tuple[ShapeProblem, ...]]:
    if not isinstance(value, yaml.MappingNode):
        return {}, (WrongKeyShape("rulesets", line),)
    rulesets: dict[str, Ruleset] = {}
    problems: list[ShapeProblem] = []
    for name_node, list_node in value.value:
        name = _written(name_node, text)
        declared = _line(name_node)
        if name in RESERVED_RULESETS:
            problems.append(ReservedRulesetDeclared(name, declared))
            continue
        references = _references(list_node, text)
        if references is None:
            problems.append(WrongRulesetShape(name, declared))
        rulesets[name] = Ruleset(name, declared, references or ())
    return rulesets, tuple(problems)


def _read_when(
    value: yaml.Node, text: str, line: int
) -> tuple[tuple[WhenItem, ...], tuple[ShapeProblem, ...]]:
    if not isinstance(value, yaml.SequenceNode):
        return (), (WrongKeyShape("when", line),)
    items: list[WhenItem] = []
    problems: list[ShapeProblem] = []
    for index, element in enumerate(value.value):
        if not _is_item(element):
            problems.append(MalformedItem(index, _line(element)))
            continue
        condition, references_node = element.value[0]
        references = _references(references_node, text)
        items.append(WhenItem(index, _line(condition), condition.value, references or ()))
    return tuple(items), tuple(problems)


def _is_unquoted_entry_failure(error: yaml.YAMLError) -> bool:
    """Whether an unquoted entry causes the failure: a `*` read as an alias, or a flow list broken open."""

    context = getattr(error, "context", None) or ""
    problem = getattr(error, "problem", None) or ""
    return "alias" in context or "alias" in problem or "flow sequence" in context


def _top_level(text: str, path: pathlib.Path) -> list[tuple[yaml.Node, yaml.Node]]:
    try:
        document = yaml.compose(text)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        reason = getattr(error, "problem", None) or str(error)
        if _is_unquoted_entry_failure(error):
            reason = f"{reason}; {_QUOTE_ADVICE}"
        raise ManifestParseError(path, mark.line + 1 if mark else 1, reason) from error
    if document is None:
        return []
    if not isinstance(document, yaml.MappingNode):
        found = "a list" if isinstance(document, yaml.SequenceNode) else "a single value"
        raise ManifestParseError(
            path, _line(document), f"the manifest is {found}, and it must be a mapping of keys"
        )
    return document.value


def parse_manifest(text: str, path: pathlib.Path) -> Manifest:
    """Parse a manifest, keeping the file line of every key, declaration, item, and reference.

    Raises ManifestParseError where the text is not a YAML mapping. A key of the wrong shape
    is not a parse failure: it holds nothing, and `problems` names it.
    """

    models: tuple[str, ...] = ()
    defaults: Ruleset | None = None
    rulesets: dict[str, Ruleset] = {}
    items: tuple[WhenItem, ...] = ()
    problems: list[ShapeProblem] = []

    for key_node, value in _top_level(text, path):
        name = _written(key_node, text)
        line = _line(key_node)
        found: tuple[ShapeProblem, ...]
        match name:
            case "models":
                models, found = _read_models(value, text, line)
            case "defaults":
                defaults, found = _read_defaults(value, text, line)
            case "rulesets":
                rulesets, found = _read_rulesets(value, text, line)
            case "when":
                items, found = _read_when(value, text, line)
            case _:
                found = (UnknownKey(name, line),)
        problems.extend(found)

    return Manifest(
        path=path,
        models=models,
        defaults=defaults,
        rulesets=rulesets,
        items=items,
        problems=tuple(problems),
    )


def read_manifest(root: pathlib.Path) -> Manifest:
    """Read `manifest.yaml` of one rulesets directory.

    A missing file reads as `defaults: ['all:*']`. A file that cannot be read or does not
    parse raises ManifestParseError.
    """

    path = root / _MANIFEST_FILE
    try:
        text = read_text_file(path) if path.is_file() else _MISSING_MANIFEST
    except UnreadableFile as failure:
        raise ManifestParseError(path, failure.line, failure.cause) from failure
    return parse_manifest(text, path)
