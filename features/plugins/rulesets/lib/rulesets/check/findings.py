"""The findings check reports: errors that disable a subject at delivery, and warnings that do not.

Every finding names its kind, its subject, and the file and line to open. This module holds the
finding types and nothing that produces them.
"""

from __future__ import annotations

import dataclasses
import pathlib
from typing import Literal

from rulesets.facts.context import Facts


@dataclasses.dataclass(frozen=True)
class RuleSubject:
    name: str


@dataclasses.dataclass(frozen=True)
class RulePairSubject:
    """A rule whose text names `other`, another rule of the pool."""

    name: str
    other: str


@dataclasses.dataclass(frozen=True)
class RulesetSubject:
    name: str


@dataclasses.dataclass(frozen=True)
class RulesetsSubject:
    """The rulesets of one cycle, by name, sorted. `defaults` can be among them."""

    names: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class BlockSubject:
    """A block, by its condition: for a nested block or a `then` list, the combined one."""

    condition: str


@dataclasses.dataclass(frozen=True)
class KeySubject:
    name: str


@dataclasses.dataclass(frozen=True)
class ModelSubject:
    """An entry of `models`, as written."""

    name: str


@dataclasses.dataclass(frozen=True)
class FlagSubject:
    """An entry of `flags`, as written."""

    name: str


@dataclasses.dataclass(frozen=True)
class ReferenceSubject:
    """A reference as written, with the file line it sits on."""

    text: str
    line: int


@dataclasses.dataclass(frozen=True)
class ReferencesSubject:
    """The references one error disables together."""

    members: tuple[ReferenceSubject, ...]


@dataclasses.dataclass(frozen=True)
class ConfigSubject:
    """The config as a whole."""


@dataclasses.dataclass(frozen=True)
class ContextSubject:
    """A context named by its facts."""

    facts: Facts


@dataclasses.dataclass(frozen=True)
class DirectorySubject:
    path: pathlib.Path


type Subject = (
    RuleSubject
    | RulePairSubject
    | RulesetSubject
    | RulesetsSubject
    | BlockSubject
    | KeySubject
    | ModelSubject
    | FlagSubject
    | ReferenceSubject
    | ReferencesSubject
    | ConfigSubject
    | DirectorySubject
    | ContextSubject
)

type ErrorKind = Literal[
    "config-unparsable",
    "config-file",
    "old-layout",
    "duplicate-key",
    "key-shape",
    "list-shape",
    "ruleset-shape",
    "ruleset-name",
    "reserved-ruleset",
    "block-shape",
    "ruleset-cycle",
    "variant-conflict",
    "condition-invalid",
    "unknown-model",
    "unknown-flag",
    "undeclared-reference",
    "malformed-reference",
    "old-reference",
    "rule-name",
    "rule-condition",
    "frontmatter-unparsable",
    "variant-without-default",
    "unreadable-file",
    "oversize-body",
]

type WarningKind = Literal[
    "never-included",
    "cross-reference",
    "stray-directory",
    "marker-for-another-rule",
    "dangling-reference",
    "external-reference",
    "too-many-parts",
]


@dataclasses.dataclass(frozen=True)
class CheckError:
    """An illegal state, the subject delivery disables, and where to find it."""

    kind: ErrorKind
    subject: Subject
    file: pathlib.Path
    line: int | None
    message: str


@dataclasses.dataclass(frozen=True)
class CheckWarning:
    """A finding worth a look that disables nothing."""

    kind: WarningKind
    subject: Subject
    file: pathlib.Path
    line: int | None
    message: str


@dataclasses.dataclass(frozen=True)
class Report:
    """Every finding of one check run, in the order found."""

    errors: tuple[CheckError, ...]
    warnings: tuple[CheckWarning, ...]
