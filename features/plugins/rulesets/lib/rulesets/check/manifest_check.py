"""The errors a manifest carries: its shape, its conditions, its cycles, and its references."""

from __future__ import annotations

from collections.abc import Iterator

from rulesets.check.findings import (
    CheckError,
    ItemSubject,
    KeySubject,
    ReferencesSubject,
    ReferenceSubject,
    RulesetSubject,
    Subject,
)
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.expansion import Conflict, Expander
from rulesets.source.manifest import Manifest
from rulesets.source.reference import MalformedTarget


def manifest_errors(manifest: Manifest, expander: Expander) -> tuple[CheckError, ...]:
    """Every error in the manifest, shape errors first, in the order the file reads."""

    return (
        *manifest.problems,
        *_cycle_errors(manifest, expander),
        *_condition_errors(manifest),
        *_list_errors(manifest, expander),
    )


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
    for references in manifest.reference_lists():
        expansion = expander.expand(references)
        for problem in expansion.problems:
            reference = problem.reference
            malformed = isinstance(reference.target, MalformedTarget)
            yield CheckError(
                "malformed-reference" if malformed else "undeclared-reference",
                ReferenceSubject(reference.text, reference.line),
                manifest.path,
                reference.line,
                f"`{reference.text}` {problem.message}"
                if malformed
                else f"`{reference.text}`: {problem.message}",
            )
        for conflict in expansion.conflicts:
            yield _conflict_error(manifest, conflict)


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
