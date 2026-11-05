#!/usr/bin/env python3
"""The audit log shows what reached every context, and the delivery check confirms it by recomposing.

Serves the engineer who asks what each agent was told and why, and who runs `delivery-check`
after editing a manifest or a rule. Each case builds a configuration directory under `tmp_path`,
produces its records through real deliveries, and runs the `delivery-check` subcommand through
the launcher.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_instruction_load_audit.py`.
"""

import hashlib
import json
import os
import pathlib
import shutil
import sys

import pytest
from delivery_world import DECLARED, HAIKU, OPUS, World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.audit import log  # noqa: E402  (path must be set before this import)
from rulesets.audit.delivery_record import DeliveryRecord  # noqa: E402
from rulesets.locations import Locations  # noqa: E402

SONNET = "claude-sonnet-5-5"


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def delegate_records(world):
    return [r for r in world.records() if r["scope"] == "delegate"]


def lines_of(result):
    return result.stdout.splitlines()


def unreadable(path):
    path.chmod(0o000)
    return path


def declare_core_and_sorting(world):
    world.rule("core-rules")
    world.rule("sorting")
    world.manifest(DECLARED + "defaults: ['core-rules']\n")


def add_sorting_to_defaults(world):
    world.manifest(DECLARED + "defaults: ['core-rules', 'sorting']\n")


def three_part_delivery(world):
    """A session start whose three rules each fill a part of their own."""

    for name in ("a-rule", "b-rule", "c-rule"):
        world.rule(name, f"{name} " + "x" * 5990 + "\n")
    world.manifest(DECLARED + "defaults: ['a-rule', 'b-rule', 'c-rule']\n")
    return world.start_session()


class TestCheckingOneSessionAmongMany:
    def test_a_corrupt_record_in_another_sessions_directory_changes_neither_output_nor_status(
        self, world
    ):
        declare_core_and_sorting(world)
        world.start_session(session_id="A")
        world.start_session(session_id="B")
        add_sorting_to_defaults(world)
        with (world.record_files("A") / "deliveries.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("{this is not a record\n")

        with_a = world.delivery_check("B")
        shutil.rmtree(world.record_files("A"))
        without_a = world.delivery_check("B")

        assert lines_of(with_a) == ["session: sorting composed but not delivered"]
        assert (with_a.stdout, with_a.returncode) == (without_a.stdout, without_a.returncode)
        assert with_a.returncode != 0


class TestPruningASessionsRecords:
    def test_removing_a_sessions_directory_leaves_the_other_sessions_check_unchanged(self, world):
        declare_core_and_sorting(world)
        world.start_session(session_id="A")
        world.start_session(session_id="B")
        add_sorting_to_defaults(world)
        before = world.delivery_check("B")

        shutil.rmtree(world.record_files("A"))
        after = world.delivery_check("B")

        assert lines_of(before) == ["session: sorting composed but not delivered"]
        assert (after.stdout, after.returncode) == (before.stdout, before.returncode)

    def test_a_compaction_reporting_no_model_composes_for_the_identifier_the_model_record_holds(
        self, world
    ):
        world.rule("core-rules")
        world.rule("opus-rules")
        world.manifest(
            DECLARED + "defaults: ['core-rules']\nwhen:\n  - model opus: ['opus-rules']\n"
        )
        world.start_session(model=OPUS, session_id="A")
        shutil.rmtree(world.record_files("A"))

        delivery = world.start_session(model=None, session_id="A", source="compact")

        assert delivery.context == "text of core-rules\ntext of opus-rules\n"

    def test_pruning_by_age_removes_the_old_sessions_and_keeps_every_other_file(self, world):
        declare_core_and_sorting(world)
        world.start_session(session_id="old")
        world.start_session(session_id="recent")
        recent_records = world.records("recent")
        for file in world.record_files("old").iterdir():
            os.utime(file, (1_000, 1_000))
        os.utime(world.record_files("old"), (1_000, 1_000))

        removed = log.prune(Locations(world.config), older_than=2_000)

        assert removed == ("old",)
        assert not world.record_files("old").exists()
        assert world.records("recent") == recent_records
        assert world.model_record("old") is not None
        assert world.model_record("recent") is not None


class TestADelegateDeliveryIsRecordedWithItsRules:
    def test_a_delegate_record_names_session_delegate_model_scope_and_each_rule_with_variant_and_digest(
        self, world
    ):
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("sorting", "Sort it.\n")
        world.manifest(
            "models: ['haiku']\ndefaults: ['voice', 'sorting']\n"
            "when:\n  - agent critic: ['voice@terse']\n"
        )
        world.start_session()
        world.spawn("critic", "haiku")

        world.start_delegate("critic", agent_id="a1")

        (record,) = delegate_records(world)
        assert (record["session_id"], record["agent_id"], record["scope"]) == (
            "s1",
            "a1",
            "delegate",
        )
        assert record["model"]["name"] == "haiku"
        assert (record["model"]["identifier"], record["model"]["source"]) == ("haiku", "per-spawn")
        assert record["rules"] == [
            {"rule": "sorting", "variant": None, "digest": digest("Sort it.\n")},
            {"rule": "voice", "variant": "terse", "digest": digest("terse voice\n")},
        ]


class TestACompactionDeliveryIsRecordedAgain:
    def test_a_second_record_with_scope_session_follows_a_compaction(self, world):
        declare_core_and_sorting(world)
        world.start_session()

        world.start_session(source="compact")

        records = world.records()
        assert [(r["session_id"], r["scope"]) for r in records] == [("s1", "session")] * 2


class TestASwitchDeliveryIsRecordedAsASwitch:
    def test_a_switch_to_a_differently_composed_model_records_scope_switch_the_new_model_and_rules(
        self, world
    ):
        world.rule("core-rules")
        world.rule("opus-rules")
        world.manifest(
            "models: ['opus', 'sonnet', 'haiku']\ndefaults: ['core-rules']\n"
            "when:\n  - model opus: ['opus-rules']\n"
        )
        world.start_session(model=SONNET)
        world.switch_model(HAIKU, from_model=SONNET, prompt_id="p1")

        world.switch_model(OPUS, from_model=HAIKU, prompt_id="p2")

        assert [r["scope"] for r in world.records()] == ["session", "switch"]
        switched = world.records()[1]
        assert (switched["model"]["name"], switched["model"]["identifier"]) == ("opus", OPUS)
        assert [rule["rule"] for rule in switched["rules"]] == ["core-rules", "opus-rules"]
        assert switched["switch"]["prompt_id"] == "p2"


class TestARecordReadBackIsTheRecordWritten:
    def test_every_kind_of_delivery_record_reads_back_to_the_json_it_was_written_as(self, world):
        world.rule("voice")
        world.rule("voice@terse")
        world.rule("opus-rules")
        unreadable(world.rule("tone"))
        world.manifest(
            "models: ['opus', 'haiku']\nflags: ['voice-terse']\n"
            "defaults: ['voice', 'tone', 'ghost']\n"
            "when:\n  - flag voice-terse: ['voice@terse']\n  - model opus: ['opus-rules']\n"
            "  - flag nope: ['voice']\n"
        )
        world.environment["RULESETS_FLAGS"] = "voice-terse"
        agent = world.config / "agents" / "critic.md"
        agent.parent.mkdir(parents=True)
        agent.write_text(
            "---\nname: critic\ndescription: a test agent\ntools: Read, Edit\n---\nbody\n",
            encoding="utf-8",
        )
        world.start_session(model="claude-nova-1")
        world.switch_model(OPUS, from_model="claude-nova-1", prompt_id="p1")
        world.toggle_flags({"strict": "set"})
        world.start_delegate("critic")
        world.start_delegate("fork", agent_id="a2")
        world.start_session(model=None, session_id="s2")

        written = [r for sid in ("s1", "s2") for r in world.records(sid)]

        assert {r["scope"] for r in written} == {"session", "switch", "delegate"}
        assert [DeliveryRecord.from_json(r).to_json() for r in written] == written


class TestADeliveryRecordNamesEachFactWithItsSource:
    def test_the_record_names_the_variant_the_launch_flag_and_each_fact_or_why_it_is_absent(
        self, world
    ):
        world.rule("voice")
        world.rule("voice@terse")
        world.manifest(
            DECLARED
            + "flags: ['voice-terse']\ndefaults: ['voice']\n"
            + "when:\n  - flag voice-terse: ['voice@terse']\n"
        )
        world.environment["RULESETS_FLAGS"] = "voice-terse"

        world.start_session()

        (record,) = world.records()
        assert [(r["rule"], r["variant"]) for r in record["rules"]] == [("voice", "terse")]
        assert record["flags"] == [{"name": "voice-terse", "source": "launch"}]
        assert record["model"]["source"] == "harness-reported"
        assert record["kind"] == "session"
        assert record["agent"]["state"] == "absent"
        assert "--agent" in record["agent"]["reason"]
        assert record["tools"]["state"] == "absent"
        assert "no agent type" in record["tools"]["reason"]

    def test_a_delegate_record_names_its_agent_and_the_definition_file_its_tools_came_from(
        self, world
    ):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: ['voice']\n")
        definition = world.config / "agents" / "critic.md"
        definition.parent.mkdir(parents=True)
        definition.write_text(
            "---\nname: critic\ndescription: a test agent\ntools: Read, Edit\n---\nbody\n",
            encoding="utf-8",
        )

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["agent"] == {"state": "named", "name": "critic"}
        assert record["tools"] == {
            "state": "listed",
            "tools": ["Edit", "Read"],
            "source": str(definition),
        }

    def test_a_delegate_with_no_definition_file_names_why_its_tools_are_absent(self, world):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: ['voice']\n")

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["tools"]["state"] == "absent"
        assert "no definition file registers its agent type `critic`" in record["tools"]["reason"]

    def test_a_forks_record_names_why_its_agent_and_tools_facts_are_absent(self, world):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: ['voice']\n")
        world.start_session()

        world.start_delegate("fork")

        (record,) = delegate_records(world)
        assert record["agent"]["state"] == "absent"
        assert record["tools"]["state"] == "absent"
        assert "inherits its parent's" in record["agent"]["reason"]


class TestTwoSessionsLaunchedAlikeDifferByOneFlag:
    def test_the_records_differ_by_the_removed_rule_and_the_flag(self, world):
        world.rule("writing-code")
        world.rule("sorting")
        world.manifest(
            DECLARED
            + "flags: ['without-writing-code']\ndefaults: ['writing-code', 'sorting']\n"
            + "when:\n  - flag without-writing-code: ['-writing-code']\n"
        )
        world.start_session(session_id="plain")
        world.environment["RULESETS_FLAGS"] = "without-writing-code"
        world.start_session(session_id="flagged")

        (plain,) = world.records("plain")
        (flagged,) = world.records("flagged")

        assert [r["rule"] for r in plain["rules"]] == ["sorting", "writing-code"]
        assert [r["rule"] for r in flagged["rules"]] == ["sorting"]
        assert plain["flags"] == []
        assert flagged["flags"] == [{"name": "without-writing-code", "source": "launch"}]
        assert plain["model"] == flagged["model"]


class TestADelegateRecordNamesTheSessionStateItRead:
    def test_the_record_names_the_state_file_and_the_flag_a_toggle_set(self, world):
        world.rule("security-pass")
        world.manifest(
            DECLARED
            + "flags: ['strict']\ndefaults: []\nwhen:\n  - flag strict: ['security-pass']\n"
        )
        world.start_session()
        world.toggle_flags({"strict": "set"})

        world.start_delegate("critic")

        (record,) = delegate_records(world)
        assert record["session_state"] == {
            "path": str(world.state_file()),
            "band": None,
            "flags": [{"name": "strict", "setting": "set"}],
        }
        assert record["flags"] == [{"name": "strict", "source": "toggle"}]

    def test_a_session_and_a_switch_read_no_session_state(self, world):
        declare_core_and_sorting(world)

        world.start_session()

        (record,) = world.records()
        assert record["session_state"] is None


class TestADeliveryRecordNamesWhatItSkippedWithheldAndConflicted:
    def test_the_record_names_the_skipped_reference_the_withheld_rule_and_the_conflict(self, world):
        for stem in ("voice", "voice@terse", "voice@warm"):
            world.rule(stem)
        unreadable(world.rule("tone"))
        world.manifest(
            "models: ['opus']\n"
            "flags: ['a', 'b']\n"
            "defaults: ['voice', 'tone', 'ghost']\n"
            "when:\n"
            "  - flag a: ['voice@terse']\n"
            "  - flag b: ['voice@warm']\n"
        )
        world.environment["RULESETS_FLAGS"] = "a,b"
        manifest = str(world.rulesets / "manifest.yaml")

        world.start_session()

        (record,) = world.records()
        assert record["skipped_references"] == [
            {"file": manifest, "line": 3, "reference": "ghost", "name": "ghost"}
        ]
        (withheld,) = record["withheld"]
        assert withheld["rule"] == "tone"
        assert "Permission denied" in withheld["error"]
        (conflict,) = record["conflicts"]
        assert conflict["rule"] == "voice"
        assert conflict["delivered"] is None
        assert conflict["statements"] == [
            {"reference": "voice@terse", "line": 5, "variant": "terse"},
            {"reference": "voice@warm", "line": 6, "variant": "warm"},
        ]

    def test_the_record_names_a_skipped_block_with_its_file_line_and_undeclared_name(self, world):
        world.rule("voice")
        world.manifest(
            "models: ['opus']\ndefaults: ['voice']\nwhen:\n  - model sonnet: ['voice']\n"
        )

        world.start_session()

        (record,) = world.records()
        assert record["skipped_blocks"] == [
            {
                "file": str(world.rulesets / "manifest.yaml"),
                "line": 4,
                "condition": "model sonnet",
                "names": ["sonnet"],
            }
        ]


class TestTheNoticesADeliverySent:
    def test_the_record_holds_the_shown_notice_for_an_unclaimed_identifier_and_a_sent_message(
        self, world
    ):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: ['voice']\n")

        delivery = world.start_session(model="claude-nova-1")

        (record,) = world.records()
        (unclaimed,) = [n for n in record["notices"] if n["kind"] == "model-unclaimed"]
        assert unclaimed["shown"] is True
        assert "claude-nova-1" in unclaimed["subject"]
        assert record["message_sent"] is True
        assert delivery.message is not None


class TestADeliveryInSeveralParts:
    def test_parts_two_and_three_each_leave_an_emitted_record_and_the_first_writes_the_model_record(
        self, world
    ):
        delivery = three_part_delivery(world)

        (record,) = world.records()
        emitted = world.emitted_records()
        assert record["part_count"] == 3
        assert [e["part"] for e in emitted] == [2, 3]
        for entry in emitted:
            text = json.loads(delivery.outputs[entry["part"]])["hookSpecificOutput"][
                "additionalContext"
            ]
            assert entry["kind"] == "emitted"
            assert entry["part_count"] == 3
            assert entry["model"] == record["model"]
            assert entry["rules"] == [["a-rule", "b-rule", "c-rule"][entry["part"] - 1]]
            assert entry["digest"] == digest(text)
        model = world.model_record()
        assert model is not None
        assert model["identifier"] == OPUS

    def test_a_delegates_later_parts_name_the_delegate_as_their_writer(self, world):
        for name in ("a-rule", "b-rule"):
            world.rule(name, f"{name} " + "x" * 5990 + "\n")
        world.manifest(DECLARED + "defaults: ['a-rule', 'b-rule']\n")
        world.start_session()

        world.start_delegate("critic", agent_id="a1")

        (entry,) = [e for e in world.emitted_records() if e["agent_id"] == "a1"]
        assert (entry["session_id"], entry["part"], entry["part_count"]) == ("s1", 2, 2)


class TestTheDeliveryCheckRecomposesEachCountedDelivery:
    def test_a_record_equal_to_its_composition_now_prints_nothing_and_exits_zero(self, world):
        declare_core_and_sorting(world)
        world.start_session()
        world.start_delegate("critic")

        result = world.delivery_check()

        assert (result.stdout, result.returncode) == ("", 0)

    def test_a_session_with_no_delivery_record_exits_zero(self, world):
        declare_core_and_sorting(world)

        result = world.delivery_check("never-started")

        assert (result.stdout, result.returncode) == ("", 0)

    def test_the_check_recomposes_a_delegate_from_the_flags_and_state_its_record_names(self, world):
        world.rule("security-pass")
        world.manifest(
            DECLARED
            + "flags: ['strict']\ndefaults: []\nwhen:\n  - flag strict: ['security-pass']\n"
        )
        world.start_session()
        world.toggle_flags({"strict": "set"})
        world.start_delegate("critic")
        world.toggle_flags({"strict": "unset"})

        result = world.delivery_check()

        assert (result.stdout, result.returncode) == ("", 0)


class TestTheDeliveryCheckPrintsOneLinePerDifference:
    def test_a_block_edited_after_delivery_to_remove_a_rule_names_it_delivered_but_not_composed(
        self, world
    ):
        declare_core_and_sorting(world)
        add_sorting_to_defaults(world)
        world.start_session()
        world.manifest(
            DECLARED + "defaults: ['core-rules', 'sorting']\nwhen:\n  - model opus: ['-sorting']\n"
        )

        result = world.delivery_check()

        assert lines_of(result) == ["session: sorting delivered but not composed"]
        assert result.returncode != 0

    def test_a_rule_the_composition_now_holds_and_the_record_lacks_is_composed_but_not_delivered(
        self, world
    ):
        declare_core_and_sorting(world)
        world.start_session()
        add_sorting_to_defaults(world)

        result = world.delivery_check()

        assert lines_of(result) == ["session: sorting composed but not delivered"]
        assert result.returncode != 0

    def test_a_delegates_variant_that_differs_names_the_rule_both_variants_and_the_delegate(
        self, world
    ):
        for stem in ("voice", "voice@warm", "voice@terse"):
            world.rule(stem)
        manifest = DECLARED + "defaults: []\nwhen:\n  - agent critic: ['{}']\n"
        world.manifest(manifest.format("voice@warm"))
        world.start_session()
        world.start_delegate("critic", agent_id="a1")
        world.manifest(manifest.format("voice@terse"))

        result = world.delivery_check()

        assert lines_of(result) == ["a1: voice delivered as warm but composed as terse"]
        assert result.returncode != 0

    def test_a_rule_delivered_at_its_default_form_and_composed_at_a_variant_names_both(self, world):
        for stem in ("voice", "voice@terse"):
            world.rule(stem)
        world.manifest(DECLARED + "defaults: ['voice']\n")
        world.start_session()
        world.manifest(DECLARED + "defaults: ['voice']\nwhen:\n  - model opus: ['voice@terse']\n")

        result = world.delivery_check()

        assert lines_of(result) == ["session: voice delivered as default but composed as terse"]


class TestTheDeliveryCheckConfirmsEveryLaterPart:
    def test_a_part_with_no_emitted_record_is_named_as_composed_and_never_emitted(self, world):
        three_part_delivery(world)
        (world.record_files() / "emitted-2.jsonl").unlink()

        result = world.delivery_check()

        assert lines_of(result) == ["session: part 2 composed and never emitted"]
        assert result.returncode != 0

    def test_a_part_whose_model_fact_differs_from_the_delivery_records_is_named(self, world):
        three_part_delivery(world)
        path = world.record_files() / "emitted-3.jsonl"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["model"]["identifier"] = "claude-other-1"
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")

        result = world.delivery_check()

        assert lines_of(result) == ["session: part 3 emitted under a different model fact"]
        assert result.returncode != 0

    def test_a_part_whose_text_no_longer_composes_is_named_by_its_digest(self, world):
        three_part_delivery(world)
        world.rule("c-rule", "c-rule " + "y" * 5990 + "\n")

        result = world.delivery_check()

        assert lines_of(result) == ["session: part 3 emitted text differs from what composes now"]
        assert result.returncode != 0

    def test_a_complete_several_part_delivery_prints_nothing(self, world):
        three_part_delivery(world)

        result = world.delivery_check()

        assert (result.stdout, result.returncode) == ("", 0)

    def test_the_later_parts_of_an_earlier_delivery_are_not_charged_to_a_later_one(self, world):
        three_part_delivery(world)
        world.start_session(source="compact")

        result = world.delivery_check()

        assert (result.stdout, result.returncode) == ("", 0)
