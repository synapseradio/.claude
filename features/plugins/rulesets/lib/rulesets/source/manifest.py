"""Parse `manifest.yaml` into its four keys, keeping the file line of everything check points at."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Iterator, Mapping

import yaml

from rulesets.check.findings import (
    CheckError,
    ErrorKind,
    ItemSubject,
    KeySubject,
    RulesetSubject,
    Subject,
)
from rulesets.source.reference import RESERVED_RULESETS, Reference, parse_reference

MANIFEST_FILE = "manifest.yaml"
MISSING_MANIFEST = "defaults: [all:*]\n"

KEY_SHAPES = {
    "models": "must be a list of model names",
    "defaults": "must be a list of references",
    "rulesets": "must be a mapping of ruleset names to lists of references",
    "when": "must be a list of items",
}
STR_TAG = "tag:yaml.org,2002:str"


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


class ManifestParseError(Exception):
    """The manifest is not YAML, or not a mapping of keys."""

    def __init__(self, path: pathlib.Path, line: int, reason: str):
        super().__init__(f"{path}:{line}: {reason}")
        self.path = path
        self.line = line
        self.reason = reason


@dataclasses.dataclass(frozen=True)
class Manifest:
    """The four keys of a manifest. A key that is missing or the wrong shape holds nothing.

    `problems` holds the errors found while reading the shape. `defaults` is None where
    the key holds nothing.
    """

    path: pathlib.Path
    models: tuple[str, ...]
    defaults: Ruleset | None
    rulesets: Mapping[str, Ruleset]
    items: tuple[WhenItem, ...]
    key_lines: Mapping[str, int]
    problems: tuple[CheckError, ...]

    def lists(self) -> dict[str, tuple[Reference, ...]]:
        """Each list a spread can name, by name: the declared rulesets and `defaults`."""

        named = {name: ruleset.references for name, ruleset in self.rulesets.items()}
        if self.defaults is not None:
            named["defaults"] = self.defaults.references
        return named

    def reference_lists(self) -> Iterator[tuple[Reference, ...]]:
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


def _references(node: yaml.Node, text: str) -> tuple[Reference, ...] | None:
    if not isinstance(node, yaml.SequenceNode):
        return None
    return tuple(parse_reference(_written(element, text), _line(element)) for element in node.value)


def _model_names(node: yaml.Node) -> tuple[str, ...] | None:
    if not isinstance(node, yaml.SequenceNode):
        return None
    if not all(isinstance(n, yaml.ScalarNode) and n.tag == STR_TAG for n in node.value):
        return None
    return tuple(n.value for n in node.value)


def _is_item(node: yaml.Node) -> bool:
    if not isinstance(node, yaml.MappingNode) or len(node.value) != 1:
        return False
    condition, references = node.value[0]
    return isinstance(condition, yaml.ScalarNode) and isinstance(references, yaml.SequenceNode)


def parse_manifest(text: str, path: pathlib.Path) -> Manifest:
    """Parse a manifest, keeping the file line of every key, declaration, item, and reference.

    Raises ManifestParseError where the text is not a YAML mapping. A key of the wrong shape
    is not a parse failure: it holds nothing, and `problems` names it.
    """

    try:
        document = yaml.compose(text)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        reason = getattr(error, "problem", None) or str(error)
        raise ManifestParseError(path, mark.line + 1 if mark else 1, reason) from error

    models: tuple[str, ...] = ()
    defaults: Ruleset | None = None
    rulesets: dict[str, Ruleset] = {}
    items: list[WhenItem] = []
    key_lines: dict[str, int] = {}
    problems: list[CheckError] = []

    def problem(kind: ErrorKind, subject: Subject, line: int, message: str) -> None:
        problems.append(CheckError(kind, subject, path, line, message))

    if document is not None and not isinstance(document, yaml.MappingNode):
        found = "a list" if isinstance(document, yaml.SequenceNode) else "a single value"
        raise ManifestParseError(
            path, _line(document), f"the manifest is {found}, and it must be a mapping of keys"
        )

    for key_node, value in document.value if document is not None else ():
        name = _written(key_node, text)
        line = _line(key_node)
        if name not in KEY_SHAPES:
            problem(
                "unknown-key",
                KeySubject(name),
                line,
                f"`{name}` is not a manifest key; the keys are models, defaults, rulesets, and when",
            )
            continue
        key_lines[name] = line
        wrong_shape = (
            "key-shape",
            KeySubject(name),
            line,
            f"`{name}` {KEY_SHAPES[name]}",
        )
        if name == "models":
            names = _model_names(value)
            if names is None:
                problem(*wrong_shape)
            models = names or ()
        elif name == "defaults":
            references = _references(value, text)
            if references is None:
                problem(*wrong_shape)
            defaults = None if references is None else Ruleset("defaults", line, references)
        elif name == "rulesets":
            if not isinstance(value, yaml.MappingNode):
                problem(*wrong_shape)
                continue
            rulesets = {}
            for ruleset_key, ruleset_value in value.value:
                ruleset = _written(ruleset_key, text)
                ruleset_line = _line(ruleset_key)
                if ruleset in RESERVED_RULESETS:
                    problem(
                        "reserved-ruleset",
                        RulesetSubject(ruleset),
                        ruleset_line,
                        f"`{ruleset}` is a reserved ruleset and cannot be declared",
                    )
                    continue
                references = _references(ruleset_value, text)
                if references is None:
                    problem(
                        "ruleset-shape",
                        RulesetSubject(ruleset),
                        ruleset_line,
                        f"ruleset `{ruleset}` must be a list of references",
                    )
                rulesets[ruleset] = Ruleset(ruleset, ruleset_line, references or ())
        else:
            if not isinstance(value, yaml.SequenceNode):
                problem(*wrong_shape)
                continue
            items = []
            for index, element in enumerate(value.value):
                if not _is_item(element):
                    problem(
                        "item-shape",
                        ItemSubject(index),
                        _line(element),
                        "an item must be a one-key mapping from a condition to a list of references",
                    )
                    continue
                condition, references_node = element.value[0]
                references = _references(references_node, text)
                items.append(WhenItem(index, _line(condition), condition.value, references or ()))

    return Manifest(
        path=path,
        models=models,
        defaults=defaults,
        rulesets=rulesets,
        items=tuple(items),
        key_lines=key_lines,
        problems=tuple(problems),
    )


def read_manifest(root: pathlib.Path) -> Manifest:
    """Read `manifest.yaml` of one rulesets directory.

    A missing file reads as `defaults: [all:*]`. A file that does not parse raises
    ManifestParseError.
    """

    path = root / MANIFEST_FILE
    text = path.read_text(encoding="utf-8") if path.is_file() else MISSING_MANIFEST
    return parse_manifest(text, path)
