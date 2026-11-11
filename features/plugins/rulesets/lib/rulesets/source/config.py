"""Read `config.yaml` into its declarations and blocks, keeping the file line of every word.

The keys `models`, `flags`, `defaults`, and `sets` hold what their names say; every other
top-level key is a block keyed by its condition. A block nests further blocks, and its `then`
holds a second list under the same condition; this module flattens each into a Block whose
condition joins every enclosing condition with `and`. A key of the wrong shape holds nothing and
comes back as a shape problem. This module records each problem as data and words none of them.
"""

from __future__ import annotations

import dataclasses
import pathlib
import re
from collections.abc import Iterator, Mapping
from typing import Literal

import yaml

from rulesets.source.reference import RESERVED_RULESETS, Reference, parse_reference
from rulesets.source.text_file import UnreadableFile, read_text_file

CONFIG_FILE = "config.yaml"
OLD_CONFIG_FILE = "manifest.yaml"
_MISSING_CONFIG = "defaults: all.*\n"
_NULL_TAG = "tag:yaml.org,2002:null"
_WORD = re.compile(r"\S+")
_CONDITION_TOKEN = re.compile(r"[()]|[^\s()]+")

type DeclarationKey = Literal["models", "flags", "defaults", "sets"]

DECLARATION_KEYS: tuple[DeclarationKey, ...] = ("models", "flags", "defaults", "sets")
BLOCK_LIST_KEYS = ("include", "exclude")
THEN_KEY = "then"


@dataclasses.dataclass(frozen=True)
class Ruleset:
    name: str
    line: int
    references: tuple[Reference, ...]


@dataclasses.dataclass(frozen=True)
class Block:
    """One list under one condition: a block's own list, a nested block's, or a `then` list's.

    `key` is the key as written at `line`; `condition` joins it with every enclosing condition.
    `index` counts the blocks in file order, legal or not.
    """

    index: int
    line: int
    key: str
    condition: str
    references: tuple[Reference, ...]


@dataclasses.dataclass(frozen=True)
class OldLayoutKey:
    """A top-level `when` or `rulesets` key, from the layout the config no longer reads."""

    name: str
    line: int


@dataclasses.dataclass(frozen=True)
class WrongKeyShape:
    """A declaration key whose value is not the shape the key holds."""

    key: DeclarationKey
    line: int


@dataclasses.dataclass(frozen=True)
class WrongRulesetShape:
    """A set whose value is neither words nor a mapping of `include` and `exclude`."""

    ruleset: str
    line: int


@dataclasses.dataclass(frozen=True)
class ReservedRulesetDeclared:
    """A reserved name declared under `sets`."""

    ruleset: str
    line: int


@dataclasses.dataclass(frozen=True)
class DottedRulesetName:
    """A set whose name holds a `.`, which a reference reads as the end of a set's name."""

    ruleset: str
    line: int


type ListForm = Literal["sequence", "mapping"]


@dataclasses.dataclass(frozen=True)
class WrongListShape:
    """A list written as a YAML sequence or mapping where words belong. `key` names the list."""

    key: str
    line: int
    form: ListForm


type BlockFault = Literal["words", "empty", "sequence"]


@dataclasses.dataclass(frozen=True)
class WrongBlockShape:
    """A block whose value is no mapping holding a list or a nested block.

    `words` is a value of bare words, `empty` one holding nothing, `sequence` a YAML list.
    """

    key: str
    condition: str
    line: int
    fault: BlockFault


@dataclasses.dataclass(frozen=True)
class DuplicateKey:
    """One key written twice or more in one mapping, at each of `lines`; every one is skipped."""

    key: str
    lines: tuple[int, ...]


type ShapeProblem = (
    OldLayoutKey
    | WrongKeyShape
    | WrongRulesetShape
    | ReservedRulesetDeclared
    | DottedRulesetName
    | WrongListShape
    | WrongBlockShape
    | DuplicateKey
)


class ConfigParseError(Exception):
    """The config cannot be read as text, is not YAML, or is not a mapping of keys."""

    def __init__(self, path: pathlib.Path, line: int | None, reason: str):
        where = f"{path}:{line}" if line is not None else str(path)
        super().__init__(f"{where}: {reason}")
        self.path = path
        self.line = line
        self.reason = reason


@dataclasses.dataclass(frozen=True)
class Config:
    """The declarations and blocks of a config. A key that is missing or the wrong shape holds nothing.

    `problems` holds the shape problems found while reading. `defaults` is None where the key
    is not written.
    """

    path: pathlib.Path
    models: tuple[str, ...]
    flags: tuple[str, ...]
    defaults: Ruleset | None
    rulesets: Mapping[str, Ruleset]
    blocks: tuple[Block, ...]
    problems: tuple[ShapeProblem, ...]

    def spreadable(self) -> dict[str, tuple[Reference, ...]]:
        """Each list a spread can name, by name: the declared sets and `defaults`."""

        named = {name: ruleset.references for name, ruleset in self.rulesets.items()}
        if self.defaults is not None:
            named["defaults"] = self.defaults.references
        return named

    def written_lists(self) -> Iterator[tuple[Reference, ...]]:
        """Every list the config writes, in file order: defaults, each set, each block."""

        if self.defaults is not None:
            yield self.defaults.references
        for ruleset in self.rulesets.values():
            yield ruleset.references
        for block in self.blocks:
            yield block.references


def _line(node: yaml.Node) -> int:
    return node.start_mark.line + 1


def _key_text(node: yaml.Node, text: str) -> str:
    if isinstance(node, yaml.ScalarNode):
        return node.value
    return text[node.start_mark.index : node.end_mark.index]


def _is_null(node: yaml.Node) -> bool:
    return isinstance(node, yaml.ScalarNode) and node.tag == _NULL_TAG


def _words(node: yaml.ScalarNode, text: str) -> Iterator[tuple[str, int]]:
    """Each word of a scalar with the file line it sits on, as written in the source."""

    if _is_null(node):
        return
    if node.style is not None:
        for word in node.value.split():
            yield word, _line(node)
        return
    start = node.start_mark.index
    written = text[start : node.end_mark.index]
    for found in _WORD.finditer(written):
        yield found.group(), _line(node) + written.count("\n", 0, found.start())


def _unique_pairs(
    node: yaml.MappingNode, text: str
) -> tuple[list[tuple[str, yaml.Node, yaml.Node]], list[DuplicateKey]]:
    """The pairs of a mapping whose key text is written once, and a problem per repeated key."""

    lines: dict[str, list[int]] = {}
    for key, _ in node.value:
        lines.setdefault(_key_text(key, text), []).append(_line(key))
    duplicates = [DuplicateKey(key, tuple(at)) for key, at in lines.items() if len(at) > 1]
    pairs = [
        (_key_text(key, text), key, value)
        for key, value in node.value
        if len(lines[_key_text(key, text)]) == 1
    ]
    return pairs, duplicates


class _Reader:
    def __init__(self, text: str):
        self._text = text
        self.problems: list[ShapeProblem] = []
        self.blocks: list[Block] = []

    def _old_list(self, node: yaml.Node, key: str) -> None:
        form: ListForm = "sequence" if isinstance(node, yaml.SequenceNode) else "mapping"
        self.problems.append(WrongListShape(key, _line(node), form))

    def words(self, node: yaml.Node, key: str) -> tuple[str, ...] | None:
        """The words of a list value: none for a sequence, which draws a problem; None for a mapping."""

        if isinstance(node, yaml.ScalarNode):
            return tuple(word for word, _ in _words(node, self._text))
        if isinstance(node, yaml.SequenceNode):
            self._old_list(node, key)
            return ()
        return None

    def references(self, node: yaml.Node, key: str, *, remove: bool) -> tuple[Reference, ...]:
        if not isinstance(node, yaml.ScalarNode):
            self._old_list(node, key)
            return ()
        return tuple(
            parse_reference(word, line, remove=remove) for word, line in _words(node, self._text)
        )

    def include_exclude(self, node: yaml.MappingNode, key: str) -> tuple[Reference, ...] | None:
        """The list a mapping of `include` and `exclude` forms, or None where it holds another key."""

        pairs, duplicates = _unique_pairs(node, self._text)
        self.problems.extend(duplicates)
        if any(name not in BLOCK_LIST_KEYS for name, _, _ in pairs):
            return None
        found: list[Reference] = []
        for name, _, value in pairs:
            found.extend(self.references(value, f"{key} {name}", remove=name == "exclude"))
        return tuple(found)

    def ruleset_list(self, node: yaml.Node, key: str) -> tuple[Reference, ...] | None:
        """The list `defaults` or a set holds: words it includes, or `include` and `exclude`."""

        if isinstance(node, yaml.ScalarNode):
            return self.references(node, key, remove=False)
        if isinstance(node, yaml.MappingNode):
            return self.include_exclude(node, key)
        self._old_list(node, key)
        return ()

    def block(self, key: str, line: int, condition: str, value: yaml.Node) -> None:
        match value:
            case yaml.ScalarNode() if _is_null(value) or not value.value.strip():
                self.problems.append(WrongBlockShape(key, condition, line, "empty"))
            case yaml.ScalarNode():
                self.problems.append(WrongBlockShape(key, condition, line, "words"))
            case yaml.SequenceNode():
                self.problems.append(WrongBlockShape(key, condition, line, "sequence"))
            case yaml.MappingNode() if not value.value:
                self.problems.append(WrongBlockShape(key, condition, line, "empty"))
            case _:
                self._mapping_block(line, key, condition, value)

    def _mapping_block(self, line: int, key: str, condition: str, value: yaml.Node) -> None:
        pairs, duplicates = _unique_pairs(value, self._text)
        self.problems.extend(duplicates)
        own = [(name, node) for name, _, node in pairs if name in BLOCK_LIST_KEYS]
        if own:
            references: list[Reference] = []
            for name, node in own:
                references.extend(self.references(node, name, remove=name == "exclude"))
            self.blocks.append(Block(len(self.blocks), line, key, condition, tuple(references)))
        for name, name_node, node in pairs:
            if name in BLOCK_LIST_KEYS:
                continue
            if name == THEN_KEY:
                self.block(THEN_KEY, _line(name_node), condition, node)
            else:
                self.block(name, _line(name_node), combine(condition, name), node)


def _top_or(condition: str) -> bool:
    depth = 0
    for token in _CONDITION_TOKEN.findall(condition):
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        elif token == "or" and depth == 0:
            return True
    return False


def combine(outer: str, inner: str) -> str:
    """The condition of a block nested under `outer`: both joined with `and`."""

    parts = [f"({part})" if _top_or(part) else part for part in (outer, inner)]
    return " and ".join(parts)


def _parse_failure_reason(error: yaml.YAMLError) -> str:
    reason = getattr(error, "problem", None) or str(error)
    context = getattr(error, "context", None) or ""
    if "alias" in reason or "alias" in context:
        return f"{reason}; a bare `*` reads as a YAML alias, so write `all.*` to spread every rule"
    return reason


def _top_level(text: str, path: pathlib.Path) -> list[tuple[yaml.Node, yaml.Node]]:
    try:
        document = yaml.compose(text)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        raise ConfigParseError(
            path, mark.line + 1 if mark else 1, _parse_failure_reason(error)
        ) from error
    if document is None:
        return []
    if not isinstance(document, yaml.MappingNode):
        found = "a list" if isinstance(document, yaml.SequenceNode) else "a single value"
        raise ConfigParseError(
            path, _line(document), f"the config is {found}, and it must be a mapping of keys"
        )
    return document.value


def _read_sets(reader: _Reader, value: yaml.Node, line: int) -> dict[str, Ruleset]:
    if _is_null(value):
        return {}
    if not isinstance(value, yaml.MappingNode):
        reader.problems.append(WrongKeyShape("sets", line))
        return {}
    pairs, duplicates = _unique_pairs(value, reader._text)
    reader.problems.extend(duplicates)
    rulesets: dict[str, Ruleset] = {}
    for name, name_node, list_node in pairs:
        declared = _line(name_node)
        if name in RESERVED_RULESETS:
            reader.problems.append(ReservedRulesetDeclared(name, declared))
            continue
        if "." in name:
            reader.problems.append(DottedRulesetName(name, declared))
            continue
        references = reader.ruleset_list(list_node, name)
        if references is None:
            reader.problems.append(WrongRulesetShape(name, declared))
        rulesets[name] = Ruleset(name, declared, references or ())
    return rulesets


def parse_config(text: str, path: pathlib.Path) -> Config:
    """Parse a config, keeping the file line of every key, declaration, block, and word.

    Raises ConfigParseError where the text is not a YAML mapping. A key of the wrong shape is
    not a parse failure: it holds nothing, and `problems` names it.
    """

    reader = _Reader(text)
    models: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    defaults: Ruleset | None = None
    rulesets: dict[str, Ruleset] = {}

    document = yaml.MappingNode("tag:yaml.org,2002:map", _top_level(text, path))
    pairs, duplicates = _unique_pairs(document, text)
    reader.problems.extend(duplicates)
    for name, key_node, value in pairs:
        line = _line(key_node)
        match name:
            case "models" | "flags":
                words = reader.words(value, name)
                if words is None:
                    reader.problems.append(WrongKeyShape(name, line))
                elif name == "models":
                    models = words
                else:
                    flags = words
            case "defaults":
                references = reader.ruleset_list(value, name)
                if references is None:
                    reader.problems.append(WrongKeyShape("defaults", line))
                else:
                    defaults = Ruleset("defaults", line, references)
            case "sets":
                rulesets = _read_sets(reader, value, line)
            case "when" | "rulesets":
                reader.problems.append(OldLayoutKey(name, line))
            case _:
                reader.block(name, line, name, value)

    return Config(
        path=path,
        models=models,
        flags=flags,
        defaults=defaults,
        rulesets=rulesets,
        blocks=tuple(reader.blocks),
        problems=tuple(reader.problems),
    )


def read_config(root: pathlib.Path) -> Config:
    """Read `config.yaml` of one rulesets directory.

    A missing file reads as `defaults: all.*`. A file that cannot be read or does not parse
    raises ConfigParseError.
    """

    path = root / CONFIG_FILE
    try:
        text = read_text_file(path) if path.is_file() else _MISSING_CONFIG
    except UnreadableFile as failure:
        raise ConfigParseError(path, failure.line, failure.cause) from failure
    return parse_config(text, path)
