#!/usr/bin/env python3
"""A context carries facts, and a block's condition tests them.

Serves the person who writes a config keyed on model, agent, tools, flag, and session
(`docs/config.md`, "Conditions" and "Which statement wins"), and whose sessions and delegates
receive the result: a declared model name claims the identifiers it prefixes, a block takes the
rank of its highest fact, an unclaimed model tests false, and a missing fact makes no block keyed
on it apply. The cases run the hook entries over a configuration directory under `tmp_path`.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_context_facts.py`.
"""

import json
import pathlib

import pytest
from delivery_world import DECLARED
from rulesets.check.report_format import report_lines
from rulesets.check.run import check


def received(delivery, stems) -> list[str]:
    """The stems whose body the delivery carries, in the order given."""
    return [stem for stem in stems if f"text of {stem}\n" in delivery.context]


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
        world.user_agent("critic", "haiku")
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
        world.user_agent("critic", "haiku")

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
        world.user_agent("critic", "haiku")

        world.start_delegate("critic")

        (record,) = world.records()
        assert (record["model"]["name"], record["agent"]["name"], record["kind"]) == (
            "haiku",
            "critic",
            "delegate",
        )


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

    def test_a_negated_model_test_holds_for_a_critic_on_another_claimed_model(self, world) -> None:
        world.rule("planning")
        world.write_config(
            "models: opus haiku\ndefaults:\nagent critic and not model haiku:\n  include: planning\n"
        )
        world.spawn("critic", model="opus")
        world.spawn("critic", model="haiku")

        on_opus = world.start_delegate("critic", agent_id="a1")
        on_haiku = world.start_delegate("critic", agent_id="a2")

        assert received(on_opus, ["planning"]) == ["planning"]
        assert received(on_haiku, ["planning"]) == []


class TestConditionsTestFactsOnly:
    @pytest.mark.parametrize(
        ("condition", "reported"),
        [
            ("project amboss", "`project amboss`"),
            ("env CI", "`env CI`"),
            ("(agent critic and flag strict", "`(agent critic and flag strict`"),
        ],
        ids=["a project test", "an environment variable test", "unbalanced parentheses"],
    )
    def test_a_condition_testing_more_than_facts_is_a_check_error_and_the_block_applies_nowhere(
        self, world, condition, reported
    ) -> None:
        world.rule("voice")
        world.write_config(f"flags: strict\ndefaults:\n{condition}:\n  include: voice\n")

        report = report_for(world)

        assert "error" in report
        assert reported in report
        assert received(world.start_session(), ["voice"]) == []
        assert received(world.start_delegate("critic"), ["voice"]) == []


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

    def test_an_agent_a_tool_and_a_session_identifier_nobody_declares_are_no_check_error(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(
            "defaults:\n"
            "agent eval-runner:\n"
            "  include: voice\n"
            "tools Bash:\n"
            "  include: voice\n"
            "session abc123:\n"
            "  include: voice\n"
            "not tools Edit and session xyz789:\n"
            "  include: voice\n"
        )

        assert check(world.rulesets).errors == ()


class TestTheEngineHoldsNoModelName:
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
    @pytest.mark.parametrize("identifier", ["glm-5", "claude-nova-1"])
    def test_an_identifier_no_declared_name_claims_receives_the_defaults_and_the_negated_block(
        self, world, identifier
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

        delivery = world.start_session(model=identifier)

        assert received(delivery, stems) == ["writing-code", "voice"]
        assert delivery.message is not None
        assert identifier in delivery.message
        assert identifier not in delivery.context
        (record,) = world.records()
        assert record["model"]["state"] == "unclaimed"


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


def model_of(record) -> tuple[str, str]:
    """The identifier and the source a delegate record names for its model."""
    return record["model"]["identifier"], record["model"]["source"]


SONNET_IDENTIFIER = "claude-sonnet-5"


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
        (record,) = world.records()
        assert record["agent"]["state"] == "absent"


class TestATestOverAnAbsentFactEvaluatesUnknown:
    def test_a_negation_over_an_absent_fact_stays_unknown_and_the_block_does_not_apply(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config("defaults:\nnot agent critic:\n  include: voice\n")

        delivery = world.start_session()

        assert received(delivery, ["voice"]) == []


class TestConditionsCombineTrueFalseAndUnknownByThreeValuedLogic:
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


TOOL_BLOCKS = "defaults:\ntools Bash:\n  include: voice\ntools Edit:\n  include: tone\n"


def define_agent(world, name, front) -> None:
    """An agent definition under the configuration directory with the given frontmatter lines."""
    path = world.config / "agents" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: a test agent\n{front}\n---\nbody\n", encoding="utf-8"
    )


def tools_world(world) -> None:
    for stem in ("voice", "tone"):
        world.rule(stem)
    world.write_config(TOOL_BLOCKS)


class TestToolsComeFromTheAgentDefinition:
    @pytest.mark.parametrize("listed", ["Read, Grep, Bash", "[Read, Grep, Bash]"])
    def test_the_tools_a_definition_lists_decide_the_blocks_a_delegate_receives(
        self, world, listed
    ) -> None:
        tools_world(world)
        define_agent(world, "critic", f"tools: {listed}")

        delivery = world.start_delegate("critic")

        assert received(delivery, ["voice", "tone"]) == ["voice"]


class TestADisallowedToolEntryRemovesTheWholeTool:
    def test_an_entry_with_a_specifier_removes_the_tool(self, world) -> None:
        tools_world(world)
        define_agent(world, "critic", "tools: Read, Grep, Bash\ndisallowedTools: Bash(git push *)")

        delivery = world.start_delegate("critic")

        assert received(delivery, ["voice", "tone"]) == []


class TestADefinitionWithNoToolsListInheritsEveryTool:
    def test_every_tool_but_the_disallowed_ones_is_held(self, world) -> None:
        tools_world(world)
        define_agent(world, "critic", "disallowedTools: Edit")

        delivery = world.start_delegate("critic")

        assert received(delivery, ["voice", "tone"]) == ["voice"]


class TestAContextWithNoAgentDefinitionHasNoToolsFact:
    def test_a_delegate_with_no_definition_file_receives_no_tools_block(self, world) -> None:
        tools_world(world)

        delivery = world.start_delegate("critic")

        assert received(delivery, ["voice", "tone"]) == []
        (record,) = world.records()
        assert record["tools"]["state"] == "absent"


class TestTheToolsFactIgnoresABackgroundSubagentsNarrowerToolSet:
    def test_a_background_delegates_tools_fact_reads_the_definition_alone(self, world) -> None:
        tools_world(world)
        define_agent(world, "critic", "tools: Edit")

        delivery = world.start_delegate("critic", run_in_background=True, tools=["Read"])

        assert received(delivery, ["voice", "tone"]) == ["tone"]


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
        records = world.delegate_records()
        assert [model_of(record) for record in records] == [
            ("haiku", "per-spawn"),
            ("opus", "per-spawn"),
        ]
        assert [n for record in records for n in ambiguity_notices(record)] == []

    def test_the_record_of_a_start_finding_every_spawn_claimed_carries_the_unshown_notice(
        self, world
    ) -> None:
        model_world(world)
        parent_runs(world, SONNET_IDENTIFIER)
        caller_names(world, "haiku")
        caller_names(world, "opus")

        for agent_id in ("a1", "a2", "a3"):
            world.start_delegate("critic", agent_id=agent_id)

        first, second, third = world.delegate_records()
        assert (ambiguity_notices(first), ambiguity_notices(second)) == ([], [])
        assert model_of(third) == (SONNET_IDENTIFIER, "parent-record")
        (ambiguous,) = ambiguity_notices(third)
        assert ambiguous["shown"] is False


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

        (record,) = world.delegate_records()
        assert model_of(record) == ("haiku", "definition-pin")
        assert received(delivery, ["reading", "editing"]) == ["reading"]


class TestTheDeliveryRecordNamesEachFactsSource:
    def test_a_record_names_the_identifier_its_claiming_name_the_agent_and_the_tools_source(
        self, world
    ) -> None:
        model_world(world)
        define_agent(world, "critic", "description: Reviews work")
        caller_names(world, "opus", "critic")

        world.start_delegate("critic")

        (record,) = world.delegate_records()
        assert model_of(record) == ("opus", "per-spawn")
        assert record["model"]["name"] == "opus"
        assert record["agent"] == {"state": "named", "name": "critic"}
        assert record["tools"]["state"] == "all-but"
        assert record["tools"]["source"] == str(world.config / "agents" / "critic.md")


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
        first, second = world.delegate_records()
        assert first["flags"] == [{"name": "voice-terse", "source": "launch"}]
        assert second["flags"] == []


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
        assert (record["model"]["state"], record["model"]["identifier"]) == ("unclaimed", "glm-5")
        (unclaimed,) = [n for n in record["notices"] if n["kind"] == "model-unclaimed"]
        assert unclaimed["shown"] is True
        assert "glm-5" in unclaimed["subject"]
        assert delivery.context == "text of core-rules\n"
        assert delivery.message is None
        assert record["message_sent"] is False
