"""The errors a manifest carries: its shape, its conditions, its cycles, and its references.

This module words every one of them. The shape problems and the reference problems arrive
as data from `rulesets.source`.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import assert_never

from rulesets.check.findings import (
    CheckError,
    ItemSubject,
    KeySubject,
    ManifestSubject,
    ReferencesSubject,
    ReferenceSubject,
    RulesetSubject,
    Subject,
)
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.expansion import Conflict, Expander, ReferenceProblem
from rulesets.source.manifest import (
    MANIFEST_KEYS,
    MalformedItem,
    Manifest,
    ManifestKey,
    ManifestParseError,
    ReservedRulesetDeclared,
    ShapeProblem,
    UnknownKey,
    WrongKeyShape,
    WrongRulesetShape,
)
from rulesets.source.reference import MalformedTarget, RuleTarget, SpreadTarget

_KEY_SHAPES: dict[ManifestKey, str] = {
    "models": "must be a list of model names",
    "defaults": "must be a list of references",
    "rulesets": "must be a mapping of ruleset names to lists of references",
    "when": "must be a list of items",
}


def unparsable_error(failure: ManifestParseError) -> CheckError:
    """The error for a manifest that cannot be read, is not YAML, or is not a mapping."""

    return CheckError(
        "manifest-unparsable", ManifestSubject(), failure.path, failure.line, failure.reason
    )


def manifest_errors(manifest: Manifest, expander: Expander) -> tuple[CheckError, ...]:
    """Every error in the manifest, shape errors first, in the order the file reads."""

    return (
        *(_shape_error(manifest, problem) for problem in manifest.problems),
        *_cycle_errors(manifest, expander),
        *_condition_errors(manifest),
        *_list_errors(manifest, expander),
    )


def _shape_error(manifest: Manifest, problem: ShapeProblem) -> CheckError:
    match problem:
        case UnknownKey(name, line):
            keys = f"{', '.join(MANIFEST_KEYS[:-1])}, and {MANIFEST_KEYS[-1]}"
            return CheckError(
                "unknown-key",
                KeySubject(name),
                manifest.path,
                line,
                f"`{name}` is not a manifest key; the keys are {keys}",
            )
        case WrongKeyShape(key, line):
            return CheckError(
                "key-shape", KeySubject(key), manifest.path, line, f"`{key}` {_KEY_SHAPES[key]}"
            )
        case WrongRulesetShape(ruleset, line):
            return CheckError(
                "ruleset-shape",
                RulesetSubject(ruleset),
                manifest.path,
                line,
                f"ruleset `{ruleset}` must be a list of references",
            )
        case ReservedRulesetDeclared(ruleset, line):
            return CheckError(
                "reserved-ruleset",
                RulesetSubject(ruleset),
                manifest.path,
                line,
                f"`{ruleset}` is a reserved ruleset and cannot be declared",
            )
        case MalformedItem(index, line):
            return CheckError(
                "item-shape",
                ItemSubject(index),
                manifest.path,
                line,
                "an item must be a one-key mapping from a condition to a list of references",
            )
        case _:
            assert_never(problem)


def _cycle_errors(manifest: Manifest, expander: Expander) -> Iterator[CheckError]:
    declarations: list[tuple[Subject, str, int]] = []
    if manifest.defaults is not None:
        declarations.append((KeySubject("defaults"), "defaults", manifest.defaults.line))
    declarations += [
        (RulesetSubject(name), name, ruleset.line) for name, ruleset in manifest.rulesets.items()
    ]
    for subject, name, line in declarations:
        if cycle := expander.cycle_of(name):
            members = ", ".join(f"`{member}`" for member in cycle)
            yield CheckError(
                "ruleset-cycle",
                subject,
                manifest.path,
                line,
                f"`{name}` spreads in a cycle with {members}; a spread of any of them reaches no rule",
            )


def _condition_errors(manifest: Manifest) -> Iterator[CheckError]:
    for item in manifest.items:
        subject = ItemSubject(item.index)
        try:
            condition = parse_condition(item.condition)
        except ConditionError as error:
            yield CheckError(
                "condition-invalid",
                subject,
                manifest.path,
                item.line,
                f"the condition `{item.condition}` is invalid: {error.reason}",
            )
            continue
        undeclared = dict.fromkeys(
            test.value
            for test in fact_tests(condition)
            if test.fact == "model" and test.value not in manifest.models
        )
        if undeclared:
            names = ", ".join(f"`{name}`" for name in undeclared)
            yield CheckError(
                "unknown-model",
                subject,
                manifest.path,
                item.line,
                f"the condition names {names}, which `models` does not declare",
            )


def _list_errors(manifest: Manifest, expander: Expander) -> Iterator[CheckError]:
    for references in manifest.written_lists():
        expansion = expander.expand(references)
        for problem in expansion.problems:
            yield _reference_error(manifest, problem)
        for conflict in expansion.conflicts:
            yield _conflict_error(manifest, conflict)


def _reference_error(manifest: Manifest, problem: ReferenceProblem) -> CheckError:
    """The subject names the reference, so the message says only what is wrong with it."""

    reference = problem.reference
    match problem.reason, reference.target:
        case "malformed", MalformedTarget(reason):
            kind, message = "malformed-reference", reason
        case "unknown-rule", RuleTarget(rule, _):
            kind, message = "undeclared-reference", f"the pool holds no rule `{rule}`"
        case "unknown-variant", RuleTarget(rule, variant):
            kind, message = "undeclared-reference", f"rule `{rule}` has no variant `{variant}`"
        case "unknown-ruleset", SpreadTarget(ruleset):
            kind, message = "undeclared-reference", f"no ruleset `{ruleset}` is declared"
        case _:
            raise AssertionError(f"reason {problem.reason!r} does not fit {reference.target!r}")
    return CheckError(
        kind,
        ReferenceSubject(reference.text, reference.line),
        manifest.path,
        reference.line,
        message,
    )


def _conflict_error(manifest: Manifest, conflict: Conflict) -> CheckError:
    members = tuple(
        dict.fromkeys(
            ReferenceSubject(entry.source.text, entry.source.line) for entry in conflict.entries
        )
    )
    variants = ", ".join(f"`{entry.variant}`" for entry in conflict.entries)
    return CheckError(
        "variant-conflict",
        ReferencesSubject(members),
        manifest.path,
        members[0].line,
        f"one list sets rule `{conflict.rule}` to the variants {variants}",
    )
