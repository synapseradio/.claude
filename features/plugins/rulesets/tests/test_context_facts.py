#!/usr/bin/env python3
"""A context carries facts, and a block's condition tests them: known, false, or unknown.

Serves the engineer who writes a config keyed on model, agent, flag, and session, and the
person whose sessions and delegates receive the result: a declared model name claims the
identifiers it prefixes, a block takes the rank of its highest fact, an unclaimed model tests
false, and a missing one tests unknown so that no block keyed on it applies. Integration cases
run the hook entries over a configuration directory under `tmp_path`; unit cases claim
identifiers and evaluate conditions in memory.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_context_facts.py`.
"""

import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from delivery_world import DECLARED, Delivery, World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.report_format import report_lines  # noqa: E402
from rulesets.check.run import check  # noqa: E402
from rulesets.facts.agent_definition import definition_front  # noqa: E402
from rulesets.facts.context import (  # noqa: E402
    ABSENT,
    UNCLAIMED,
    Absent,
    AllToolsBut,
    Facts,
    ListedTools,
)
from rulesets.facts.model import claim as model_claim  # noqa: E402
from rulesets.facts.model import fact as model_fact  # noqa: E402
from rulesets.facts.model import session as session_model  # noqa: E402
from rulesets.facts.tools_fact import tools_fact  # noqa: E402
from rulesets.source.condition import evaluate, parse_condition  # noqa: E402


@pytest.fixture
def world(tmp_path) -> World:
    return World(tmp_path)


def pin_agent_model(world, agent, model) -> None:
    """An agent definition under the configuration directory that pins its model."""
    path = world.config / "agents" / f"{agent}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {agent}\ndescription: a test agent\nmodel: {model}\n---\nbody\n",
        encoding="utf-8",
    )


def received(delivery, stems) -> list[str]:
    """The stems whose body the delivery carries, in the order given."""
    return [stem for stem in stems if f"text of {stem}\n" in delivery.context]


def claim(identifier, models) -> model_fact.ModelFact:
    return model_claim.claim_model(identifier, "harness-reported", models)


def truth(text, *, model="missing", agent=None, flags=()) -> str:
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


def report_for(world) -> str:
    return "\n".join(report_lines(check(world.rulesets)))


class TestFactKindsAndTheirRanks:
    def test_each_fact_kinds_block_beats_the_exclude_one_rank_below_it(self, world) -> None:
        stems = ["security-pass", "voice", "tone", "sorting"]
        for stem in stems:
            world.rule(stem)
        world.write_config(
            "models: haiku\n"
            "flags: strict\n"
            "defaults:\n"
            "  exclude: security-pass\n"
            "model haiku:\n"
            "  include: security-pass\n"
            "  exclude: voice\n"
            "agent critic:\n"
            "  include: voice\n"
            "  exclude: tone\n"
            "flag strict:\n"
            "  include: tone\n"
            "  exclude: sorting\n"
            "session abc123:\n"
            "  include: sorting\n"
        )
        pin_agent_model(world, "critic", "haiku")
        world.environment["RULESETS_FLAGS"] = "strict"

        delivery = world.start_delegate("critic", session_id="abc123")

        assert received(delivery, stems) == stems

    def test_a_block_takes_the_rank_of_its_highest_fact(self, world) -> None:
        world.rule("security-pass")
        world.write_config(
            "models: haiku\n"
            "model haiku:\n"
            "  exclude: security-pass\n"
            "model haiku and agent critic:\n"
            "  include: security-pass\n"
        )
        pin_agent_model(world, "critic", "haiku")

        delivery = world.start_delegate("critic")

        assert received(delivery, ["security-pass"]) == ["security-pass"]

    @pytest.mark.parametrize("test", ["kind delegate", "tools Bash"])
    def test_a_kind_or_tools_block_stands_above_model_and_below_flag(self, world, test) -> None:
        stems = ["alpha", "beta"]
        for stem in stems:
            world.rule(stem)
        world.write_config(
            "models: haiku\n"
            "flags: strict\n"
            "defaults:\n"
            "flag strict:\n"
            "  include: beta\n"
            f"{test}:\n"
            "  include: alpha\n"
            "  exclude: beta\n"
            "model haiku:\n"
            "  exclude: alpha\n"
        )
        define_agent(world, "critic", "model: haiku\ntools: Bash")
        world.environment["RULESETS_FLAGS"] = "strict"

        delivery = world.start_delegate("critic")

        assert received(delivery, stems) == stems


class TestEachFactKindHasADefinedValue:
    def test_a_delegate_on_a_claimed_model_has_the_model_agent_and_kind_facts(self, world) -> None:
        world.rule("voice")
        world.write_config("models: haiku\ndefaults: voice\n")
        pin_agent_model(world, "critic", "haiku")

        world.start_delegate("critic")

        (record,) = world.records()
        assert (record["model"]["name"], record["agent"]["name"], record["kind"]) == (
            "haiku",
            "critic",
            "delegate",
        )

    def test_an_identifier_no_declared_name_claims_is_the_model_fact(self) -> None:
        fact = claim("claude-nova-1", ["opus", "haiku"])

        assert fact == model_fact.Unclaimed("claude-nova-1", "harness-reported")


class TestConditionsCombineFactTests:
    def test_and_binds_tighter_than_or_so_a_critic_without_the_flag_receives_the_rule(
        self, world
    ) -> None:
        world.rule("security-pass")
        world.write_config(
            "flags: strict\n"
            "defaults:\n"
            "agent critic or agent auditor and flag strict:\n"
            "  include: security-pass\n"
        )

        delivery = world.start_delegate("critic")

        assert received(delivery, ["security-pass"]) == ["security-pass"]

    def test_parentheses_group_so_a_critic_without_the_flag_does_not_apply(self, world) -> None:
        world.rule("security-pass")
        world.write_config(
            "flags: strict\n"
            "defaults:\n"
            "(agent critic or agent auditor) and flag strict:\n"
            "  include: security-pass\n"
        )

        delivery = world.start_delegate("critic")

        assert received(delivery, ["security-pass"]) == []
        assert truth("(agent critic or agent auditor) and flag strict", agent="critic") == "FALSE"

    def test_a_negated_model_test_holds_for_a_critic_on_another_claimed_model(self) -> None:
        assert truth("agent critic and not model haiku", agent="critic", model="opus") == "TRUE"


class TestConditionsTestFactsOnly:
    def test_a_project_test_is_a_check_error_and_the_block_applies_nowhere(self, world) -> None:
        world.rule("voice")
        world.write_config("defaults:\nproject amboss:\n  include: voice\n")

        report = report_for(world)

        assert "error" in report
        assert "`project amboss`" in report
        assert received(world.start_session(), ["voice"]) == []
        assert received(world.start_delegate("critic"), ["voice"]) == []

    def test_an_environment_variable_test_is_a_check_error_naming_the_condition(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config("env CI:\n  include: voice\n")

        report = report_for(world)

        assert "error" in report
        assert "`env CI`" in report

    def test_unbalanced_parentheses_are_a_check_error_naming_the_condition(self, world) -> None:
        world.rule("voice")
        world.write_config("(agent critic and flag strict:\n  include: voice\n")

        report = report_for(world)

        assert "error" in report
        assert "`(agent critic and flag strict`" in report


class TestAConditionNamingAnUndeclaredModelOrFlagIsSkippedWithANotice:
    def test_a_misspelled_model_is_a_check_error_and_delivery_skips_the_block_with_a_notice(
        self, world
    ) -> None:
        world.rule("voice")
        world.rule("tone")
        world.write_config(
            "models: haiku\n"
            "defaults:\n"
            "model hiaku:\n"
            "  include: tone\n"
            "model haiku:\n"
            "  include: voice\n"
        )

        report = report_for(world)
        delivery = world.start_session(model="claude-haiku-4-5")

        assert "error" in report
        assert "`model hiaku`" in report
        assert "`hiaku`" in report
        assert received(delivery, ["voice", "tone"]) == ["voice"]
        assert delivery.message is not None
        assert "hiaku" in delivery.message
        (record,) = world.records()
        assert record["withheld"] == []

    def test_an_agent_nobody_declares_is_no_check_error(self, world) -> None:
        world.rule("voice")
        world.write_config("agent eval-runner:\n  include: voice\n")

        assert check(world.rulesets).errors == ()

    def test_a_tool_and_a_session_identifier_nobody_declares_are_no_check_error(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(
            "defaults:\n"
            "tools Bash:\n"
            "  include: voice\n"
            "session abc123:\n"
            "  include: voice\n"
            "not tools Edit and session xyz789:\n"
            "  include: voice\n"
        )

        assert check(world.rulesets).errors == ()


class TestADeclaredModelNameClaimsTheIdentifiersItPrefixes:
    def test_the_longest_declared_name_wins(self) -> None:
        fact = claim("claude-opus-4-8", ["opus", "opus-4-8"])

        assert model_fact.claimed_name(fact) == "opus-4-8"

    def test_a_shorter_name_still_claims_other_identifiers(self) -> None:
        fact = claim("claude-opus-5-5[1m]", ["opus", "opus-4-8"])

        assert model_fact.claimed_name(fact) == "opus"

    def test_a_continuation_that_is_not_a_boundary_claims_nothing(self) -> None:
        assert isinstance(claim("claude-opusx", ["opus"]), model_fact.Unclaimed)

    def test_an_alias_equal_to_a_declared_name_takes_that_name(self) -> None:
        fact = claim("haiku", ["haiku"])

        assert model_fact.claimed_name(fact) == "haiku"


class TestAnIdentifierEndingIn1mFollowsItsBaseNameUnlessA1mNameIsDeclared:
    def test_a_declared_1m_name_wins_as_the_longer_name(self) -> None:
        fact = claim("claude-opus-4-8[1m]", ["opus-4-8", "opus-4-8[1m]"])

        assert model_fact.claimed_name(fact) == "opus-4-8[1m]"


class TestAModelNameDeclaredTwiceIsNotAnError:
    def test_a_name_declared_twice_draws_no_check_error_and_claims_as_once(self, world) -> None:
        world.rule("voice")
        world.write_config("models: sonnet sonnet\ndefaults: voice\n")

        once = claim("claude-sonnet-5-5", ["sonnet"])
        twice = claim("claude-sonnet-5-5", ["sonnet", "sonnet"])

        assert check(world.rulesets).errors == ()
        assert model_fact.claimed_name(twice) == "sonnet"
        assert twice == once


class TestTheEngineHoldsNoModelName:
    def test_a_config_declaring_no_model_claims_nothing(self) -> None:
        for identifier in ("claude-opus-4-8", "claude-haiku-5"):
            assert isinstance(claim(identifier, []), model_fact.Unclaimed)

    def test_declaring_a_new_model_name_gives_sessions_on_it_the_rules_declared_for_it(
        self, world
    ) -> None:
        world.rule("fresh")
        world.write_config("models: opus-5\ndefaults:\nmodel opus-5:\n  include: fresh\n")

        on_new = world.start_session(model="claude-opus-5-0")
        on_old = world.start_session(model="claude-opus-4-8", session_id="s2")

        assert received(on_new, ["fresh"]) == ["fresh"]
        assert received(on_old, ["fresh"]) == []
        assert world.records("s1")[0]["model"]["name"] == "opus-5"


class TestAnUnclaimedIdentifierTestsFalseAndAMissingOneTestsUnknown:
    def test_a_non_claude_identifier_receives_the_defaults_and_the_negated_block(
        self, world
    ) -> None:
        stems = ["writing-code", "security-pass", "voice"]
        for stem in stems:
            world.rule(stem)
        world.write_config(
            "models: haiku\n"
            "defaults: writing-code\n"
            "model haiku:\n"
            "  include: security-pass\n"
            "not model haiku:\n"
            "  include: voice\n"
        )

        delivery = world.start_session(model="glm-5")

        assert received(delivery, stems) == ["writing-code", "voice"]
        assert delivery.message is not None
        assert "glm-5" in delivery.message
        assert "glm-5" not in delivery.context

    def test_a_claude_model_before_its_name_is_declared_draws_a_shown_notice(self, world) -> None:
        world.rule("writing-code")
        world.write_config("models: haiku\ndefaults: writing-code\n")

        delivery = world.start_session(model="claude-nova-1")

        assert received(delivery, ["writing-code"]) == ["writing-code"]
        assert delivery.message is not None
        assert "claude-nova-1" in delivery.message
        assert "claude-nova-1" not in delivery.context
        (record,) = world.records()
        assert record["model"]["state"] == "unclaimed"

    def test_an_unclaimed_model_tests_false_and_its_negation_true(self) -> None:
        assert truth("model haiku", model="unclaimed") == "FALSE"
        assert truth("not model haiku", model="unclaimed") == "TRUE"


class TestAMissingModelIdentifierMakesEveryModelTestUnknown:
    def test_a_session_with_no_identifier_source_has_a_missing_model_and_a_shown_notice(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + ("defaults:\nnot model haiku:\n  include: voice\n"))

        delivery = world.start_session(model=None)

        assert received(delivery, ["voice"]) == []
        assert delivery.message is not None
        assert "no model identifier was available" in delivery.message
        (record,) = world.records()
        assert record["model"]["state"] == "missing"

    def test_a_missing_model_makes_a_test_and_its_negation_unknown(self) -> None:
        assert truth("model haiku", model="missing") == "UNKNOWN"
        assert truth("not model haiku", model="missing") == "UNKNOWN"

    def test_a_pin_that_is_a_list_ends_resolution_without_taking_the_default_variable(
        self, world
    ) -> None:
        model_world(world, **{DEFAULT_VARIABLE: SONNET_IDENTIFIER})
        parent_runs(world, OPUS_IDENTIFIER)
        define_agent(world, "critic", "model: [opus, haiku]")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["model"]["state"] == "missing"
        assert record["model"]["identifier"] is None
        assert record["model"]["source"] == "definition-pin"
        assert record["model"]["not_a_string"] == {"value": ["opus", "haiku"], "type": "list"}
        (notice,) = shown_notices(record)
        assert "no model identifier was available" in notice["subject"]
        assert "the definition's pin is a list" in notice["subject"]

    def test_a_per_spawn_model_that_is_a_number_ends_resolution_without_taking_a_later_source(
        self, world
    ) -> None:
        model_world(world, **{DEFAULT_VARIABLE: SONNET_IDENTIFIER})
        parent_runs(world, OPUS_IDENTIFIER)
        define_agent(world, "critic", "model: haiku")
        caller_names(world, 123, "critic")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["model"]["state"] == "missing"
        assert record["model"]["identifier"] is None
        assert record["model"]["source"] == "per-spawn"
        assert record["model"]["not_a_string"] == {"value": 123, "type": "int"}
        (notice,) = shown_notices(record)
        assert "no model identifier was available" in notice["subject"]
        assert "the model the caller named is an int" in notice["subject"]


class TestDeliveryCompletesWhenTheModelIsUnclaimedOrMissing:
    def test_a_block_testing_no_unknown_fact_applies_while_the_model_is_missing(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config("flags: strict\ndefaults:\nflag strict:\n  include: voice\n")
        world.environment["RULESETS_FLAGS"] = "strict"

        delivery = world.start_session(model=None)

        assert received(delivery, ["voice"]) == ["voice"]
        (record,) = world.records()
        assert record["model"]["state"] == "missing"


def model_world(world, **variables) -> None:
    """A world declaring `opus`, `sonnet`, and `haiku`, with the given variables set."""
    world.rule("voice")
    world.write_config("models: opus sonnet haiku\ndefaults: voice\n")
    world.environment.update(variables)


def state_directory(world) -> pathlib.Path:
    return world.config / ".tmp" / "rulesets-engine"


def caller_names(world, model, agent_type="critic", prompt_id="p1") -> None:
    """One line of the session's spawn log, in the JSON-lines format the Agent tool hook appends."""
    path = state_directory(world) / "audit" / "s1" / "spawns.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "kind": "spawn",
        "session_id": "s1",
        "prompt_id": prompt_id,
        "agent_type": agent_type,
        "model": model,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line) + "\n")


def parent_runs(world, identifier) -> None:
    """The parent session's model record, in the JSON format the session hook leaves."""
    path = state_directory(world) / "models" / "s1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"identifier": identifier}) + "\n", encoding="utf-8")


def shown_notices(record) -> list[dict]:
    return [n for n in record["notices"] if n["shown"]]


def delegate_records(world) -> list[dict]:
    return [record for record in world.records() if record["scope"] == "delegate"]


def model_of(record) -> tuple[str, str]:
    """The identifier and the source a delegate record names for its model."""
    return record["model"]["identifier"], record["model"]["source"]


FORCE = "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"
DEFAULT_VARIABLE = "CLAUDE_CODE_SUBAGENT_MODEL"
COORDINATOR = "CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL"
OPUS_IDENTIFIER = "claude-opus-5-5"
SONNET_IDENTIFIER = "claude-sonnet-5"
HAIKU_IDENTIFIER = "claude-haiku-4-5"


class TestTheEngineClaimsAModelIdentifierAsReportedAndResolvesNoAlias:
    def test_an_alias_whose_mapping_variable_is_set_is_claimed_as_reported(self, world) -> None:
        model_world(world, ANTHROPIC_DEFAULT_HAIKU_MODEL="claude-haiku-5")
        caller_names(world, "haiku")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["model"]["identifier"] == "haiku"
        assert record["model"]["name"] == "haiku"


class TestTheEngineReadsNoModelVariableMeantForASeparateMechanism:
    def test_the_collapse_model_variable_changes_nothing(self, tmp_path) -> None:
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
    def test_an_inherited_anthropic_model_draws_only_an_unshown_notice(self, world) -> None:
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

    def test_an_anthropic_model_with_no_host_variable_draws_no_notice(self, world) -> None:
        model_world(world, ANTHROPIC_MODEL="claude-opus-5-5")

        delivery = world.start_session(model=None)

        (record,) = world.records()
        assert [n for n in record["notices"] if n["kind"] == "provider-variable"] == []
        assert delivery.message is None


class TestTheAgentFactComesFromTheHarnessesAgentType:
    def test_a_delegates_agent_fact_follows_its_start_payload(self, world) -> None:
        stems = ["voice", "tone"]
        for stem in stems:
            world.rule(stem)
        world.write_config(
            "defaults:\nagent critic:\n  include: voice\nagent auditor:\n  include: tone\n"
        )

        delivery = world.start_delegate("critic")

        assert received(delivery, stems) == ["voice"]
        assert truth("agent critic", agent="critic") == "TRUE"
        assert truth("agent auditor", agent="critic") == "FALSE"

    def test_a_session_started_with_an_agent_carries_that_agent_fact(self, world) -> None:
        stems = ["voice", "tone"]
        for stem in stems:
            world.rule(stem)
        world.write_config(
            "defaults:\nagent critic:\n  include: voice\nagent auditor:\n  include: tone\n"
        )

        delivery = world.start_session(agent_type="critic")

        assert received(delivery, stems) == ["voice"]
        (record,) = world.records()
        assert record["agent"] == {"state": "named", "name": "critic"}


class TestAPlainMainSessionCarriesNoAgentFact:
    def test_an_agent_test_evaluates_unknown_and_the_record_names_the_absence(self, world) -> None:
        world.rule("voice")
        world.write_config("defaults:\nagent eval-runner:\n  include: voice\n")

        delivery = world.start_session()

        assert received(delivery, ["voice"]) == []
        assert truth("agent eval-runner") == "UNKNOWN"
        (record,) = world.records()
        assert record["agent"]["state"] == "absent"
        assert "without `--agent`" in record["agent"]["reason"]
        (absent,) = [n for n in record["notices"] if n["kind"] == "agent-absent"]
        assert absent["shown"] is False
        assert "agent fact is absent" in absent["subject"]

    def test_a_config_that_tests_no_agent_draws_no_absence_notice(self, world) -> None:
        world.rule("voice")
        world.write_config("flags: strict\ndefaults: voice\nflag strict:\n  include: voice\n")

        world.start_session()

        (record,) = world.records()
        assert [n for n in record["notices"] if n["kind"] == "agent-absent"] == []


class TestATestOverAnAbsentFactEvaluatesUnknown:
    def test_a_negation_over_an_absent_fact_stays_unknown_and_the_block_does_not_apply(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config("defaults:\nnot agent critic:\n  include: voice\n")

        delivery = world.start_session()

        assert received(delivery, ["voice"]) == []
        assert truth("not agent critic") == "UNKNOWN"


class TestConditionsCombineTrueFalseAndUnknownByThreeValuedLogic:
    def test_a_true_side_settles_an_or_over_an_unknown_side(self) -> None:
        assert truth("flag strict or model haiku", flags=["strict"], model="missing") == "TRUE"
        assert truth("model haiku or flag strict", flags=["strict"], model="missing") == "TRUE"
        assert truth("flag strict or model haiku", model="missing") == "UNKNOWN"

    def test_a_false_side_settles_an_and_inside_a_negation(self, world) -> None:
        world.rule("security-pass")
        world.write_config(
            DECLARED
            + ("defaults:\nnot (agent critic and model haiku):\n  include: security-pass\n")
        )

        scout = world.start_delegate("scout", session_id="s1")
        critic = world.start_delegate("critic", session_id="s2")

        assert received(scout, ["security-pass"]) == ["security-pass"]
        assert received(critic, ["security-pass"]) == []
        assert truth("not (agent critic and model haiku)", agent="scout") == "TRUE"
        assert truth("not (agent critic and model haiku)", agent="critic") == "UNKNOWN"


TOOL_BLOCKS = "defaults:\ntools Bash:\n  include: voice\ntools Edit:\n  include: tone\n"


def define_agent(world, name, front) -> None:
    """An agent definition under the configuration directory with the given frontmatter lines."""
    path = world.config / "agents" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: a test agent\n{front}\n---\nbody\n", encoding="utf-8"
    )


def tools_of(world, name) -> ListedTools | AllToolsBut | Absent:
    return tools_fact(definition_front(name, None, world.config))


def tools_world(world) -> None:
    for stem in ("voice", "tone"):
        world.rule(stem)
    world.write_config(TOOL_BLOCKS)


class TestToolsComeFromTheAgentDefinition:
    def test_the_tools_fact_follows_a_definitions_tools_list(self, world) -> None:
        tools_world(world)
        define_agent(world, "critic", "tools: Read, Grep, Bash")

        delivery = world.start_delegate("critic")

        assert tools_of(world, "critic") == ListedTools(frozenset({"Read", "Grep", "Bash"}))
        assert received(delivery, ["voice", "tone"]) == ["voice"]

    def test_a_yaml_list_of_tools_reads_as_the_same_fact(self, world) -> None:
        define_agent(world, "critic", "tools: [Read, Grep, Bash]")

        assert tools_of(world, "critic") == ListedTools(frozenset({"Read", "Grep", "Bash"}))


class TestADisallowedToolEntryRemovesTheWholeTool:
    def test_an_entry_with_a_specifier_removes_the_tool(self, world) -> None:
        tools_world(world)
        define_agent(world, "critic", "tools: Read, Grep, Bash\ndisallowedTools: Bash(git push *)")

        delivery = world.start_delegate("critic")

        assert tools_of(world, "critic") == ListedTools(frozenset({"Read", "Grep"}))
        assert received(delivery, ["voice", "tone"]) == []


class TestADefinitionWithNoToolsListInheritsEveryTool:
    def test_every_tool_but_the_disallowed_ones_is_held(self, world) -> None:
        tools_world(world)
        define_agent(world, "critic", "disallowedTools: Edit")

        delivery = world.start_delegate("critic")

        assert tools_of(world, "critic") == AllToolsBut(frozenset({"Edit"}))
        assert received(delivery, ["voice", "tone"]) == ["voice"]


class TestAContextWithNoAgentDefinitionHasNoToolsFact:
    def test_a_delegate_with_no_definition_file_has_an_absent_tools_fact_named_in_the_record(
        self, world
    ) -> None:
        tools_world(world)

        delivery = world.start_delegate("critic")

        assert tools_of(world, "critic") is ABSENT
        assert received(delivery, ["voice", "tone"]) == []
        (record,) = world.records()
        (absent,) = [n for n in record["notices"] if n["kind"] == "tools-absent"]
        assert absent["shown"] is False
        assert "no definition file registers its agent type" in absent["subject"]

    def test_a_config_that_tests_no_tools_draws_no_absence_notice(self, world) -> None:
        world.rule("voice")
        world.write_config("defaults: voice\nagent critic:\n  include: voice\n")

        world.start_delegate("critic")

        (record,) = world.records()
        assert [n for n in record["notices"] if n["kind"] == "tools-absent"] == []

    def test_the_tools_test_over_an_absent_fact_and_its_negation_are_unknown(self) -> None:
        assert truth_of_tools("tools Bash", ABSENT) == "UNKNOWN"
        assert truth_of_tools("not tools Bash", ABSENT) == "UNKNOWN"


def truth_of_tools(text, tools) -> str:
    facts = Facts(model=ABSENT, agent=ABSENT, kind="delegate", flags=frozenset(), tools=tools)
    return evaluate(parse_condition(text), facts).name


class TestTheToolsFactIgnoresABackgroundSubagentsNarrowerToolSet:
    def test_a_background_delegates_tools_fact_reads_the_definition_alone(self, world) -> None:
        tools_world(world)
        define_agent(world, "critic", "tools: Edit")

        delivery = world.start_delegate("critic", run_in_background=True, tools=["Read"])

        assert received(delivery, ["voice", "tone"]) == ["tone"]


class TestTheCallersModelIsReadFromTheAgentToolHooksRecord:
    def test_two_agent_types_under_one_prompt_each_read_their_own_per_spawn_model(
        self, world
    ) -> None:
        model_world(world)
        caller_names(world, "haiku", "critic")
        caller_names(world, "opus", "scout")

        world.start_delegate("critic", agent_id="a1")
        world.start_delegate("scout", agent_id="a2")

        by_agent = {record["agent"]["name"]: model_of(record) for record in delegate_records(world)}
        assert by_agent == {"critic": ("haiku", "per-spawn"), "scout": ("opus", "per-spawn")}

    def test_a_spawn_naming_no_model_leaves_the_named_model_to_the_delegate_it_belongs_to(
        self, world
    ) -> None:
        model_world(world)
        define_agent(world, "critic", "model: sonnet")
        world.spawn("critic", model=None)
        world.spawn("critic", model="haiku")

        world.start_delegate("critic", agent_id="a1")
        world.start_delegate("critic", agent_id="a2")

        unnamed, named = delegate_records(world)
        assert model_of(unnamed) == ("sonnet", "definition-pin")
        assert model_of(named) == ("haiku", "per-spawn")


def haiku_rule_world(world) -> None:
    """A world whose rules give a haiku delegate the `terse` rule an opus delegate lacks."""
    world.rule("voice")
    world.rule("terse")
    world.write_config(
        "models: opus sonnet haiku\ndefaults: voice\nmodel haiku:\n  include: terse\n"
    )


def ambiguity_notices(record) -> list[dict]:
    return [n for n in record["notices"] if n["kind"] == "per-spawn-ambiguous"]


class TestSeveralMatchingPerSpawnRecordsNamingDifferentModels:
    def test_two_delegates_of_one_type_spawned_in_one_message_each_receive_their_own_models_rules(
        self, world
    ) -> None:
        haiku_rule_world(world)
        world.spawn("critic", model="haiku")
        world.spawn("critic", model="opus")

        first = world.start_delegate("critic", agent_id="a1")
        second = world.start_delegate("critic", agent_id="a2")

        assert received(first, ["voice", "terse"]) == ["voice", "terse"]
        assert received(second, ["voice", "terse"]) == ["voice"]
        records = delegate_records(world)
        assert [model_of(record) for record in records] == [
            ("haiku", "per-spawn"),
            ("opus", "per-spawn"),
        ]
        assert [n for record in records for n in ambiguity_notices(record)] == []

    def test_two_delegates_starting_at_once_each_claim_a_different_spawn(self, world) -> None:
        model_world(world)
        world.spawn("critic", model="haiku")
        world.spawn("critic", model="opus")

        def start(agent_id) -> Delivery:
            return world.start_delegate("critic", agent_id=agent_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(start, ["a1", "a2"]))

        assert sorted(model_of(record) for record in delegate_records(world)) == [
            ("haiku", "per-spawn"),
            ("opus", "per-spawn"),
        ]

    def test_the_record_of_a_start_finding_every_spawn_claimed_carries_the_unshown_notice(
        self, world
    ) -> None:
        model_world(world)
        parent_runs(world, SONNET_IDENTIFIER)
        caller_names(world, "haiku")
        caller_names(world, "opus")

        for agent_id in ("a1", "a2", "a3"):
            world.start_delegate("critic", agent_id=agent_id)

        first, second, third = delegate_records(world)
        assert (ambiguity_notices(first), ambiguity_notices(second)) == ([], [])
        assert model_of(third) == (SONNET_IDENTIFIER, "parent-record")
        (ambiguous,) = ambiguity_notices(third)
        assert ambiguous["shown"] is False

    def test_two_same_type_spawns_under_one_prompt_naming_one_model_give_that_model_with_no_notice(
        self, world
    ) -> None:
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
    def test_a_plugin_agent_reads_its_plugins_definition(self, world) -> None:
        world.rule("voice")
        world.write_config("models: haiku\ndefaults:\ntools Read:\n  include: voice\n")
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
    def test_a_per_spawn_model_outranks_a_built_in_agents_harness_pin(self, world) -> None:
        model_world(world)
        caller_names(world, "opus", "claude-code-guide")

        world.start_delegate("claude-code-guide")

        (record,) = delegate_records(world)
        assert model_of(record) == ("opus", "per-spawn")

    def test_a_per_spawn_model_outranks_the_default_variable_for_an_agent_the_engine_holds_no_pin_for(
        self, world
    ) -> None:
        model_world(world, **{DEFAULT_VARIABLE: SONNET_IDENTIFIER})
        caller_names(world, "haiku", "general-purpose")

        world.start_delegate("general-purpose")

        (record,) = delegate_records(world)
        assert model_of(record) == ("haiku", "per-spawn")


class TestTheSubagentForceVariableOutranksEveryAgentTypesPins:
    def test_a_pinned_built_in_agent_under_the_force_variable_alone_takes_the_parents_identifier(
        self, world
    ) -> None:
        model_world(world, **{FORCE: "1"})
        parent_runs(world, OPUS_IDENTIFIER)

        world.start_delegate("claude-code-guide")

        (record,) = delegate_records(world)
        assert model_of(record) == (OPUS_IDENTIFIER, FORCE)

    def test_an_agent_the_engine_holds_no_pin_for_takes_the_default_variable_under_both_variables(
        self, world
    ) -> None:
        model_world(world, **{FORCE: "1", DEFAULT_VARIABLE: HAIKU_IDENTIFIER})
        parent_runs(world, OPUS_IDENTIFIER)

        world.start_delegate("general-purpose")

        (record,) = delegate_records(world)
        assert record["model"]["identifier"] == HAIKU_IDENTIFIER


class TestAnEnvironmentVariableCountsAsSetUnlessEmptyOrFalse:
    def test_a_force_variable_holding_zero_has_no_effect(self, world) -> None:
        model_world(world, **{FORCE: "0", DEFAULT_VARIABLE: SONNET_IDENTIFIER})
        caller_names(world, "haiku")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert model_of(record) == ("haiku", "per-spawn")


class TestADelegatesModelFactComesFromFourSourcesInOrder:
    def test_a_delegate_with_no_other_source_takes_the_parents_recorded_identifier(
        self, world
    ) -> None:
        model_world(world)
        define_agent(world, "critic", "tools: Read")
        parent_runs(world, OPUS_IDENTIFIER)

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert model_of(record) == (OPUS_IDENTIFIER, "parent-record")

    def test_the_model_a_caller_names_for_one_spawn_decides_the_rules_that_spawn_receives(
        self, world
    ) -> None:
        world.rule("writing-code")
        world.write_config(
            "models: sonnet haiku\ndefaults: writing-code\nmodel haiku:\n  exclude: writing-code\n"
        )
        define_agent(world, "builder", "model: sonnet")
        caller_names(world, "haiku", "builder", prompt_id="p1")

        named = world.start_delegate("builder", agent_id="a1", prompt_id="p1")
        unnamed = world.start_delegate("builder", agent_id="a2", prompt_id="p2")

        assert received(named, ["writing-code"]) == []
        assert received(unnamed, ["writing-code"]) == ["writing-code"]
        first, second = delegate_records(world)
        assert model_of(first) == ("haiku", "per-spawn")
        assert first["model"]["name"] == "haiku"
        assert model_of(second) == ("sonnet", "definition-pin")
        assert second["model"]["name"] == "sonnet"


class TestTheDefaultVariableSitsBetweenThePinAndTheParent:
    def test_a_pin_outranks_the_default_variable_which_outranks_the_parent(self, world) -> None:
        model_world(world, **{DEFAULT_VARIABLE: SONNET_IDENTIFIER})
        parent_runs(world, OPUS_IDENTIFIER)
        define_agent(world, "pinned", "model: haiku")
        define_agent(world, "plain", "tools: Read")

        world.start_delegate("pinned", agent_id="a1")
        world.start_delegate("plain", agent_id="a2")

        pinned, plain = delegate_records(world)
        assert model_of(pinned) == ("haiku", "definition-pin")
        assert model_of(plain) == (SONNET_IDENTIFIER, "subagent-default-variable")


class TestAParentWithNoRecordedIdentifier:
    def test_the_delegates_model_is_missing_and_a_shown_notice_says_so(self, world) -> None:
        model_world(world)
        define_agent(world, "critic", "tools: Read")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["model"]["state"] == "missing"
        (notice,) = shown_notices(record)
        assert "no model identifier was available" in notice["subject"]


class TestEachDelegateStartClaimsTheOldestUnclaimedMatchingSpawnRecord:
    def test_a_resumed_delegate_receives_the_rules_of_its_first_start(self, world) -> None:
        haiku_rule_world(world)
        world.spawn("critic", model="haiku")
        world.spawn("critic", model="opus")
        first = world.start_delegate("critic", agent_id="a1")
        world.start_delegate("critic", agent_id="a2")

        resumed = world.start_delegate("critic", agent_id="a1")

        assert received(first, ["voice", "terse"]) == ["voice", "terse"]
        assert resumed.context == first.context


class TestAStartPayloadWithoutAPromptIdentifier:
    def test_the_per_spawn_source_yields_to_the_pin_then_the_default_variable_then_the_parent(
        self, world
    ) -> None:
        model_world(world, **{DEFAULT_VARIABLE: SONNET_IDENTIFIER})
        parent_runs(world, OPUS_IDENTIFIER)
        define_agent(world, "pinned", "model: haiku")
        define_agent(world, "plain", "tools: Read")
        caller_names(world, "opus", "pinned", prompt_id=None)
        caller_names(world, "opus", "plain", prompt_id=None)

        world.start_delegate("pinned", agent_id="a1", prompt_id=None)
        world.start_delegate("plain", agent_id="a2", prompt_id=None)
        del world.environment[DEFAULT_VARIABLE]
        world.start_delegate("plain", agent_id="a3", prompt_id=None)

        records = delegate_records(world)
        assert [model_of(record) for record in records] == [
            ("haiku", "definition-pin"),
            (SONNET_IDENTIFIER, "subagent-default-variable"),
            (OPUS_IDENTIFIER, "parent-record"),
        ]
        for record in records:
            (unreadable,) = [n for n in record["notices"] if n["kind"] == "per-spawn-unreadable"]
            assert unreadable["shown"] is False


class TestAProjectDefinitionWinsOverTheHomeOne:
    def test_the_pin_and_the_tools_come_from_the_project_file(self, world) -> None:
        for stem in ("reading", "editing"):
            world.rule(stem)
        world.write_config(
            "models: opus haiku\n"
            "defaults:\n"
            "tools Read:\n"
            "  include: reading\n"
            "tools Edit:\n"
            "  include: editing\n"
        )
        define_agent(world, "scout", "model: opus\ntools: Edit")
        project = world.config.parent / "project"
        (project / ".git").mkdir(parents=True)
        agents = project / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "scout.md").write_text(
            "---\nname: scout\ndescription: a test agent\nmodel: haiku\ntools: Read\n---\nbody\n",
            encoding="utf-8",
        )

        delivery = world.start_delegate("scout", cwd=str(project))

        (record,) = delegate_records(world)
        assert model_of(record) == ("haiku", "definition-pin")
        assert received(delivery, ["reading", "editing"]) == ["reading"]


class TestTheDefinitionPinsInherit:
    def test_the_delegate_takes_the_parents_identifier_ahead_of_the_default_variable(
        self, world
    ) -> None:
        model_world(world, **{DEFAULT_VARIABLE: SONNET_IDENTIFIER})
        parent_runs(world, OPUS_IDENTIFIER)
        define_agent(world, "critic", "model: inherit")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert model_of(record) == (OPUS_IDENTIFIER, "parent-record")


class TestABuiltInAgentWithoutAFile:
    def test_the_delegate_takes_the_harness_pin_and_the_record_names_it(self, world) -> None:
        model_world(world)

        world.start_delegate("claude-code-guide")

        (record,) = delegate_records(world)
        assert model_of(record) == ("haiku", "built-in-pin")


class TestADefinitionFileForABuiltInType:
    def test_a_definition_naming_no_model_hides_the_harness_pin(self, world) -> None:
        model_world(world)
        parent_runs(world, OPUS_IDENTIFIER)
        define_agent(world, "statusline-setup", "tools: Read")

        world.start_delegate("statusline-setup")

        (record,) = delegate_records(world)
        assert model_of(record) == (OPUS_IDENTIFIER, "parent-record")


class TestTheForceVariableAndADefaultModelAreBothSet:
    def test_the_default_variable_wins_over_the_definitions_pin(self, world) -> None:
        model_world(world, **{FORCE: "1", DEFAULT_VARIABLE: HAIKU_IDENTIFIER})
        define_agent(world, "critic", "model: opus")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert model_of(record) == (HAIKU_IDENTIFIER, FORCE)

    def test_with_no_default_variable_the_delegate_takes_the_parents_identifier(
        self, world
    ) -> None:
        model_world(world, **{FORCE: "1"})
        parent_runs(world, OPUS_IDENTIFIER)

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert model_of(record) == (OPUS_IDENTIFIER, FORCE)


class TestTheCoordinatorLeverGivesADelegateTheParentsModelFact:
    def test_it_overrides_the_callers_model_and_the_pin(self, world) -> None:
        model_world(world, **{COORDINATOR: "1"})
        parent_runs(world, OPUS_IDENTIFIER)
        define_agent(world, "critic", "model: sonnet")
        caller_names(world, "haiku", "critic", prompt_id="p1")

        world.start_delegate("critic", agent_id="a1", prompt_id="p1")
        world.start_delegate("critic", agent_id="a2", prompt_id="p2")

        records = delegate_records(world)
        assert [model_of(record) for record in records] == [(OPUS_IDENTIFIER, COORDINATOR)] * 2

    def test_with_both_force_levers_set_the_delegate_takes_the_parents_identifier(
        self, world
    ) -> None:
        model_world(world, **{COORDINATOR: "1", FORCE: "1", DEFAULT_VARIABLE: HAIKU_IDENTIFIER})
        parent_runs(world, OPUS_IDENTIFIER)

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["model"]["identifier"] == OPUS_IDENTIFIER


class TestTheDeliveryRecordNamesEachFactsSource:
    def test_a_record_names_the_identifier_its_claiming_name_the_agent_and_the_tools_source(
        self, world
    ) -> None:
        model_world(world)
        define_agent(world, "critic", "description: Reviews work")
        caller_names(world, "opus", "critic")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert model_of(record) == ("opus", "per-spawn")
        assert record["model"]["name"] == "opus"
        assert record["agent"] == {"state": "named", "name": "critic"}
        assert record["tools"]["state"] == "all-but"
        assert record["tools"]["source"] == str(world.config / "agents" / "critic.md")

    def test_the_delivered_text_holds_rule_text_only_and_the_record_names_the_pin(
        self, world
    ) -> None:
        model_world(world)
        define_agent(world, "critic", "model: haiku")

        delivery = world.start_delegate("critic")

        assert delivery.context == "text of voice\n"
        assert delivery.message is None
        (record,) = delegate_records(world)
        assert model_of(record) == ("haiku", "definition-pin")


class TestTheRecordNamesASessionModelsSource:
    def test_a_source_from_the_environment_names_the_variable_and_its_value(self, world) -> None:
        model_world(world, ANTHROPIC_MODEL=OPUS_IDENTIFIER)

        world.start_session(model=None)

        (record,) = world.records()
        assert record["model"]["source"] == f"ANTHROPIC_MODEL={OPUS_IDENTIFIER}"


class TestTheRecordNamesADelegateModelsSource:
    def test_a_source_from_a_force_lever_names_the_lever(self, world) -> None:
        model_world(world, **{FORCE: "1", DEFAULT_VARIABLE: HAIKU_IDENTIFIER})

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["model"]["source"] == FORCE


class TestTheRecordNamesTheIdentifierAndTheNameThatClaimedIt:
    def test_an_identifier_no_declared_name_claims_is_stated_unclaimed(self, world) -> None:
        model_world(world)

        world.start_session(model="glm-5")

        (record,) = world.records()
        assert record["model"]["identifier"] == "glm-5"
        assert record["model"]["state"] == "unclaimed"
        assert record["model"]["name"] is None


class TestTheRecordNamesTheAgentToolsAndFlagSources:
    def test_a_flag_a_toggle_set_names_toggle_as_its_source(self, world) -> None:
        world.rule("security-pass")
        world.write_config("flags: strict\ndefaults:\nflag strict:\n  include: security-pass\n")
        world.start_session()
        world.toggle_flags({"strict": "set"})

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["flags"] == [{"name": "strict", "source": "toggle"}]


def flag_names(record) -> list[str]:
    """The names of the flags a delivery record lists."""
    return sorted(flag["name"] for flag in record["flags"])


class TestAnUnsetFlagTestsFalseNeverUnknown:
    def test_a_declared_flag_not_set_gives_the_negated_block_and_the_record_lists_no_flag(
        self, world
    ) -> None:
        world.rule("security-pass")
        world.rule("voice")
        world.write_config(
            "flags: strict\n"
            "defaults:\n"
            "flag strict:\n"
            "  include: security-pass\n"
            "not flag strict:\n"
            "  include: voice\n"
        )

        delivery = world.start_session()

        assert received(delivery, ["security-pass", "voice"]) == ["voice"]
        (record,) = world.records()
        assert record["flags"] == []


class TestAFlagNobodyDeclares:
    def test_check_reports_an_error_naming_the_condition_and_the_flag(self, world) -> None:
        world.rule("voice")
        world.write_config("flags: strict\ndefaults:\nflag stirct:\n  include: voice\n")

        report = report_for(world)

        assert "error" in report
        assert "flag stirct" in report
        assert "`stirct`" in report

    def test_delivery_skips_the_block_with_a_shown_notice_and_delivers_the_rest(
        self, world
    ) -> None:
        world.rule("voice")
        world.rule("tone")
        world.write_config("flags: strict\ndefaults: tone\nnot flag stirct:\n  include: voice\n")

        delivery = world.start_session()

        assert received(delivery, ["voice", "tone"]) == ["tone"]
        assert delivery.message is not None
        assert "`not flag stirct`" in delivery.message
        assert "`stirct`" in delivery.message
        (record,) = world.records()
        assert record["withheld"] == []
        (skipped,) = [n for n in record["notices"] if n["kind"] == "block-skipped"]
        assert skipped["shown"] is True

    def test_a_flag_a_toggle_sets_without_a_declaration_gives_its_block_to_no_delegate(
        self, world
    ) -> None:
        world.rule("voice")
        world.rule("tone")
        world.write_config("flags: strict\ndefaults: tone\nflag ghost:\n  include: voice\n")
        world.toggle_flags({"ghost": "set"})

        delivery = world.start_delegate()

        assert received(delivery, ["voice", "tone"]) == ["tone"]
        (record,) = world.records()
        assert [n["kind"] for n in record["notices"] if n["kind"] == "block-skipped"] == [
            "block-skipped"
        ]


class TestALaunchFlagNobodyDeclares:
    def test_the_flag_is_dropped_changes_no_block_and_a_shown_notice_names_it(self, world) -> None:
        world.rule("security-pass")
        world.write_config("flags: strict\ndefaults:\nflag strict:\n  include: security-pass\n")
        world.environment["RULESETS_FLAGS"] = "strict"
        control = world.start_session(session_id="control")
        world.environment["RULESETS_FLAGS"] = "stirct,strict"

        delivery = world.start_session(session_id="s1")

        assert received(delivery, ["security-pass"]) == received(control, ["security-pass"])
        assert received(delivery, ["security-pass"]) == ["security-pass"]
        assert delivery.message is not None
        assert "stirct" in delivery.message
        (record,) = world.records("s1")
        assert flag_names(record) == ["strict"]


class TestALaunchFlagReachesTheFirstDelivery:
    def test_a_block_keyed_on_the_flag_removes_a_rule_from_the_first_delivery(self, world) -> None:
        world.rule("writing-code")
        world.write_config(
            "flags: without-writing-code\n"
            "defaults: writing-code\n"
            "flag without-writing-code:\n"
            "  exclude: writing-code\n"
        )
        control = world.start_session(session_id="control")
        world.environment["RULESETS_FLAGS"] = "without-writing-code"

        delivery = world.start_session(session_id="s1")

        assert received(control, ["writing-code"]) == ["writing-code"]
        assert received(delivery, ["writing-code"]) == []


class TestTwoLaunchFlags:
    def test_voice_terse_gives_the_terse_wording_to_session_and_delegate_and_the_record_names_it(
        self, world
    ) -> None:
        for stem in ("voice", "voice@terse", "security-pass"):
            world.rule(stem)
        world.write_config(
            "flags: voice-terse strict\n"
            "defaults: voice\n"
            "flag voice-terse:\n"
            "  include: voice@terse\n"
            "flag strict:\n"
            "  include: security-pass\n"
        )
        world.environment["RULESETS_FLAGS"] = "voice-terse,strict"

        session = world.start_session()
        delegate = world.start_delegate("critic")

        for delivery in (session, delegate):
            assert received(delivery, ["voice@terse", "voice", "security-pass"]) == [
                "voice@terse",
                "security-pass",
            ]
        session_record = world.records()[0]
        assert {"rule": "voice", "variant": "terse"}.items() <= session_record["rules"][1].items()
        assert session_record["flags"] == [
            {"name": "strict", "source": "launch"},
            {"name": "voice-terse", "source": "launch"},
        ]


class TestALaunchFlagReachesADelegate:
    def test_two_delegates_of_different_agent_types_both_hold_the_flag(self, world) -> None:
        world.rule("security-pass")
        world.write_config("flags: strict\ndefaults:\nflag strict:\n  include: security-pass\n")
        world.environment["RULESETS_FLAGS"] = "strict"

        world.start_session()
        first = world.start_delegate("critic", agent_id="a1")
        second = world.start_delegate("scout", agent_id="a2")

        assert received(first, ["security-pass"]) == ["security-pass"]
        assert received(second, ["security-pass"]) == ["security-pass"]


class TestAToggleUnsetMidSession:
    def test_a_later_delegate_composes_without_the_flag_and_the_earlier_record_keeps_it(
        self, world
    ) -> None:
        world.rule("voice")
        world.rule("voice@terse")
        world.write_config(
            "flags: voice-terse\ndefaults: voice\nflag voice-terse:\n  include: voice@terse\n"
        )
        world.environment["RULESETS_FLAGS"] = "voice-terse"
        world.start_session()
        earlier = world.start_delegate("critic", agent_id="a1")

        world.toggle_flags({"voice-terse": "unset"})
        later = world.start_delegate("critic", agent_id="a2")

        assert received(earlier, ["voice@terse", "voice"]) == ["voice@terse"]
        assert received(later, ["voice@terse", "voice"]) == ["voice"]
        first, second = delegate_records(world)
        assert first["flags"] == [{"name": "voice-terse", "source": "launch"}]
        assert second["flags"] == []

    def test_a_toggle_set_flag_holds_for_the_next_delegate_with_source_toggle(self, world) -> None:
        world.rule("security-pass")
        world.write_config("flags: strict\ndefaults:\nflag strict:\n  include: security-pass\n")
        world.start_session()
        world.toggle_flags({"strict": "set"})

        delegate = world.start_delegate("critic")

        assert received(delegate, ["security-pass"]) == ["security-pass"]
        (record,) = delegate_records(world)
        assert record["flags"] == [{"name": "strict", "source": "toggle"}]

    def test_a_toggle_never_changes_the_main_sessions_flags(self, world) -> None:
        world.rule("security-pass")
        world.write_config("flags: strict\ndefaults:\nflag strict:\n  include: security-pass\n")
        world.toggle_flags({"strict": "set"})

        session = world.start_session()

        assert received(session, ["security-pass"]) == []


class TestAModelNamedForOneSpawnSetsNoFlag:
    def test_each_delegates_flags_are_exactly_the_launch_flag(self, world) -> None:
        world.rule("voice")
        world.write_config("models: opus haiku\nflags: strict\ndefaults: voice\n")
        world.environment["RULESETS_FLAGS"] = "strict"
        caller_names(world, "haiku", "critic")

        world.start_session()
        world.start_delegate("critic", agent_id="a1")
        world.start_delegate("scout", agent_id="a2")

        named, unnamed = delegate_records(world)
        assert model_of(named)[1] == "per-spawn"
        assert flag_names(named) == ["strict"]
        assert flag_names(unnamed) == ["strict"]


SESSION_MODELS = ["opus", "sonnet", "haiku"]


class TestTheHarnessReportsTheModel:
    def test_the_reported_identifier_is_claimed_and_the_environment_is_not_read(
        self, tmp_path, read_spy
    ) -> None:
        environment = read_spy({"ANTHROPIC_MODEL": HAIKU_IDENTIFIER})

        resolution = session_model.resolve_session_model(
            {"model": OPUS_IDENTIFIER, "session_id": "s1"}, SESSION_MODELS, environment, tmp_path
        )

        assert resolution.fact == model_fact.Claimed("opus", OPUS_IDENTIFIER, "harness-reported")
        assert environment.reads.isdisjoint({"ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL"})


class TestBothEnvironmentVariablesAreSet:
    def test_anthropic_model_is_read_before_anthropic_default_model(self, tmp_path) -> None:
        environment = {
            "ANTHROPIC_MODEL": HAIKU_IDENTIFIER,
            "ANTHROPIC_DEFAULT_MODEL": OPUS_IDENTIFIER,
        }

        resolution = session_model.resolve_session_model(
            {"session_id": "s1"}, SESSION_MODELS, environment, tmp_path
        )

        assert resolution.fact.identifier == HAIKU_IDENTIFIER
        assert resolution.fact.name == "haiku"


class TestOnlyTheRecordNamesAModel:
    def test_the_recorded_identifier_is_taken_and_the_record_is_its_source(self, tmp_path) -> None:
        record = tmp_path / "models" / "s1.json"
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps({"identifier": OPUS_IDENTIFIER}), encoding="utf-8")

        resolution = session_model.resolve_session_model(
            {"session_id": "s1"}, SESSION_MODELS, {}, tmp_path
        )

        assert resolution.fact == model_fact.Claimed("opus", OPUS_IDENTIFIER, "session-record")


class TestTheHarnessReportsAnUnclaimedIdentifier:
    def test_it_stands_unclaimed_and_the_environment_is_not_read(self, tmp_path, read_spy) -> None:
        environment = read_spy({"ANTHROPIC_MODEL": OPUS_IDENTIFIER})

        resolution = session_model.resolve_session_model(
            {"model": "glm-5", "session_id": "s1"}, SESSION_MODELS, environment, tmp_path
        )

        assert resolution.fact == model_fact.Unclaimed("glm-5", "harness-reported")
        assert environment.reads.isdisjoint({"ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL"})


class TestAModelSwitchsTargetIsTheNextDeliverysIdentifier:
    def test_a_switch_to_an_identifier_no_name_claims_delivers_it_unclaimed_and_a_shown_notice_names_it(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.rule("opus-rules")
        world.write_config(
            DECLARED + ("defaults: core-rules\nmodel opus:\n  include: opus-rules\n")
        )
        world.start_session()

        delivery = world.switch_model("glm-5", from_model="claude-opus-5-5", prompt_id="p1")

        (_, record) = world.records()
        assert record["model"] == {
            "state": "unclaimed",
            "name": None,
            "identifier": "glm-5",
            "source": "switch-target",
            "not_a_string": None,
        }
        (unclaimed,) = [n for n in record["notices"] if n["kind"] == "model-unclaimed"]
        assert unclaimed["shown"] is True
        assert "glm-5" in unclaimed["subject"]
        assert delivery.context == "text of core-rules\n"
        assert delivery.message is None
        assert record["message_sent"] is False
