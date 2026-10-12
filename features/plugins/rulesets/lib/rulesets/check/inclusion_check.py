"""Find the rules of a pool that no add in the manifest includes."""

from __future__ import annotations

from rulesets.check.findings import CheckWarning, RuleSubject
from rulesets.source.expansion import Expander
from rulesets.source.manifest import Manifest
from rulesets.source.pool import Pool


def inclusion_warnings(
    manifest: Manifest, pool: Pool, expander: Expander
) -> tuple[CheckWarning, ...]:
    """One warning for each rule that no add in any list includes, by name or through a ruleset.

    A rule counts as included where any list adds it, whether or not that list applies in
    any context.
    """

    included = {
        entry.rule
        for references in manifest.written_lists()
        for entry in expander.expand(references).without_conflicts
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
