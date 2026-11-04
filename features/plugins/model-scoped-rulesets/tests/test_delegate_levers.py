#!/usr/bin/env python3
"""The levers that reroute a delegate's model fact, and the host-managed provider notice.

Serves the person who runs delegates under a forced or inherited model, and the engineer
who builds their facts. Two force levers (`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` and
`CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL`) override the caller's and the
definition's models; the built-in Explore and Plan agents skip the default variable;
Explore under a Fable parent lists the `opus` alias on a direct connection; and a
host-managed provider raises a notice in every kind of resolution.

Run with `python3.14 -m pytest features/plugins/model-scoped-rulesets/tests/test_delegate_levers.py`.
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
PROVIDER_NOTICE = [("provider-variable", HOST_MANAGED)]
PROVIDER_VARIABLES = (
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_MANTLE",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
)
FABLE = "claude-fable-5"


def forced(lever):
    return model_fact.FromForceLever(lever)


class TestAVariableIsSetWhenItsValueIsNonEmptyAndNotAFalseWord:
    @pytest.mark.parametrize("lever", LEVERS)
    @pytest.mark.parametrize("value", ["", "0", "false", "False"])
    def test_a_lever_holding_an_empty_or_false_word_has_no_effect(self, scene, lever, value):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")

        fact = scene.fact(env={lever: value})

        assert fact == model_fact.Claimed("haiku", "haiku", "per-spawn")

    @pytest.mark.parametrize("lever", LEVERS)
    @pytest.mark.parametrize("value", ["1", "true", "True", "yes", "FALSE"])
    def test_a_lever_holding_any_other_word_is_set(self, scene, lever, value):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")

        fact = scene.fact(env={lever: value})

        assert fact.source == forced(lever)

    def test_neither_lever_set_leaves_the_four_sources_in_charge(self, scene):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")

        fact = scene.fact(env={SUBAGENT_FORCE: "0", COORDINATOR_FORCE: ""})

        assert fact == model_fact.Claimed("haiku", "haiku", "per-spawn")


class TestTheSubagentForceVariableOverridesTheCallerAndTheDefinition:
    def test_the_default_variable_names_the_model_over_the_definitions_pin(self, scene):
        scene.parent_runs(OPUS)
        scene.user_agent("scout.md", "name: scout\nmodel: opus")

        fact = scene.fact("scout", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Claimed("haiku", HAIKU, forced(SUBAGENT_FORCE))

    def test_the_caller_is_ignored(self, scene):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")

        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("sonnet", SONNET, forced(SUBAGENT_FORCE))

    def test_a_built_in_pin_is_ignored(self, scene):
        fact = scene.fact("claude-code-guide", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("sonnet", SONNET, forced(SUBAGENT_FORCE))

    def test_an_inherit_pin_is_ignored_too(self, scene):
        scene.parent_runs(OPUS)
        scene.user_agent("helper.md", "name: helper\nmodel: inherit")

        fact = scene.fact("helper", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Claimed("haiku", HAIKU, forced(SUBAGENT_FORCE))

    def test_with_no_default_variable_the_parents_model_stands(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact(env={SUBAGENT_FORCE: "1"})

        assert fact == model_fact.Claimed("opus", OPUS, forced(SUBAGENT_FORCE))

    def test_an_empty_default_variable_yields_to_the_parent(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: ""})

        assert fact == model_fact.Claimed("opus", OPUS, forced(SUBAGENT_FORCE))

    def test_a_default_variable_naming_inherit_yields_to_the_parent(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: "inherit"})

        assert fact == model_fact.Claimed("opus", OPUS, forced(SUBAGENT_FORCE))

    def test_with_no_default_variable_and_no_parent_record_the_model_is_missing(self, scene):
        fact = scene.fact(env={SUBAGENT_FORCE: "1"})

        assert fact == model_fact.Missing()

    def test_a_default_variable_no_declared_name_claims_stands(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: "claude-nova-1"})

        assert fact == model_fact.Unclaimed("claude-nova-1", forced(SUBAGENT_FORCE))

    def test_a_default_variable_alias_resolves_through_its_profile_variable(self, scene):
        env = {
            SUBAGENT_FORCE: "1",
            DEFAULT_VARIABLE: "haiku",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-5",
        }

        assert scene.fact(env=env) == model_fact.Claimed(
            "haiku", "claude-haiku-5", forced(SUBAGENT_FORCE)
        )

    def test_the_callers_spawn_records_are_never_joined(self, scene):
        scene.parent_runs(OPUS)
        scene.caller_names("opus")
        scene.caller_names("haiku")

        resolution = scene.resolve(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: SONNET})

        assert resolution.notices == ()


class TestTheCoordinatorLeverGivesTheDelegateTheParentsModel:
    def test_the_parent_stands_over_the_caller_the_definition_and_the_default_variable(self, scene):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku", agent_type="scout")
        scene.user_agent("scout.md", "name: scout\nmodel: sonnet")

        fact = scene.fact("scout", env={COORDINATOR_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Claimed("opus", OPUS, forced(COORDINATOR_FORCE))

    def test_the_agent_definition_is_never_read(self, scene, definition_reads):
        scene.parent_runs(OPUS)
        scene.user_agent("scout.md", "name: scout\nmodel: sonnet")

        scene.fact("scout", env={COORDINATOR_FORCE: "1"})

        assert definition_reads == []

    def test_with_both_levers_the_coordinator_lever_is_the_source(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact(
            env={COORDINATOR_FORCE: "1", SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU}
        )

        assert fact == model_fact.Claimed("opus", OPUS, forced(COORDINATOR_FORCE))

    def test_with_no_parent_record_the_model_is_missing(self, scene):
        fact = scene.fact(env={COORDINATOR_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Missing()

    def test_an_unclaimed_parent_identifier_stands(self, scene):
        scene.parent_runs("claude-nova-1")

        fact = scene.fact(env={COORDINATOR_FORCE: "1"})

        assert fact == model_fact.Unclaimed("claude-nova-1", forced(COORDINATOR_FORCE))

    def test_explore_under_a_fable_parent_takes_the_parent_too(self, scene):
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", env={COORDINATOR_FORCE: "1"})

        assert fact == model_fact.Claimed("fable", FABLE, forced(COORDINATOR_FORCE))


class TestExploreAndPlanSkipTheDefaultVariable:
    @pytest.mark.parametrize("agent_type", ["Explore", "Plan"])
    def test_the_caller_names_a_model(self, scene, agent_type):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku", agent_type=agent_type)

        fact = scene.fact(agent_type, env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("haiku", "haiku", "per-spawn")

    @pytest.mark.parametrize("agent_type", ["Explore", "Plan"])
    def test_the_default_variable_is_skipped_for_the_parents_model(self, scene, agent_type):
        scene.parent_runs(OPUS)

        fact = scene.fact(agent_type, env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("opus", OPUS, "parent-record")

    @pytest.mark.parametrize("agent_type", ["Explore", "Plan"])
    def test_the_engine_never_reads_the_default_variable_for_them(
        self, scene, read_spy, agent_type
    ):
        scene.parent_runs(OPUS)
        env = read_spy({DEFAULT_VARIABLE: SONNET})

        scene.resolve(agent_type, env=env)

        assert DEFAULT_VARIABLE not in env.reads

    @pytest.mark.parametrize("agent_type", ["Explore", "Plan"])
    def test_with_no_parent_record_the_model_is_missing(self, scene, agent_type):
        assert scene.fact(agent_type, env={DEFAULT_VARIABLE: SONNET}) == model_fact.Missing()

    def test_a_definition_registered_as_explore_makes_it_an_ordinary_agent(self, scene):
        scene.parent_runs(OPUS)
        scene.user_agent("explore.md", "name: Explore")

        fact = scene.fact("Explore", env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("sonnet", SONNET, "subagent-default-variable")

    def test_a_definition_registered_as_explore_pins_its_model(self, scene):
        scene.user_agent("explore.md", "name: Explore\nmodel: haiku")

        assert scene.fact("Explore") == model_fact.Claimed("haiku", "haiku", "definition-pin")

    def test_a_plugin_scoped_agent_of_the_same_name_is_ordinary(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact("kit:Explore", env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("sonnet", SONNET, "subagent-default-variable")


class TestExploreUnderAFableParentListsTheOpusAlias:
    def test_on_a_direct_connection(self, scene):
        scene.parent_runs(FABLE)

        assert scene.fact("Explore") == model_fact.Claimed("opus", "opus", "built-in-pin")

    def test_the_alias_resolves_through_its_profile_variable(self, scene):
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", env={"ANTHROPIC_DEFAULT_OPUS_MODEL": OPUS})

        assert fact == model_fact.Claimed("opus", OPUS, "built-in-pin")

    def test_the_alias_is_an_identifier_that_only_a_declared_name_claims(self, scene):
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", models=["fable"])

        assert fact == model_fact.Unclaimed("opus", "built-in-pin")

    @pytest.mark.parametrize("variable", PROVIDER_VARIABLES)
    def test_each_provider_variable_keeps_the_parents_model(self, scene, variable):
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", env={variable: "1"})

        assert fact == model_fact.Claimed("fable", FABLE, "parent-record")

    @pytest.mark.parametrize("variable", PROVIDER_VARIABLES)
    def test_a_provider_variable_holding_a_false_word_does_not_count(self, scene, variable):
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", env={variable: "0"})

        assert fact == model_fact.Claimed("opus", "opus", "built-in-pin")

    def test_a_gateway_session_that_sets_no_provider_variable_gets_the_alias(self, scene):
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", env={"ANTHROPIC_BASE_URL": "https://gateway.example"})

        assert fact == model_fact.Claimed("opus", "opus", "built-in-pin")

    @pytest.mark.parametrize("identifier", ["claude-fable", "claude-fable-5", "claude-fable[1m]"])
    def test_every_identifier_opening_on_the_prefix_at_a_boundary(self, scene, identifier):
        scene.parent_runs(identifier)

        assert scene.fact("Explore").source == "built-in-pin"

    @pytest.mark.parametrize("identifier", ["claude-fablex", "fable", "claude-opus-5-5"])
    def test_an_identifier_not_opening_on_the_prefix_keeps_the_parents_model(
        self, scene, identifier
    ):
        scene.parent_runs(identifier)

        assert scene.fact("Explore").source == "parent-record"

    def test_plan_under_a_fable_parent_keeps_the_parents_model(self, scene):
        scene.parent_runs(FABLE)

        assert scene.fact("Plan") == model_fact.Claimed("fable", FABLE, "parent-record")

    def test_the_caller_outranks_the_listed_model(self, scene):
        scene.parent_runs(FABLE)
        scene.caller_names("haiku", agent_type="Explore")

        assert scene.fact("Explore") == model_fact.Claimed("haiku", "haiku", "per-spawn")


class TestExploreAndPlanUnderTheSubagentForceVariable:
    def test_explore_takes_the_default_variable(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact("Explore", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Claimed("haiku", HAIKU, forced(SUBAGENT_FORCE))

    def test_explore_with_no_default_variable_takes_the_parents_model(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact("Explore", env={SUBAGENT_FORCE: "1"})

        assert fact == model_fact.Claimed("opus", OPUS, forced(SUBAGENT_FORCE))

    def test_explore_with_no_default_variable_under_a_fable_parent_takes_its_listed_model(
        self, scene
    ):
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", env={SUBAGENT_FORCE: "1"})

        assert fact == model_fact.Claimed("opus", "opus", "built-in-pin")

    def test_plan_with_no_default_variable_under_a_fable_parent_takes_the_parents_model(
        self, scene
    ):
        scene.parent_runs(FABLE)

        fact = scene.fact("Plan", env={SUBAGENT_FORCE: "1"})

        assert fact == model_fact.Claimed("fable", FABLE, forced(SUBAGENT_FORCE))

    def test_a_default_variable_naming_inherit_leaves_explore_its_listed_model(self, scene):
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: "inherit"})

        assert fact == model_fact.Claimed("opus", "opus", "built-in-pin")

    def test_the_default_variable_outranks_explores_listed_model(self, scene):
        scene.parent_runs(FABLE)

        fact = scene.fact("Explore", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("sonnet", SONNET, forced(SUBAGENT_FORCE))


class TestSkillsRunningInSubagents:
    def test_with_no_force_lever_the_four_sources_decide(self, scene):
        scene.parent_runs(OPUS)
        scene.user_agent("skill-runner.md", "name: skill-runner\nmodel: inherit")

        fact = scene.fact("skill-runner", env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("opus", OPUS, "parent-record")

    def test_under_the_force_variable_a_skill_with_an_inherit_model_resolves_by_its_agent_type(
        self, scene
    ):
        # A subagent's start payload carries `agent_id` and `agent_type` only, so the skill's
        # inherit model is out of the engine's sight:
        # https://code.claude.com/docs/en/hooks.md#subagentstart
        scene.parent_runs(OPUS)

        fact = scene.fact("general-purpose", env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact == model_fact.Claimed("haiku", HAIKU, forced(SUBAGENT_FORCE))


class TestAHostManagedProviderDrawsAProviderVariableNotice:
    def test_a_session_resolves_its_alias_and_carries_the_notice(self, tmp_path):
        env = {HOST_MANAGED: "1", "ANTHROPIC_DEFAULT_OPUS_MODEL": OPUS}

        resolution = session_model.resolve_session_model(
            {"model": "opus", "session_id": "s1"}, MODELS, env, tmp_path
        )

        assert resolution.fact == model_fact.Claimed("opus", OPUS, "harness-reported")
        assert [(n.kind, n.subject) for n in resolution.notices] == PROVIDER_NOTICE

    def test_a_switch_carries_the_notice(self):
        resolution = session_model.resolve_switch_model(
            {"to_model": OPUS}, MODELS, {HOST_MANAGED: "1"}
        )

        assert resolution.fact == model_fact.Claimed("opus", OPUS, "switch-target")
        assert [(n.kind, n.subject) for n in resolution.notices] == PROVIDER_NOTICE

    def test_a_delegate_carries_the_notice(self, scene):
        scene.parent_runs(OPUS)

        resolution = scene.resolve(env={HOST_MANAGED: "1"})

        assert resolution.fact == model_fact.Claimed("opus", OPUS, "parent-record")
        assert [(n.kind, n.subject) for n in resolution.notices] == PROVIDER_NOTICE

    def test_the_notice_sits_beside_a_per_spawn_notice(self, scene):
        scene.caller_names("opus")
        scene.caller_names("haiku")

        resolution = scene.resolve(env={HOST_MANAGED: "1"})

        assert sorted(n.kind for n in resolution.notices) == [
            "per-spawn-ambiguous",
            "provider-variable",
        ]

    def test_the_notice_changes_no_fact(self, scene):
        scene.parent_runs(OPUS)

        assert scene.resolve(env={HOST_MANAGED: "1"}).fact == scene.resolve().fact

    @pytest.mark.parametrize("value", ["", "0", "false", "False"])
    def test_a_variable_that_is_not_set_draws_no_notice(self, scene, value):
        assert scene.resolve(env={HOST_MANAGED: value}).notices == ()

    def test_a_session_without_the_variable_draws_no_notice(self, tmp_path):
        resolution = session_model.resolve_session_model({"model": OPUS}, MODELS, {}, tmp_path)

        assert resolution.notices == ()


class TestTheModelFactsSourceNamesWhatDecidedIt:
    def test_a_force_lever_that_decided_a_default_variable_model_is_named(self, scene):
        fact = scene.fact(env={SUBAGENT_FORCE: "1", DEFAULT_VARIABLE: HAIKU})

        assert fact.source == model_fact.FromForceLever("CLAUDE_CODE_SUBAGENT_MODEL_FORCE")

    def test_the_coordinator_lever_is_named_by_its_variable(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact(env={COORDINATOR_FORCE: "true"})

        assert fact.source == model_fact.FromForceLever(
            "CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL"
        )

    def test_the_harness_pin_for_a_built_in_agent_is_named_as_such(self, scene):
        assert scene.fact("claude-code-guide").source == "built-in-pin"
