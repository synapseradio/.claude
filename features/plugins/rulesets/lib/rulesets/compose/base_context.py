"""The base context's composition: the rules `defaults` gives, with no block applied."""

from __future__ import annotations

import dataclasses

from rulesets.compose.composition import Composition, compose
from rulesets.facts.context import ABSENT, Facts
from rulesets.session.state import SessionState
from rulesets.source.directory import Present, RulesetsDirectory

_NO_FACTS = Facts(model=ABSENT, agent=ABSENT, kind=ABSENT, flags=frozenset())


def base_composition(directory: RulesetsDirectory) -> Composition:
    """Compose `defaults` alone, at the variants its list names."""

    match directory.config:
        case Present(config):
            without_blocks = dataclasses.replace(config, blocks=())
            directory = dataclasses.replace(directory, config=Present(without_blocks))
        case _:
            pass
    return compose(directory, _NO_FACTS, SessionState())
