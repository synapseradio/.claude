"""Find the rules of a pool that no add in the config includes."""

from __future__ import annotations

from rulesets.check.findings import CheckWarning, RuleSubject
from rulesets.source.config import Config
from rulesets.source.expansion import Expander
from rulesets.source.pool import Pool


def inclusion_warnings(config: Config, pool: Pool, expander: Expander) -> tuple[CheckWarning, ...]:
    """One warning for each rule that no add in any list includes, by name or through a ruleset.

    A rule counts as included where any list adds it, a conflicted add included, whether or
    not that list applies in any context.
    """

    included = {
        entry.rule
        for references in config.written_lists()
        for entry in expander.expand(references).entries
    }
    return tuple(
        CheckWarning(
            "never-included",
            RuleSubject(rule.name),
            rule.path,
            None,
            f"no add in any list includes rule `{rule.name}`",
        )
        for rule in pool.rules.values()
        if rule.name not in included
    )
