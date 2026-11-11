"""The models and flags a condition tests that the config does not declare."""

from __future__ import annotations

import dataclasses

from rulesets.source.condition import Condition, fact_tests
from rulesets.source.config import Config


@dataclasses.dataclass(frozen=True)
class Undeclared:
    """The undeclared model names and flag names a condition tests, once each, in reading order."""

    models: tuple[str, ...]
    flags: tuple[str, ...]

    @property
    def named(self) -> bool:
        return bool(self.models or self.flags)


def undeclared_names(condition: Condition, config: Config) -> Undeclared:
    """The models and flags `condition` tests that `config` does not declare."""

    tests = fact_tests(condition)
    return Undeclared(
        tuple(
            dict.fromkeys(
                test.value
                for test in tests
                if test.fact == "model" and test.value not in config.models
            )
        ),
        tuple(
            dict.fromkeys(
                test.value
                for test in tests
                if test.fact == "flag" and test.value not in config.flags
            )
        ),
    )
