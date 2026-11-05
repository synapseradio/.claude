#!/usr/bin/env python3
"""A context carries facts, and a block's condition tests them: known, false, or unknown.

Serves the engineer who writes a manifest keyed on model, agent, flag, and session, and the
person whose sessions and delegates receive the result: a declared model name claims the
identifiers it prefixes, a block takes the rank of its highest fact, an unclaimed model tests
false, and a missing one tests unknown so that no block keyed on it applies. Integration cases
run the hook entries over a configuration directory under `tmp_path`; unit cases claim
identifiers and evaluate conditions in memory.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_context_facts.py`.
"""

import json
import pathlib
import sys

import pytest
from delivery_world import DECLARED, World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import spawn_log  # noqa: E402
from rulesets.check.report_format import report_lines  # noqa: E402
from rulesets.check.run import check  # noqa: E402
from rulesets.facts.agent_definition import definition_front  # noqa: E402
from rulesets.facts.context import ABSENT, UNCLAIMED, AllToolsBut, Facts, ListedTools  # noqa: E402
from rulesets.facts.model import claim as model_claim  # noqa: E402
from rulesets.facts.model import fact as model_fact  # noqa: E402
from rulesets.facts.model import record as model_record  # noqa: E402
from rulesets.facts.model import session as session_model  # noqa: E402
from rulesets.facts.tools_fact import tools_fact  # noqa: E402
from rulesets.source.condition import evaluate, parse_condition  # noqa: E402


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def pin_agent_model(world, agent, model):
    """An agent definition under the configuration directory that pins its model."""

    path = world.config / "agents" / f"{agent}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {agent}\nmodel: {model}\n---\nbody\n", encoding="utf-8")


def received(delivery, stems):
    """The stems whose body the delivery carries, in the order given."""

    return [stem for stem in stems if f"text of {stem}\n" in delivery.context]


def claim(identifier, models):
    return model_claim.claim_model(identifier, "harness-reported", models)


def truth(text, *, model="missing", agent=None, flags=()):
    """The condition's value as a name: TRUE, FALSE, or UNKNOWN.

    `model` is a claimed name, "unclaimed", or "missing".
    """

    standing = {"missing": ABSENT, "unclaimed": UNCLAIMED}.get(model, model)
    facts = Facts(
        model=standing,
        agent=ABSENT if agent is None else agent,
        kind="session",
        flags=frozenset(flags),
    )
    return evaluate(parse_condition(text), facts).name


def report_for(world):
    return "\n".join(report_lines(check(world.rulesets)))


class TestFactKindsAndTheirRanks:
    def test_each_fact_kinds_block_beats_the_exclude_one_rank_below_it(self, world):
        stems = ["security-pass", "voice", "tone", "sorting"]
        for stem in stems:
            world.rule(stem)
        world.manifest(
            "models: ['haiku']\n"
            "flags: ['strict']\n"
            "defaults: ['-security-pass']\n"
            "when:\n"
            "  - model haiku: ['security-pass', '-voice']\n"
            "  - agent critic: ['voice', '-tone']\n"
            "  - flag strict: ['tone', '-sorting']\n"
            "  - session abc123: ['sorting']\n"
        )
        pin_agent_model(world, "critic", "haiku")
        world.environment["RULESETS_FLAGS"] = "strict"

        delivery = world.start_delegate("critic", session_id="abc123")

        assert received(delivery, stems) == stems

    def test_a_block_takes_the_rank_of_its_highest_fact(self, world):
        world.rule("security-pass")
        world.manifest(
            "models: ['haiku']\n"
            "when:\n"
            "  - model haiku: ['-security-pass']\n"
            "  - model haiku and agent critic: ['security-pass']\n"
        )
        pin_agent_model(world, "critic", "haiku")

        delivery = world.start_delegate("critic")

        assert received(delivery, ["security-pass"]) == ["security-pass"]


class TestEachFactKindHasADefinedValue:
    def test_a_delegate_on_a_claimed_model_has_the_model_agent_and_kind_facts(self, world):
        world.rule("voice")
        world.manifest("models: ['haiku']\ndefaults: ['voice']\n")
        pin_agent_model(world, "critic", "haiku")

        world.start_delegate("critic")

        (record,) = world.records()
        assert (record["model"]["name"], record["agent"], record["kind"]) == (
            "haiku",
            "critic",
            "delegate",
        )

    def test_an_identifier_no_declared_name_claims_is_the_model_fact(self):
        fact = claim("claude-nova-1", ["opus", "haiku"])

        assert fact == model_fact.Unclaimed("claude-nova-1", "harness-reported")


class TestConditionsCombineFactTests:
    def test_and_binds_tighter_than_or_so_a_critic_without_the_flag_receives_the_rule(self, world):
        world.rule("security-pass")
        world.manifest(
            "flags: ['strict']\n"
            "defaults: []\n"
            "when:\n"
            "  - agent critic or agent auditor and flag strict: ['security-pass']\n"
        )

        delivery = world.start_delegate("critic")

        assert received(delivery, ["security-pass"]) == ["security-pass"]

    def test_parentheses_group_so_a_critic_without_the_flag_does_not_apply(self, world):
        world.rule("security-pass")
        world.manifest(
            "flags: ['strict']\n"
            "defaults: []\n"
            "when:\n"
            "  - (agent critic or agent auditor) and flag strict: ['security-pass']\n"
        )

        delivery = world.start_delegate("critic")

        assert received(delivery, ["security-pass"]) == []
        assert truth("(agent critic or agent auditor) and flag strict", agent="critic") == "FALSE"

    def test_a_negated_model_test_holds_for_a_critic_on_another_claimed_model(self):
        assert truth("agent critic and not model haiku", agent="critic", model="opus") == "TRUE"


class TestConditionsTestFactsOnly:
    def test_a_project_test_is_a_check_error_and_the_block_applies_nowhere(self, world):
        world.rule("voice")
        world.manifest("defaults: []\nwhen:\n  - project amboss: ['voice']\n")

        report = report_for(world)

        assert "error" in report
        assert "`project amboss`" in report
        assert received(world.start_session(), ["voice"]) == []
        assert received(world.start_delegate("critic"), ["voice"]) == []

    def test_an_environment_variable_test_is_a_check_error_naming_the_condition(self, world):
        world.rule("voice")
        world.manifest("when:\n  - env CI: ['voice']\n")

        report = report_for(world)

        assert "error" in report
        assert "`env CI`" in report

    def test_unbalanced_parentheses_are_a_check_error_naming_the_condition(self, world):
        world.rule("voice")
        world.manifest("when:\n  - (agent critic and flag strict: ['voice']\n")

        report = report_for(world)

        assert "error" in report
        assert "`(agent critic and flag strict`" in report


class TestAConditionNamingAnUndeclaredModelOrFlagIsSkippedWithANotice:
    def test_a_misspelled_model_is_a_check_error_and_delivery_skips_the_block_with_a_notice(
        self, world
    ):
        world.rule("voice")
        world.rule("tone")
        world.manifest(
            "models: ['haiku']\n"
            "defaults: []\n"
            "when:\n"
            "  - model hiaku: ['tone']\n"
            "  - model haiku: ['voice']\n"
        )

        report = report_for(world)
        delivery = world.start_session(model="claude-haiku-4-5")

        assert "error" in report
        assert "hiaku" in report
        assert received(delivery, ["voice", "tone"]) == ["voice"]
        assert delivery.message is not None
        assert "hiaku" in delivery.message
        (record,) = world.records()
        assert record["withheld"] == []

    def test_an_agent_nobody_declares_is_no_check_error(self, world):
        world.rule("voice")
        world.manifest("when:\n  - agent eval-runner: ['voice']\n")

        assert check(world.rulesets).errors == ()


class TestADeclaredModelNameClaimsTheIdentifiersItPrefixes:
    def test_the_longest_declared_name_wins(self):
        fact = claim("claude-opus-4-8", ["opus", "opus-4-8"])

        assert model_fact.claimed_name(fact) == "opus-4-8"

    def test_a_shorter_name_still_claims_other_identifiers(self):
        fact = claim("claude-opus-5-5[1m]", ["opus", "opus-4-8"])

        assert model_fact.claimed_name(fact) == "opus"

    def test_a_continuation_that_is_not_a_boundary_claims_nothing(self):
        assert isinstance(claim("claude-opusx", ["opus"]), model_fact.Unclaimed)

    def test_an_alias_equal_to_a_declared_name_takes_that_name(self):
        fact = claim("haiku", ["haiku"])

        assert model_fact.claimed_name(fact) == "haiku"


class TestAnIdentifierEndingIn1mFollowsItsBaseNameUnlessA1mNameIsDeclared:
    def test_a_declared_1m_name_wins_as_the_longer_name(self):
        fact = claim("claude-opus-4-8[1m]", ["opus-4-8", "opus-4-8[1m]"])

        assert model_fact.claimed_name(fact) == "opus-4-8[1m]"


class TestAModelNameDeclaredTwiceIsNotAnError:
    def test_a_name_declared_twice_draws_no_check_error_and_claims_as_once(self, world):
        world.rule("voice")
        world.manifest("models: ['sonnet', 'sonnet']\ndefaults: ['voice']\n")

        once = claim("claude-sonnet-5-5", ["sonnet"])
        twice = claim("claude-sonnet-5-5", ["sonnet", "sonnet"])

        assert check(world.rulesets).errors == ()
        assert model_fact.claimed_name(twice) == "sonnet"
        assert twice == once


class TestTheEngineHoldsNoModelName:
    def test_a_manifest_declaring_no_model_claims_nothing(self):
        for identifier in ("claude-opus-4-8", "claude-haiku-5"):
            assert isinstance(claim(identifier, []), model_fact.Unclaimed)

    def test_declaring_a_new_model_name_gives_sessions_on_it_the_rules_declared_for_it(self, world):
        world.rule("fresh")
        world.manifest("models: ['opus-5']\ndefaults: []\nwhen:\n  - model opus-5: ['fresh']\n")

        on_new = world.start_session(model="claude-opus-5-0")
        on_old = world.start_session(model="claude-opus-4-8", session_id="s2")

        assert received(on_new, ["fresh"]) == ["fresh"]
        assert received(on_old, ["fresh"]) == []
        assert world.records("s1")[0]["model"]["name"] == "opus-5"


class TestAnUnclaimedIdentifierTestsFalseAndAMissingOneTestsUnknown:
    def test_a_non_claude_identifier_receives_the_defaults_and_the_negated_block(self, world):
        stems = ["writing-code", "security-pass", "voice"]
        for stem in stems:
            world.rule(stem)
        world.manifest(
            "models: ['haiku']\n"
            "defaults: ['writing-code']\n"
            "when:\n"
            "  - model haiku: ['security-pass']\n"
            "  - not model haiku: ['voice']\n"
        )

        delivery = world.start_session(model="glm-5")

        assert received(delivery, stems) == ["writing-code", "voice"]
        assert delivery.message is not None
        assert "glm-5" in delivery.message
        assert "glm-5" not in delivery.context

    def test_a_claude_model_before_its_name_is_declared_draws_a_shown_notice(self, world):
        world.rule("writing-code")
        world.manifest("models: ['haiku']\ndefaults: ['writing-code']\n")

        delivery = world.start_session(model="claude-nova-1")

        assert received(delivery, ["writing-code"]) == ["writing-code"]
        assert delivery.message is not None
        assert "claude-nova-1" in delivery.message
        assert "claude-nova-1" not in delivery.context
        (record,) = world.records()
        assert record["model"]["state"] == "unclaimed"

    def test_an_unclaimed_model_tests_false_and_its_negation_true(self):
        assert truth("model haiku", model="unclaimed") == "FALSE"
        assert truth("not model haiku", model="unclaimed") == "TRUE"


class TestAMissingModelIdentifierMakesEveryModelTestUnknown:
    def test_a_session_with_no_identifier_source_has_a_missing_model_and_a_shown_notice(
        self, world
    ):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: []\nwhen:\n  - not model haiku: ['voice']\n")

        delivery = world.start_session(model=None)

        assert received(delivery, ["voice"]) == []
        assert delivery.message is not None
        assert "no model identifier was available" in delivery.message
        (record,) = world.records()
        assert record["model"]["state"] == "missing"

    def test_a_missing_model_makes_a_test_and_its_negation_unknown(self):
        assert truth("model haiku", model="missing") == "UNKNOWN"
        assert truth("not model haiku", model="missing") == "UNKNOWN"


class TestDeliveryCompletesWhenTheModelIsUnclaimedOrMissing:
    def test_a_block_testing_no_unknown_fact_applies_while_the_model_is_missing(self, world):
        world.rule("voice")
        world.manifest("flags: ['strict']\ndefaults: []\nwhen:\n  - flag strict: ['voice']\n")
        world.environment["RULESETS_FLAGS"] = "strict"

        delivery = world.start_session(model=None)

        assert received(delivery, ["voice"]) == ["voice"]
        (record,) = world.records()
        assert record["model"]["state"] == "missing"


def model_world(world, **variables):
    """A world declaring `opus`, `sonnet`, and `haiku`, with the given variables set."""

    world.rule("voice")
    world.manifest("models: ['opus', 'sonnet', 'haiku']\ndefaults: ['voice']\n")
    world.environment.update(variables)


def caller_names(world, model, agent_type="critic"):
    """The per-spawn model the caller named, as the Agent tool hook records it."""

    state = world.config / ".tmp" / "rulesets-engine"
    spawn_log.append_spawn("s1", "p1", agent_type, model, state)


def parent_runs(world, identifier):
    """The parent session's recorded identifier, as the session hook leaves it for delegates."""

    model_record.write_model_record("s1", identifier, world.config / ".tmp" / "rulesets-engine")


def shown_notices(record):
    return [n for n in record["notices"] if n["shown"]]


def delegate_records(world):
    return [record for record in world.records() if record["scope"] == "delegate"]


def model_of(record):
    """The identifier and the source a delegate record names for its model."""

    return record["model"]["identifier"], record["model"]["source"]


FORCE = "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"
DEFAULT_VARIABLE = "CLAUDE_CODE_SUBAGENT_MODEL"
OPUS_IDENTIFIER = "claude-opus-5-5"
SONNET_IDENTIFIER = "claude-sonnet-5"
HAIKU_IDENTIFIER = "claude-haiku-4-5"


class TestTheEngineClaimsAModelIdentifierAsReportedAndResolvesNoAlias:
    def test_an_alias_whose_mapping_variable_is_set_is_claimed_as_reported(self, world):
        model_world(world, ANTHROPIC_DEFAULT_HAIKU_MODEL="claude-haiku-5")
        caller_names(world, "haiku")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["model"]["identifier"] == "haiku"
        assert record["model"]["name"] == "haiku"


class TestTheEngineReadsNoModelVariableMeantForASeparateMechanism:
    def test_the_collapse_model_variable_changes_nothing(self, tmp_path):
        payload = {"model": "claude-opus-5-5", "session_id": "s1"}
        collapse = {"CLAUDE_CONTEXT_COLLAPSE_MODEL": "claude-haiku-4-5"}

        with_variable = session_model.resolve_session_model(
            payload, ["opus", "haiku"], collapse, tmp_path
        )
        without_variable = session_model.resolve_session_model(
            payload, ["opus", "haiku"], {}, tmp_path
        )

        assert with_variable.fact == model_fact.Claimed(
            "opus", "claude-opus-5-5", "harness-reported"
        )
        assert with_variable == without_variable


class TestAHostManagedProviderDrawsAnUnshownNoticeForADisregardedVariable:
    def test_an_inherited_anthropic_model_draws_only_an_unshown_notice(self, world):
        model_world(
            world,
            CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST="1",
            ANTHROPIC_MODEL="claude-opus-5-5",
        )

        delivery = world.start_session(model=None)

        (record,) = world.records()
        assert {
            "kind": "provider-variable",
            "subject": "ANTHROPIC_MODEL",
            "shown": False,
        } in record["notices"]
        assert shown_notices(record) == []
        assert delivery.message is None


class TestTheAgentFactComesFromTheHarnessesAgentType:
    def test_a_delegates_agent_fact_follows_its_start_payload(self, world):
        stems = ["voice", "tone"]
        for stem in stems:
            world.rule(stem)
        world.manifest(
            "defaults: []\nwhen:\n  - agent critic: ['voice']\n  - agent auditor: ['tone']\n"
        )

        delivery = world.start_delegate("critic")

        assert received(delivery, stems) == ["voice"]
        assert truth("agent critic", agent="critic") == "TRUE"
        assert truth("agent auditor", agent="critic") == "FALSE"

    def test_a_session_started_with_an_agent_carries_that_agent_fact(self, world):
        stems = ["voice", "tone"]
        for stem in stems:
            world.rule(stem)
        world.manifest(
            "defaults: []\nwhen:\n  - agent critic: ['voice']\n  - agent auditor: ['tone']\n"
        )

        delivery = world.start_session(agent_type="critic")

        assert received(delivery, stems) == ["voice"]
        (record,) = world.records()
        assert record["agent"] == "critic"


class TestAPlainMainSessionCarriesNoAgentFact:
    def test_an_agent_test_evaluates_unknown_and_the_record_names_the_absence(self, world):
        world.rule("voice")
        world.manifest("defaults: []\nwhen:\n  - agent eval-runner: ['voice']\n")

        delivery = world.start_session()

        assert received(delivery, ["voice"]) == []
        assert truth("agent eval-runner") == "UNKNOWN"
        (record,) = world.records()
        assert record["agent"] is None
        (absent,) = [n for n in record["notices"] if n["kind"] == "agent-absent"]
        assert absent["shown"] is False
        assert "agent fact is absent" in absent["subject"]


class TestATestOverAnAbsentFactEvaluatesUnknown:
    def test_a_negation_over_an_absent_fact_stays_unknown_and_the_block_does_not_apply(self, world):
        world.rule("voice")
        world.manifest("defaults: []\nwhen:\n  - not agent critic: ['voice']\n")

        delivery = world.start_session()

        assert received(delivery, ["voice"]) == []
        assert truth("not agent critic") == "UNKNOWN"


class TestConditionsCombineTrueFalseAndUnknownByThreeValuedLogic:
    def test_a_true_side_settles_an_or_over_an_unknown_side(self):
        assert truth("flag strict or model haiku", flags=["strict"], model="missing") == "TRUE"
        assert truth("model haiku or flag strict", flags=["strict"], model="missing") == "TRUE"
        assert truth("flag strict or model haiku", model="missing") == "UNKNOWN"

    def test_a_false_side_settles_an_and_inside_a_negation(self, world):
        world.rule("security-pass")
        world.manifest(
            DECLARED
            + "defaults: []\nwhen:\n  - not (agent critic and model haiku): ['security-pass']\n"
        )

        scout = world.start_delegate("scout", session_id="s1")
        critic = world.start_delegate("critic", session_id="s2")

        assert received(scout, ["security-pass"]) == ["security-pass"]
        assert received(critic, ["security-pass"]) == []
        assert truth("not (agent critic and model haiku)", agent="scout") == "TRUE"
        assert truth("not (agent critic and model haiku)", agent="critic") == "UNKNOWN"


TOOL_BLOCKS = "defaults: []\nwhen:\n  - tools Bash: ['voice']\n  - tools Edit: ['tone']\n"


def define_agent(world, name, front):
    """An agent definition under the configuration directory with the given frontmatter lines."""

    path = world.config / "agents" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\n{front}\n---\nbody\n", encoding="utf-8")


def tools_of(world, name):
    return tools_fact(definition_front(name, None, world.config))


def tools_world(world):
    for stem in ("voice", "tone"):
        world.rule(stem)
    world.manifest(TOOL_BLOCKS)


class TestToolsComeFromTheAgentDefinition:
    def test_the_tools_fact_follows_a_definitions_tools_list(self, world):
        tools_world(world)
        define_agent(world, "critic", "tools: Read, Grep, Bash")

        delivery = world.start_delegate("critic")

        assert tools_of(world, "critic") == ListedTools(frozenset({"Read", "Grep", "Bash"}))
        assert received(delivery, ["voice", "tone"]) == ["voice"]

    def test_a_yaml_list_of_tools_reads_as_the_same_fact(self, world):
        define_agent(world, "critic", "tools: [Read, Grep, Bash]")

        assert tools_of(world, "critic") == ListedTools(frozenset({"Read", "Grep", "Bash"}))


class TestADisallowedToolEntryRemovesTheWholeTool:
    def test_an_entry_with_a_specifier_removes_the_tool(self, world):
        tools_world(world)
        define_agent(world, "critic", "tools: Read, Grep, Bash\ndisallowedTools: Bash(git push *)")

        delivery = world.start_delegate("critic")

        assert tools_of(world, "critic") == ListedTools(frozenset({"Read", "Grep"}))
        assert received(delivery, ["voice", "tone"]) == []


class TestADefinitionWithNoToolsListInheritsEveryTool:
    def test_every_tool_but_the_disallowed_ones_is_held(self, world):
        tools_world(world)
        define_agent(world, "critic", "disallowedTools: Edit")

        delivery = world.start_delegate("critic")

        assert tools_of(world, "critic") == AllToolsBut(frozenset({"Edit"}))
        assert received(delivery, ["voice", "tone"]) == ["voice"]


class TestAContextWithNoAgentDefinitionHasNoToolsFact:
    def test_a_delegate_with_no_definition_file_has_an_absent_tools_fact_named_in_the_record(
        self, world
    ):
        tools_world(world)

        delivery = world.start_delegate("critic")

        assert tools_of(world, "critic") is ABSENT
        assert received(delivery, ["voice", "tone"]) == []
        (record,) = world.records()
        (absent,) = [n for n in record["notices"] if n["kind"] == "tools-absent"]
        assert absent["shown"] is False
        assert "no definition file registers its agent type" in absent["subject"]

    def test_the_tools_test_over_an_absent_fact_and_its_negation_are_unknown(self):
        assert truth_of_tools("tools Bash", ABSENT) == "UNKNOWN"
        assert truth_of_tools("not tools Bash", ABSENT) == "UNKNOWN"


def truth_of_tools(text, tools):
    facts = Facts(model=ABSENT, agent=ABSENT, kind="delegate", flags=frozenset(), tools=tools)
    return evaluate(parse_condition(text), facts).name


class TestTheToolsFactIgnoresABackgroundSubagentsNarrowerToolSet:
    def test_a_background_delegates_tools_fact_reads_the_definition_alone(self, world):
        tools_world(world)
        define_agent(world, "critic", "tools: Edit")

        delivery = world.start_delegate("critic", run_in_background=True, tools=["Read"])

        assert received(delivery, ["voice", "tone"]) == ["tone"]


class TestTheCallersModelIsReadFromTheAgentToolHooksRecord:
    def test_two_agent_types_under_one_prompt_each_read_their_own_per_spawn_model(self, world):
        model_world(world)
        caller_names(world, "haiku", "critic")
        caller_names(world, "opus", "scout")

        world.start_delegate("critic", agent_id="a1")
        world.start_delegate("scout", agent_id="a2")

        by_agent = {record["agent"]: model_of(record) for record in delegate_records(world)}
        assert by_agent == {"critic": ("haiku", "per-spawn"), "scout": ("opus", "per-spawn")}


class TestSeveralMatchingPerSpawnRecordsNamingDifferentModels:
    def test_two_same_type_spawns_under_one_prompt_naming_one_model_give_that_model_with_no_notice(
        self, world
    ):
        model_world(world)
        caller_names(world, "haiku")
        caller_names(world, "haiku")

        world.start_delegate("critic", agent_id="a1")
        world.start_delegate("critic", agent_id="a2")

        records = delegate_records(world)
        assert [model_of(record) for record in records] == [("haiku", "per-spawn")] * 2
        assert [
            n for record in records for n in record["notices"] if n["kind"] == "per-spawn-ambiguous"
        ] == []


class TestAPluginScopedAgentTypeReadsItsPluginsAgentsDirectory:
    def test_a_plugin_agent_reads_its_plugins_definition(self, world):
        world.rule("voice")
        world.manifest("models: ['haiku']\ndefaults: []\nwhen:\n  - tools Read: ['voice']\n")
        install = world.config.parent / "installs" / "p@market"
        (install / "agents").mkdir(parents=True)
        (install / "agents" / "scout.md").write_text(
            "---\nname: scout\nmodel: haiku\ntools: Read\n---\nbody\n", encoding="utf-8"
        )
        (world.config / "plugins").mkdir()
        (world.config / "plugins" / "installed_plugins.json").write_text(
            json.dumps({"version": 2, "plugins": {"p@market": [{"installPath": str(install)}]}}),
            encoding="utf-8",
        )

        delivery = world.start_delegate("p:scout")

        (record,) = delegate_records(world)
        assert model_of(record) == ("haiku", "definition-pin")
        assert received(delivery, ["voice"]) == ["voice"]


class TestAPerSpawnModelOutranksABuiltInAgentsPin:
    def test_a_per_spawn_model_outranks_a_built_in_agents_harness_pin(self, world):
        model_world(world)
        caller_names(world, "opus", "claude-code-guide")

        world.start_delegate("claude-code-guide")

        (record,) = delegate_records(world)
        assert model_of(record) == ("opus", "per-spawn")

    def test_a_per_spawn_model_outranks_the_default_variable_for_an_agent_the_engine_holds_no_pin_for(
        self, world
    ):
        model_world(world, **{DEFAULT_VARIABLE: SONNET_IDENTIFIER})
        caller_names(world, "haiku", "general-purpose")

        world.start_delegate("general-purpose")

        (record,) = delegate_records(world)
        assert model_of(record) == ("haiku", "per-spawn")


class TestTheSubagentForceVariableOutranksEveryAgentTypesPins:
    def test_a_pinned_built_in_agent_under_the_force_variable_alone_takes_the_parents_identifier(
        self, world
    ):
        model_world(world, **{FORCE: "1"})
        parent_runs(world, OPUS_IDENTIFIER)

        world.start_delegate("claude-code-guide")

        (record,) = delegate_records(world)
        assert model_of(record) == (OPUS_IDENTIFIER, FORCE)

    def test_an_agent_the_engine_holds_no_pin_for_takes_the_default_variable_under_both_variables(
        self, world
    ):
        model_world(world, **{FORCE: "1", DEFAULT_VARIABLE: HAIKU_IDENTIFIER})
        parent_runs(world, OPUS_IDENTIFIER)

        world.start_delegate("general-purpose")

        (record,) = delegate_records(world)
        assert record["model"]["identifier"] == HAIKU_IDENTIFIER


class TestAnEnvironmentVariableCountsAsSetUnlessEmptyOrFalse:
    def test_a_force_variable_holding_zero_has_no_effect(self, world):
        model_world(world, **{FORCE: "0", DEFAULT_VARIABLE: SONNET_IDENTIFIER})
        caller_names(world, "haiku")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert model_of(record) == ("haiku", "per-spawn")
