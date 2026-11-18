#!/usr/bin/env -S uv run --frozen
"""The levers that reroute a delegate's model fact.

Serves the person who runs delegates under a forced or inherited model. Two force levers
(`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` and `CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL`)
override the caller's and the definition's models for every agent type alike, and the built-in
Explore and Plan agents follow the same order as any other type.

Run with `uv run --frozen pytest features/plugins/rulesets/tests/test_delegate_levers.py`.
"""

import pytest
from delivery_world import HAIKU, OPUS
from test_delegate_facts import DEFAULT_VARIABLE, NOVA, SONNET, standing

SUBAGENT_FORCE = "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"
COORDINATOR_FORCE = "CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL"
FABLE = "claude-fable-5"


@pytest.mark.parametrize("lever", [SUBAGENT_FORCE, COORDINATOR_FORCE])
@pytest.mark.parametrize(
    ("value", "is_set"),
    [
        ("", False),
        ("0", False),
        ("false", False),
        ("False", False),
        ("1", True),
        ("true", True),
        ("True", True),
        ("yes", True),
        ("FALSE", True),
    ],
)
def test_a_lever_is_set_when_its_value_is_non_empty_and_not_a_false_word(
    scene, lever, value, is_set
) -> None:
    scene.parent_runs(OPUS)
    scene.caller_names("haiku")

    fact = scene.fact(env={lever: value})

    assert standing(fact) == ((OPUS, "opus") if is_set else ("haiku", "haiku"))


SUBAGENT_FORCE_ROWS = [
    pytest.param(
        lambda s: (s.parent_runs(OPUS), s.user_agent("scout.md", "name: scout\nmodel: opus")),
        "scout",
        {DEFAULT_VARIABLE: HAIKU},
        (HAIKU, "haiku"),
        id="the default variable names the model over the definition's pin",
    ),
    pytest.param(
        lambda s: (s.parent_runs(OPUS), s.caller_names("haiku")),
        "general-purpose",
        {DEFAULT_VARIABLE: SONNET},
        (SONNET, "sonnet"),
        id="the caller's model is ignored",
    ),
    pytest.param(
        lambda s: None,
        "claude-code-guide",
        {DEFAULT_VARIABLE: SONNET},
        (SONNET, "sonnet"),
        id="a built-in pin is ignored",
    ),
    pytest.param(
        lambda s: (
            s.parent_runs(OPUS),
            s.user_agent("helper.md", "name: helper\nmodel: inherit"),
        ),
        "helper",
        {DEFAULT_VARIABLE: HAIKU},
        (HAIKU, "haiku"),
        id="an inherit pin is ignored too",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        "general-purpose",
        {},
        (OPUS, "opus"),
        id="with no default variable the parent's model stands",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        "general-purpose",
        {DEFAULT_VARIABLE: ""},
        (OPUS, "opus"),
        id="an empty default variable yields to the parent",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        "general-purpose",
        {DEFAULT_VARIABLE: "inherit"},
        (OPUS, "opus"),
        id="a default variable naming inherit yields to the parent",
    ),
    pytest.param(
        lambda s: None,
        "general-purpose",
        {},
        (None, None),
        id="with no default variable and no parent record the model is missing",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        "general-purpose",
        {DEFAULT_VARIABLE: NOVA},
        (NOVA, None),
        id="a default variable no declared name claims stands",
    ),
]


@pytest.mark.parametrize(("setup", "agent_type", "env", "expected"), SUBAGENT_FORCE_ROWS)
def test_the_subagent_force_variable_overrides_the_caller_and_the_definition(
    scene, setup, agent_type, env, expected
) -> None:
    setup(scene)

    fact = scene.fact(agent_type, env={SUBAGENT_FORCE: "1", **env})

    assert standing(fact) == expected


COORDINATOR_ROWS = [
    pytest.param(
        lambda s: (
            s.parent_runs(OPUS),
            s.caller_names("haiku", agent_type="scout"),
            s.user_agent("scout.md", "name: scout\nmodel: sonnet"),
        ),
        "scout",
        {COORDINATOR_FORCE: "1", DEFAULT_VARIABLE: HAIKU},
        (OPUS, "opus"),
        id="the parent stands over the caller, the definition, and the default variable",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        "general-purpose",
        {COORDINATOR_FORCE: "1", SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU},
        (OPUS, "opus"),
        id="with both levers the coordinator lever decides",
    ),
    pytest.param(
        lambda s: None,
        "general-purpose",
        {COORDINATOR_FORCE: "1", DEFAULT_VARIABLE: HAIKU},
        (None, None),
        id="with no parent record the model is missing",
    ),
    pytest.param(
        lambda s: s.parent_runs(NOVA),
        "general-purpose",
        {COORDINATOR_FORCE: "1"},
        (NOVA, None),
        id="an unclaimed parent identifier stands",
    ),
    pytest.param(
        lambda s: s.parent_runs(FABLE),
        "Explore",
        {COORDINATOR_FORCE: "1"},
        (FABLE, "fable"),
        id="the built-in Explore agent takes the parent too",
    ),
]


@pytest.mark.parametrize(("setup", "agent_type", "env", "expected"), COORDINATOR_ROWS)
def test_the_coordinator_lever_gives_the_delegate_the_parents_model(
    scene, setup, agent_type, env, expected
) -> None:
    setup(scene)

    fact = scene.fact(agent_type, env=env)

    assert standing(fact) == expected
