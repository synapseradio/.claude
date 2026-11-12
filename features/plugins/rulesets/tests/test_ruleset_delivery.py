#!/usr/bin/env python3
"""A context receives its rules by hook, as rule text only, and the person hears of problems.

Serves the person whose sessions and delegates start with rules, and the engineer who reads the
delivery record afterwards. Each case builds a configuration directory under `tmp_path` and runs
the hook entries that `hooks/hooks.json` wires for an event, as the harness runs them.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_ruleset_delivery.py`.
"""

import hashlib
import json
import pathlib
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
import yaml
from delivery_world import (
    DECLARED,
    HOOKS_JSON,
    OPUS,
    Delivery,
    World,
    delivered,
    matcher_admits,
    select_commands,
)
from launcher_stubs import launch, path_of, stub

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.locations import Locations  # noqa: E402  (path must be set before this import)
from rulesets.session.state import (  # noqa: E402
    Band,
    FlagSetting,
    SessionState,
    read_state,
    write_state,
)


@pytest.fixture
def world(tmp_path) -> World:
    return World(tmp_path)


class TestEveryContextReceivesItsRulesByHook:
    def test_a_main_session_receives_the_body_of_core_rules_through_the_session_start_hook(
        self, world
    ) -> None:
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.write_config(DECLARED + "defaults: core-rules\n")

        delivery = world.start_session()

        assert delivery.context == "Hold every rule as mandatory.\n"
        assert delivery.targets == {"SessionStart"}

    def test_a_delegate_receives_its_rules_in_its_own_context_and_the_main_session_gains_none(
        self, world
    ) -> None:
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.write_config(DECLARED + "defaults: core-rules\n")
        world.start_session()

        delivery = world.start_delegate("critic")

        assert delivery.context == "Hold every rule as mandatory.\n"
        assert delivery.targets == {"SubagentStart"}

    def test_a_delivery_leaves_the_agent_definition_file_byte_for_byte_as_it_was(
        self, world
    ) -> None:
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.write_config(DECLARED + "defaults: core-rules\n")
        definition = world.config / "agents" / "critic.md"
        definition.parent.mkdir(parents=True)
        definition.write_bytes(
            b"---\nname: critic\nmodel: haiku\n---\nReview the diff.\r\n\xc3\xa9"
        )
        before = definition.read_bytes()

        delivery = world.start_delegate("critic")

        assert delivery.context == "Hold every rule as mandatory.\n"
        assert definition.read_bytes() == before

    def test_a_delivery_leaves_a_project_scope_agent_definition_file_byte_for_byte_as_it_was(
        self, world
    ) -> None:
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.write_config(DECLARED + "defaults: core-rules\n")
        definition = world.project / ".claude" / "agents" / "critic.md"
        definition.parent.mkdir(parents=True)
        definition.write_bytes(
            b"---\nname: critic\ndescription: a test agent\ntools: Read, Grep\n---\n"
            b"Review the diff.\r\n\xc3\xa9"
        )
        before = definition.read_bytes()

        delivery = world.start_delegate("critic", cwd=str(world.project))

        assert delivery.context == "Hold every rule as mandatory.\n"
        (record,) = delegate_records(world)
        assert record["tools"]["state"] == "listed", "the delegate read the project definition"
        assert definition.read_bytes() == before


ALL_PARTS = [str(number) for number in range(1, 11)]


def part_numbers(commands) -> list[str]:
    return [command.rsplit("--part ", 1)[1] for command in commands if "--part " in command]


class TestTheHarnessMatchersAreHonoredByTheWorldThatRunsTheHooks:
    @pytest.mark.parametrize(
        ("matcher", "value", "admitted"),
        [
            (None, "resume", True),
            ("", "resume", True),
            ("*", "resume", True),
            ("startup", "startup", True),
            ("startup", "resume", False),
            ("startup|resume", "resume", True),
            ("startup, clear", "clear", True),
            ("Edit", "NotebookEdit", False),
            ("^Notebook", "NotebookEdit", True),
            ("^Notebook", "Edit", False),
        ],
    )
    def test_a_matcher_admits_the_values_the_hooks_documentation_gives_it(
        self, matcher, value, admitted
    ) -> None:
        assert matcher_admits(matcher, value) is admitted

    def test_a_group_whose_matcher_leaves_out_a_value_runs_no_command_for_it(self) -> None:
        groups = [
            {"matcher": "startup", "hooks": [{"command": "only-at-startup"}]},
            {"hooks": [{"command": "always"}]},
        ]

        assert select_commands(groups, "startup") == ["only-at-startup", "always"]
        assert select_commands(groups, "resume") == ["always"]


class TestEveryDeliveryEntryRunsWhateverStartsTheContext:
    @pytest.mark.parametrize("source", ["startup", "resume", "clear", "compact", "fork"])
    def test_every_session_start_entry_runs_for_each_source(self, world, source) -> None:
        assert part_numbers(world.commands_for("SessionStart", source)) == ALL_PARTS

    @pytest.mark.parametrize(
        "agent_type",
        ["general-purpose", "Explore", "Plan", "fork", "critic", "plugin:reviewer", ""],
    )
    def test_every_subagent_start_entry_runs_for_each_agent_type(self, world, agent_type) -> None:
        assert part_numbers(world.commands_for("SubagentStart", agent_type)) == ALL_PARTS

    @pytest.mark.parametrize("target", [OPUS, "claude-haiku-4-5", "glm-5", ""])
    def test_every_model_switch_entry_runs_for_each_target(self, world, target) -> None:
        assert part_numbers(world.commands_for("PostModelSwitch", target)) == ALL_PARTS

    @pytest.mark.parametrize("reason", ["clear", "resume", "logout", "prompt_input_exit", "other"])
    def test_the_session_end_entry_runs_for_each_reason(self, world, reason) -> None:
        assert [c for c in world.commands_for("SessionEnd", reason) if c.endswith("--end")]


def engine_files(world) -> dict[pathlib.Path, bytes]:
    """Every file the engine keeps under the configuration directory, with its bytes."""
    root = world.config / ".tmp" / "rulesets-engine"
    return {path: path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


class TestAForkedSessionAndAForkSubagentReceiveNothingAndLeaveNoRecord:
    def test_a_forked_session_start_delivers_nothing_and_leaves_no_record(self, world) -> None:
        world.rule("core-rules")
        world.rule("sorting")
        world.write_config(DECLARED + "defaults: core-rules sorting\n")
        assert world.start_session().context == "text of core-rules\ntext of sorting\n"
        transcript = world.transcripts / "s2.jsonl"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text("{}\n", encoding="utf-8")
        before = engine_files(world)
        payload = {"session_id": "s2", "source": "fork", "model": OPUS}
        payload["transcript_path"] = str(transcript)

        delivery = world.run_event("SessionStart", payload)
        first_part = world.run_part_process("SessionStart", payload, 1)

        assert delivery.context == ""
        assert delivery.message is None
        assert set(delivery.outputs.values()) == {""}
        assert (first_part.returncode, first_part.stdout, first_part.stderr) == (0, "", "")
        assert engine_files(world) == before
        assert world.records("s2") == []
        assert world.model_record("s2") is None
        assert not world.state_file("s2").exists()

    def test_a_fork_subagent_start_delivers_nothing_and_leaves_no_record(self, world) -> None:
        world.rule("core-rules")
        world.rule("sorting")
        world.write_config(DECLARED + "defaults: core-rules sorting\n")
        assert world.start_session().context == "text of core-rules\ntext of sorting\n"
        before = engine_files(world)

        delivery = world.start_delegate("fork")
        first_part = world.run_part_process(
            "SubagentStart",
            {"session_id": "s1", "agent_id": "a2", "agent_type": "fork", "prompt_id": "p1"},
            1,
        )

        assert delivery.context == ""
        assert delivery.message is None
        assert set(delivery.outputs.values()) == {""}
        assert (first_part.returncode, first_part.stdout, first_part.stderr) == (0, "", "")
        assert engine_files(world) == before
        assert [r for r in world.records() if r["agent_id"] in ("a1", "a2")] == []


class TestDeliveredTextIsRuleTextOnly:
    def test_a_part_holds_each_rules_marker_and_body_sorted_by_name_and_no_other_line(
        self, world
    ) -> None:
        world.rule("sorting", "Sort what you hold.\n")
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.write_config(DECLARED + "defaults: sorting core-rules\n")

        delivery = world.start_session()

        assert delivery.received.splitlines() == [
            "<!-- rule: core-rules -->",
            "",
            "Hold every rule as mandatory.",
            "<!-- rule: sorting -->",
            "",
            "Sort what you hold.",
        ]

    def test_a_variant_arrives_under_its_rules_marker_which_names_no_variant(self, world) -> None:
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.write_config(DECLARED + "defaults: voice\nagent critic:\n  include: voice@terse\n")

        delivery = world.start_delegate("critic")

        assert delivery.received == "<!-- rule: voice -->\n\nterse voice\n"

    def test_markers_count_toward_the_part_budget(self, world) -> None:
        world.rule("a-rule", "a" * 4489 + "\n")
        world.rule("b-rule", "b" * 4489 + "\n")
        world.write_config(DECLARED + "defaults: all.*\n")

        delivery = world.start_session()

        assert {part: text[:21] for part, text in delivery.received_parts.items()} == {
            1: "<!-- rule: a-rule -->",
            2: "<!-- rule: b-rule -->",
        }
        assert all(len(text) <= 9000 for text in delivery.received_parts.values())


def unreadable(path) -> pathlib.Path:
    path.chmod(0o000)
    return path


def notice_entries(world, kind) -> list[dict]:
    return [n for r in world.records() for n in r["notices"] if n["kind"] == kind]


class TestNoticesReachThePersonAndTheRecordNeverTheAgent:
    def test_a_delivery_that_raises_no_shown_notice_shows_the_person_no_message(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")

        delivery = world.start_session()

        assert delivery.message is None
        assert [r["message_sent"] for r in world.records()] == [False]

    def test_several_shown_notices_reach_the_person_as_one_message_and_the_record_as_one_entry_each(
        self, world
    ) -> None:
        world.rule("voice")
        unreadable(world.rule("tone"))
        world.write_config(DECLARED + "defaults: voice tone ghost-one ghost-two\n")

        delivery = world.start_session()

        assert len(delivery.messages) == 1
        assert all(name in delivery.message for name in ("ghost-one", "ghost-two", "tone"))
        shown = [n["kind"] for r in world.records() for n in r["notices"] if n["shown"]]
        assert sorted(shown) == ["reference-skipped", "reference-skipped", "rule-withheld"]
        assert delivery.context == "text of voice\n"
        assert [r["message_sent"] for r in world.records()] == [True]


class TestDeliveryProblemsAreShownNotices:
    def test_an_unclaimed_model_an_undeclared_flag_and_a_variant_without_a_default_stay_out_of_the_agents_context(
        self, world
    ) -> None:
        world.rule("voice")
        world.rule("tone@dry")
        world.write_config("models: opus\nflags: strict\ndefaults: voice tone\n")
        world.environment["RULESETS_FLAGS"] = "stirct"

        delivery = world.start_session(model="claude-x-1")

        assert len(delivery.messages) == 1
        assert all(name in delivery.message for name in ("claude-x-1", "stirct", "tone"))
        assert delivery.context == "text of voice\n"


class TestAnUnreadableRuleFileIsWithheld:
    def test_the_session_receives_voice_and_not_tone_and_the_notice_names_the_file_and_the_error(
        self, world
    ) -> None:
        world.rule("voice")
        unreadable(world.rule("tone"))
        world.write_config(DECLARED + "defaults: tone voice\n")

        delivery = world.start_session()

        assert delivery.context == "text of voice\n"
        assert "tone.md" in delivery.message
        assert "Permission denied" in delivery.message
        assert [w["rule"] for r in world.records() for w in r["withheld"]] == ["tone"]


class TestFactsSwitchesAndHostVariablesGoToTheRecordAlone:
    def test_an_absent_agent_fact_reaches_the_record_and_shows_no_message(self, world) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\nagent eval-runner:\n  include: voice\n")

        delivery = world.start_session()

        assert [n["shown"] for n in notice_entries(world, "agent-absent")] == [False]
        assert delivery.message is None


class TestADelegateStartThatShowsNoMessageSendsShownNoticesToTheRecordAlone:
    def test_a_withheld_rule_at_a_delegates_start_is_a_shown_notice_in_the_record_and_no_message(
        self, world
    ) -> None:
        world.rule("voice")
        unreadable(world.rule("tone"))
        world.write_config(DECLARED + "defaults: tone voice\n")

        session = world.start_session()

        delivery = world.start_delegate("critic")

        assert delivery.messages == []
        assert delivery.context == "text of voice\n"
        (start, delegate) = world.records()
        assert [n["shown"] for n in start["notices"] if n["kind"] == "rule-withheld"] == [True]
        assert [n["shown"] for n in delegate["notices"] if n["kind"] == "rule-withheld"] == [True]
        assert session.message is not None
        assert start["message_sent"] is True, "a session start shows the notice"
        assert delegate["message_sent"] is False, "a delegate start shows no message"


class TestEveryPartOfOneDeliveryCarriesWhatItsFirstPartComposed:
    def test_later_parts_ignore_a_toggle_and_a_launch_flag_that_arrive_after_the_first_part(
        self, world
    ) -> None:
        bodies = {name: f"{name} " + "x" * 5990 + "\n" for name in ("a-rule", "b-rule", "c-rule")}
        for name, text in bodies.items():
            world.rule(name, text)
        world.rule("security-pass")
        world.write_config(
            DECLARED + "flags: strict\n" + "defaults: a-rule b-rule c-rule\n" + "flag strict:\n"
            "  include: security-pass\n"
        )
        payload = {"session_id": "s1", "agent_id": "a1", "agent_type": "critic", "prompt_id": "p1"}

        first = world.run_part("SubagentStart", payload, 1)
        world.rule("b-rule", "b-rule EDITED after the first part\n")
        (world.rulesets / "rules" / "c-rule.md").unlink()
        write_state(Locations(world.config), "s1", SessionState(Band.ALL))
        world.environment["RULESETS_FLAGS"] = "strict"
        later = {part: world.run_part("SubagentStart", payload, part) for part in range(2, 11)}

        delivery = Delivery({1: first, **later})
        assert delivery.context == "".join(bodies.values())
        assert "security-pass" not in delivery.context
        assert [part for part, out in delivery.outputs.items() if out] == [1, 2, 3]


class TestRulesPastTheLastPartReachAShownNotice:
    def test_a_composition_needing_eleven_parts_delivers_ten_and_names_the_rule_left_out(
        self, world
    ) -> None:
        names = [f"rule-{number:02d}" for number in range(10)]
        bodies = {name: name + " " + "x" * (8500 - len(name) - 2) + "\n" for name in names}
        for name, text in bodies.items():
            world.rule(name, text)
        world.rule("zeta", "zeta " + "x" * 8494 + "\n")
        world.write_config(DECLARED + "defaults: all.*\n")

        delivery = world.start_session()

        assert delivery.context == "".join(bodies.values())
        assert "zeta" in delivery.message
        (record,) = world.records()
        assert record["left_out"] == ["zeta"]
        assert [rule["rule"] for rule in record["rules"]] == [*names, "zeta"]
        left_out = notice_entries(world, "rule-left-out")
        assert [(n["shown"], "zeta" in n["subject"]) for n in left_out] == [(True, True)]


CORE = "text of core-rules\n"
SECURITY = "text of security-pass\n"


def declare_strict(world) -> None:
    """A pool whose rule `security-pass` joins a context that holds the flag `strict`."""
    world.rule("core-rules")
    world.rule("security-pass")
    world.write_config(
        DECLARED + "flags: strict\n" + "defaults: core-rules\n" + "flag strict:\n"
        "  include: security-pass\n"
    )


class TestAToggleReachesOnlyDelegateDeliveriesThatBeginAfterIt:
    def test_a_rule_a_toggle_removes_stays_in_the_main_session_and_leaves_the_next_delegate(
        self, world
    ) -> None:
        world.rule("writing-code")
        world.rule("voice")
        world.write_config(
            DECLARED
            + "flags: without-writing-code\n"
            + "defaults: writing-code voice\n"
            + "flag without-writing-code:\n"
            "  exclude: writing-code\n"
        )
        session = world.start_session()
        assert "text of writing-code" in session.context

        toggled = world.toggle("flag without-writing-code")

        assert toggled.returncode == 0, toggled.stderr
        assert "text of writing-code" not in toggled.stdout
        assert world.start_delegate().context == "text of voice\n"
        for source in ("compact", "resume"):
            later = world.start_session(source=source)
            assert later.context == "text of voice\ntext of writing-code\n", source

    def test_a_compaction_after_a_toggle_composes_from_the_launch_flags_alone(self, world) -> None:
        world.rule("core-rules")
        world.rule("security-pass")
        world.rule("loud-pass")
        world.write_config(
            DECLARED + "flags: strict loud\n" + "defaults: core-rules\n" + "flag strict:\n"
            "  include: security-pass\n"
            "flag loud:\n"
            "  include: loud-pass\n"
        )
        world.environment["RULESETS_FLAGS"] = "loud"
        assert world.toggle("flag strict").returncode == 0

        compacted = world.start_session(source="compact")

        assert compacted.context == "text of core-rules\ntext of loud-pass\n"

    def test_a_running_delegate_keeps_the_rules_its_first_part_composed_when_none_is_toggled(
        self, world
    ) -> None:
        bodies = {name: f"{name} " + "x" * 5990 + "\n" for name in ("a-rule", "b-rule", "c-rule")}
        for name, text in bodies.items():
            world.rule(name, text)
        world.rule("writing-code")
        world.write_config(DECLARED + "defaults: writing-code a-rule b-rule c-rule\n")
        payload = {"session_id": "s1", "agent_id": "a1", "agent_type": "critic", "prompt_id": "p1"}

        first = world.run_part("SubagentStart", payload, 1)
        world.rule("b-rule", "b-rule EDITED after the first part\n")
        (world.rulesets / "rules" / "c-rule.md").unlink()
        assert world.toggle("none").returncode == 0
        later = {part: world.run_part("SubagentStart", payload, part) for part in range(2, 11)}

        delivery = Delivery({1: first, **later})
        assert delivery.context == "".join(bodies.values()) + "text of writing-code\n"
        assert world.start_delegate(agent_id="a2").context == ""

    def test_all_toggled_after_the_first_delivery_gives_the_main_session_nothing_and_the_next_delegate_every_rule(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.rule("critic-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        assert world.start_session().context == CORE

        toggled = world.toggle("all")

        assert toggled.returncode == 0, toggled.stderr
        assert "text of" not in toggled.stdout
        assert world.start_delegate().context == CORE + "text of critic-rules\n"
        for source in ("compact", "resume"):
            assert world.start_session(source=source).context == CORE, source


class TestThePluginShipsAToggleSkillWithFiveActions:
    def test_the_flag_action_sets_a_declared_flag_for_the_next_delegate_and_names_toggle_as_its_source(
        self, world
    ) -> None:
        declare_strict(world)

        toggled = world.toggle("flag strict")
        delivery = world.start_delegate()

        assert toggled.returncode == 0, toggled.stderr
        assert delivery.context == CORE + SECURITY
        (record,) = world.records()
        assert [(f["name"], f["source"]) for f in record["flags"]] == [("strict", "toggle")]


class TestTheActionsAllAndNoneSetTheSessionBandsList:
    def test_the_later_of_all_and_none_decides_in_each_of_two_sessions(self, world) -> None:
        world.rule("core-rules")
        world.rule("critic-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")

        for action in ("all", "none"):
            assert world.toggle(action, session_id="all-then-none").returncode == 0
        for action in ("none", "all"):
            assert world.toggle(action, session_id="none-then-all").returncode == 0

        first = world.start_delegate(session_id="all-then-none")
        second = world.start_delegate(session_id="none-then-all")
        assert first.context == ""
        assert second.context == CORE + "text of critic-rules\n"


class TestTheFlagActionsCheckTheNameAgainstTheConfigsFlags:
    @pytest.mark.parametrize("action", ["flag", "unflag"])
    def test_an_undeclared_flag_name_is_named_refused_and_writes_nothing(
        self, world, action
    ) -> None:
        declare_strict(world)
        before = world.start_delegate(agent_id="a0").context

        toggled = world.toggle(f"{action} stirct")

        assert toggled.returncode != 0
        assert "stirct" in toggled.stderr
        assert not world.state_file().exists()
        assert world.start_delegate(agent_id="a1").context == before == CORE

    @pytest.mark.parametrize("action", ["flag", "unflag"])
    def test_an_undeclared_flag_name_leaves_the_state_a_toggle_already_wrote_as_it_was(
        self, world, action
    ) -> None:
        declare_strict(world)
        assert world.toggle("flag strict").returncode == 0
        written = world.state_file().read_bytes()

        toggled = world.toggle(f"{action} stirct")

        assert toggled.returncode != 0
        assert world.state_file().read_bytes() == written


class TestTheActionClearRemovesTheSessionsState:
    def test_clear_undoes_none_so_the_next_delegate_gets_the_configs_rules(self, world) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        assert world.toggle("none").returncode == 0

        cleared = world.toggle("clear")

        assert cleared.returncode == 0, cleared.stderr
        assert not world.state_file().exists()
        assert world.start_delegate().context == CORE

    def test_clear_removes_a_state_file_no_toggle_could_read_and_the_next_delegate_gets_the_configs_rules(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        world.state_file().parent.mkdir(parents=True)
        world.state_file().write_text("band: sideways\n", encoding="utf-8")

        cleared = world.toggle("clear")

        assert cleared.returncode == 0, cleared.stderr
        assert not world.state_file().exists()
        assert world.start_delegate().context == CORE


class TestSessionStateEndsAtAClearAndAtTheSessionsEnd:
    def test_a_cleared_session_ends_its_toggles(self, world) -> None:
        declare_strict(world)
        assert world.toggle("flag strict").returncode == 0

        world.start_session(source="clear")

        assert world.start_delegate().context == CORE

    def test_a_closed_session_ends_its_toggles_for_the_resumed_session(self, world) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        assert world.toggle("none").returncode == 0

        world.end_session()
        assert not world.state_file().exists()
        world.start_session(source="resume")

        assert world.start_delegate().context == CORE

    def test_a_resume_after_a_crash_that_sent_no_session_end_starts_without_toggles(
        self, world
    ) -> None:
        declare_strict(world)
        assert world.toggle("flag strict").returncode == 0
        assert world.state_file().exists()

        world.start_session(source="resume")

        assert not world.state_file().exists()
        assert world.start_delegate().context == CORE


class TestCompactionKeepsSessionState:
    def test_a_compacted_session_keeps_the_flag_a_toggle_set_for_later_delegates(
        self, world
    ) -> None:
        declare_strict(world)
        assert world.toggle("flag strict").returncode == 0

        world.start_session(source="compact")

        assert world.start_delegate().context == CORE + SECURITY


class TestDeliveryRunsOnPython315OrLater:
    def test_the_launcher_refuses_python_3_14_with_a_message_to_the_person_and_exit_zero(
        self, tmp_path
    ) -> None:
        stub(tmp_path, "python3", minor=14, has_yaml=True)

        result = launch(tmp_path, announce=True)

        assert result.returncode == 0
        assert "3.15" in result.stderr
        output = json.loads(result.stdout)
        assert "3.15" in output["systemMessage"]
        assert "hookSpecificOutput" not in output, "the agent's context holds no such line"

    def test_a_session_on_python_3_14_starts_without_rules_and_shows_the_person_the_requirement(
        self, world, tmp_path
    ) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        stub(tmp_path, "python3", minor=14, has_yaml=True)
        world.environment["PATH"] = path_of(tmp_path)

        delivery = world.start_session()

        assert delivery.context == ""
        assert len(delivery.messages) == 1
        assert "3.15" in delivery.message

    def test_a_session_on_python_3_15_with_the_yaml_library_receives_its_rules_and_no_requirement_message(
        self, world
    ) -> None:
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.write_config(DECLARED + "defaults: core-rules\n")
        world.environment["RULESETS_PYTHON"] = sys.executable
        assert sys.version_info >= (3, 15)

        delivery = world.start_session()

        assert delivery.context == "Hold every rule as mandatory.\n"
        assert delivery.message is None

    def test_the_launcher_refuses_python_3_15_without_the_yaml_library_and_names_the_requirement(
        self, tmp_path
    ) -> None:
        stub(tmp_path, "python3", minor=15, has_yaml=False)

        result = launch(tmp_path, announce=True)

        assert result.returncode == 0
        assert "pyyaml" in result.stderr
        output = json.loads(result.stdout)
        assert "pyyaml" in output["systemMessage"]
        assert "hookSpecificOutput" not in output, "the agent's context holds no such line"


class TestSessionStateRoundTripsThroughItsFile:
    def test_a_band_and_flags_written_are_the_band_and_flags_read(self, tmp_path) -> None:
        locations = Locations(tmp_path)
        written = SessionState(Band.NONE, {"strict": FlagSetting.SET, "loud": FlagSetting.UNSET})

        write_state(locations, "s1", written)

        assert read_state(locations, "s1") == written
        assert list((tmp_path / ".tmp" / "rulesets-engine" / "session").iterdir()) == [
            tmp_path / ".tmp" / "rulesets-engine" / "session" / "s1.yaml"
        ]


def tree_of(root) -> dict[pathlib.Path, bytes]:
    """Every file under `root` with its bytes, so a later read shows any file written or changed."""
    return {p.relative_to(root): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def delegate_records(world) -> list[dict]:
    return [r for r in world.records() if r["scope"] == "delegate"]


class TestAPreToolUseHookRecordsTheModelACallerNamesForOneSpawn:
    def test_the_recording_hook_is_wired_on_the_agent_tool_alone(self) -> None:
        groups = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]

        assert [group["matcher"] for group in groups] == ["Agent"]

    def test_the_model_a_caller_names_for_a_spawn_is_the_model_its_delegate_is_composed_for(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.rule("terse-rules")
        world.write_config(
            "models: opus haiku\ndefaults: core-rules\nmodel haiku:\n  include: terse-rules\n"
        )
        world.start_session(model=OPUS)

        recorded = world.spawn("critic", model="haiku")
        delivery = world.start_delegate("critic")

        assert (recorded.returncode, recorded.stdout) == (0, "")
        assert delivery.context == "text of core-rules\ntext of terse-rules\n"
        (record,) = delegate_records(world)
        assert (record["model"]["name"], record["model"]["source"]) == ("haiku", "per-spawn")

    def test_the_recording_hooks_and_the_delegate_start_alter_no_prompt_and_the_hooks_print_no_rule_text(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        world.start_session(model=OPUS)

        spawned = world.spawn("critic", model="opus")
        loaded = world.load(world.config / "CLAUDE.md", "session_start")
        delivery = world.start_delegate("critic")

        assert (spawned.stdout, loaded.stdout) == ("", "")
        assert (spawned.returncode, loaded.returncode) == (0, 0)
        (spawn,) = [
            json.loads(line)
            for line in (world.record_files() / "spawns.jsonl").read_text("utf-8").splitlines()
        ]
        assert (spawn["model"], spawn["agent_type"]) == ("opus", "critic")
        assert [(r["file_path"], r["load_reason"]) for r in world.load_records()] == [
            (str(world.config / "CLAUDE.md"), "session_start")
        ]
        injected = [
            set(json.loads(text)["hookSpecificOutput"])
            for text in delivery.outputs.values()
            if text.strip()
        ]
        assert injected == [{"hookEventName", "additionalContext"}]
        assert delivery.context == "text of core-rules\n"

    def test_a_spawn_that_names_no_model_leaves_the_delegate_on_its_parents_model(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        world.start_session(model=OPUS)

        recorded = world.spawn("critic", model=None)
        world.start_delegate("critic")

        assert (recorded.returncode, recorded.stdout) == (0, "")
        (record,) = delegate_records(world)
        assert (record["model"]["name"], record["model"]["source"]) == ("opus", "parent-record")

    @pytest.mark.parametrize(
        "stdin",
        ["not json", "[]", "{}", '{"session_id": "s1", "tool_input": "oops"}'],
    )
    def test_a_payload_the_hook_cannot_read_exits_zero_and_prints_nothing(
        self, world, stdin
    ) -> None:
        result = world.run_spawn_hook(stdin)

        assert (result.returncode, result.stdout) == (0, "")

    def test_a_state_directory_that_cannot_be_written_exits_zero_and_prints_nothing(
        self, world, tmp_path
    ) -> None:
        not_a_directory = tmp_path / "file"
        not_a_directory.write_text("", encoding="utf-8")
        world.environment["CLAUDE_CONFIG_DIR"] = str(not_a_directory)

        result = world.spawn("critic", model="haiku")

        assert (result.returncode, result.stdout) == (0, "")


class TestTheActionNoneLeavesANoticeThatTheContextReceivedNothing:
    def test_a_delegate_under_none_receives_no_rule_and_a_shown_notice_says_it_received_nothing(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        world.start_session(model=OPUS)
        assert world.toggle("none").returncode == 0

        delivery = world.start_delegate()

        assert delivery.context == ""
        (record,) = delegate_records(world)
        (notice,) = [n["subject"] for n in record["notices"] if n["shown"]]
        assert "received nothing" in notice
        assert "fail" not in notice.lower()


NOT_UTF_8 = b'{"session_id": "s1", "source": "\xff\xfe"}'


class TestEveryHookExitsZeroOnAPayloadThatIsNotUtf8:
    @pytest.mark.parametrize(
        ("event", "last_argument"),
        [
            ("SessionStart", "--part 1"),
            ("SessionStart", "--part 2"),
            ("SubagentStart", "--part 1"),
            ("PostModelSwitch", "--part 1"),
            ("SessionEnd", "--end"),
            ("PreToolUse", 'record-spawn.py"'),
            ("InstructionsLoaded", 'record-load.py"'),
        ],
    )
    def test_the_hook_exits_zero_and_prints_nothing(self, world, event, last_argument) -> None:
        matched = "Agent" if event == "PreToolUse" else "session_start"
        result = world.run_hook_bytes(event, last_argument, NOT_UTF_8, matched)

        assert (result.returncode, result.stdout) == (0, b"")


class TestAnUnreadablePayloadLeavesATrace:
    def test_a_start_naming_no_session_prints_the_reason_to_stderr_and_shows_the_person_a_notice(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")

        result = world.run_part_process("SessionStart", {"source": "startup"}, 1)

        assert result.returncode == 0
        assert "the payload names no session" in result.stderr
        message = json.loads(result.stdout)["systemMessage"]
        assert "the payload names no session" in message
        assert "additionalContext" not in result.stdout

    def test_a_switch_naming_no_target_model_leaves_a_record_with_the_reason_and_delivers_nothing(
        self, world
    ) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=SONNET)

        result = world.run_part_process(
            "PostModelSwitch", {"session_id": "s1", "from_model": SONNET, "prompt_id": "p1"}, 1
        )

        assert result.returncode == 0
        assert "the switch names no target model" in result.stderr
        assert result.stdout == ""
        _, failed = world.records()
        (notice,) = failed["notices"]
        assert notice["kind"] == "delivery-failure"
        assert "the switch names no target model" in notice["subject"]
        assert failed["rules"] == []
        assert counted_models(world) == [SONNET]

    def test_a_payload_that_is_not_json_prints_the_reason_to_stderr_and_nothing_else(
        self, world
    ) -> None:
        result = world.run_hook_bytes("SessionStart", "--part 1", b"{not json")

        assert (result.returncode, result.stdout) == (0, b"")
        assert b"not UTF-8 JSON" in result.stderr

    def test_a_later_part_prints_nothing_for_an_unreadable_payload(self, world) -> None:
        result = world.run_part_process("SessionStart", {"source": "startup"}, 2)

        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


class TestASessionsModelFactIsRecordedAndReadBack:
    def test_a_session_whose_start_reports_no_identifier_records_that_none_was_available(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")

        world.start_session(model=None)

        record = world.model_record()
        assert record is not None
        assert record["identifier"] is None
        assert "no model identifier was available" in json.dumps(record)

    def test_a_session_that_starts_on_an_identifier_records_it_for_a_later_start_to_read(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")
        world.start_session(model=OPUS)

        world.start_session(model=None, source="resume")

        (_, resumed) = world.records()
        assert (resumed["model"]["identifier"], resumed["model"]["source"]) == (
            OPUS,
            "session-record",
        )


class TestADeliverysFirstPartAloneWritesTheSessionsModelRecord:
    def test_the_first_part_writes_the_record_and_no_later_part_writes_it_again(
        self, world
    ) -> None:
        for name in ("a-rule", "b-rule", "c-rule"):
            world.rule(name, f"{name} " + "x" * 5990 + "\n")
        world.write_config(DECLARED + "defaults: a-rule b-rule c-rule\n")
        payload = {"session_id": "s1", "source": "startup", "model": OPUS}

        first = world.run_part("SessionStart", payload, 1)
        record = world.model_record()
        path = world.config / ".tmp" / "rulesets-engine" / "models" / "s1.json"
        path.unlink()
        later = [world.run_part("SessionStart", payload, part) for part in (2, 3)]

        assert first
        assert all(later), "the rules span three parts"
        assert record is not None
        assert record["identifier"] == OPUS
        assert not path.exists()


def declare_voice_scene(world) -> None:
    """A pool whose `core-rules` every context receives, and a haiku or sonnet delegate adds a rule."""
    world.rule("core-rules")
    world.rule("haiku-rules")
    world.rule("sonnet-rules")
    world.write_config(
        "models: opus sonnet haiku\n"
        "defaults: core-rules\n"
        "model haiku:\n"
        "  include: haiku-rules\n"
        "model sonnet:\n"
        "  include: sonnet-rules\n"
    )


class TestADelegateReceivesAllItsRulesAtItsStart:
    def test_a_delegate_spawned_after_a_rule_edit_receives_the_edit_and_the_earlier_one_keeps_its_text(
        self, world
    ) -> None:
        world.rule("voice", "old voice\n")
        world.write_config(DECLARED + "defaults: voice\n")

        before = world.start_delegate(agent_id="a1")
        world.rule("voice", "edited voice\n")
        after = world.start_delegate(agent_id="a2")

        assert before.context == "old voice\n"
        assert after.context == "edited voice\n"

    def test_a_rule_edited_after_a_delegate_starts_reaches_the_next_delegate_and_not_the_running_one(
        self, world
    ) -> None:
        three_part_pool(world)
        payload = {"session_id": "s1", "agent_id": "a1", "agent_type": "critic", "prompt_id": "p1"}

        first = world.run_part("SubagentStart", payload, 1)
        three_part_pool(world, mark="NEW")
        later = {part: world.run_part("SubagentStart", payload, part) for part in range(2, 11)}
        running = Delivery({1: first, **later})
        next_delegate = world.start_delegate(agent_id="a2")

        assert [running.part_texts[part][:12] for part in (1, 2, 3)] == [
            "a-rule OLD x",
            "b-rule OLD x",
            "c-rule OLD x",
        ]
        assert [next_delegate.part_texts[part][:12] for part in (1, 2, 3)] == [
            "a-rule NEW x",
            "b-rule NEW x",
            "c-rule NEW x",
        ]
        (first_record, _) = delegate_records(world)
        assert (
            first_record["rules"][0]["digest"]
            == hashlib.sha256(running.part_texts[1].encode()).hexdigest()
        )

    def test_delegates_on_different_models_each_receive_the_composition_of_their_own_facts(
        self, world
    ) -> None:
        declare_voice_scene(world)
        world.user_agent("quick", "haiku")
        world.user_agent("careful", "sonnet")
        world.start_session(model=OPUS)

        quick = world.start_delegate("quick", agent_id="a1")
        careful = world.start_delegate("careful", agent_id="a2")
        quick_again = world.start_delegate("quick", agent_id="a3")

        assert quick.context == "text of core-rules\ntext of haiku-rules\n"
        assert careful.context == "text of core-rules\ntext of sonnet-rules\n"
        assert quick_again.context == quick.context


class TestADelegatesDeliveryWritesNoSessionFile:
    def test_a_haiku_delegate_under_an_opus_session_leaves_the_record_and_the_rulesets_untouched(
        self, world
    ) -> None:
        declare_voice_scene(world)
        world.user_agent("quick", "haiku")
        session = world.start_session(model=OPUS)
        record = world.model_record()
        record_bytes = (world.config / ".tmp/rulesets-engine/models/s1.json").read_bytes()
        rulesets = tree_of(world.rulesets)
        assert world.load(world.rulesets / "rules" / "core-rules.md").returncode == 0
        loads = (world.record_files() / "loads.jsonl").read_bytes()

        delegate = world.start_delegate("quick")

        assert (world.record_files() / "loads.jsonl").read_bytes() == loads
        assert session.context == "text of core-rules\n"
        assert delegate.context == "text of core-rules\ntext of haiku-rules\n"
        assert record is not None
        assert record["identifier"] == OPUS
        assert (world.config / ".tmp/rulesets-engine/models/s1.json").read_bytes() == record_bytes
        assert tree_of(world.rulesets) == rulesets


class TestAMissingOrUnparsableConfigDeliversEveryRuleAtItsDefault:
    def test_a_missing_config_delivers_each_default_form_sorted_and_the_notice_names_the_path(
        self, world
    ) -> None:
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("a-rule", "a text\n")

        delivery = world.start_session()

        assert delivery.context == "a text\ndefault voice\n"
        assert str(world.rulesets / "config.yaml") in delivery.message
        assert "manifest" not in delivery.message

    def test_an_unparsable_config_delivers_each_default_form_and_the_notice_names_path_and_error(
        self, world
    ) -> None:
        world.rule("voice", "default voice\n")
        world.rule("a-rule", "a text\n")
        broken = "models: ['opus'\ndefaults: ['voice']\n"
        world.write_config(broken)
        with pytest.raises(yaml.YAMLError) as parsed:
            yaml.safe_load(broken)

        delivery = world.start_session()

        assert delivery.context == "a text\ndefault voice\n"
        assert str(world.rulesets / "config.yaml") in delivery.message
        assert parsed.value.problem in delivery.message
        assert "manifest" not in delivery.message


class TestACompositionThatReachesNoRuleIsNoFailure:
    @pytest.mark.parametrize(
        "pool",
        [[], ["voice"]],
        ids=["the pool holds no rule file", "no applying statement includes a rule"],
    )
    def test_the_session_starts_with_no_text_and_a_notice_says_the_context_received_nothing(
        self, world, pool
    ) -> None:
        for name in pool:
            world.rule(name)
        world.write_config(DECLARED + "defaults:\n")

        delivery = world.start_session()

        assert delivery.context == ""
        assert "received nothing" in delivery.message
        assert "fail" not in delivery.message.lower()


class TestAMissingRulesetsDirectoryIsScaffolded:
    def test_a_session_without_a_rulesets_directory_starts_with_an_empty_one_and_a_notice_saying_where(
        self, world
    ) -> None:
        shutil.rmtree(world.rulesets)

        delivery = world.start_session()

        assert delivery.context == ""
        assert str(world.rulesets) in delivery.message
        assert list((world.rulesets / "rules").iterdir()) == []
        declared = yaml.safe_load((world.rulesets / "config.yaml").read_text(encoding="utf-8"))
        assert not any(declared.values())
        assert not (world.rulesets / "manifest.yaml").exists()


class TestADeliveryFailureKeepsTheSessionRunning:
    def test_a_scaffold_that_cannot_write_its_parent_starts_the_session_and_says_why(
        self, world
    ) -> None:
        shutil.rmtree(world.rulesets)
        (world.config / ".tmp" / "rulesets-engine").mkdir(parents=True)
        world.config.chmod(0o500)
        try:
            delivery = world.start_session()
        finally:
            world.config.chmod(0o700)

        assert delivery.context == ""
        assert "Permission denied" in delivery.message
        assert str(world.rulesets) in delivery.message
        assert not world.rulesets.exists()

    def test_a_delivery_that_raises_answers_with_a_notice_naming_the_failure_and_the_command(
        self, world, tmp_path
    ) -> None:
        not_a_directory = tmp_path / "file"
        not_a_directory.write_text("", encoding="utf-8")
        world.environment["CLAUDE_CONFIG_DIR"] = str(not_a_directory)

        delivery = world.start_session()

        assert delivery.context == ""
        assert len(delivery.messages) == 1
        assert "not a directory" in delivery.message.lower()
        assert "deliver.py" in delivery.message
        assert "--part 1" in delivery.message

    def test_a_defect_writes_its_traceback_to_stderr_and_an_environment_failure_does_not(
        self, world, tmp_path
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")
        world.state_file().parent.mkdir(parents=True)
        world.state_file().write_text("band: sideways\n", encoding="utf-8")
        delegate = {"session_id": "s1", "agent_id": "a1", "agent_type": "critic"}

        defect = world.run_part_process("SubagentStart", delegate, 1)

        assert defect.returncode == 0
        assert "Traceback (most recent call last)" in defect.stderr
        assert "ValueError" in defect.stderr
        assert defect.stdout == "", "a delegate start shows no message and delivers no text"
        assert [r["notices"][0]["kind"] for r in world.records()] == ["delivery-failure"]

        not_a_directory = tmp_path / "file"
        not_a_directory.write_text("", encoding="utf-8")
        world.environment["CLAUDE_CONFIG_DIR"] = str(not_a_directory)

        environment = world.run_part_process("SessionStart", {"session_id": "s2"}, 1)

        assert environment.returncode == 0
        assert "Traceback" not in environment.stderr
        assert "NotADirectoryError" in environment.stderr or "Not a directory" in environment.stderr


THREE_PARTS = ("a-rule", "b-rule", "c-rule")


def three_part_pool(world, mark="OLD") -> None:
    """Rules whose bodies each fill most of a part, so that a delivery needs three parts."""
    for name in THREE_PARTS:
        world.rule(name, f"{name} {mark} " + "x" * 5980 + "\n")
    world.write_config(DECLARED + "defaults: a-rule b-rule c-rule\n")


def block_audit(world) -> None:
    """Put a file where the audit directory belongs, so no record can be appended."""
    audit = world.config / ".tmp" / "rulesets-engine" / "audit"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text("not a directory", encoding="utf-8")


def jam_delivery_records(world, session_id="s1") -> None:
    """Put a directory where the session's delivery records belong, so only that append fails."""
    (world.record_files(session_id) / "deliveries.jsonl").mkdir(parents=True)


def rerun_command_of(message) -> str:
    return message.split("run it again with: ", 1)[1]


class TestAFailureAfterThePlanIsWrittenDeliversNoPartAtAll:
    def test_when_the_first_part_cannot_append_its_record_no_later_part_delivers_text(
        self, world
    ) -> None:
        three_part_pool(world)
        jam_delivery_records(world)
        payload = {"session_id": "s1", "source": "startup", "model": OPUS}

        delivery = world.run_event("SessionStart", payload)

        assert delivery.context == ""
        assert [part for part, out in delivery.outputs.items() if "additionalContext" in out] == []
        assert len(delivery.messages) == 1

    def test_a_delivery_that_succeeds_again_after_a_failure_delivers_every_part(
        self, world
    ) -> None:
        three_part_pool(world)
        jam_delivery_records(world)
        payload = {"session_id": "s1", "source": "startup", "model": OPUS}
        world.run_event("SessionStart", payload)
        (world.record_files() / "deliveries.jsonl").rmdir()

        delivery = world.run_event("SessionStart", payload)

        assert sorted(delivery.part_texts) == [1, 2, 3]


class TestAResumedDelegateReplaysTheDeliveryItFirstReceived:
    def test_a_start_for_an_agent_id_that_already_started_carries_the_text_of_its_first_delivery(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        first = world.start_delegate(agent_id="a1")
        assert world.toggle("none").returncode == 0
        world.rule("core-rules", "core-rules, edited\n")

        resumed = world.start_delegate(agent_id="a1")

        assert first.context == CORE
        assert resumed.context == CORE

    def test_every_part_of_the_first_delivery_is_replayed(self, world) -> None:
        three_part_pool(world)
        first = world.start_delegate(agent_id="a1")
        three_part_pool(world, mark="NEW")

        resumed = world.start_delegate(agent_id="a1")

        assert sorted(first.part_texts) == [1, 2, 3]
        assert resumed.part_texts == first.part_texts

    def test_an_agent_id_that_never_started_is_composed_afresh(self, world) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        world.start_delegate(agent_id="a1")
        assert world.toggle("none").returncode == 0

        assert world.start_delegate(agent_id="a2").context == ""

    def test_a_replay_leaves_the_one_record_of_the_delivery_it_repeats(self, world) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        world.start_delegate(agent_id="a1")

        world.start_delegate(agent_id="a1")

        assert [r["agent_id"] for r in delegate_records(world)] == ["a1"]
        assert world.delivery_check().stdout == ""

    def test_a_delegate_whose_first_delivery_failed_is_composed_afresh_when_it_starts_again(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        jam_delivery_records(world)
        failed = world.start_delegate(agent_id="a1")
        (world.record_files() / "deliveries.jsonl").rmdir()

        again = world.start_delegate(agent_id="a1")

        assert failed.context == ""
        assert again.context == CORE


class TestAFailedDeliveryWritesItsRecord:
    def test_a_main_session_failure_leaves_one_record_carrying_the_failure_notice(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")
        (world.rulesets / "rules").chmod(0o000)
        try:
            delivery = world.start_session()
        finally:
            (world.rulesets / "rules").chmod(0o700)

        (record,) = world.records()
        assert [n["kind"] for n in record["notices"]] == ["delivery-failure"]
        assert record["notices"][0]["subject"] == delivery.message
        assert (record["scope"], record["kind"], record["message_sent"]) == (
            "session",
            "session",
            True,
        )
        assert record["rules"] == []
        assert not (world.record_files() / "failures.jsonl").exists()

    def test_where_no_record_can_be_written_stderr_carries_the_failure_alone(self, world) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")
        block_audit(world)
        payload = {"session_id": "s1", "source": "startup", "model": OPUS}

        failed = world.run_part_process("SessionStart", payload, 1)

        assert failed.returncode == 0
        assert "delivery failed" in failed.stderr
        assert "audit" in failed.stderr
        assert world.records() == []

    def test_a_delegate_failure_leaves_a_record_that_states_no_message_was_shown(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")
        (world.rulesets / "rules").chmod(0o000)
        try:
            delivery = world.start_delegate("critic")
        finally:
            (world.rulesets / "rules").chmod(0o700)

        (record,) = world.records()
        assert [n["kind"] for n in record["notices"]] == ["delivery-failure"]
        assert (record["scope"], record["agent_id"], record["message_sent"]) == (
            "delegate",
            "a1",
            False,
        )
        assert delivery.outputs[1] == ""

    def test_a_failed_delivery_counts_as_nothing_delivered(self, world) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")
        (world.rulesets / "rules").chmod(0o000)
        try:
            world.start_session()
        finally:
            (world.rulesets / "rules").chmod(0o700)

        listed = world.deliveries()
        checked = world.delivery_check()

        assert (listed.stdout, listed.returncode) == ("", 0)
        assert (checked.stdout, checked.returncode) == ("", 0)


class TestTheFailureNoticeNamesACommandThatRunsTheDeliveryAgain:
    def fail_once(self, world) -> Delivery:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")
        (world.rulesets / "rules").chmod(0o000)
        try:
            return world.start_session()
        finally:
            (world.rulesets / "rules").chmod(0o700)

    def test_the_command_reproduces_the_delivery_once_the_cause_is_gone(self, world) -> None:
        failed = self.fail_once(world)

        rerun = world.run_shell(rerun_command_of(failed.message))

        assert rerun.returncode == 0, rerun.stderr
        assert json.loads(rerun.stdout)["hookSpecificOutput"]["additionalContext"] == (
            delivered("voice", "text of voice\n")
        )

    def test_the_command_names_a_payload_file_under_the_state_directory(self, world) -> None:
        failed = self.fail_once(world)

        command = rerun_command_of(failed.message)

        (payload,) = (world.config / ".tmp" / "rulesets-engine" / "payloads").iterdir()
        assert str(payload) in command
        assert json.loads(payload.read_text(encoding="utf-8"))["session_id"] == "s1"

    def test_the_command_carries_the_payload_where_no_file_can_be_written(
        self, world, tmp_path
    ) -> None:
        not_a_directory = tmp_path / "file"
        not_a_directory.write_text("", encoding="utf-8")
        world.environment["CLAUDE_CONFIG_DIR"] = str(not_a_directory)
        failed = world.start_session()

        command = rerun_command_of(failed.message)

        assert command.startswith("printf %s ")
        assert '"session_id"' in command

    def test_running_the_command_leaves_the_next_identical_delivery_its_own_plan(
        self, world
    ) -> None:
        three_part_pool(world)
        payload = {"session_id": "s1", "source": "compact", "model": OPUS}
        (world.rulesets / "rules").chmod(0o000)
        try:
            failed = world.run_event("SessionStart", payload)
        finally:
            (world.rulesets / "rules").chmod(0o700)
        assert world.run_shell(rerun_command_of(failed.message)).returncode == 0
        world.rule("b-rule", "b-rule NEW " + "x" * 5980 + "\n")

        delivery = deliver_with_part_two_first(world, payload)

        assert delivery.part_texts[2].startswith("b-rule NEW")


def deliver_with_part_two_first(world, payload) -> Delivery:
    """One delivery of `payload` whose part 2 has started long before its part 1."""
    outputs = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        later = {
            part: pool.submit(world.run_part, "SessionStart", payload, part) for part in (2, 3)
        }
        threading.Event().wait(0.5)
        outputs[1] = world.run_part("SessionStart", payload, 1)
        outputs.update({part: job.result() for part, job in later.items()})
    return Delivery(outputs)


class TestAnIdenticalPayloadDeliveredAgainMeetsOnlyItsOwnPlan:
    def test_part_two_started_ahead_of_part_one_carries_the_text_edited_since_the_last_delivery(
        self, world
    ) -> None:
        three_part_pool(world)
        payload = {"session_id": "s1", "source": "compact", "model": OPUS}
        first = world.run_event("SessionStart", payload)
        world.rule("b-rule", "b-rule NEW " + "x" * 5980 + "\n")

        second = deliver_with_part_two_first(world, payload)

        assert first.part_texts[2].startswith("b-rule OLD")
        assert second.part_texts[2].startswith("b-rule NEW")
        assert "b-rule OLD" not in second.context

    def test_each_of_several_concurrent_deliveries_carries_the_edit_made_before_it(
        self, world
    ) -> None:
        three_part_pool(world)
        payload = {"session_id": "s1", "source": "compact", "model": OPUS}
        world.run_event("SessionStart", payload)

        for number in range(6):
            mark = f"MARK{number}"
            world.rule("b-rule", f"b-rule {mark} " + "x" * 5970 + "\n")
            delivery = world.run_event("SessionStart", payload)
            assert mark in delivery.part_texts[2], f"delivery {number} carried a stale part"


class TestTermsOfDelivery:
    def test_a_delegates_record_names_the_variant_and_its_digest_of_the_text_delivered(
        self, world
    ) -> None:
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice")
        world.write_config(DECLARED + "defaults: voice\nagent critic:\n  include: voice@terse\n")

        delivery = world.start_delegate("critic")

        (record,) = delegate_records(world)
        (line,) = record["rules"]
        body = (world.rulesets / "rules" / "voice@terse.md").read_bytes()
        assert body == b"terse voice", "the variant file ends without a newline"
        assert (line["rule"], line["variant"]) == ("voice", "terse")
        assert delivery.received.encode() == b"<!-- rule: voice -->\n\n" + body
        assert line["digest"] == hashlib.sha256(body).hexdigest()


SONNET = "claude-sonnet-5-5"
HAIKU = "claude-haiku-4-5"
TIERS = "models: opus sonnet haiku\n"


def declare_tiers(world, *keyed) -> None:
    """A pool whose `core-rules` every context receives, and a `<tier>-rules` for each tier in `keyed`."""
    world.rule("core-rules")
    blocks = ""
    for tier in keyed:
        world.rule(f"{tier}-rules")
        blocks += f"model {tier}:\n  include: {tier}-rules\n"
    world.write_config(TIERS + "defaults: core-rules\n" + blocks)


def switch_records(world) -> list[dict]:
    return [r for r in world.records() if r.get("switch") is not None]


def counted_models(world) -> list[str]:
    """The identifiers of the records the readers count, in file order."""
    from rulesets.audit.counted import counted
    from rulesets.audit.delivery_record import DeliveryRecord

    return [
        r.model.identifier for r in counted(DeliveryRecord.from_json(r) for r in world.records())
    ]


class TestAMidSessionModelChangeDeliversTheNewRulesAndStatesItsLimit:
    def test_a_switch_to_a_differently_composed_model_delivers_its_rules_and_notes_the_earlier_ones_remain(
        self, world
    ) -> None:
        declare_tiers(world, "sonnet", "opus")
        world.start_session(model=SONNET)

        delivery = world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        assert delivery.targets == {"PostModelSwitch"}
        assert delivery.context == "text of core-rules\ntext of opus-rules\n"
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == OPUS
        (record,) = switch_records(world)
        (remaining,) = [n for n in record["notices"] if n["kind"] == "earlier-rules-remain"]
        assert remaining["shown"] is False
        assert "remain" in remaining["subject"]
        assert delivery.message is None

    def test_a_switch_from_an_unclaimed_identifier_delivers_the_rules_composed_for_opus(
        self, world
    ) -> None:
        declare_tiers(world, "opus")
        world.start_session(model="glm-5")

        delivery = world.switch_model(OPUS, from_model="glm-5", prompt_id="p1")

        assert delivery.context == "text of core-rules\ntext of opus-rules\n"
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == OPUS


class TestASwitchThatChangesNoRuleDeliversNothing:
    def test_a_switch_between_models_that_compose_alike_delivers_nothing_and_writes_the_model_record(
        self, world
    ) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=SONNET)

        delivery = world.switch_model(HAIKU, from_model=SONNET, prompt_id="p1")

        assert [out for out in delivery.outputs.values() if out] == []
        assert len(world.records()) == 1, "only the session start left a delivery record"
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == HAIKU

    def test_a_switch_whose_compositions_differ_only_in_a_variant_delivers_the_target_variant(
        self, world
    ) -> None:
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.write_config(TIERS + "defaults: voice\nmodel haiku:\n  include: voice@terse\n")
        world.start_session(model=SONNET)

        delivery = world.switch_model(HAIKU, from_model=SONNET, prompt_id="p1")

        assert delivery.context == "terse voice\n"
        (record,) = switch_records(world)
        assert [(r["rule"], r["variant"]) for r in record["rules"]] == [("voice", "terse")]

    def test_a_delegate_after_a_switch_that_composes_alike_reads_the_new_model_as_its_parents(
        self, world
    ) -> None:
        declare_tiers(world, "haiku")
        world.start_session(model=SONNET)
        world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert (record["model"]["identifier"], record["model"]["source"]) == (
            OPUS,
            "parent-record",
        )


def declare_critic_pool(world) -> None:
    """A pool where an `opus` context adds `opus-rules` and an agent `critic` drops `writing-code`."""
    for name in ("core-rules", "writing-code", "opus-rules", "security-pass"):
        world.rule(name)
    world.write_config(
        TIERS
        + "flags: strict\n"
        + "defaults: core-rules writing-code\n"
        + "agent critic:\n"
        + "  exclude: writing-code\n"
        + "model opus:\n"
        + "  include: opus-rules\n"
        + "flag strict:\n"
        + "  include: security-pass\n"
    )


class TestASwitchKeepsTheSessionsNonModelFacts:
    def test_a_session_launched_under_an_agent_receives_the_rules_composed_for_that_agent(
        self, world
    ) -> None:
        declare_critic_pool(world)
        world.start_session(model=SONNET, agent_type="critic")

        delivery = world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        assert delivery.context == "text of core-rules\ntext of opus-rules\n"
        (record,) = switch_records(world)
        assert record["agent"] == {"state": "named", "name": "critic"}

    def test_a_switch_between_models_that_compose_alike_under_the_agent_delivers_nothing(
        self, world
    ) -> None:
        for name in ("core-rules", "opus-rules"):
            world.rule(name)
        world.write_config(
            TIERS + "defaults: core-rules\n" + "model opus:\n"
            "  include: opus-rules\n"
            "agent critic:\n"
            "  exclude: opus-rules\n"
        )
        world.start_session(model=SONNET, agent_type="critic")

        delivery = world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        assert [out for out in delivery.outputs.values() if out] == []
        assert len(world.records()) == 1, "only the session start left a delivery record"

    def test_a_session_launched_under_no_agent_receives_no_agent_rule_after_a_switch(
        self, world
    ) -> None:
        declare_critic_pool(world)
        world.start_session(model=SONNET, agent_type="critic")
        world.start_session(model=SONNET, source="clear")

        delivery = world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        assert delivery.context == "text of core-rules\ntext of opus-rules\ntext of writing-code\n"

    def test_a_launch_flag_still_holds_after_a_switch(self, world) -> None:
        declare_critic_pool(world)
        world.environment["RULESETS_FLAGS"] = "strict"
        world.start_session(model=SONNET)

        delivery = world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        assert delivery.context == (
            "text of core-rules\ntext of opus-rules\ntext of security-pass\ntext of writing-code\n"
        )

    def test_a_toggle_does_not_reach_a_switch(self, world) -> None:
        declare_critic_pool(world)
        world.start_session(model=SONNET)
        assert world.toggle("flag strict").returncode == 0
        assert world.toggle("none").returncode == 0

        delivery = world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        assert delivery.context == "text of core-rules\ntext of opus-rules\ntext of writing-code\n"

    def test_a_switch_that_names_no_origin_model_delivers_even_where_the_rules_are_alike(
        self, world
    ) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=SONNET)

        delivery = world.switch_model(HAIKU, from_model=None, prompt_id="p1")

        assert delivery.context == "text of core-rules\n"
        assert len(switch_records(world)) == 1


def declare_session_pool(world) -> None:
    """A pool of `core-rules`, `sorting`, and `voice`, and a composition reaching the first two."""
    world.rule("core-rules", "Hold every rule as mandatory.\n")
    world.rule("sorting", "Sort what you hold.\n")
    world.rule("voice", "Speak plainly.\n")
    world.write_config(DECLARED + "defaults: core-rules sorting\n")


WHOLE_COMPOSITION = "Hold every rule as mandatory.\nSort what you hold.\n"


class TestASessionReceivesAllItsRulesAtEveryStart:
    def test_a_new_session_receives_the_bodies_its_composition_reaches_and_no_other(
        self, world
    ) -> None:
        declare_session_pool(world)

        delivery = world.start_session(source="startup")

        assert delivery.context == WHOLE_COMPOSITION

    def test_a_compacted_session_receives_every_body_its_composition_yields(self, world) -> None:
        declare_session_pool(world)
        world.start_session(source="startup")

        delivery = world.start_session(source="compact")

        assert delivery.context == WHOLE_COMPOSITION

    def test_a_cleared_session_receives_every_body_its_composition_yields(self, world) -> None:
        declare_session_pool(world)
        world.start_session(source="startup")

        delivery = world.start_session(source="clear")

        assert delivery.context == WHOLE_COMPOSITION

    def test_a_resumed_session_is_composed_for_the_model_its_record_names(self, world) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=OPUS)

        delivery = world.start_session(model=None, source="resume")

        assert delivery.context == "text of core-rules\ntext of opus-rules\n"

    def test_a_ruleset_over_9000_characters_divides_into_whole_sorted_parts_one_entry_each(
        self, world
    ) -> None:
        # Each marker adds 23 characters. The delivered sizes, 4,500, 4,501, and 4,499, give a
        # different split under a budget of 8,999, 9,000, and 9,001, and under `<` against `<=`:
        # b joins a only at 9,001, and c joins b at 9,000 exactly.
        bodies = {"a-rule": "a" * 4477, "b-rule": "b" * 4478, "c-rule": "c" * 4476}
        for name, text in bodies.items():
            world.rule(name, text)
        world.write_config(DECLARED + "defaults: c-rule a-rule b-rule\n")

        delivery = world.start_session()

        assert delivery.received_parts == {
            1: delivered("a-rule", bodies["a-rule"]),
            2: delivered("b-rule", bodies["b-rule"]) + delivered("c-rule", bodies["c-rule"]),
        }
        assert all(len(text) <= 9000 for text in delivery.received_parts.values())
        assert [delivery.outputs[part].strip() for part in range(3, 11)] == [""] * 8

    def test_two_bodies_totalling_exactly_9000_characters_share_a_part(self, world) -> None:
        bodies = {"a-rule": "a" * 4477, "b-rule": "b" * 4477, "c-rule": "c" * 10}
        for name, text in bodies.items():
            world.rule(name, text)
        world.write_config(DECLARED + "defaults: all.*\n")

        delivery = world.start_session()

        assert delivery.received_parts == {
            1: delivered("a-rule", "a" * 4477) + delivered("b-rule", "b" * 4477),
            2: delivered("c-rule", "c" * 10),
        }

    def test_a_body_that_would_take_a_part_to_9001_characters_opens_the_next_part(
        self, world
    ) -> None:
        bodies = {"a-rule": "a" * 4477, "b-rule": "b" * 4478, "c-rule": "c" * 10}
        for name, text in bodies.items():
            world.rule(name, text)
        world.write_config(DECLARED + "defaults: all.*\n")

        delivery = world.start_session()

        assert delivery.received_parts == {
            1: delivered("a-rule", "a" * 4477),
            2: delivered("b-rule", "b" * 4478) + delivered("c-rule", "c" * 10),
        }


OTHER_OPUS = "claude-opus-5-6"


class TestASwitchIsComparedWithWhatTheConversationHolds:
    def test_a_no_change_switch_after_a_superseded_switch_delivers_the_rules_the_conversation_lacks(
        self, world
    ) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=SONNET)
        world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        second = world.switch_model(OTHER_OPUS, from_model=OPUS, prompt_id="p1")

        assert second.context == "text of core-rules\ntext of opus-rules\n"
        assert counted_models(world) == [SONNET, OTHER_OPUS]

    def test_a_no_change_switch_after_a_switch_that_counted_delivers_nothing(self, world) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=SONNET)
        world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        second = world.switch_model(OTHER_OPUS, from_model=OPUS, prompt_id="p2")

        assert [out for out in second.outputs.values() if out] == []
        assert counted_models(world) == [SONNET, OPUS]
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == OTHER_OPUS

    def test_a_switch_back_to_the_rules_the_conversation_holds_replaces_the_superseded_record(
        self, world
    ) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=SONNET)
        world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        back = world.switch_model(HAIKU, from_model=OPUS, prompt_id="p1")

        assert back.context == "text of core-rules\n"
        assert counted_models(world) == [SONNET, HAIKU]


class TestOnlyTheLastOfSeveralRapidSwitchesCountsAsDelivered:
    def test_two_switches_before_the_next_request_count_only_the_last(self, world) -> None:
        declare_tiers(world, "sonnet", "haiku")
        world.start_session(model=OPUS)

        world.switch_model(SONNET, from_model=OPUS, prompt_id="p1")
        world.switch_model(HAIKU, from_model=SONNET, prompt_id="p1")

        assert [r["model"]["identifier"] for r in switch_records(world)] == [SONNET, HAIKU]
        assert counted_models(world) == [OPUS, HAIKU]
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == HAIKU

    def test_a_switch_a_request_then_another_switch_count_both(self, world) -> None:
        declare_tiers(world, "sonnet", "haiku")
        world.start_session(model=OPUS)

        world.switch_model(SONNET, from_model=OPUS, prompt_id="p1")
        world.switch_model(HAIKU, from_model=SONNET, prompt_id="p2")

        assert counted_models(world) == [OPUS, SONNET, HAIKU]

    def test_a_switch_payload_with_no_prompt_id_counts_as_delivered(self, world) -> None:
        declare_tiers(world, "sonnet", "haiku")
        world.start_session(model=OPUS)

        world.switch_model(SONNET, from_model=OPUS)
        world.switch_model(HAIKU, from_model=SONNET)

        assert counted_models(world) == [OPUS, SONNET, HAIKU]
        check = world.delivery_check()
        assert (check.stdout, check.returncode) == ("", 0)
        assert "composed but not delivered" not in check.stdout


class TestTheEngineReadsOnlyConfigYaml:
    def test_config_yaml_decides_delivery_while_a_manifest_yaml_sits_beside_it(self, world) -> None:
        world.rule("voice")
        world.rule("tone")
        world.write_config(DECLARED + "defaults: voice\n")
        (world.rulesets / "manifest.yaml").write_text("defaults: ['tone']\n", encoding="utf-8")

        delivery = world.start_session()

        assert delivery.context == "text of voice\n"
        assert "text of tone" not in delivery.context

    def test_a_manifest_yaml_alone_draws_a_shown_notice_naming_config_yaml(self, world) -> None:
        world.rule("voice")
        (world.rulesets / "manifest.yaml").write_text("defaults: ['voice']\n", encoding="utf-8")

        delivery = world.start_session()

        assert str(world.rulesets / "config.yaml") in delivery.message
        assert str(world.rulesets / "manifest.yaml") in delivery.message
        assert "reads only the config" in delivery.message


class TestAConditionKeyWrittenTwiceAtDelivery:
    def test_neither_block_delivers_and_a_shown_notice_names_the_key_and_both_lines(
        self, world
    ) -> None:
        world.rule("voice")
        world.rule("tone")
        world.write_config(
            DECLARED + "defaults:\nmodel haiku:\n  include: voice\nmodel haiku:\n  include: tone\n"
        )

        delivery = world.start_session(model=HAIKU)

        assert "text of voice" not in delivery.context
        assert "text of tone" not in delivery.context
        assert delivery.message is not None
        assert "`model haiku` at lines 3 and 5" in delivery.message
        assert "`then`" in delivery.message
        (record,) = world.records()
        (skipped,) = [n for n in record["notices"] if n["kind"] == "key-skipped"]
        assert skipped["shown"] is True
