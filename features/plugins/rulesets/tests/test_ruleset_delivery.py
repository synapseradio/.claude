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

import pytest
import yaml
from delivery_world import (
    DECLARED,
    HAIKU,
    HOOKS_JSON,
    MAX_PARTS,
    OPUS,
    Delivery,
    delivered,
)
from launcher_stubs import launch, stub
from rulesets.locations import Locations
from rulesets.session.state import (
    Band,
    SessionState,
    write_state,
)


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

    @pytest.mark.parametrize(
        ("home", "definition_bytes", "listed_tools"),
        [
            ("user", b"---\nname: critic\nmodel: haiku\n---\nReview the diff.\r\n\xc3\xa9", None),
            (
                "project",
                b"---\nname: critic\ndescription: a test agent\ntools: Read, Grep\n---\n"
                b"Review the diff.\r\n\xc3\xa9",
                "listed",
            ),
        ],
        ids=["a user agent definition", "a project agent definition"],
    )
    def test_a_delivery_leaves_the_agent_definition_file_byte_for_byte_as_it_was(
        self, world, home, definition_bytes, listed_tools
    ) -> None:
        world.rule("core-rules", "Hold every rule as mandatory.\n")
        world.write_config(DECLARED + "defaults: core-rules\n")
        root = world.config if home == "user" else world.project / ".claude"
        definition = root / "agents" / "critic.md"
        definition.parent.mkdir(parents=True)
        definition.write_bytes(definition_bytes)

        delivery = world.start_delegate(
            "critic", **({"cwd": str(world.project)} if home == "project" else {})
        )

        assert delivery.context == "Hold every rule as mandatory.\n"
        if listed_tools:
            (record,) = world.delegate_records()
            assert record["tools"]["state"] == listed_tools, "the delegate read the definition"
        assert definition.read_bytes() == definition_bytes


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
        later = {
            part: world.run_part("SubagentStart", payload, part) for part in range(2, MAX_PARTS + 1)
        }

        delivery = Delivery({1: first, **later})
        assert delivery.context == "".join(bodies.values())
        assert "security-pass" not in delivery.context
        assert [part for part, out in delivery.outputs.items() if out] == [1, 2, 3]


class TestRulesPastTheLastPartReachAShownNotice:
    def test_a_composition_one_part_past_the_cap_delivers_the_cap_and_names_the_rule_left_out(
        self, world
    ) -> None:
        names = [f"rule-{number:02d}" for number in range(MAX_PARTS)]
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


class TestSessionStateEndsAtAClearAndAtTheSessionsEnd:
    @pytest.mark.parametrize(
        "source",
        ["clear", "resume"],
        ids=["a cleared session", "a resume after a crash that sent no session end"],
    )
    def test_a_clear_or_a_resume_ends_the_sessions_toggles(self, world, source) -> None:
        declare_strict(world)
        assert world.toggle("flag strict").returncode == 0
        assert world.state_file().exists()

        world.start_session(source=source)

        assert not world.state_file().exists()
        assert world.start_delegate().context == CORE

    def test_a_closed_session_ends_its_toggles_for_the_resumed_session(self, world) -> None:
        world.rule("core-rules")
        world.write_config(DECLARED + "defaults: core-rules\n")
        assert world.toggle("none").returncode == 0

        world.end_session()
        assert not world.state_file().exists()
        world.start_session(source="resume")

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
    @pytest.mark.parametrize(
        ("minor", "has_yaml", "named"),
        [(14, True, "3.15"), (15, False, "pyyaml")],
        ids=["a Python older than 3.15", "Python 3.15 without the yaml library"],
    )
    def test_the_launcher_refuses_with_a_message_to_the_person_that_names_the_requirement_and_exits_zero(
        self, tmp_path, minor, has_yaml, named
    ) -> None:
        stub(tmp_path, "python3", minor=minor, has_yaml=has_yaml)

        result = launch(tmp_path, announce=True)

        assert result.returncode == 0
        assert named in result.stderr
        output = json.loads(result.stdout)
        assert named in output["systemMessage"]
        assert "hookSpecificOutput" not in output, "the agent's context holds no such line"


def tree_of(root) -> dict[pathlib.Path, bytes]:
    """Every file under `root` with its bytes, so a later read shows any file written or changed."""
    return {p.relative_to(root): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


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
        (record,) = world.delegate_records()
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
        (record,) = world.delegate_records()
        (notice,) = [n["subject"] for n in record["notices"] if n["shown"]]
        assert "received nothing" in notice
        assert "fail" not in notice.lower()


NOT_UTF_8 = b'{"session_id": "s1", "source": "\xff\xfe"}'


class TestEveryHookExitsZeroOnAPayloadThatIsNotUtf8:
    @pytest.mark.parametrize(
        "last_argument",
        ["--part 1", "--part 2", "--end", 'record-spawn.py"', 'record-load.py"'],
    )
    def test_the_hook_exits_zero_and_prints_nothing(self, world, last_argument) -> None:
        result = world.run_hook_bytes(last_argument, NOT_UTF_8)

        assert (result.returncode, result.stdout) == (0, b"")


class TestAnUnreadablePayloadLeavesATrace:
    def test_a_start_naming_no_session_prints_the_reason_to_stderr_and_shows_the_person_a_notice(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")

        result = world.run_part_process("SessionStart", {"source": "startup"}, 1)

        assert result.returncode == 0
        assert result.stderr
        assert json.loads(result.stdout)["systemMessage"]
        assert "additionalContext" not in result.stdout

    def test_a_switch_naming_no_target_model_leaves_a_failure_record_and_delivers_nothing(
        self, world
    ) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=SONNET)

        result = world.run_part_process(
            "PostModelSwitch", {"session_id": "s1", "from_model": SONNET, "prompt_id": "p1"}, 1
        )

        assert result.returncode == 0
        assert result.stderr
        assert result.stdout == ""
        _, failed = world.records()
        (notice,) = failed["notices"]
        assert notice["kind"] == "delivery-failure"
        assert failed["rules"] == []


class TestASessionsModelFactIsRecordedAndReadBack:
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
    def test_a_rule_edited_after_a_delegate_starts_reaches_the_next_delegate_and_not_the_running_one(
        self, world
    ) -> None:
        three_part_pool(world)
        payload = {"session_id": "s1", "agent_id": "a1", "agent_type": "critic", "prompt_id": "p1"}

        first = world.run_part("SubagentStart", payload, 1)
        three_part_pool(world, mark="NEW")
        later = {
            part: world.run_part("SubagentStart", payload, part) for part in range(2, MAX_PARTS + 1)
        }
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
        (first_record, _) = world.delegate_records()
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
    @pytest.mark.parametrize(
        "broken",
        [None, "models: ['opus'\ndefaults: ['voice']\n"],
        ids=["a missing config", "an unparsable config"],
    )
    def test_the_session_receives_each_default_form_sorted_and_the_notice_names_the_path_and_any_error(
        self, world, broken
    ) -> None:
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("a-rule", "a text\n")
        if broken is not None:
            world.write_config(broken)
            with pytest.raises(yaml.YAMLError) as parsed:
                yaml.safe_load(broken)

        delivery = world.start_session()

        assert delivery.context == "a text\ndefault voice\n"
        assert str(world.rulesets / "config.yaml") in delivery.message
        if broken is not None:
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


THREE_PARTS = ("a-rule", "b-rule", "c-rule")


def three_part_pool(world, mark="OLD") -> None:
    """Rules whose bodies each fill most of a part, so that a delivery needs three parts."""
    for name in THREE_PARTS:
        world.rule(name, f"{name} {mark} " + "x" * 5980 + "\n")
    world.write_config(DECLARED + "defaults: a-rule b-rule c-rule\n")


def rerun_command_of(message) -> str:
    return message.split("run it again with: ", 1)[1]


class TestAResumedDelegateReplaysTheDeliveryItFirstReceived:
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


class TestAnIdenticalPayloadDeliveredAgainMeetsOnlyItsOwnPlan:
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

        (record,) = world.delegate_records()
        (line,) = record["rules"]
        body = (world.rulesets / "rules" / "voice@terse.md").read_bytes()
        assert body == b"terse voice", "the variant file ends without a newline"
        assert (line["rule"], line["variant"]) == ("voice", "terse")
        assert delivery.received.encode() == b"<!-- rule: voice -->\n\n" + body
        assert line["digest"] == hashlib.sha256(body).hexdigest()


SONNET = "claude-sonnet-5-5"
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


class TestAMidSessionModelChangeDeliversTheNewRulesAndStatesItsLimit:
    @pytest.mark.parametrize(
        "before", [SONNET, "glm-5"], ids=["a claimed model", "an unclaimed one"]
    )
    def test_a_switch_to_a_differently_composed_model_delivers_its_rules_and_notes_the_earlier_ones_remain(
        self, world, before
    ) -> None:
        declare_tiers(world, "sonnet", "opus")
        world.start_session(model=before)

        delivery = world.switch_model(OPUS, from_model=before, prompt_id="p1")

        assert delivery.targets == {"PostModelSwitch"}
        assert delivery.context == "text of core-rules\ntext of opus-rules\n"
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == OPUS
        (record,) = switch_records(world)
        (remaining,) = [n for n in record["notices"] if n["kind"] == "earlier-rules-remain"]
        assert remaining["shown"] is False
        assert delivery.message is None


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


def declare_session_pool(world) -> None:
    """A pool of `core-rules`, `sorting`, and `voice`, and a composition reaching the first two."""
    world.rule("core-rules", "Hold every rule as mandatory.\n")
    world.rule("sorting", "Sort what you hold.\n")
    world.rule("voice", "Speak plainly.\n")
    world.write_config(DECLARED + "defaults: core-rules sorting\n")


WHOLE_COMPOSITION = "Hold every rule as mandatory.\nSort what you hold.\n"


class TestASessionReceivesAllItsRulesAtEveryStart:
    @pytest.mark.parametrize("source", ["startup", "compact", "clear"])
    def test_a_session_receives_the_bodies_its_composition_reaches_and_no_other(
        self, world, source
    ) -> None:
        declare_session_pool(world)
        world.start_session(source="startup")

        delivery = world.start_session(source=source)

        assert delivery.context == WHOLE_COMPOSITION

    def test_a_resumed_session_is_composed_for_the_model_its_record_names(self, world) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=OPUS)

        delivery = world.start_session(model=None, source="resume")

        assert delivery.context == "text of core-rules\ntext of opus-rules\n"

    @pytest.mark.parametrize(
        ("sizes", "parts"),
        [
            ({"a-rule": 4477, "b-rule": 4478, "c-rule": 4476}, [["a-rule"], ["b-rule", "c-rule"]]),
            ({"a-rule": 4477, "b-rule": 4477, "c-rule": 10}, [["a-rule", "b-rule"], ["c-rule"]]),
            ({"a-rule": 4477, "b-rule": 4478, "c-rule": 10}, [["a-rule"], ["b-rule", "c-rule"]]),
            ({"a-rule": 4489, "b-rule": 4489}, [["a-rule"], ["b-rule"]]),
        ],
        ids=[
            "whole sorted bodies fill each part",
            "two bodies totalling exactly 9000 characters share a part",
            "a body that would take a part to 9001 characters opens the next part",
            "markers count toward the part budget",
        ],
    )
    def test_a_ruleset_over_9000_characters_divides_into_whole_sorted_parts(
        self, world, sizes, parts
    ) -> None:
        # Each marker and its blank line add 23 characters to a delivered body.
        bodies = {name: name[0] * size for name, size in sizes.items()}
        for name, text in bodies.items():
            world.rule(name, text)
        world.write_config(DECLARED + "defaults: " + " ".join(reversed(bodies)) + "\n")

        delivery = world.start_session()

        assert delivery.received_parts == {
            number: "".join(delivered(name, bodies[name]) for name in names)
            for number, names in enumerate(parts, start=1)
        }
        assert all(len(text) <= 9000 for text in delivery.received_parts.values())


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

    def test_a_no_change_switch_after_a_switch_that_counted_delivers_nothing(self, world) -> None:
        declare_tiers(world, "opus")
        world.start_session(model=SONNET)
        world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")

        second = world.switch_model(OTHER_OPUS, from_model=OPUS, prompt_id="p2")

        assert [out for out in second.outputs.values() if out] == []
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == OTHER_OPUS


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
