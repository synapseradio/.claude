#!/usr/bin/env python3
"""The levers that reroute a delegate's model fact, and the host-managed provider.

Serves the person who runs delegates under a forced or inherited model, and the engineer
who builds their facts. Two force levers (`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` and
`CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL`) override the caller's and the
definition's models for every agent type alike; the built-in Explore and Plan agents follow
the same order as any other type; and a host-managed provider draws no notice of its own.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_delegate_levers.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.facts.model import fact as model_fact  # noqa: E402  (path must be set first)
from rulesets.facts.model import session as session_model  # noqa: E402
from test_delegate_facts import DEFAULT_VARIABLE, HAIKU, OPUS, SONNET  # noqa: E402

MODELS = ["opus", "sonnet", "haiku", "fable"]
SUBAGENT_FORCE = "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"
COORDINATOR_FORCE = "CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL"
LEVERS = (SUBAGENT_FORCE, COORDINATOR_FORCE)
HOST_MANAGED = "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"
FABLE = "claude-fable-5"


def forced(lever) -> model_fact.FromForceLever:
    return model_fact.FromForceLever(lever)


class TestAVariableIsSetWhenItsValueIsNonEmptyAndNotAFalseWord:
    @pytest.mark.parametrize("lever", LEVERS)
    @pytest.mark.parametrize("value", ["", "0", "false", "False"])
    def test_a_lever_holding_an_empty_or_false_word_has_no_effect(
        self, scene, lever, value
    ) -> None:
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")

        fact = scene.fact(env={lever: value})

        assert fact == model_fact.Claimed("haiku", "haiku", "per-spawn")

    @pytest.mark.parametrize("lever", LEVERS)
    @pytest.mark.parametrize("value", ["1", "true", "True", "yes", "FALSE"])
    def test_a_lever_holding_any_other_word_is_set(self, scene, lever, value) -> None:
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")

        fact = scene.fact(env={lever: value})

        assert fact.source == forced(lever)

    def test_neither_lever_set_leaves_the_four_sources_in_charge(self, scene) -> None:
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")

        fact = scene.fact(env={SUBAGENT_FORCE: "0", COORDINATOR_FORCE: ""})

        assert fact == model_fact.Claimed("haiku", "haiku", "per-spawn")


class TestTheSubagentForceVariableOverridesTheCallerAndTheDefinition:
    def test_the_default_variable_names_the_model_over_the_definitions_pin(self, scene) -> None:
        scene.parent_runs(OPUS)
        scene.user_agent("scout.md", "name: scout\nmodel: opus")

        fact = scene.fact("scout", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Claimed("haiku", HAIKU, forced(SUBAGENT_FORCE))

    def test_the_caller_is_ignored(self, scene) -> None:
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")

        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("sonnet", SONNET, forced(SUBAGENT_FORCE))

    def test_a_built_in_pin_is_ignored(self, scene) -> None:
        fact = scene.fact("claude-code-guide", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("sonnet", SONNET, forced(SUBAGENT_FORCE))

    def test_an_inherit_pin_is_ignored_too(self, scene) -> None:
        scene.parent_runs(OPUS)
        scene.user_agent("helper.md", "name: helper\nmodel: inherit")

        fact = scene.fact("helper", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Claimed("haiku", HAIKU, forced(SUBAGENT_FORCE))

    def test_with_no_default_variable_the_parents_model_stands(self, scene) -> None:
        scene.parent_runs(OPUS)

        fact = scene.fact(env={SUBAGENT_FORCE: "1"})

        assert fact == model_fact.Claimed("opus", OPUS, forced(SUBAGENT_FORCE))

    def test_an_empty_default_variable_yields_to_the_parent(self, scene) -> None:
        scene.parent_runs(OPUS)

        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: ""})

        assert fact == model_fact.Claimed("opus", OPUS, forced(SUBAGENT_FORCE))

    def test_a_default_variable_naming_inherit_yields_to_the_parent(self, scene) -> None:
        scene.parent_runs(OPUS)

        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: "inherit"})

        assert fact == model_fact.Claimed("opus", OPUS, forced(SUBAGENT_FORCE))

    def test_with_no_default_variable_and_no_parent_record_the_model_is_missing(
        self, scene
    ) -> None:
        fact = scene.fact(env={SUBAGENT_FORCE: "1"})

        assert fact == model_fact.Missing()

    def test_a_default_variable_no_declared_name_claims_stands(self, scene) -> None:
        scene.parent_runs(OPUS)

        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: "claude-nova-1"})

        assert fact == model_fact.Unclaimed("claude-nova-1", forced(SUBAGENT_FORCE))

    def test_a_default_variable_alias_is_claimed_as_reported(self, scene) -> None:
        env = {
            SUBAGENT_FORCE: "1",
            DEFAULT_VARIABLE: "haiku",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-5",
        }

        assert scene.fact(env=env) == model_fact.Claimed("haiku", "haiku", forced(SUBAGENT_FORCE))

    def test_the_callers_spawn_records_are_never_joined(self, scene) -> None:
        scene.parent_runs(OPUS)
        scene.caller_names("opus")
        scene.caller_names("haiku")

        resolution = scene.resolve(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: SONNET})

        assert resolution.notices == ()


class TestTheCoordinatorLeverGivesTheDelegateTheParentsModel:
    def test_the_parent_stands_over_the_caller_the_definition_and_the_default_variable(
        self, scene
    ) -> None:
        scene.parent_runs(OPUS)
        scene.caller_names("haiku", agent_type="scout")
        scene.user_agent("scout.md", "name: scout\nmodel: sonnet")

        fact = scene.fact("scout", env={COORDINATOR_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Claimed("opus", OPUS, forced(COORDINATOR_FORCE))

    def test_the_agent_definition_is_never_read(self, scene, definition_reads) -> None:
        scene.parent_runs(OPUS)
        scene.user_agent("scout.md", "name: scout\nmodel: sonnet")

        scene.fact("scout", env={COORDINATOR_FORCE: "1"})

        assert definition_reads == []

    def test_with_both_levers_the_coordinator_lever_is_the_source(self, scene) -> None:
        scene.parent_runs(OPUS)

        fact = scene.fact(
            env={COORDINATOR_FORCE: "1", SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU}
        )

        assert fact == model_fact.Claimed("opus", OPUS, forced(COORDINATOR_FORCE))

    def test_with_no_parent_record_the_model_is_missing(self, scene) -> None:
        fact = scene.fact(env={COORDINATOR_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Missing()

    def test_an_unclaimed_parent_identifier_stands(self, scene) -> None:
        scene.parent_runs("claude-nova-1")

        fact = scene.fact(env={COORDINATOR_FORCE: "1"})

        assert fact == model_fact.Unclaimed("claude-nova-1", forced(COORDINATOR_FORCE))

    def test_explore_under_a_fable_parent_takes_the_parent_too(self, scene) -> None:
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", env={COORDINATOR_FORCE: "1"})

        assert fact == model_fact.Claimed("fable", FABLE, forced(COORDINATOR_FORCE))


class TestSkillsRunningInSubagents:
    def test_with_no_force_lever_the_four_sources_decide(self, scene) -> None:
        scene.parent_runs(OPUS)
        scene.user_agent("skill-runner.md", "name: skill-runner\nmodel: inherit")

        fact = scene.fact("skill-runner", env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("opus", OPUS, "parent-record")

    def test_under_the_force_variable_a_skill_with_an_inherit_model_resolves_by_its_agent_type(
        self, scene
    ) -> None:
        # A subagent's start payload carries `agent_id` and `agent_type` only, so the skill's
        # inherit model is out of the engine's sight:
        # https://code.claude.com/docs/en/hooks.md#subagentstart
        scene.parent_runs(OPUS)

        fact = scene.fact("general-purpose", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Claimed("haiku", HAIKU, forced(SUBAGENT_FORCE))


class TestAHostManagedProviderDrawsNoNoticeOfItsOwn:
    def test_a_session_resolves_its_reported_model_with_no_notice(self, tmp_path) -> None:
        resolution = session_model.resolve_session_model(
            {"model": OPUS, "session_id": "s1"}, MODELS, {HOST_MANAGED: "1"}, tmp_path
        )

        assert resolution.fact == model_fact.Claimed("opus", OPUS, "harness-reported")
        assert resolution.notices == ()

    def test_a_delegate_resolves_with_no_notice(self, scene) -> None:
        scene.parent_runs(OPUS)

        resolution = scene.resolve(env={HOST_MANAGED: "1"})

        assert resolution.fact == model_fact.Claimed("opus", OPUS, "parent-record")
        assert resolution.notices == ()

    def test_a_delegate_keeps_the_per_spawn_notice_alone(self, scene) -> None:
        scene.caller_names("opus")
        scene.caller_names("haiku")

        resolution = scene.resolve(env={HOST_MANAGED: "1"}, agent_id=None)

        assert [n.kind for n in resolution.notices] == ["per-spawn-ambiguous"]


class TestTheModelFactsSourceNamesWhatDecidedIt:
    def test_a_force_lever_that_decided_a_default_variable_model_is_named(self, scene) -> None:
        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact.source == model_fact.FromForceLever("CLAUDE_CODE_SUBAGENT_MODEL_FORCE")

    def test_the_coordinator_lever_is_named_by_its_variable(self, scene) -> None:
        scene.parent_runs(OPUS)

        fact = scene.fact(env={COORDINATOR_FORCE: "true"})

        assert fact.source == model_fact.FromForceLever(
            "CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL"
        )

    def test_the_harness_pin_for_a_built_in_agent_is_named_as_such(self, scene) -> None:
        assert scene.fact("claude-code-guide").source == "built-in-pin"
