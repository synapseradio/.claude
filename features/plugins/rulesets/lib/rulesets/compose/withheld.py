"""Which rules delivery withholds: those whose files carry a pool error."""

from __future__ import annotations

from collections.abc import Mapping

from rulesets.check.findings import RuleSubject
from rulesets.check.pool_check import pool_errors
from rulesets.source.pool import Pool


def withheld(pool: Pool) -> Mapping[str, str]:
    """Each rule with a pool error, with the first error's file and message."""

    found: dict[str, str] = {}
    for error in pool_errors(pool):
        if isinstance(error.subject, RuleSubject):
            found.setdefault(error.subject.name, f"{error.file.name}: {error.message}")
    return found
