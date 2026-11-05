#!/usr/bin/env python3
"""A context receives its rules by hook, as rule text only, and the person hears of problems.

Serves the person whose sessions and delegates start with rules, and the engineer who reads the
delivery record afterwards. Each case builds a configuration directory under `tmp_path` and runs
the hook entries that `hooks/hooks.json` wires for an event, as the harness runs them.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_ruleset_delivery.py`.
"""

import json
import pathlib
import sys

import pytest
from delivery_world import DECLARED, Delivery, World
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
        world.manifest(DECLARED + "when:\n  - agent eval-runner: ['voice']\n")

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
