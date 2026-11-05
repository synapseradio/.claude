#!/usr/bin/env python3
"""A context receives its rules by hook, as rule text only, and the person hears of problems.

Serves the person whose sessions and delegates start with rules, and the engineer who reads the
delivery record afterwards. Each case builds a configuration directory under `tmp_path` and runs
the hook entries that `hooks/hooks.json` wires for an event, as the harness runs them.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_ruleset_delivery.py`.
"""

import hashlib
import json
import pathlib
import shutil
import sys

import pytest
import yaml
from delivery_world import DECLARED, HOOKS_JSON, OPUS, Delivery, World
from launcher_stubs import launch, path_of, stub
from transcripts import write_transcript

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
def world(tmp_path):
    return World(tmp_path)


class TestEveryContextReceivesItsRulesByHook:
    def test_a_main_session_receives_the_body_of_core_rules_through_the_session_start_hook(
        self, world
    ):
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")

        delivery = world.start_session()

        assert delivery.context == "Hold every rule as mandatory.\n"
        assert delivery.targets == {"SessionStart"}

    def test_a_delegate_receives_its_rules_in_its_own_context_and_the_main_session_gains_none(
        self, world
    ):
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
        world.start_session()

        delivery = world.start_delegate("critic")

        assert delivery.context == "Hold every rule as mandatory.\n"
        assert delivery.targets == {"SubagentStart"}

    def test_a_delivery_leaves_the_agent_definition_file_byte_for_byte_as_it_was(self, world):
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
        definition = world.config / "agents" / "critic.md"
        definition.parent.mkdir(parents=True)
        definition.write_bytes(
            b"---\nname: critic\nmodel: haiku\n---\nReview the diff.\r\n\xc3\xa9"
        )
        before = definition.read_bytes()

        delivery = world.start_delegate("critic")

        assert delivery.context == "Hold every rule as mandatory.\n"
        assert definition.read_bytes() == before


class TestAForkSubagentReceivesNoRulesDelivery:
    def test_a_fork_starting_under_a_parent_that_received_rules_gets_no_rule_text(self, world):
        world.rule("core-rules")
        world.rule("sorting")
        world.manifest(DECLARED + "defaults: ['core-rules', 'sorting']\n")
        assert world.start_session().context == "text of core-rules\ntext of sorting\n"

        delivery = world.start_delegate("fork")

        assert delivery.context == ""
        assert set(delivery.outputs.values()) == {""}

    def test_the_record_of_a_forks_start_says_it_inherits_its_parents_rules_and_shows_no_message(
        self, world
    ):
        world.rule("core-rules")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
        world.start_session()

        delivery = world.start_delegate("fork")

        inherited = [
            n for r in world.records() for n in r["notices"] if n["kind"] == "fork-inherits"
        ]
        assert [(n["subject"], n["shown"]) for n in inherited] == [
            ("the fork received no rules because it inherits its parent's", False)
        ]
        assert delivery.message is None


class TestDeliveredTextIsRuleTextOnly:
    def test_a_part_holds_the_rule_bodies_sorted_by_name_and_no_other_line(self, world):
        world.rule("sorting", "Sort what you hold.\n")
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.manifest(DECLARED + "defaults: ['sorting', 'core-rules']\n")

        delivery = world.start_session()

        assert delivery.context.splitlines() == [
            "Hold every rule as mandatory.",
            "Sort what you hold.",
        ]


def unreadable(path):
    path.chmod(0o000)
    return path


def notice_entries(world, kind):
    return [n for r in world.records() for n in r["notices"] if n["kind"] == kind]


class TestNoticesReachThePersonAndTheRecordNeverTheAgent:
    def test_a_delivery_that_raises_no_shown_notice_shows_the_person_no_message(self, world):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: ['voice']\n")

        delivery = world.start_session()

        assert delivery.message is None
        assert [r["message_sent"] for r in world.records()] == [False]

    def test_several_shown_notices_reach_the_person_as_one_message_and_the_record_as_one_entry_each(
        self, world
    ):
        world.rule("voice")
        unreadable(world.rule("tone"))
        world.manifest(DECLARED + "defaults: ['voice', 'tone', 'ghost-one', 'ghost-two']\n")

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
    ):
        world.rule("voice")
        world.rule("tone@dry")
        world.manifest("models: ['opus']\nflags: ['strict']\ndefaults: ['voice', 'tone']\n")
        world.environment["RULESETS_FLAGS"] = "stirct"

        delivery = world.start_session(model="claude-x-1")

        assert len(delivery.messages) == 1
        assert all(name in delivery.message for name in ("claude-x-1", "stirct", "tone"))
        assert delivery.context == "text of voice\n"


class TestAnUnreadableRuleFileIsWithheld:
    def test_the_session_receives_voice_and_not_tone_and_the_notice_names_the_file_and_the_error(
        self, world
    ):
        world.rule("voice")
        unreadable(world.rule("tone"))
        world.manifest(DECLARED + "defaults: ['tone', 'voice']\n")

        delivery = world.start_session()

        assert delivery.context == "text of voice\n"
        assert "tone.md" in delivery.message
        assert "Permission denied" in delivery.message
        assert [w["rule"] for r in world.records() for w in r["withheld"]] == ["tone"]


class TestFactsSwitchesAndHostVariablesGoToTheRecordAlone:
    def test_an_absent_agent_fact_reaches_the_record_and_shows_no_message(self, world):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: ['voice']\nwhen:\n  - agent eval-runner: ['voice']\n")

        delivery = world.start_session()

        assert [n["shown"] for n in notice_entries(world, "agent-absent")] == [False]
        assert delivery.message is None


class TestADelegateStartThatShowsNoMessageSendsShownNoticesToTheRecordAlone:
    def test_a_withheld_rule_at_a_delegates_start_is_a_shown_notice_in_the_record_and_no_message(
        self, world
    ):
        world.rule("voice")
        unreadable(world.rule("tone"))
        world.manifest(DECLARED + "defaults: ['tone', 'voice']\n")

        delivery = world.start_delegate("critic")

        assert delivery.messages == []
        withheld = notice_entries(world, "rule-withheld")
        assert [n["shown"] for n in withheld] == [True]
        assert [r["message_sent"] for r in world.records()] == [False]
        assert delivery.context == "text of voice\n"


class TestEveryPartOfOneDeliveryCarriesWhatItsFirstPartComposed:
    def test_later_parts_ignore_a_toggle_and_a_launch_flag_that_arrive_after_the_first_part(
        self, world
    ):
        bodies = {name: f"{name} " + "x" * 5990 + "\n" for name in ("a-rule", "b-rule", "c-rule")}
        for name, text in bodies.items():
            world.rule(name, text)
        world.rule("security-pass")
        world.manifest(
            DECLARED
            + "flags: ['strict']\n"
            + "defaults: ['a-rule', 'b-rule', 'c-rule']\n"
            + "when:\n  - flag strict: ['security-pass']\n"
        )
        payload = {"session_id": "s1", "agent_id": "a1", "agent_type": "critic", "prompt_id": "p1"}

        first = world.run_part("SubagentStart", payload, 1)
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
    ):
        names = [f"rule-{number:02d}" for number in range(10)]
        bodies = {name: name + " " + "x" * (8500 - len(name) - 2) + "\n" for name in names}
        for name, text in bodies.items():
            world.rule(name, text)
        world.rule("zeta", "zeta " + "x" * 8494 + "\n")
        world.manifest(DECLARED + "defaults: ['*']\n")

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


def declare_strict(world):
    """A pool whose rule `security-pass` joins a context that holds the flag `strict`."""

    world.rule("core-rules")
    world.rule("security-pass")
    world.manifest(
        DECLARED
        + "flags: ['strict']\n"
        + "defaults: ['core-rules']\n"
        + "when:\n  - flag strict: ['security-pass']\n"
    )


def fork_session(world, parent="s1", fork="s2"):
    """The fork's SessionStart, over transcripts shaped as the harness writes them.

    The project directory also holds an unrelated session's transcript, written after the
    parent's, so that the newest file there is not the parent's.
    """

    parent_transcript = write_transcript(world.transcripts, parent)
    write_transcript(world.transcripts, "unrelated")
    transcript = write_transcript(world.transcripts, fork, fork_of=parent_transcript)
    return world.start_session(session_id=fork, source="fork", transcript_path=str(transcript))


class TestAToggleReachesOnlyDelegateDeliveriesThatBeginAfterIt:
    def test_a_rule_a_toggle_removes_stays_in_the_main_session_and_leaves_the_next_delegate(
        self, world
    ):
        world.rule("writing-code")
        world.rule("voice")
        world.manifest(
            DECLARED
            + "flags: ['without-writing-code']\n"
            + "defaults: ['writing-code', 'voice']\n"
            + "when:\n  - flag without-writing-code: ['-writing-code']\n"
        )
        session = world.start_session()
        assert "text of writing-code" in session.context

        toggled = world.toggle("flag without-writing-code")

        assert toggled.returncode == 0, toggled.stderr
        assert "text of writing-code" not in toggled.stdout
        assert world.start_delegate().context == "text of voice\n"

    def test_a_compaction_after_a_toggle_composes_from_the_launch_flags_alone(self, world):
        world.rule("core-rules")
        world.rule("security-pass")
        world.rule("loud-pass")
        world.manifest(
            DECLARED
            + "flags: ['strict', 'loud']\n"
            + "defaults: ['core-rules']\n"
            + "when:\n  - flag strict: ['security-pass']\n  - flag loud: ['loud-pass']\n"
        )
        world.environment["RULESETS_FLAGS"] = "loud"
        assert world.toggle("flag strict").returncode == 0

        compacted = world.start_session(source="compact")

        assert compacted.context == "text of core-rules\ntext of loud-pass\n"

    def test_a_running_delegate_keeps_the_rules_its_first_part_composed_when_none_is_toggled(
        self, world
    ):
        bodies = {name: f"{name} " + "x" * 5990 + "\n" for name in ("a-rule", "b-rule", "c-rule")}
        for name, text in bodies.items():
            world.rule(name, text)
        world.rule("writing-code")
        world.manifest(DECLARED + "defaults: ['writing-code', 'a-rule', 'b-rule', 'c-rule']\n")
        payload = {"session_id": "s1", "agent_id": "a1", "agent_type": "critic", "prompt_id": "p1"}

        first = world.run_part("SubagentStart", payload, 1)
        assert world.toggle("none").returncode == 0
        later = {part: world.run_part("SubagentStart", payload, part) for part in range(2, 11)}

        delivery = Delivery({1: first, **later})
        assert delivery.context == "".join(bodies.values()) + "text of writing-code\n"
        assert world.start_delegate(agent_id="a2").context == ""

    def test_all_toggled_after_the_first_delivery_gives_the_main_session_nothing_and_the_next_delegate_every_rule(
        self, world
    ):
        world.rule("core-rules")
        world.rule("critic-rules")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
        assert world.start_session().context == CORE

        toggled = world.toggle("all")

        assert toggled.returncode == 0, toggled.stderr
        assert "text of" not in toggled.stdout
        assert world.start_delegate().context == CORE + "text of critic-rules\n"


class TestThePluginShipsAToggleSkillWithFiveActions:
    def test_the_flag_action_sets_a_declared_flag_for_the_next_delegate_and_names_toggle_as_its_source(
        self, world
    ):
        declare_strict(world)

        toggled = world.toggle("flag strict")
        delivery = world.start_delegate()

        assert toggled.returncode == 0, toggled.stderr
        assert delivery.context == CORE + SECURITY
        (record,) = world.records()
        assert [(f["name"], f["source"]) for f in record["flags"]] == [("strict", "toggle")]


class TestTheActionsAllAndNoneSetTheSessionBandsList:
    def test_the_later_of_all_and_none_decides_in_each_of_two_sessions(self, world):
        world.rule("core-rules")
        world.rule("critic-rules")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")

        for action in ("all", "none"):
            assert world.toggle(action, session_id="all-then-none").returncode == 0
        for action in ("none", "all"):
            assert world.toggle(action, session_id="none-then-all").returncode == 0

        first = world.start_delegate(session_id="all-then-none")
        second = world.start_delegate(session_id="none-then-all")
        assert first.context == ""
        assert second.context == CORE + "text of critic-rules\n"


class TestTheFlagActionsCheckTheNameAgainstTheManifestsFlags:
    def test_an_undeclared_flag_name_is_named_refused_and_writes_nothing(self, world):
        declare_strict(world)
        before = world.start_delegate(agent_id="a0").context

        toggled = world.toggle("flag stirct")

        assert toggled.returncode != 0
        assert "stirct" in toggled.stderr
        assert not world.state_file().exists()
        assert world.start_delegate(agent_id="a1").context == before == CORE


class TestTheActionClearRemovesTheSessionsState:
    def test_clear_undoes_none_so_the_next_delegate_gets_the_manifests_rules(self, world):
        world.rule("core-rules")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
        assert world.toggle("none").returncode == 0

        cleared = world.toggle("clear")

        assert cleared.returncode == 0, cleared.stderr
        assert not world.state_file().exists()
        assert world.start_delegate().context == CORE


class TestSessionStateEndsAtAClearAndAtTheSessionsEnd:
    def test_a_cleared_session_ends_its_toggles(self, world):
        declare_strict(world)
        assert world.toggle("flag strict").returncode == 0

        world.start_session(source="clear")

        assert world.start_delegate().context == CORE

    def test_a_closed_session_ends_its_toggles_for_the_resumed_session(self, world):
        world.rule("core-rules")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
        assert world.toggle("none").returncode == 0

        world.end_session()
        world.start_session(source="resume")

        assert world.start_delegate().context == CORE


class TestCompactionKeepsSessionState:
    def test_a_compacted_session_keeps_the_flag_a_toggle_set_for_later_delegates(self, world):
        declare_strict(world)
        assert world.toggle("flag strict").returncode == 0

        world.start_session(source="compact")

        assert world.start_delegate().context == CORE + SECURITY


class TestAForkedSessionStartsWithACopyOfItsParentsSessionState:
    def test_a_fork_inherits_the_toggles_while_the_parents_later_toggle_stays_its_own(self, world):
        declare_strict(world)
        assert world.toggle("flag strict", session_id="s1").returncode == 0
        fork_session(world)

        assert world.toggle("unflag strict", session_id="s1").returncode == 0

        assert world.start_delegate(session_id="s2").context == CORE + SECURITY
        assert world.start_delegate(session_id="s1").context == CORE

    def test_a_toggle_in_the_fork_leaves_the_parents_state_unchanged(self, world):
        declare_strict(world)
        assert world.toggle("flag strict", session_id="s1").returncode == 0
        fork_session(world)

        assert world.toggle("unflag strict", session_id="s2").returncode == 0

        assert world.start_delegate(session_id="s1").context == CORE + SECURITY
        assert world.start_delegate(session_id="s2").context == CORE


class TestAForkedSessionWhoseParentIsNotFound:
    def test_it_starts_with_empty_state_and_a_shown_notice_says_its_parents_state_was_not_found(
        self, world
    ):
        declare_strict(world)
        assert world.toggle("flag strict", session_id="s1").returncode == 0
        write_transcript(world.transcripts, "s1")
        lonely = write_transcript(world.transcripts, "s2")

        delivery = world.start_session(session_id="s2", source="fork", transcript_path=str(lonely))

        assert delivery.message is not None
        assert "parent" in delivery.message
        assert "not found" in delivery.message
        (shown,) = [
            n for n in world.records("s2")[0]["notices"] if n["kind"] == "fork-parent-missing"
        ]
        assert shown["shown"] is True
        assert world.start_delegate(session_id="s2").context == CORE

    def test_a_fork_whose_parent_is_found_draws_no_such_notice(self, world):
        declare_strict(world)
        assert world.toggle("flag strict", session_id="s1").returncode == 0

        delivery = fork_session(world)

        assert delivery.message is None
        assert [
            n for n in world.records("s2")[0]["notices"] if n["kind"] == "fork-parent-missing"
        ] == []


class TestDeliveryRunsOnPython314OrLater:
    def test_the_launcher_refuses_python_3_13_with_a_message_to_the_person_and_exit_zero(
        self, tmp_path
    ):
        stub(tmp_path, "python3", minor=13, has_yaml=True)

        result = launch(tmp_path, announce=True)

        assert result.returncode == 0
        assert "3.14" in result.stderr
        output = json.loads(result.stdout)
        assert "3.14" in output["systemMessage"]
        assert "hookSpecificOutput" not in output, "the agent's context holds no such line"

    def test_a_session_on_python_3_13_starts_without_rules_and_shows_the_person_the_requirement(
        self, world, tmp_path
    ):
        world.rule("core-rules")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
        stub(tmp_path, "python3", minor=13, has_yaml=True)
        world.environment["PATH"] = path_of(tmp_path)

        delivery = world.start_session()

        assert delivery.context == ""
        assert len(delivery.messages) == 1
        assert "3.14" in delivery.message

    def test_a_session_on_python_3_14_with_the_yaml_library_receives_its_rules_and_no_requirement_message(
        self, world
    ):
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
        world.environment["RULESETS_PYTHON"] = sys.executable
        assert sys.version_info >= (3, 14)

        delivery = world.start_session()

        assert delivery.context == "Hold every rule as mandatory.\n"
        assert delivery.message is None

    def test_the_launcher_refuses_python_3_14_without_the_yaml_library_and_names_the_requirement(
        self, tmp_path
    ):
        stub(tmp_path, "python3", minor=14, has_yaml=False)

        result = launch(tmp_path, announce=True)

        assert result.returncode == 0
        assert "pyyaml" in result.stderr
        output = json.loads(result.stdout)
        assert "pyyaml" in output["systemMessage"]
        assert "hookSpecificOutput" not in output, "the agent's context holds no such line"


class TestSessionStateRoundTripsThroughItsFile:
    def test_a_band_and_flags_written_are_the_band_and_flags_read(self, tmp_path):
        locations = Locations(tmp_path)
        written = SessionState(Band.NONE, {"strict": FlagSetting.SET, "loud": FlagSetting.UNSET})

        write_state(locations, "s1", written)

        assert read_state(locations, "s1") == written
        assert list((tmp_path / ".tmp" / "rulesets-engine" / "session").iterdir()) == [
            tmp_path / ".tmp" / "rulesets-engine" / "session" / "s1.yaml"
        ]


def tree_of(root):
    """Every file under `root` with its bytes, so a later read shows any file written or changed."""

    return {p.relative_to(root): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def delegate_records(world):
    return [r for r in world.records() if r["scope"] == "delegate"]


class TestAPreToolUseHookRecordsTheModelACallerNamesForOneSpawn:
    def test_the_recording_hook_is_wired_on_the_agent_tool_alone(self):
        groups = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]

        assert [group["matcher"] for group in groups] == ["Agent"]

    def test_the_model_a_caller_names_for_a_spawn_is_the_model_its_delegate_is_composed_for(
        self, world
    ):
        world.rule("core-rules")
        world.rule("terse-rules")
        world.manifest(
            "models: ['opus', 'haiku']\ndefaults: ['core-rules']\n"
            "when:\n  - model haiku: ['terse-rules']\n"
        )
        world.start_session(model=OPUS)

        recorded = world.spawn("critic", model="haiku")
        delivery = world.start_delegate("critic")

        assert (recorded.returncode, recorded.stdout) == (0, "")
        assert delivery.context == "text of core-rules\ntext of terse-rules\n"
        (record,) = delegate_records(world)
        assert (record["model"]["name"], record["model"]["source"]) == ("haiku", "per-spawn")

    def test_a_spawn_that_names_no_model_leaves_the_delegate_on_its_parents_model(self, world):
        world.rule("core-rules")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
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
    def test_a_payload_the_hook_cannot_read_exits_zero_and_prints_nothing(self, world, stdin):
        result = world.run_spawn_hook(stdin)

        assert (result.returncode, result.stdout) == (0, "")

    def test_a_state_directory_that_cannot_be_written_exits_zero_and_prints_nothing(
        self, world, tmp_path
    ):
        not_a_directory = tmp_path / "file"
        not_a_directory.write_text("", encoding="utf-8")
        world.environment["CLAUDE_CONFIG_DIR"] = str(not_a_directory)

        result = world.spawn("critic", model="haiku")

        assert (result.returncode, result.stdout) == (0, "")


class TestTheActionNoneLeavesANoticeThatTheContextReceivedNothing:
    def test_a_delegate_under_none_receives_no_rule_and_a_shown_notice_says_it_received_nothing(
        self, world
    ):
        world.rule("core-rules")
        world.manifest(DECLARED + "defaults: ['core-rules']\n")
        world.start_session(model=OPUS)
        assert world.toggle("none").returncode == 0

        delivery = world.start_delegate()

        assert delivery.context == ""
        (record,) = delegate_records(world)
        (notice,) = [n["subject"] for n in record["notices"] if n["shown"]]
        assert "received nothing" in notice
        assert "fail" not in notice.lower()


class TestASessionsModelFactIsRecordedAndReadBack:
    def test_a_session_whose_start_reports_no_identifier_records_that_none_was_available(
        self, world
    ):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: ['voice']\n")

        world.start_session(model=None)

        record = world.model_record()
        assert record is not None
        assert record["identifier"] is None
        assert "no model identifier was available" in json.dumps(record)

    def test_a_session_that_starts_on_an_identifier_records_it_for_a_later_start_to_read(
        self, world
    ):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: ['voice']\n")
        world.start_session(model=OPUS)

        world.start_session(model=None, source="resume")

        (_, resumed) = world.records()
        assert (resumed["model"]["identifier"], resumed["model"]["source"]) == (
            OPUS,
            "session-record",
        )


class TestADeliverysFirstPartAloneWritesTheSessionsModelRecord:
    def test_the_first_part_writes_the_record_and_no_later_part_writes_it_again(self, world):
        for name in ("a-rule", "b-rule", "c-rule"):
            world.rule(name, f"{name} " + "x" * 5990 + "\n")
        world.manifest(DECLARED + "defaults: ['a-rule', 'b-rule', 'c-rule']\n")
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


def declare_voice_scene(world):
    """A pool whose `core-rules` every context receives, and a haiku or sonnet delegate adds a rule."""

    world.rule("core-rules")
    world.rule("haiku-rules")
    world.rule("sonnet-rules")
    world.manifest(
        "models: ['opus', 'sonnet', 'haiku']\ndefaults: ['core-rules']\n"
        "when:\n  - model haiku: ['haiku-rules']\n  - model sonnet: ['sonnet-rules']\n"
    )


class TestADelegateReceivesAllItsRulesAtItsStart:
    def test_a_delegate_spawned_after_a_rule_edit_receives_the_edit_and_the_earlier_one_keeps_its_text(
        self, world
    ):
        world.rule("voice", "old voice\n")
        world.manifest(DECLARED + "defaults: ['voice']\n")

        before = world.start_delegate(agent_id="a1")
        world.rule("voice", "edited voice\n")
        after = world.start_delegate(agent_id="a2")

        assert before.context == "old voice\n"
        assert after.context == "edited voice\n"

    def test_delegates_on_different_models_each_receive_the_composition_of_their_own_facts(
        self, world
    ):
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
    ):
        declare_voice_scene(world)
        world.user_agent("quick", "haiku")
        session = world.start_session(model=OPUS)
        record = world.model_record()
        record_bytes = (world.config / ".tmp/rulesets-engine/models/s1.json").read_bytes()
        rulesets = tree_of(world.rulesets)

        delegate = world.start_delegate("quick")

        assert session.context == "text of core-rules\n"
        assert delegate.context == "text of core-rules\ntext of haiku-rules\n"
        assert record is not None
        assert record["identifier"] == OPUS
        assert (world.config / ".tmp/rulesets-engine/models/s1.json").read_bytes() == record_bytes
        assert tree_of(world.rulesets) == rulesets


class TestAMissingOrUnparsableManifestDeliversEveryRuleAtItsDefault:
    def test_a_missing_manifest_delivers_each_default_form_sorted_and_the_notice_names_the_path(
        self, world
    ):
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("a-rule", "a text\n")

        delivery = world.start_session()

        assert delivery.context == "a text\ndefault voice\n"
        assert str(world.rulesets / "manifest.yaml") in delivery.message

    def test_an_unparsable_manifest_delivers_each_default_form_and_the_notice_names_path_and_error(
        self, world
    ):
        world.rule("voice", "default voice\n")
        world.rule("a-rule", "a text\n")
        broken = "models: ['opus'\ndefaults: ['voice']\n"
        world.manifest(broken)
        with pytest.raises(yaml.YAMLError) as parsed:
            yaml.safe_load(broken)

        delivery = world.start_session()

        assert delivery.context == "a text\ndefault voice\n"
        assert str(world.rulesets / "manifest.yaml") in delivery.message
        assert parsed.value.problem in delivery.message


class TestACompositionThatReachesNoRuleIsNoFailure:
    @pytest.mark.parametrize(
        "pool",
        [[], ["voice"]],
        ids=["the pool holds no rule file", "no applying statement includes a rule"],
    )
    def test_the_session_starts_with_no_text_and_a_notice_says_the_context_received_nothing(
        self, world, pool
    ):
        for name in pool:
            world.rule(name)
        world.manifest(DECLARED + "defaults: []\n")

        delivery = world.start_session()

        assert delivery.context == ""
        assert "received nothing" in delivery.message
        assert "fail" not in delivery.message.lower()


class TestAMissingRulesetsDirectoryIsScaffolded:
    def test_a_session_without_a_rulesets_directory_starts_with_an_empty_one_and_a_notice_saying_where(
        self, world
    ):
        shutil.rmtree(world.rulesets)

        delivery = world.start_session()

        assert delivery.context == ""
        assert str(world.rulesets) in delivery.message
        assert list((world.rulesets / "rules").iterdir()) == []
        declared = yaml.safe_load((world.rulesets / "manifest.yaml").read_text(encoding="utf-8"))
        assert not any(declared.values())


class TestADeliveryFailureKeepsTheSessionRunning:
    def test_a_scaffold_that_cannot_write_its_parent_starts_the_session_and_says_why(self, world):
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
    ):
        not_a_directory = tmp_path / "file"
        not_a_directory.write_text("", encoding="utf-8")
        world.environment["CLAUDE_CONFIG_DIR"] = str(not_a_directory)

        delivery = world.start_session()

        assert delivery.context == ""
        assert len(delivery.messages) == 1
        assert "not a directory" in delivery.message.lower()
        assert "deliver.py" in delivery.message
        assert "--part 1" in delivery.message


class TestTermsOfDelivery:
    def test_a_delegates_record_names_the_variant_and_its_digest_of_the_text_delivered(self, world):
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.manifest(DECLARED + "defaults: ['voice']\nwhen:\n  - agent critic: ['voice@terse']\n")

        delivery = world.start_delegate("critic")

        (record,) = delegate_records(world)
        (line,) = record["rules"]
        body = (world.rulesets / "rules" / "voice@terse.md").read_bytes().decode()
        assert (line["rule"], line["variant"]) == ("voice", "terse")
        assert delivery.context == body
        assert line["digest"] == hashlib.sha256(delivery.context.encode()).hexdigest()


SONNET = "claude-sonnet-5-5"
HAIKU = "claude-haiku-4-5"
TIERS = "models: ['opus', 'sonnet', 'haiku']\n"


def declare_tiers(world, *keyed):
    """A pool whose `core-rules` every context receives, and a `<tier>-rules` for each tier in `keyed`."""

    world.rule("core-rules")
    blocks = ""
    for tier in keyed:
        world.rule(f"{tier}-rules")
        blocks += f"  - model {tier}: ['{tier}-rules']\n"
    when = f"when:\n{blocks}" if blocks else ""
    world.manifest(TIERS + "defaults: ['core-rules']\n" + when)


def switch_records(world):
    return [r for r in world.records() if r.get("switch") is not None]


def counted_models(world):
    """The identifiers of the records the readers count, in file order."""

    from rulesets.audit.counted import counted
    from rulesets.audit.delivery_record import DeliveryRecord

    return [
        r.model.identifier for r in counted(DeliveryRecord.from_json(r) for r in world.records())
    ]


class TestAMidSessionModelChangeDeliversTheNewRulesAndStatesItsLimit:
    def test_a_switch_to_a_differently_composed_model_delivers_its_rules_and_notes_the_earlier_ones_remain(
        self, world
    ):
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
    ):
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
    ):
        declare_tiers(world, "opus")
        world.start_session(model=SONNET)

        delivery = world.switch_model(HAIKU, from_model=SONNET, prompt_id="p1")

        assert [out for out in delivery.outputs.values() if out] == []
        assert len(world.records()) == 1, "only the session start left a delivery record"
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == HAIKU

    def test_a_delegate_after_a_switch_that_composes_alike_reads_the_new_model_as_its_parents(
        self, world
    ):
        declare_tiers(world, "haiku")
        world.start_session(model=SONNET)
        world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert (record["model"]["identifier"], record["model"]["source"]) == (
            OPUS,
            "parent-record",
        )


def declare_session_pool(world):
    """A pool of `core-rules`, `sorting`, and `voice`, and a composition reaching the first two."""

    world.rule("core-rules", "Hold every rule as mandatory.\n")
    world.rule("sorting", "Sort what you hold.\n")
    world.rule("voice", "Speak plainly.\n")
    world.manifest(DECLARED + "defaults: ['core-rules', 'sorting']\n")


WHOLE_COMPOSITION = "Hold every rule as mandatory.\nSort what you hold.\n"


class TestASessionReceivesAllItsRulesAtEveryStart:
    def test_a_new_session_receives_the_bodies_its_composition_reaches_and_no_other(self, world):
        declare_session_pool(world)

        delivery = world.start_session(source="startup")

        assert delivery.context == WHOLE_COMPOSITION

    def test_a_compacted_session_receives_every_body_its_composition_yields(self, world):
        declare_session_pool(world)
        world.start_session(source="startup")

        delivery = world.start_session(source="compact")

        assert delivery.context == WHOLE_COMPOSITION

    def test_a_cleared_session_receives_every_body_its_composition_yields(self, world):
        declare_session_pool(world)
        world.start_session(source="startup")

        delivery = world.start_session(source="clear")

        assert delivery.context == WHOLE_COMPOSITION

    def test_a_resumed_session_is_composed_for_the_model_its_record_names(self, world):
        declare_tiers(world, "opus")
        world.start_session(model=OPUS)

        delivery = world.start_session(model=None, source="resume")

        assert delivery.context == "text of core-rules\ntext of opus-rules\n"

    def test_a_forked_session_is_composed_for_the_model_its_start_reports(self, world):
        declare_tiers(world, "opus")
        world.start_session(session_id="s1", model=SONNET)

        delivery = fork_session(world)

        assert delivery.context == "text of core-rules\ntext of opus-rules\n"

    def test_a_ruleset_over_9000_characters_divides_into_whole_sorted_parts_one_entry_each(
        self, world
    ):
        bodies = {name: f"{name} " + "x" * 3990 + "\n" for name in ("a-rule", "b-rule", "c-rule")}
        for name, text in bodies.items():
            world.rule(name, text)
        world.manifest(DECLARED + "defaults: ['c-rule', 'a-rule', 'b-rule']\n")

        delivery = world.start_session()

        parts = {
            part: json.loads(out)["hookSpecificOutput"]["additionalContext"]
            for part, out in delivery.outputs.items()
            if out.strip()
        }
        assert parts == {
            1: bodies["a-rule"] + bodies["b-rule"],
            2: bodies["c-rule"],
        }
        assert [delivery.outputs[part].strip() for part in range(3, 11)] == [""] * 8


class TestOnlyTheLastOfSeveralRapidSwitchesCountsAsDelivered:
    def test_two_switches_before_the_next_request_count_only_the_last(self, world):
        declare_tiers(world, "sonnet", "haiku")
        world.start_session(model=OPUS)

        world.switch_model(SONNET, from_model=OPUS, prompt_id="p1")
        world.switch_model(HAIKU, from_model=SONNET, prompt_id="p1")

        assert [r["model"]["identifier"] for r in switch_records(world)] == [SONNET, HAIKU]
        assert counted_models(world) == [OPUS, HAIKU]
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == HAIKU

    def test_a_switch_a_request_then_another_switch_count_both(self, world):
        declare_tiers(world, "sonnet", "haiku")
        world.start_session(model=OPUS)

        world.switch_model(SONNET, from_model=OPUS, prompt_id="p1")
        world.switch_model(HAIKU, from_model=SONNET, prompt_id="p2")

        assert counted_models(world) == [OPUS, SONNET, HAIKU]

    def test_a_switch_payload_with_no_prompt_id_counts_as_delivered(self, world):
        declare_tiers(world, "sonnet", "haiku")
        world.start_session(model=OPUS)

        world.switch_model(SONNET, from_model=OPUS)
        world.switch_model(HAIKU, from_model=SONNET)

        assert counted_models(world) == [OPUS, SONNET, HAIKU]
        check = world.delivery_check()
        assert (check.stdout, check.returncode) == ("", 0)
        assert "composed but not delivered" not in check.stdout
