"""Find the rules whose text refers to another rule of the pool by one of its reference forms."""

from __future__ import annotations

import re

from rulesets.check.findings import CheckWarning, RulePairSubject
from rulesets.source.pool import Pool, Rule

_NAME_CHARACTERS = "A-Za-z0-9_-"


def _reference_forms(name: str) -> re.Pattern[str]:
    escaped = re.escape(name)
    start = rf"(?<![{_NAME_CHARACTERS}])"
    end = rf"(?![{_NAME_CHARACTERS}])"
    forms = (
        rf"`{escaped}`",
        rf"{start}{escaped}(?:@[{_NAME_CHARACTERS}]+)?\.md{end}",
        rf"{start}rule\s+(?:{escaped}{end}|`{escaped}`)",
        rf"{start}the\s+(?:{escaped}|`{escaped}`)\s+rule{end}",
    )
    return re.compile("|".join(forms))


def cross_reference_warnings(pool: Pool) -> tuple[CheckWarning, ...]:
    """One warning for each rule that names another rule, at the first match in file order.

    A rule is named by its name in backticks, by its file name (`name.md` or `name@variant.md`,
    backticked or bare, as a link target too), or by the phrase "rule name" or "the name rule"
    with the name bare or backticked. A bare name elsewhere is no mention. A name matches
    case-sensitively and ends at any character that is no letter, digit, hyphen, or underscore.
    A rule's files are searched default form first, then by variant, and a first-line marker is
    no mention.
    """

    patterns = {name: _reference_forms(name) for name in pool.rules}
    warnings: list[CheckWarning] = []
    for rule in pool.rules.values():
        for other, pattern in patterns.items():
            if other != rule.name and (warning := _first_mention(rule, other, pattern)):
                warnings.append(warning)
    return tuple(warnings)


def _first_mention(rule: Rule, other: str, pattern: re.Pattern[str]) -> CheckWarning | None:
    for file in rule.files():
        if found := pattern.search(file.text, file.body_start):
            return CheckWarning(
                "cross-reference",
                RulePairSubject(rule.name, other),
                file.path,
                file.line_of(found.start()),
                f"the text of rule `{rule.name}` names rule `{other}`",
            )
    return None
