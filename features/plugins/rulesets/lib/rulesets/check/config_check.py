"""The errors a config carries: its shape, its conditions, its cycles, and its references.

This module words every one of them. The shape problems and the reference problems arrive
as data from `rulesets.source`.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import assert_never

from rulesets.check.findings import (
    BlockSubject,
    CheckError,
    ConfigSubject,
    KeySubject,
    ReferencesSubject,
    ReferenceSubject,
    RulesetsSubject,
    RulesetSubject,
)
from rulesets.source.condition import ConditionError, parse_condition
from rulesets.source.config import (
    CONFIG_FILE,
    OLD_CONFIG_FILE,
    Config,
    ConfigParseError,
    DeclarationKey,
    DottedRulesetName,
    DuplicateKey,
    OldLayoutKey,
    ReservedRulesetDeclared,
    ShapeProblem,
    WrongBlockShape,
    WrongKeyShape,
    WrongListShape,
    WrongRulesetShape,
)
from rulesets.source.expansion import (
    Conflict,
    Expander,
    MalformedReference,
    OldFormReference,
    ReferenceProblem,
    RuleOutsideRuleset,
    UnknownRule,
    UnknownRuleset,
    UnknownVariant,
)
from rulesets.source.undeclared import undeclared_names

_WORDS = "a list is words, one or more per line, with no quotes, brackets, or dashes"

_KEY_SHAPES: dict[DeclarationKey, str] = {
    "models": f"must be model names; {_WORDS}",
    "flags": f"must be flag names; {_WORDS}",
    "defaults": "must be references, or a mapping of `include` and `exclude`",
    "sets": "must be a mapping of ruleset names to references",
}

_OLD_LAYOUT: dict[str, str] = {
    "when": (
        "the config no longer reads `when`; each condition is a top-level key, "
        "its rules under `include` and `exclude`"
    ),
    "rulesets": "the config no longer reads `rulesets`; declare each ruleset under `sets`",
}


def unparsable_error(failure: ConfigParseError) -> CheckError:
    """The error for a config that cannot be read, is not YAML, or is not a mapping."""

    return CheckError(
        "config-unparsable", ConfigSubject(), failure.path, failure.line, failure.reason
    )


def old_file_error(root: pathlib.Path) -> CheckError:
    """The error for a directory that holds the old file and no config."""

    return CheckError(
        "config-file",
        ConfigSubject(),
        root / OLD_CONFIG_FILE,
        None,
        f"the engine reads only `{CONFIG_FILE}`, and this directory holds `{OLD_CONFIG_FILE}` "
        f"and no `{CONFIG_FILE}`; rewrite it as `{root / CONFIG_FILE}`",
    )


def config_errors(config: Config, expander: Expander) -> tuple[CheckError, ...]:
    """Every error in the config, shape errors first, in the order the file reads."""

    return (
        *(_shape_error(config, problem) for problem in config.problems),
        *_cycle_errors(config, expander),
        *_condition_errors(config),
        *_list_errors(config, expander),
    )


def _block_shape_message(problem: WrongBlockShape) -> str:
    match problem.fault:
        case "words":
            return "its rules belong under `include` or `exclude`, not directly under the condition"
        case "empty":
            return "it holds no list and no nested block; give it `include`, `exclude`, or a block"
        case "sequence":
            return f"its rules belong under `include` or `exclude`; {_WORDS}"
        case _:
            assert_never(problem.fault)


def _shape_error(config: Config, problem: ShapeProblem) -> CheckError:
    match problem:
        case OldLayoutKey(name, line):
            return CheckError("old-layout", KeySubject(name), config.path, line, _OLD_LAYOUT[name])
        case DuplicateKey(key, lines):
            at = ", ".join(str(line) for line in lines)
            return CheckError(
                "duplicate-key",
                KeySubject(key),
                config.path,
                lines[0],
                f"the key is written at lines {at}, so each is skipped; "
                "give a second list under one condition with `then`",
            )
        case WrongKeyShape(key, line):
            return CheckError(
                "key-shape", KeySubject(key), config.path, line, f"`{key}` {_KEY_SHAPES[key]}"
            )
        case WrongListShape(key, line, _):
            return CheckError("list-shape", KeySubject(key), config.path, line, _WORDS)
        case WrongRulesetShape(ruleset, line):
            return CheckError(
                "ruleset-shape",
                RulesetSubject(ruleset),
                config.path,
                line,
                f"ruleset `{ruleset}` must be references, or a mapping of `include` and `exclude`",
            )
        case ReservedRulesetDeclared(ruleset, line):
            return CheckError(
                "reserved-ruleset",
                RulesetSubject(ruleset),
                config.path,
                line,
                f"`{ruleset}` is a reserved ruleset and cannot be declared",
            )
        case DottedRulesetName(ruleset, line):
            return CheckError(
                "ruleset-name",
                RulesetSubject(ruleset),
                config.path,
                line,
                "a ruleset name holds no `.`, since a reference reads `.` as the end of a ruleset's name",
            )
        case WrongBlockShape():
            return CheckError(
                "block-shape",
                BlockSubject(problem.condition),
                config.path,
                problem.line,
                _block_shape_message(problem),
            )
        case _:
            assert_never(problem)


def _cycle_errors(config: Config, expander: Expander) -> Iterator[CheckError]:
    """One error for each cycle, at the line of the first member written."""

    declared = {name: ruleset.line for name, ruleset in config.rulesets.items()}
    if config.defaults is not None:
        declared = {"defaults": config.defaults.line, **declared}
    reported: set[tuple[str, ...]] = set()
    for name in declared:
        cycle = expander.cycle_of(name)
        if not cycle or cycle in reported:
            continue
        reported.add(cycle)
        yield CheckError(
            "ruleset-cycle",
            RulesetsSubject(cycle),
            config.path,
            min(declared[member] for member in cycle),
            "their spreads form a cycle; a spread of any of them reaches no rule",
        )


def _condition_errors(config: Config) -> Iterator[CheckError]:
    for block in config.blocks:
        subject = BlockSubject(block.condition)
        try:
            condition = parse_condition(block.condition)
        except ConditionError as error:
            yield CheckError(
                "condition-invalid",
                subject,
                config.path,
                block.line,
                f"the condition `{block.condition}` is invalid: {error.reason}",
            )
            continue
        undeclared = undeclared_names(condition, config)
        if undeclared.flags:
            names = ", ".join(f"`{name}`" for name in undeclared.flags)
            yield CheckError(
                "unknown-flag",
                subject,
                config.path,
                block.line,
                f"the condition `{block.condition}` names {names}, which the config does not "
                "declare under `flags`",
            )
        if undeclared.models:
            names = ", ".join(f"`{name}`" for name in undeclared.models)
            yield CheckError(
                "unknown-model",
                subject,
                config.path,
                block.line,
                f"the condition `{block.condition}` names {names}, which the config does not "
                "declare under `models`",
            )


def _list_errors(config: Config, expander: Expander) -> Iterator[CheckError]:
    for references in config.written_lists():
        expansion = expander.expand(references)
        for problem in expansion.problems:
            yield _reference_error(config, problem)
        for conflict in expansion.conflicts:
            yield _conflict_error(config, conflict)


def _reference_error(config: Config, problem: ReferenceProblem) -> CheckError:
    """The subject names the reference, so the message says only what is wrong with it."""

    reference = problem.reference
    match problem:
        case MalformedReference(_, reason):
            kind, message = "malformed-reference", reason
        case OldFormReference(_, advice):
            kind, message = "old-reference", f"the config no longer reads this form; {advice}"
        case UnknownRule(_, rule):
            kind, message = "undeclared-reference", f"the pool holds no rule `{rule}`"
        case UnknownVariant(_, rule, variant):
            kind, message = "undeclared-reference", f"rule `{rule}` has no variant `{variant}`"
        case UnknownRuleset(_, ruleset):
            kind, message = "undeclared-reference", f"no ruleset `{ruleset}` is declared"
        case RuleOutsideRuleset(_, ruleset, rule):
            kind, message = "undeclared-reference", f"ruleset `{ruleset}` holds no rule `{rule}`"
        case _:
            assert_never(problem)
    return CheckError(
        kind,
        ReferenceSubject(reference.text, reference.line),
        config.path,
        reference.line,
        message,
    )


def _conflict_error(config: Config, conflict: Conflict) -> CheckError:
    members = tuple(
        dict.fromkeys(
            ReferenceSubject(entry.source.text, entry.source.line) for entry in conflict.entries
        )
    )
    variants = ", ".join(f"`{entry.variant}`" for entry in conflict.entries)
    return CheckError(
        "variant-conflict",
        ReferencesSubject(members),
        config.path,
        members[0].line,
        f"one list sets rule `{conflict.rule}` to the variants {variants}",
    )
