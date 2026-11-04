"""The errors a manifest carries: its shape, its conditions, its cycles, and its references.

This module words every one of them. The shape problems and the reference problems arrive
as data from `rulesets.source`.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import assert_never

from rulesets.check.findings import (
    CheckError,
    FlagSubject,
    ItemSubject,
    KeySubject,
    ManifestSubject,
    ModelSubject,
    ReferencesSubject,
    ReferenceSubject,
    RulesetSubject,
    Subject,
)
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.expansion import (
    Conflict,
    Expander,
    MalformedReference,
    ReferenceProblem,
    UnknownRule,
    UnknownRuleset,
    UnknownVariant,
    UnquotedReference,
)
from rulesets.source.manifest import (
    MANIFEST_KEYS,
    MalformedItem,
    Manifest,
    ManifestKey,
    ManifestParseError,
    ReservedRulesetDeclared,
    ShapeProblem,
    UnknownKey,
    UnquotedFlag,
    UnquotedModel,
    WrongKeyShape,
    WrongRulesetShape,
)
from rulesets.source.reference import EntryForm

_KEY_SHAPES: dict[ManifestKey, str] = {
    "models": "must be a list of model names",
    "flags": "must be a list of flag names",
    "defaults": "must be a list of references",
    "rulesets": "must be a mapping of ruleset names to lists of references",
    "when": "must be a list of items",
}


def _unquoted_message(text: str, form: EntryForm) -> str:
    """What is wrong with an entry that is no quoted string, and how to write it."""

    advice = "write every list entry as a quoted string"
    match form:
        case "mapping":
            return f"`{text}` is a mapping; {advice}"
        case "list":
            return f"`{text}` is a list; {advice}"
        case "plain" if not text:
            return f"an empty entry is not a quoted string; {advice}"
        case "plain":
            quoted = f'"{text}"' if "'" in text else f"'{text}'"
            return f"`{text}` is not quoted; {advice}, `{quoted}`"
        case _:
            assert_never(form)


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
        case UnquotedModel(text, line, form):
            return CheckError(
                "unquoted-entry",
                ModelSubject(text),
                manifest.path,
                line,
                _unquoted_message(text, form),
            )
        case UnquotedFlag(text, line, form):
            return CheckError(
                "unquoted-entry",
                FlagSubject(text),
                manifest.path,
                line,
                _unquoted_message(text, form),
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
    match problem:
        case MalformedReference(_, reason):
            kind, message = "malformed-reference", reason
        case UnquotedReference(_, form):
            kind, message = "unquoted-entry", _unquoted_message(reference.text, form)
        case UnknownRule(_, rule):
            kind, message = "undeclared-reference", f"the pool holds no rule `{rule}`"
        case UnknownVariant(_, rule, variant):
            kind, message = "undeclared-reference", f"rule `{rule}` has no variant `{variant}`"
        case UnknownRuleset(_, ruleset):
            kind, message = "undeclared-reference", f"no ruleset `{ruleset}` is declared"
        case _:
            assert_never(problem)
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
