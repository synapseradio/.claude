#!/usr/bin/env python3
"""The audit log shows what reached every context, and the delivery check confirms it by recomposing.

Serves the engineer who asks what each agent was told and why, and who runs `delivery-check`,
`load-check`, or `deliveries` after editing a config or a rule. Each case builds a configuration
directory under `tmp_path`, produces its records through real deliveries, and runs the subcommand
through the launcher. What the records hold and the lines the commands print come from
`docs/records.md` and `docs/commands.md`.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_instruction_load_audit.py`.
"""

import hashlib
import json
import pathlib
import shutil

import pytest
from delivery_world import DECLARED, HAIKU, OPUS, Delivery, World

SONNET = "claude-sonnet-5-5"


@pytest.fixture
def world(tmp_path) -> World:
    return World(tmp_path)


def digest(text) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lines_of(result) -> list[str]:
    return result.stdout.splitlines()


def unreadable(path) -> pathlib.Path:
    path.chmod(0o000)
    return path


def declare_core_and_sorting(world) -> None:
    world.rule("core-rules")
    world.rule("sorting")
    world.write_config(DECLARED + "defaults: core-rules\n")


def add_sorting_to_defaults(world) -> None:
    world.write_config(DECLARED + "defaults: core-rules sorting\n")


def three_part_delivery(world) -> Delivery:
    """A session start whose three rules each fill a part of their own."""
    for name in ("a-rule", "b-rule", "c-rule"):
        world.rule(name, f"{name} " + "x" * 5990 + "\n")
    world.write_config(DECLARED + "defaults: a-rule b-rule c-rule\n")
    return world.start_session()


def still_loading(path, reason) -> str:
    return f"still auto-loading: {path} (reason {reason})"


class TestCheckingOneSessionAmongMany:
    @pytest.mark.parametrize("command", ["delivery-check", "load-check"])
    def test_another_sessions_records_change_neither_output_nor_status_of_the_check(
        self, world, command
    ) -> None:
        if command == "delivery-check":
            declare_core_and_sorting(world)
            world.start_session(session_id="A")
            world.start_session(session_id="B")
            add_sorting_to_defaults(world)
            file, expected = "deliveries.jsonl", ["session: sorting composed but not delivered"]
            check = world.delivery_check
        else:
            world.rule("sorting")
            b_path = world.project / "b" / "sorting.md"
            world.load(world.project / "a" / "sorting.md", session_id="A")
            world.load(b_path, session_id="B")
            file, expected = "loads.jsonl", [still_loading(b_path, "session_start")]
            check = world.load_check
        with (world.record_files("A") / file).open("a", encoding="utf-8") as handle:
            handle.write("{this is not a record\n")

        with_a = check("B")
        shutil.rmtree(world.record_files("A"))
        without_a = check("B")

        assert lines_of(with_a) == expected
        assert (with_a.stdout, with_a.returncode) == (without_a.stdout, without_a.returncode)
        assert with_a.returncode != 0


class TestPruningASessionsRecords:
    def test_a_compaction_reporting_no_model_composes_for_the_identifier_the_model_record_holds(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.rule("opus-rules")
        world.write_config(
            DECLARED + ("defaults: core-rules\nmodel opus:\n  include: opus-rules\n")
        )
        world.start_session(model=OPUS, session_id="A")
        shutil.rmtree(world.record_files("A"))

        delivery = world.start_session(model=None, session_id="A", source="compact")

        assert delivery.context == "text of core-rules\ntext of opus-rules\n"


class TestADeliveryIsRecordedWithItsScopeAndRules:
    def test_a_delegate_record_names_session_delegate_model_scope_and_each_rule_with_variant_and_digest(
        self, world
    ) -> None:
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("sorting", "Sort it.\n")
        world.write_config(
            "models: haiku\ndefaults: voice sorting\nagent critic:\n  include: voice@terse\n"
        )
        world.start_session()
        world.spawn("critic", "haiku")

        world.start_delegate("critic", agent_id="a1")

        (record,) = world.delegate_records()
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

    def test_a_compaction_records_another_session_delivery_and_a_model_switch_a_switch_delivery(
        self, world
    ) -> None:
        world.rule("core-rules")
        world.rule("opus-rules")
        world.write_config(
            "models: opus sonnet haiku\ndefaults: core-rules\nmodel opus:\n  include: opus-rules\n"
        )
        world.start_session(model=SONNET)
        world.start_session(model=SONNET, source="compact")
        world.switch_model(HAIKU, from_model=SONNET, prompt_id="p1")

        world.switch_model(OPUS, from_model=HAIKU, prompt_id="p2")

        records = world.records()
        assert [r["scope"] for r in records] == ["session", "session", "switch"]
        switched = records[-1]
        assert (switched["model"]["name"], switched["model"]["identifier"]) == ("opus", OPUS)
        assert [rule["rule"] for rule in switched["rules"]] == ["core-rules", "opus-rules"]


class TestADeliveryRecordNamesEachFactWithItsSource:
    def test_the_session_record_names_the_variant_the_launch_flag_and_the_model_source(
        self, world
    ) -> None:
        world.rule("voice")
        world.rule("voice@terse")
        world.write_config(
            DECLARED
            + ("flags: voice-terse\ndefaults: voice\n")
            + ("flag voice-terse:\n  include: voice@terse\n")
        )
        world.environment["RULESETS_FLAGS"] = "voice-terse"

        world.start_session()

        (record,) = world.records()
        assert [(r["rule"], r["variant"]) for r in record["rules"]] == [("voice", "terse")]
        assert record["flags"] == [{"name": "voice-terse", "source": "launch"}]
        assert record["model"]["source"] == "harness-reported"
        assert record["kind"] == "session"
        assert record["agent"]["state"] == "absent"
        assert record["tools"]["state"] == "absent"

    def test_a_delegate_record_names_its_agent_and_the_definition_file_its_tools_came_from(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")
        definition = world.config / "agents" / "critic.md"
        definition.parent.mkdir(parents=True)
        definition.write_text(
            "---\nname: critic\ndescription: a test agent\ntools: Read, Edit\n---\nbody\n",
            encoding="utf-8",
        )

        world.start_delegate("critic")

        (record,) = world.delegate_records()
        assert record["agent"] == {"state": "named", "name": "critic"}
        assert record["tools"] == {
            "state": "listed",
            "tools": ["Edit", "Read"],
            "source": str(definition),
        }


class TestADeliveryRecordNamesWhatItSkippedWithheldAndConflicted:
    def test_the_record_names_the_skipped_reference_and_block_the_withheld_rule_and_the_conflict(
        self, world
    ) -> None:
        for stem in ("voice", "voice@terse", "voice@warm"):
            world.rule(stem)
        unreadable(world.rule("tone"))
        world.write_config(
            "models: opus\n"
            "flags: a b\n"
            "defaults: voice tone ghost\n"
            "flag a:\n"
            "  include: voice@terse\n"
            "flag b:\n"
            "  include: voice@warm\n"
            "model sonnet:\n"
            "  include: voice\n"
        )
        world.environment["RULESETS_FLAGS"] = "a,b"
        config = str(world.rulesets / "config.yaml")

        world.start_session()

        (record,) = world.records()
        assert record["skipped_references"] == [
            {"file": config, "line": 3, "reference": "ghost", "name": "ghost"}
        ]
        assert record["skipped_blocks"] == [
            {"file": config, "line": 8, "condition": "model sonnet", "names": ["sonnet"]}
        ]
        assert world.withheld_rules() == ["tone"]
        (conflict,) = record["conflicts"]
        assert conflict["rule"] == "voice"
        assert conflict["statements"] == [
            {"reference": "voice@terse", "line": 5, "variant": "terse"},
            {"reference": "voice@warm", "line": 7, "variant": "warm"},
        ]


class TestTheNoticesADeliverySent:
    def test_the_record_holds_the_shown_notice_for_an_unclaimed_identifier_and_a_sent_message(
        self, world
    ) -> None:
        world.rule("voice")
        world.write_config(DECLARED + "defaults: voice\n")

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
    ) -> None:
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


def equal_record_and_delegate(world) -> None:
    declare_core_and_sorting(world)
    world.start_session()
    world.start_delegate("critic")


def delegate_after_a_toggle_since_unset(world) -> None:
    world.rule("security-pass")
    world.write_config(
        DECLARED + ("flags: strict\ndefaults:\nflag strict:\n  include: security-pass\n")
    )
    world.start_session()
    world.toggle_flags({"strict": "set"})
    world.start_delegate("critic")
    world.toggle_flags({"strict": "unset"})


def three_parts_then_compaction(world) -> None:
    three_part_delivery(world)
    world.start_session(source="compact")


def a_block_removes_a_delivered_rule(world) -> None:
    declare_core_and_sorting(world)
    add_sorting_to_defaults(world)
    world.start_session()
    world.write_config(
        DECLARED + ("defaults: core-rules sorting\nmodel opus:\n  exclude: sorting\n")
    )


def a_rule_is_added_after_delivery(world) -> None:
    declare_core_and_sorting(world)
    world.start_session()
    add_sorting_to_defaults(world)


def a_delegates_variant_changes(world) -> None:
    for stem in ("voice", "voice@warm", "voice@terse"):
        world.rule(stem)
    config = DECLARED + ("defaults:\nagent critic:\n  include: {}\n")
    world.write_config(config.format("voice@warm"))
    world.start_session()
    world.start_delegate("critic", agent_id="a1")
    world.write_config(config.format("voice@terse"))


def a_default_form_gains_a_variant(world) -> None:
    for stem in ("voice", "voice@terse"):
        world.rule(stem)
    world.write_config(DECLARED + "defaults: voice\n")
    world.start_session()
    world.write_config(DECLARED + ("defaults: voice\nmodel opus:\n  include: voice@terse\n"))


def a_part_loses_its_emitted_record(world) -> None:
    three_part_delivery(world)
    (world.record_files() / "emitted-2.jsonl").unlink()


def a_part_records_another_model(world) -> None:
    three_part_delivery(world)
    path = world.record_files() / "emitted-3.jsonl"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["model"]["identifier"] = "claude-other-1"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def a_part_text_changes(world) -> None:
    three_part_delivery(world)
    world.rule("c-rule", "c-rule " + "y" * 5990 + "\n")


DELIVERY_CHECKS = {
    "a record equal to its composition now": (equal_record_and_delegate, "s1", []),
    "a session with no delivery record": (declare_core_and_sorting, "never-started", []),
    "a delegate recomposed from the flags and state its record names": (
        delegate_after_a_toggle_since_unset,
        "s1",
        [],
    ),
    "a complete several-part delivery": (three_part_delivery, "s1", []),
    "the later parts of an earlier delivery are not charged to a later one": (
        three_parts_then_compaction,
        "s1",
        [],
    ),
    "a block edited after delivery to remove a rule": (
        a_block_removes_a_delivered_rule,
        "s1",
        ["session: sorting delivered but not composed"],
    ),
    "a rule the composition now holds and the record lacks": (
        a_rule_is_added_after_delivery,
        "s1",
        ["session: sorting composed but not delivered"],
    ),
    "a delegate's variant that differs": (
        a_delegates_variant_changes,
        "s1",
        ["a1: voice delivered as warm but composed as terse"],
    ),
    "a rule delivered at its default form and composed at a variant": (
        a_default_form_gains_a_variant,
        "s1",
        ["session: voice delivered as default but composed as terse"],
    ),
    "a part with no emitted record": (
        a_part_loses_its_emitted_record,
        "s1",
        ["session: part 2 composed and never emitted"],
    ),
    "a part whose model fact differs from the delivery record's": (
        a_part_records_another_model,
        "s1",
        ["session: part 3 emitted under a different model fact"],
    ),
    "a part whose text no longer composes": (
        a_part_text_changes,
        "s1",
        ["session: part 3 emitted text differs from what composes now"],
    ),
}


@pytest.mark.parametrize(
    ("setup", "session", "expected"), list(DELIVERY_CHECKS.values()), ids=list(DELIVERY_CHECKS)
)
def test_the_delivery_check_prints_one_line_per_difference_and_exits_zero_only_where_there_is_none(
    world, setup, session, expected
) -> None:
    setup(world)

    result = world.delivery_check(session)

    assert lines_of(result) == expected
    assert (result.returncode == 0) == (expected == [])


class TestTheInstructionsLoadedHookRecordsWhatTheHarnessLoaded:
    def test_the_hook_records_the_loaded_file_and_the_reason_for_its_session_and_prints_nothing(
        self, world
    ) -> None:
        loaded = world.project / "CLAUDE.md"

        result = world.load(loaded, "nested_traversal", session_id="s7", trigger_file_path="x.ts")

        assert (result.returncode, result.stdout) == (0, "")
        assert [
            (r["session_id"], r["file_path"], r["load_reason"]) for r in world.load_records("s7")
        ] == [("s7", str(loaded), "nested_traversal")]
        assert world.load_records("s1") == []

    @pytest.mark.parametrize(
        "stdin",
        [
            "not json",
            "[]",
            "{}",
            '{"session_id": "s1"}',
            '{"session_id": "s1", "file_path": 5, "load_reason": "session_start"}',
            '{"session_id": "s1", "file_path": "/a/CLAUDE.md"}',
            '{"file_path": "/a/CLAUDE.md", "load_reason": "session_start"}',
        ],
    )
    def test_a_payload_the_hook_cannot_read_exits_zero_prints_nothing_and_records_nothing(
        self, world, stdin
    ) -> None:
        result = world.run_load_hook(stdin)

        assert (result.returncode, result.stdout) == (0, "")
        assert not (world.config / ".tmp").exists()

    def test_a_state_directory_that_cannot_be_written_exits_zero_and_prints_nothing(
        self, world, tmp_path
    ) -> None:
        not_a_directory = tmp_path / "file"
        not_a_directory.write_text("", encoding="utf-8")
        world.environment["CLAUDE_CONFIG_DIR"] = str(not_a_directory)

        result = world.load(world.project / "CLAUDE.md")

        assert (result.returncode, result.stdout) == (0, "")


# Each row: the pool's rule files, the config text (None keeps the one the world holds), each
# file the harness loaded as (folder and path, reason, extra payload fields), and the loads the
# check reports, by position.
LOAD_CHECKS = {
    "a session start naming a pool rule's file": (
        ["core-rules", "sorting"],
        None,
        [("config/rules/sorting.md", "session_start", {})],
        [0],
    ),
    "a same-named file in a project's rules directory": (
        ["sorting"],
        None,
        [
            (
                "project/.claude/rules/sorting.md",
                "path_glob_match",
                {"globs": ["src/**"], "trigger_file_path": "src/a.ts"},
            )
        ],
        [0],
    ),
    "a pool rule imported into CLAUDE.md": (
        ["sorting"],
        None,
        [("project/docs/sorting.md", "include", {"parent_file_path": "CLAUDE.md"})],
        [0],
    ),
    "each record naming a pool rule, in file order": (
        ["sorting", "voice"],
        None,
        [("project/a/voice.md", "session_start", {}), ("project/b/sorting.md", "compact", {})],
        [0, 1],
    ),
    "a config that is not valid yaml": (
        ["sorting"],
        "models: ['opus'\ndefaults: [\n",
        [("project/.claude/rules/sorting.md", "session_start", {})],
        [0],
    ),
    "a rule with variants": (
        ["voice", "voice@terse"],
        None,
        [("project/voice.md", "session_start", {})],
        [0],
    ),
    "only a file whose whole stem is a rule name": (
        ["sorting", "core-rules"],
        None,
        [
            ("project/x/resorting.md", "session_start", {}),
            ("project/x/sorting-notes.md", "session_start", {}),
            ("project/x/sort.md", "session_start", {}),
            ("project/x/core-rules-v2.md", "session_start", {}),
            ("project/x/sorting/CLAUDE.md", "session_start", {}),
            ("project/x/sorting@terse.md", "session_start", {}),
            ("project/x/sorting.md", "session_start", {}),
        ],
        [6],
    ),
    "an empty pool": ([], None, [("project/sorting.md", "session_start", {})], []),
    "CLAUDE.md files in several directories": (
        ["sorting"],
        None,
        [
            ("config/CLAUDE.md", "session_start", {"memory_type": "User"}),
            ("project/CLAUDE.md", "session_start", {}),
            ("project/sub/CLAUDE.md", "nested_traversal", {}),
            ("project/docs/CLAUDE.md", "include", {}),
        ],
        [],
    ),
    "CLAUDE.md where the pool holds a rule of that name": (
        ["CLAUDE"],
        None,
        [("project/CLAUDE.md", "session_start", {})],
        [],
    ),
    "a path-scoped rule whose stem names no pool rule": (
        ["sorting"],
        None,
        [("project/.claude/rules/api-style.md", "path_glob_match", {})],
        [],
    ),
}


@pytest.mark.parametrize(
    ("stems", "config", "loads", "reported"), list(LOAD_CHECKS.values()), ids=list(LOAD_CHECKS)
)
def test_the_load_check_reports_each_loaded_file_named_for_a_pool_rule_and_fails_only_then(
    world, stems, config, loads, reported
) -> None:
    for stem in stems:
        world.rule(stem)
    if config is not None:
        world.write_config(config)
    paths = []
    for location, reason, extra in loads:
        folder, _, relative = location.partition("/")
        path = (world.project if folder == "project" else world.config) / relative
        paths.append(path)
        world.load(path, reason, **extra)

    result = world.load_check()

    assert lines_of(result) == [still_loading(paths[i], loads[i][1]) for i in reported]
    assert (result.returncode == 0) == (reported == [])


class TestDeliveriesListsWhatReachedEachContext:
    def test_a_delegate_line_holds_scope_model_source_rule_count_flags_and_delegate(
        self, world
    ) -> None:
        stems = [f"rule-{number:02d}" for number in range(1, 13)]
        for stem in stems:
            world.rule(stem)
        world.write_config(DECLARED + "flags: voice-terse\ndefaults: " + " ".join(stems) + "\n")
        world.start_session(model=OPUS)
        world.toggle_flags({"voice-terse": "set"})
        world.spawn("critic", model="haiku")
        world.start_delegate("critic", agent_id="a1")

        result = world.deliveries()

        assert lines_of(result) == [
            "session\topus\tharness-reported\t12\t-",
            "delegate\thaiku\tper-spawn\t12\tvoice-terse\ta1",
        ]
        assert result.returncode == 0

    def test_three_switches_before_the_next_request_print_one_line_for_the_last(
        self, world
    ) -> None:
        world.rule("core-rules")
        for stem in ("opus-rules", "sonnet-rules", "haiku-a", "haiku-b"):
            world.rule(stem)
        world.write_config(
            "models: opus sonnet haiku\n"
            "defaults: core-rules\n"
            "model opus:\n"
            "  include: opus-rules\n"
            "model sonnet:\n"
            "  include: sonnet-rules\n"
            "model haiku:\n"
            "  include: haiku-a haiku-b\n"
        )
        world.start_session(model=OPUS)
        world.switch_model(SONNET, from_model=OPUS, prompt_id="p1")
        world.switch_model(OPUS, from_model=SONNET, prompt_id="p1")
        world.switch_model(HAIKU, from_model=OPUS, prompt_id="p1")

        result = world.deliveries()

        last_source = world.records()[-1]["model"]["source"]
        assert lines_of(result) == [
            "session\topus\tharness-reported\t2\t-",
            f"switch\thaiku\t{last_source}\t3\t-",
        ]

    def test_a_session_without_records_prints_nothing_and_exits_zero(self, world) -> None:
        result = world.deliveries("never-started")

        assert (result.stdout, result.returncode) == ("", 0)
