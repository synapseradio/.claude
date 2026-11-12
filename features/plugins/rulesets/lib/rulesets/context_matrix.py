"""The contexts a rulesets directory composes for, and the rules each one receives."""

from __future__ import annotations

import dataclasses
import itertools

from rulesets.compose.composition import compose
from rulesets.facts.named_context import named_context
from rulesets.session.state import SessionState
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.directory import Present, RulesetsDirectory

KINDS = ("session", "delegate")
NONE = "-"


@dataclasses.dataclass(frozen=True)
class Context:
    """One context of the matrix; None leaves that fact absent, or no flag set."""

    kind: str
    model: str | None
    agent: str | None
    flag: str | None
    tool: str | None

    def label(self) -> str:
        return " ".join(
            f"{name}={value or NONE}"
            for name, value in (
                ("kind", self.kind),
                ("model", self.model),
                ("agent", self.agent),
                ("flag", self.flag),
                ("tools", self.tool),
            )
        )


type Received = dict[str, str | None]


def _tested(directory: RulesetsDirectory, fact: str) -> set[str]:
    """The values a `when` condition tests the fact against."""
    if not isinstance(directory.config, Present):
        return set()
    values: set[str] = set()
    for block in directory.config.config.blocks:
        try:
            condition = parse_condition(block.condition)
        except ConditionError:
            continue
        values |= {test.value for test in fact_tests(condition) if test.fact == fact}
    return values


def _declared(directory: RulesetsDirectory) -> tuple[set[str], set[str]]:
    if not isinstance(directory.config, Present):
        return set(), set()
    config = directory.config.config
    return set(config.models), set(config.flags)


def contexts(*directories: RulesetsDirectory) -> list[Context]:
    """The matrix the directories' configs name between them, each fact's values in order."""
    models: set[str] = set()
    flags: set[str] = set()
    agents: set[str] = set()
    tools: set[str] = set()
    for directory in directories:
        declared_models, declared_flags = _declared(directory)
        models |= declared_models
        flags |= declared_flags
        agents |= _tested(directory, "agent")
        tools |= _tested(directory, "tools")

    def with_none(values: set[str]) -> list[str | None]:
        return [None, *sorted(values)]

    return [
        Context(kind, model, agent, flag, tool)
        for kind, model, agent, flag, tool in itertools.product(
            KINDS, with_none(models), with_none(agents), with_none(flags), with_none(tools)
        )
    ]


def received(directory: RulesetsDirectory, context: Context) -> Received:
    """Each rule the context receives, with its variant (None for the default form)."""
    config = directory.config.config if isinstance(directory.config, Present) else None
    facts = named_context(
        context.model,
        context.agent,
        context.kind,
        [context.tool] if context.tool else [],
        [context.flag] if context.flag else [],
        config,
    )
    return {rule.rule: rule.variant for rule in compose(directory, facts, SessionState()).rules}


def form(rule: str, variant: str | None) -> str:
    return f"{rule}@{variant}" if variant else rule
