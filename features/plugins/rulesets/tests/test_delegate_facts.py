#!/usr/bin/env python3
"""A delegate's model fact comes from the first of four sources that names a string.

Serves the person who spawns delegates and the engineer who builds their facts: the
model the caller named for the spawn, the agent definition's pin, the
`CLAUDE_CODE_SUBAGENT_MODEL` default variable, then the parent session's recorded
identifier. This is the harness's own order. The caller's model joins the delegate's
start on `prompt_id` and agent type. Agent definitions, spawn records, and the parent's
record sit under `tmp_path`, and the environment reaches each case as a mapping.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_delegate_facts.py`.
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
DEFAULT_VARIABLE = "CLAUDE_CODE_SUBAGENT_MODEL"
SEPARATE_MECHANISM_VARIABLES = (
    "CLAUDE_CODE_AUTO_MODE_MODEL",
    "CLAUDE_CODE_BG_CLASSIFIER_MODEL",
    "CLAUDE_CONTEXT_COLLAPSE_MODEL",
)


class TestADelegatesModelFactComesFromFourSourcesInOrder:
    def test_the_caller_names_a_model(self, scene):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")

        assert scene.fact() == model_fact.Claimed("haiku", "haiku", "per-spawn")

    def test_only_the_definition_pins_a_model(self, scene):
        scene.user_agent("scout.md", "name: scout\nmodel: haiku")

        assert scene.fact("scout") == model_fact.Claimed("haiku", "haiku", "definition-pin")

    def test_the_definition_outranks_the_default_variable(self, scene):
        scene.user_agent("scout.md", "name: scout\nmodel: haiku")

        fact = scene.fact("scout", env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("haiku", "haiku", "definition-pin")

    def test_only_the_default_variable_names_a_model(self, scene):
        fact = scene.fact(env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("sonnet", SONNET, "subagent-default-variable")

    def test_no_source_but_the_parent(self, scene):
        scene.parent_runs(OPUS)

        assert scene.fact() == model_fact.Claimed("opus", OPUS, "parent-record")

    def test_the_parent_has_no_recorded_model_fact(self, scene):
        fact = scene.fact()

        assert fact == model_fact.Missing()
        assert fact.source == "no-identifier"

    def test_a_delegate_start_with_no_session_id_has_no_parent_to_read(self, scene):
        scene.parent_runs(OPUS)

        assert scene.fact(session_id=None) == model_fact.Missing()

    def test_the_caller_outranks_every_later_source(self, scene):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku")
        scene.user_agent("general-purpose.md", "model: sonnet")

        fact = scene.fact(env={DEFAULT_VARIABLE: OPUS})

        assert model_fact.claimed_name(fact) == "haiku"

    def test_the_caller_names_an_identifier_no_declared_name_claims(self, scene):
        scene.caller_names("claude-nova-1", agent_type="scout")
        scene.user_agent("scout.md", "name: scout\nmodel: haiku")

        assert scene.fact("scout") == model_fact.Unclaimed("claude-nova-1", "per-spawn")

    def test_an_unclaimed_definition_pin_stands_over_the_default_variable(self, scene):
        scene.user_agent("scout.md", "name: scout\nmodel: claude-nova-1")

        fact = scene.fact("scout", env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Unclaimed("claude-nova-1", "definition-pin")

    def test_an_unclaimed_default_variable_stands_over_the_parent(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact(env={DEFAULT_VARIABLE: "claude-nova-1"})

        assert fact == model_fact.Unclaimed("claude-nova-1", "subagent-default-variable")

    def test_an_unclaimed_parent_identifier_stands(self, scene):
        scene.parent_runs("claude-nova-1")

        assert scene.fact() == model_fact.Unclaimed("claude-nova-1", "parent-record")

    def test_a_caller_alias_is_claimed_as_reported(self, scene):
        scene.caller_names("haiku")

        fact = scene.fact(env={"ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-5"})

        assert fact == model_fact.Claimed("haiku", "haiku", "per-spawn")

    def test_a_definition_alias_is_claimed_as_reported(self, scene):
        scene.user_agent("scout.md", "name: scout\nmodel: sonnet")

        fact = scene.fact("scout", env={"ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-6"})

        assert fact == model_fact.Claimed("sonnet", "sonnet", "definition-pin")

    def test_a_caller_model_that_is_not_a_string_ends_the_search_with_a_missing_model(self, scene):
        scene.caller_names(5, agent_type="scout")
        scene.user_agent("scout.md", "name: scout\nmodel: haiku")

        assert scene.fact("scout") == model_fact.Missing(model_fact.NotAString(5, "per-spawn"))

    def test_a_definition_model_that_is_not_a_string_ends_the_search_with_a_missing_model(
        self, scene
    ):
        scene.user_agent("scout.md", "name: scout\nmodel: 123")
        scene.parent_runs(OPUS)

        fact = scene.fact("scout", env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Missing(model_fact.NotAString(123, "definition-pin"))

    def test_an_empty_default_variable_yields_to_the_parent(self, scene):
        scene.parent_runs(OPUS)

        assert scene.fact(env={DEFAULT_VARIABLE: ""}).source == "parent-record"


class TestTheDefinitionIsReadOnlyWhereTheSearchReachesIt:
    def test_the_caller_naming_a_model_ends_the_search_ahead_of_the_definition(
        self, scene, definition_reads
    ):
        scene.caller_names("haiku", agent_type="scout")
        scene.user_agent("scout.md", "name: scout\nmodel: sonnet")

        scene.fact("scout")

        assert definition_reads == []

    def test_a_caller_naming_nothing_sends_the_search_to_the_definition(
        self, scene, definition_reads
    ):
        scene.user_agent("scout.md", "name: scout\nmodel: sonnet")

        scene.fact("scout")

        assert definition_reads == ["scout"]


class TestTheCallersModelJoinsByPromptAndAgentType:
    def test_two_spawns_of_one_type_naming_one_model_resolve_to_it(self, scene):
        scene.caller_names("haiku")
        scene.caller_names("haiku")

        resolution = scene.resolve()

        assert resolution.fact == model_fact.Claimed("haiku", "haiku", "per-spawn")
        assert resolution.notices == ()

    def test_two_spawns_of_one_type_naming_different_models_leave_the_source_yielding(self, scene):
        scene.parent_runs(OPUS)
        scene.caller_names("opus")
        scene.caller_names("haiku")
        scene.user_agent("general-purpose.md", "model: sonnet")

        resolution = scene.resolve()

        assert resolution.fact == model_fact.Claimed("sonnet", "sonnet", "definition-pin")
        assert [notice.kind for notice in resolution.notices] == ["per-spawn-ambiguous"]

    def test_each_of_the_two_delegates_resolves_from_the_next_source_and_carries_the_notice(
        self, scene
    ):
        scene.parent_runs(OPUS)
        scene.caller_names("opus")
        scene.caller_names("haiku")

        first = scene.resolve(agent_id="a1")
        second = scene.resolve(agent_id="a2")

        assert first == second
        assert first.fact == model_fact.Claimed("opus", OPUS, "parent-record")
        assert [notice.kind for notice in first.notices] == ["per-spawn-ambiguous"]

    def test_the_ambiguity_notice_names_the_models_the_records_disagree_on(self, scene):
        scene.caller_names("opus")
        scene.caller_names("haiku")

        (notice,) = scene.resolve().notices

        assert notice.subject == "opus, haiku"

    def test_two_spawns_of_different_types_each_resolve_from_their_own_record(self, scene):
        scene.caller_names("opus", agent_type="critic")
        scene.caller_names("haiku", agent_type="auditor")

        assert model_fact.claimed_name(scene.fact("critic")) == "opus"
        assert model_fact.claimed_name(scene.fact("auditor")) == "haiku"

    def test_no_record_matching_the_pair_leaves_the_source_yielding_to_the_definition(self, scene):
        scene.caller_names("opus", prompt_id="other-prompt")
        scene.caller_names("opus", session="other-session")
        scene.caller_names("opus", agent_type="critic")
        scene.user_agent("general-purpose.md", "model: haiku")

        resolution = scene.resolve()

        assert resolution.fact == model_fact.Claimed("haiku", "haiku", "definition-pin")
        assert resolution.notices == ()


class TestAnUnreadableStartPayloadYieldsThePerSpawnModel:
    @pytest.mark.parametrize("field", ["session_id", "prompt_id", "agent_type"])
    def test_a_start_lacking_one_field_carries_the_unreadable_notice(self, scene, field):
        scene.user_agent("general-purpose.md", "model: haiku")

        resolution = scene.resolve(**{field: None})

        assert [(n.kind, n.subject) for n in resolution.notices] == [
            ("per-spawn-unreadable", field)
        ]

    def test_the_identifier_comes_from_the_definition_then_the_default_variable_then_the_parent(
        self, scene
    ):
        scene.parent_runs(OPUS)
        env = {DEFAULT_VARIABLE: SONNET}
        scene.user_agent("general-purpose.md", "model: haiku")

        by_definition = scene.resolve(prompt_id=None, env=env)
        (scene.config / "agents" / "general-purpose.md").unlink()
        by_default = scene.resolve(prompt_id=None, env=env)
        by_parent = scene.resolve(prompt_id=None)

        assert by_definition.fact.source == "definition-pin"
        assert by_default.fact.source == "subagent-default-variable"
        assert by_parent.fact.source == "parent-record"
        assert all(
            [n.kind for n in each.notices] == ["per-spawn-unreadable"]
            for each in (by_definition, by_default, by_parent)
        )

    def test_a_record_written_with_no_prompt_id_is_not_joined_to_a_start_with_none(self, scene):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku", prompt_id=None)

        resolution = scene.resolve(prompt_id=None)

        assert resolution.fact.source == "parent-record"

    def test_a_readable_start_carries_no_unreadable_notice(self, scene):
        assert scene.resolve().notices == ()


class TestTheDefaultVariableNamingInheritCountsAsUnset:
    def test_the_parents_model_stands_where_no_other_source_names_one(self, scene):
        scene.parent_runs(OPUS)

        fact = scene.fact(env={DEFAULT_VARIABLE: "inherit"})

        assert fact == model_fact.Claimed("opus", OPUS, "parent-record")

    def test_with_no_parent_record_the_model_is_missing(self, scene):
        assert scene.fact(env={DEFAULT_VARIABLE: "inherit"}) == model_fact.Missing()


class TestTheDefinitionIsLocatedByAgentType:
    def test_a_definition_registers_under_its_name_field(self, scene):
        scene.user_agent("other.md", "name: scout\nmodel: haiku")

        assert model_fact.claimed_name(scene.fact("scout")) == "haiku"

    def test_a_definition_naming_nothing_registers_under_its_filename(self, scene):
        scene.user_agent("scout.md", "model: haiku")

        assert model_fact.claimed_name(scene.fact("scout")) == "haiku"

    def test_a_definition_in_a_subfolder_of_the_user_directory_is_found(self, scene):
        scene.user_agent("team/scout.md", "name: scout\nmodel: haiku")

        assert model_fact.claimed_name(scene.fact("scout")) == "haiku"

    def test_the_first_file_registered_under_the_type_wins(self, scene):
        scene.user_agent("a.md", "name: scout\nmodel: haiku")
        scene.user_agent("b.md", "name: scout\nmodel: sonnet")

        assert model_fact.claimed_name(scene.fact("scout")) == "haiku"

    def test_a_project_definition_and_a_user_definition(self, scene):
        scene.project_agent("scout.md", "name: scout\nmodel: haiku")
        scene.user_agent("scout.md", "name: scout\nmodel: sonnet")

        fact = scene.fact("scout", cwd=str(scene.project / "sub"))

        assert model_fact.claimed_name(fact) == "haiku"

    def test_the_project_definition_closest_to_the_working_directory_wins(self, scene):
        scene.project_agent("scout.md", "name: scout\nmodel: sonnet")
        scene.project_agent("s.md", "name: scout\nmodel: haiku", under=scene.project / "sub")

        fact = scene.fact("scout", cwd=str(scene.project / "sub"))

        assert model_fact.claimed_name(fact) == "haiku"

    def test_a_project_definition_naming_no_model_hides_a_user_pin(self, scene):
        scene.parent_runs(OPUS)
        scene.project_agent("scout.md", "name: scout")
        scene.user_agent("scout.md", "name: scout\nmodel: haiku")

        fact = scene.fact("scout", cwd=str(scene.project))

        assert fact == model_fact.Claimed("opus", OPUS, "parent-record")

    def test_a_definition_above_the_repository_root_is_not_read(self, scene):
        above = scene.project.parent
        scene.project_agent("scout.md", "name: scout\nmodel: haiku", under=above)

        assert scene.fact("scout", cwd=str(scene.project / "sub")) == model_fact.Missing()

    def test_a_working_directory_outside_any_repository_reads_only_itself(self, tmp_path, scene):
        loose = tmp_path / "loose" / "deeper"
        loose.mkdir(parents=True)
        scene.project_agent("scout.md", "name: scout\nmodel: sonnet", under=loose.parent)

        assert scene.fact("scout", cwd=str(loose)) == model_fact.Missing()

    def test_a_start_carrying_no_working_directory_reads_the_user_directory_alone(self, scene):
        scene.project_agent("scout.md", "name: scout\nmodel: sonnet")
        scene.user_agent("scout.md", "name: scout\nmodel: haiku")

        assert model_fact.claimed_name(scene.fact("scout")) == "haiku"

    def test_a_file_whose_frontmatter_does_not_parse_registers_nothing(self, scene):
        scene.parent_runs(OPUS)
        scene.user_agent("scout.md", "name: [unclosed")

        assert scene.fact("scout").source == "parent-record"

    def test_a_plugin_scoped_type_reads_that_plugins_agents_directory(self, scene):
        install = scene.install_plugin()
        scene.define(install / "agents", "rev.md", "name: reviewer\nmodel: sonnet")
        scene.user_agent("reviewer.md", "name: reviewer\nmodel: haiku")

        assert model_fact.claimed_name(scene.fact("kit:reviewer")) == "sonnet"

    def test_a_plugin_scoped_type_in_a_subfolder_names_the_subfolder(self, scene):
        install = scene.install_plugin()
        scene.define(install / "agents" / "review", "sec.md", "name: security\nmodel: haiku")

        assert model_fact.claimed_name(scene.fact("kit:review:security")) == "haiku"
        assert scene.fact("kit:security") == model_fact.Missing()

    def test_a_plugin_definition_with_no_name_goes_by_its_filename(self, scene):
        install = scene.install_plugin()
        scene.define(install / "agents", "rev.md", "model: opus")

        assert model_fact.claimed_name(scene.fact("kit:rev")) == "opus"

    def test_a_plugin_that_is_not_installed_pins_nothing(self, scene):
        scene.user_agent("reviewer.md", "name: reviewer\nmodel: haiku")

        assert scene.fact("kit:reviewer") == model_fact.Missing()


class TestAPinOfInheritAndTheHarnessBuiltInPins:
    def test_the_definition_pins_inherit(self, scene):
        scene.parent_runs(OPUS)
        scene.user_agent("helper.md", "name: helper\nmodel: inherit")

        fact = scene.fact("helper", env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("opus", OPUS, "parent-record")

    def test_an_inherit_pin_with_no_recorded_parent_leaves_the_model_missing(self, scene):
        scene.user_agent("helper.md", "name: helper\nmodel: inherit")

        assert scene.fact("helper", env={DEFAULT_VARIABLE: SONNET}) == model_fact.Missing()

    def test_the_caller_outranks_an_inherit_pin(self, scene):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku", agent_type="helper")
        scene.user_agent("helper.md", "name: helper\nmodel: inherit")

        assert model_fact.claimed_name(scene.fact("helper")) == "haiku"

    @pytest.mark.parametrize(
        ("agent_type", "alias"), [("claude-code-guide", "haiku"), ("statusline-setup", "sonnet")]
    )
    def test_a_built_in_agent_with_no_definition_takes_the_harness_pin(
        self, scene, agent_type, alias
    ):
        scene.parent_runs(OPUS)

        assert scene.fact(agent_type) == model_fact.Claimed(alias, alias, "built-in-pin")

    def test_a_built_in_pin_is_an_identifier_that_only_a_declared_name_claims(self, scene):
        fact = scene.fact("claude-code-guide", models=["opus", "sonnet"])

        assert fact == model_fact.Unclaimed("haiku", "built-in-pin")

    def test_a_built_in_pin_is_claimed_as_reported(self, scene):
        fact = scene.fact(
            "claude-code-guide", env={"ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-5"}
        )

        assert fact == model_fact.Claimed("haiku", "haiku", "built-in-pin")

    def test_the_built_in_pin_is_read_ahead_of_the_default_variable(self, scene):
        fact = scene.fact("claude-code-guide", env={DEFAULT_VARIABLE: SONNET})

        assert fact.source == "built-in-pin"

    def test_the_caller_outranks_the_built_in_pin(self, scene):
        scene.caller_names("opus", agent_type="claude-code-guide")

        assert model_fact.Claimed("opus", "opus", "per-spawn") == scene.fact("claude-code-guide")

    def test_a_definition_naming_no_model_hides_the_built_in_pin(self, scene):
        scene.parent_runs(OPUS)
        scene.user_agent("setup.md", "name: statusline-setup")

        assert scene.fact("statusline-setup") == model_fact.Claimed("opus", OPUS, "parent-record")

    def test_a_definition_naming_a_model_replaces_the_built_in_pin(self, scene):
        scene.user_agent("guide.md", "name: claude-code-guide\nmodel: opus")

        assert scene.fact("claude-code-guide") == model_fact.Claimed(
            "opus", "opus", "definition-pin"
        )

    def test_a_plugin_scoped_type_of_the_same_name_takes_no_built_in_pin(self, scene):
        assert scene.fact("kit:claude-code-guide") == model_fact.Missing()

    def test_a_type_the_harness_pins_nothing_for_takes_no_built_in_pin(self, scene):
        assert scene.fact("general-purpose") == model_fact.Missing()

    def test_a_skill_in_a_subagent_with_an_inherit_model_resolves_through_the_four_sources(
        self, scene
    ):
        scene.parent_runs(OPUS)
        scene.user_agent("skill-runner.md", "name: skill-runner\nmodel: inherit")

        fact = scene.fact("skill-runner", env={DEFAULT_VARIABLE: SONNET})

        assert fact == model_fact.Claimed("opus", OPUS, "parent-record")


class TestTheEngineReadsNoVariableThatNamesASeparateMechanismsModel:
    def test_no_delegate_resolution_asks_for_any_of_the_three(self, scene, read_spy):
        scene.parent_runs(OPUS)
        scene.caller_names("haiku", agent_type="spawned")
        scene.user_agent("pinned.md", "name: pinned\nmodel: sonnet")
        env = read_spy({name: HAIKU for name in SEPARATE_MECHANISM_VARIABLES})

        for agent_type in ("spawned", "pinned", "claude-code-guide", "general-purpose"):
            scene.resolve(agent_type, env=env)
        scene.resolve("general-purpose", env=env, prompt_id=None)

        assert not env.reads & set(SEPARATE_MECHANISM_VARIABLES)

    def test_a_collapse_model_changes_nothing(self, scene):
        scene.parent_runs(OPUS)
        collapse = {"CLAUDE_CONTEXT_COLLAPSE_MODEL": HAIKU}

        assert scene.resolve(env=collapse) == scene.resolve()
