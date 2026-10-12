"""Find the rules whose text names another rule of the pool as a whole word."""

from __future__ import annotations

import re

from rulesets.check.findings import CheckWarning, RulePairSubject
from rulesets.source.pool import Pool, Rule

NAME_CHARACTERS = "A-Za-z0-9_-"


def _whole_word(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![{NAME_CHARACTERS}]){re.escape(name)}(?![{NAME_CHARACTERS}])")


def cross_reference_warnings(pool: Pool) -> tuple[CheckWarning, ...]:
    """One warning for each rule that names another rule, at the first match in file order.

    A name matches case-sensitively and ends at any character that is no letter, digit,
    hyphen, or underscore. A rule's files are searched default form first, then by variant,
    and a first-line marker is no mention.
    """

    patterns = {name: _whole_word(name) for name in pool.rules}
    warnings: list[CheckWarning] = []
    for rule in pool.rules.values():
        for other, pattern in patterns.items():
            if other != rule.name and (warning := _first_mention(rule, other, pattern)):
                warnings.append(warning)
    return tuple(warnings)


def _first_mention(rule: Rule, other: str, pattern: re.Pattern[str]) -> CheckWarning | None:
    for file in rule.files():
        start = len(file.text.split("\n", 1)[0]) + 1 if file.marker else 0
        if found := pattern.search(file.text, start):
            return CheckWarning(
                "cross-reference",
                RulePairSubject(rule.name, other),
                file.path,
                file.line_of(found.start()),
                f"the text of rule `{rule.name}` names rule `{other}`",
            )
    return None
