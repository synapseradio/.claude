#!/usr/bin/env python3
"""A delegate's model fact comes from the first of four sources that names a string.

Serves the person who spawns delegates (`docs/delivery.md`, "What it delivers, and to whom"):
the model the caller named for the spawn, the agent definition's pin, the
`CLAUDE_CODE_SUBAGENT_MODEL` default variable, then the parent session's recorded identifier.
The caller's model joins the delegate's start on `prompt_id` and agent type, and each delegate
takes the oldest spawn of its type that no earlier delegate took, and keeps it when resumed.
Agent definitions, spawn records, and the parent's record sit under `tmp_path`, and the
environment reaches each case as a mapping.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_delegate_facts.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.facts.model import fact as model_fact  # noqa: E402

OPUS = "claude-opus-5-5"
SONNET = "claude-sonnet-5"
HAIKU = "claude-haiku-4-5"
NOVA = "claude-nova-1"
DEFAULT_VARIABLE = "CLAUDE_CODE_SUBAGENT_MODEL"


def standing(fact) -> tuple[str | None, str | None]:
    """The identifier a fact holds and the declared name that claims it, `None` where absent."""
    return getattr(fact, "identifier", None), model_fact.claimed_name(fact)


def under_project(scene) -> dict[str, str]:
    """The start's working directory, one folder below the project root."""
    return {"cwd": str(scene.project / "sub")}


SOURCE_ORDER = [
    pytest.param(
        lambda s: (s.parent_runs(OPUS), s.caller_names("haiku")),
        {},
        ("haiku", "haiku"),
        id="the caller names a model",
    ),
    pytest.param(
        lambda s: s.user_agent("scout.md", "name: scout\nmodel: haiku"),
        {"agent_type": "scout"},
        ("haiku", "haiku"),
        id="only the definition pins a model",
    ),
    pytest.param(
        lambda s: s.user_agent("scout.md", "name: scout\nmodel: haiku"),
        {"agent_type": "scout", "env": {DEFAULT_VARIABLE: SONNET}},
        ("haiku", "haiku"),
        id="the definition outranks the default variable",
    ),
    pytest.param(
        lambda s: None,
        {"env": {DEFAULT_VARIABLE: SONNET}},
        (SONNET, "sonnet"),
        id="only the default variable names a model",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        {},
        (OPUS, "opus"),
        id="no source but the parent",
    ),
    pytest.param(lambda s: None, {}, (None, None), id="the parent has no recorded model"),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        {"session_id": None},
        (None, None),
        id="a start with no session id has no parent to read",
    ),
    pytest.param(
        lambda s: (
            s.parent_runs(OPUS),
            s.caller_names("haiku"),
            s.user_agent("general-purpose.md", "model: sonnet"),
        ),
        {"env": {DEFAULT_VARIABLE: OPUS}},
        ("haiku", "haiku"),
        id="the caller outranks every later source",
    ),
    pytest.param(
        lambda s: (
            s.caller_names(NOVA, agent_type="scout"),
            s.user_agent("scout.md", "name: scout\nmodel: haiku"),
        ),
        {"agent_type": "scout"},
        (NOVA, None),
        id="an identifier no declared name claims stands over the definition",
    ),
    pytest.param(
        lambda s: s.user_agent("scout.md", f"name: scout\nmodel: {NOVA}"),
        {"agent_type": "scout", "env": {DEFAULT_VARIABLE: SONNET}},
        (NOVA, None),
        id="an unclaimed definition pin stands over the default variable",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        {"env": {DEFAULT_VARIABLE: NOVA}},
        (NOVA, None),
        id="an unclaimed default variable stands over the parent",
    ),
    pytest.param(
        lambda s: s.parent_runs(NOVA),
        {},
        (NOVA, None),
        id="an unclaimed parent identifier stands",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        {"env": {DEFAULT_VARIABLE: ""}},
        (OPUS, "opus"),
        id="an empty default variable yields to the parent",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        {"env": {DEFAULT_VARIABLE: "inherit"}},
        (OPUS, "opus"),
        id="a default variable naming inherit yields to the parent",
    ),
    pytest.param(
        lambda s: None,
        {"env": {DEFAULT_VARIABLE: "inherit"}},
        (None, None),
        id="a default variable naming inherit leaves the model missing with no parent",
    ),
    pytest.param(
        lambda s: (s.parent_runs(OPUS), s.user_agent("helper.md", "name: helper\nmodel: inherit")),
        {"agent_type": "helper", "env": {DEFAULT_VARIABLE: SONNET}},
        (OPUS, "opus"),
        id="a definition pinning inherit takes the parent ahead of the default variable",
    ),
    pytest.param(
        lambda s: s.user_agent("helper.md", "name: helper\nmodel: inherit"),
        {"agent_type": "helper", "env": {DEFAULT_VARIABLE: SONNET}},
        (None, None),
        id="a definition pinning inherit leaves the model missing with no parent",
    ),
    pytest.param(
        lambda s: (
            s.parent_runs(OPUS),
            s.caller_names("haiku", agent_type="helper"),
            s.user_agent("helper.md", "name: helper\nmodel: inherit"),
        ),
        {"agent_type": "helper"},
        ("haiku", "haiku"),
        id="the caller outranks an inherit pin",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        {"agent_type": "claude-code-guide"},
        ("haiku", "haiku"),
        id="a built-in agent with no definition takes the harness pin",
    ),
    pytest.param(
        lambda s: s.parent_runs(OPUS),
        {"agent_type": "statusline-setup"},
        ("sonnet", "sonnet"),
        id="another built-in agent takes its own harness pin",
    ),
    pytest.param(
        lambda s: None,
        {"agent_type": "claude-code-guide", "env": {DEFAULT_VARIABLE: SONNET}},
        ("haiku", "haiku"),
        id="the built-in pin is read ahead of the default variable",
    ),
    pytest.param(
        lambda s: s.caller_names("opus", agent_type="claude-code-guide"),
        {"agent_type": "claude-code-guide"},
        ("opus", "opus"),
        id="the caller outranks the built-in pin",
    ),
    pytest.param(
        lambda s: (s.parent_runs(OPUS), s.user_agent("setup.md", "name: statusline-setup")),
        {"agent_type": "statusline-setup"},
        (OPUS, "opus"),
        id="a definition naming no model hides the built-in pin",
    ),
    pytest.param(
        lambda s: s.user_agent("guide.md", "name: claude-code-guide\nmodel: opus"),
        {"agent_type": "claude-code-guide"},
        ("opus", "opus"),
        id="a definition naming a model replaces the built-in pin",
    ),
    pytest.param(
        lambda s: None,
        {"agent_type": "kit:claude-code-guide"},
        (None, None),
        id="a plugin-scoped type of the same name takes no built-in pin",
    ),
    pytest.param(
        lambda s: None,
        {"agent_type": "general-purpose"},
        (None, None),
        id="a type the harness pins nothing for takes no built-in pin",
    ),
    pytest.param(
        lambda s: (s.parent_runs(OPUS), s.caller_names("haiku", prompt_id=None)),
        {"prompt_id": None},
        (OPUS, "opus"),
        id="a start with no prompt id takes no caller model",
    ),
]


@pytest.mark.parametrize(("setup", "start", "expected"), SOURCE_ORDER)
def test_a_delegates_model_comes_from_the_first_source_that_names_one(
    scene, setup, start, expected
) -> None:
    setup(scene)
    agent_type = start.pop("agent_type", "general-purpose")

    assert standing(scene.fact(agent_type, **start)) == expected


DEFINITION_LOCATIONS = [
    pytest.param(
        lambda s: s.user_agent("other.md", "name: scout\nmodel: haiku"),
        {},
        "haiku",
        id="a definition registers under its name field",
    ),
    pytest.param(
        lambda s: s.user_agent("team/scout.md", "name: scout\nmodel: haiku"),
        {},
        "haiku",
        id="a definition in a subfolder of the user directory is found",
    ),
    pytest.param(
        lambda s: (
            s.project_agent("scout.md", "name: scout\nmodel: haiku"),
            s.user_agent("scout.md", "name: scout\nmodel: sonnet"),
        ),
        under_project,
        "haiku",
        id="a project definition outranks a user definition",
    ),
    pytest.param(
        lambda s: (
            s.project_agent("scout.md", "name: scout\nmodel: sonnet"),
            s.project_agent("s.md", "name: scout\nmodel: haiku", under=s.project / "sub"),
        ),
        under_project,
        "haiku",
        id="the project definition closest to the working directory wins",
    ),
    pytest.param(
        lambda s: (
            s.parent_runs(OPUS),
            s.project_agent("scout.md", "name: scout"),
            s.user_agent("scout.md", "name: scout\nmodel: haiku"),
        ),
        under_project,
        "opus",
        id="a project definition naming no model hides a user pin",
    ),
    pytest.param(
        lambda s: s.project_agent("scout.md", "name: scout\nmodel: haiku", under=s.project.parent),
        under_project,
        None,
        id="a definition above the repository root is not read",
    ),
    pytest.param(
        lambda s: (
            s.project_agent("scout.md", "name: scout\nmodel: sonnet"),
            s.user_agent("scout.md", "name: scout\nmodel: haiku"),
        ),
        {},
        "haiku",
        id="a start carrying no working directory reads the user directory alone",
    ),
    pytest.param(
        lambda s: (
            s.define(s.install_plugin() / "agents", "rev.md", "name: reviewer\nmodel: sonnet"),
            s.user_agent("reviewer.md", "name: reviewer\nmodel: haiku"),
        ),
        {"agent_type": "kit:reviewer"},
        "sonnet",
        id="a plugin-scoped type reads that plugin's agents directory",
    ),
    pytest.param(
        lambda s: s.define(
            s.install_plugin() / "agents" / "review", "sec.md", "name: security\nmodel: haiku"
        ),
        {"agent_type": "kit:review:security"},
        "haiku",
        id="a plugin-scoped type in a subfolder names the subfolder",
    ),
    pytest.param(
        lambda s: s.user_agent("reviewer.md", "name: reviewer\nmodel: haiku"),
        {"agent_type": "kit:reviewer"},
        None,
        id="a plugin that is not installed pins nothing",
    ),
]


@pytest.mark.parametrize(("setup", "start", "claimed_by"), DEFINITION_LOCATIONS)
def test_a_delegates_pin_comes_from_the_definition_the_harness_would_load(
    scene, setup, start, claimed_by
) -> None:
    setup(scene)
    arguments = start(scene) if callable(start) else dict(start)
    agent_type = arguments.pop("agent_type", "scout")

    fact = scene.fact(agent_type, **arguments)

    assert model_fact.claimed_name(fact) == claimed_by


class TestSeveralSpawnsOfOneTypeNamingDifferentModels:
    def test_each_delegate_takes_the_oldest_spawn_no_earlier_delegate_took(self, scene) -> None:
        scene.parent_runs(SONNET)
        scene.caller_names("haiku")
        scene.caller_names("opus")

        first = scene.resolve(agent_id="a1")
        second = scene.resolve(agent_id="a2")

        assert (standing(first.fact), standing(second.fact)) == (
            ("haiku", "haiku"),
            ("opus", "opus"),
        )
        assert (first.notices, second.notices) == ((), ())

    def test_a_resumed_delegate_keeps_the_spawn_it_took_first(self, scene) -> None:
        scene.caller_names("haiku")
        scene.caller_names("opus")

        first = scene.resolve(agent_id="a1")
        again = scene.resolve(agent_id="a1")
        second = scene.resolve(agent_id="a2")

        assert [standing(each.fact)[1] for each in (first, again, second)] == [
            "haiku",
            "haiku",
            "opus",
        ]

    def test_starts_arriving_out_of_spawn_order_take_each_others_models_with_no_notice(
        self, scene
    ) -> None:
        scene.caller_names("haiku")
        scene.caller_names("opus")

        spawned_second = scene.resolve(agent_id="a2")
        spawned_first = scene.resolve(agent_id="a1")

        assert standing(spawned_second.fact)[1] == "haiku"
        assert standing(spawned_first.fact)[1] == "opus"
        assert (spawned_second.notices, spawned_first.notices) == ((), ())

    def test_a_start_finding_every_matching_spawn_taken_yields_to_the_pin_with_an_ambiguity_notice(
        self, scene
    ) -> None:
        scene.parent_runs(OPUS)
        scene.caller_names("opus")
        scene.caller_names("haiku")
        scene.user_agent("general-purpose.md", "model: sonnet")
        scene.resolve(agent_id="a1")
        scene.resolve(agent_id="a2")

        third = scene.resolve(agent_id="a3")

        assert standing(third.fact) == ("sonnet", "sonnet")
        assert [notice.kind for notice in third.notices] == ["per-spawn-ambiguous"]

    def test_a_start_carrying_no_agent_id_yields_to_the_parent_with_an_ambiguity_notice(
        self, scene
    ) -> None:
        scene.parent_runs(OPUS)
        scene.caller_names("opus")
        scene.caller_names("haiku")

        resolution = scene.resolve(agent_id=None)

        assert standing(resolution.fact) == (OPUS, "opus")
        assert [notice.kind for notice in resolution.notices] == ["per-spawn-ambiguous"]


class TestSpawnsOfOneModelOrOfOtherTypes:
    def test_spawns_of_one_type_naming_one_model_resolve_to_it_with_no_notice(self, scene) -> None:
        scene.caller_names("haiku")
        scene.caller_names("haiku")

        resolution = scene.resolve()

        assert standing(resolution.fact) == ("haiku", "haiku")
        assert resolution.notices == ()

    def test_a_spawn_naming_haiku_before_one_naming_no_model_gives_the_first_start_haiku(
        self, scene
    ) -> None:
        scene.caller_names("haiku")
        scene.caller_names(None)

        resolution = scene.resolve()

        assert standing(resolution.fact) == ("haiku", "haiku")
        assert resolution.notices == ()

    def test_spawns_of_different_types_each_resolve_from_their_own_record(self, scene) -> None:
        scene.caller_names("opus", agent_type="critic")
        scene.caller_names("haiku", agent_type="auditor")

        assert standing(scene.fact("critic", agent_id="a1"))[1] == "opus"
        assert standing(scene.fact("auditor", agent_id="a2"))[1] == "haiku"

    def test_no_record_matching_the_prompt_session_and_type_leaves_the_pin_in_charge(
        self, scene
    ) -> None:
        scene.caller_names("opus", prompt_id="other-prompt")
        scene.caller_names("opus", session="other-session")
        scene.caller_names("opus", agent_type="critic")
        scene.user_agent("general-purpose.md", "model: haiku")

        resolution = scene.resolve()

        assert standing(resolution.fact) == ("haiku", "haiku")
        assert resolution.notices == ()
