#!/usr/bin/env python3
"""A rulesets directory holds a pool of rule files that reach a context only through a list.

Serves the person who writes rules and lists and the engineer who reads check output: the pool
names rules and variants by file name, the reserved rulesets and folders carry fixed meanings, and
the engine reads one directory at user scope and leaves the harness's own rules folders alone.
Each case builds a configuration directory under `tmp_path` and runs the hook entries that
`hooks/hooks.json` wires, as the harness runs them, then reads what they deliver and what `check`
prints. The promises come from `docs/config.md` and `docs/delivery.md`.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_rules_directories.py`.
"""

import json
import pathlib
import re
import sys
from typing import NamedTuple

import pytest
from delivery_world import Delivery, World
from delivery_world import delivered as under_marker

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import spawn_log  # noqa: E402  (path must be set before this import)
from rulesets.cli import main  # noqa: E402
from rulesets.locations import Locations  # noqa: E402
from rulesets.session.state import Band, SessionState, write_state  # noqa: E402

MODELS = "models: opus sonnet haiku\n"


@pytest.fixture
def world(tmp_path) -> World:
    return World(tmp_path)


def every_context(world: World) -> list[Delivery]:
    """The main session and the delegates of two agents on several models, each delivered."""
    deliveries = [world.start_session()]
    state = Locations(world.config).state
    for number, (agent, model) in enumerate(
        [("critic", "haiku"), ("auditor", "sonnet"), ("critic", "opus")], start=2
    ):
        session_id = f"s{number}"
        spawn_log.append_spawn(session_id, "p1", agent, model, state)
        deliveries.append(world.start_delegate(agent, session_id=session_id))
    return deliveries


def launch_with(world: World, flags: str | None) -> None:
    """Set the flags a launch sets through `RULESETS_FLAGS`, or none."""
    if flags is None:
        world.environment.pop("RULESETS_FLAGS", None)
    else:
        world.environment["RULESETS_FLAGS"] = flags


class Finding(NamedTuple):
    severity: str
    kind: str
    path: pathlib.Path
    line: int | None
    message: str


_FINDING = re.compile(
    r"^(?P<path>.+?)(?::(?P<line>\d+))?: (?P<severity>error|warning) \[(?P<kind>[\w-]+)\] (?P<message>.*)$"
)


def check_findings(world: World, capsys) -> tuple[int, list[Finding]]:
    """The exit status of `check` on the world's directory and each finding line it prints."""
    status = main(["check", "--root", str(world.rulesets)])
    found = []
    for text in capsys.readouterr().out.splitlines():
        match = _FINDING.match(text)
        assert match, text
        line = match["line"]
        found.append(
            Finding(
                match["severity"],
                match["kind"],
                pathlib.Path(match["path"]),
                int(line) if line else None,
                match["message"],
            )
        )
    return status, found


class TestAPoolRuleWhoseNameHoldsADotIsACheckError:
    def test_the_file_is_named_in_an_error_and_a_spread_of_all_delivers_none_of_its_text(
        self, world, capsys
    ) -> None:
        world.rule("voice", "the voice\n")
        world.rule("voice.short", "the short voice\n")
        world.write_config(MODELS + "defaults: all.*\n")

        status, found = check_findings(world, capsys)
        delivery = world.start_session()

        assert status == 1
        ((severity, kind, path, _, message),) = found
        assert (severity, kind, path.name) == ("error", "rule-name", "voice.short.md")
        assert "`voice.short.md`" in message
        assert delivery.context == "the voice\n"
        assert world.withheld_rules() == ["voice.short"]


class TestALaunchSetsTheFlagsItsBlocksKeyOn:
    @pytest.mark.parametrize(
        ("config", "flags", "context"),
        [
            (
                "defaults:\nflag plain:\n  include: voice\nflag terse:\n  include: voice@terse\n",
                "plain",
                "the default voice\n",
            ),
            (
                "defaults:\nflag plain:\n  include: voice\nflag terse:\n  include: voice@terse\n",
                "terse",
                "the terse voice\n",
            ),
            (
                "defaults:\nflag plain:\n  include: voice\nflag terse:\n  include: voice@terse\n",
                None,
                "",
            ),
            (
                "sets:\n  review: security-pass\ndefaults:\nflag plain:\n  include: review.*\n",
                "plain",
                "check the security\n",
            ),
        ],
        ids=[
            "a list naming a rule bare delivers its default file",
            "a list naming a rule at a variant delivers that variant's file and no other",
            "a launch setting no flag applies neither block",
            "a block spreading a ruleset delivers its rules",
        ],
    )
    def test_a_block_keyed_on_a_declared_flag_applies_in_a_launch_that_sets_it_and_in_no_other(
        self, world, config, flags, context
    ) -> None:
        world.rule("voice", "the default voice\n")
        world.rule("voice@terse", "the terse voice\n")
        world.rule("voice@warm", "the warm voice\n")
        world.rule("security-pass", "check the security\n")
        world.write_config(MODELS + "flags: plain terse\n" + config)
        launch_with(world, flags)

        assert world.start_session().context == context


class TestThePoolHoldsEveryRuleFile:
    def test_an_empty_default_form_passes_check_and_delivers_no_text(self, world, capsys) -> None:
        world.rule("voice", "")
        world.rule("voice@terse", "the terse voice\n")
        world.write_config(MODELS + "defaults: voice\n")

        status, found = check_findings(world, capsys)
        delivery = world.start_session()

        assert (status, found) == (0, [])
        assert delivery.context == ""
        assert delivery.messages == []
        (record,) = world.records()
        assert [(line["rule"], line["variant"]) for line in record["rules"]] == [("voice", None)]
        assert record["withheld"] == []

    def test_a_variant_with_no_default_form_fails_check_and_is_withheld_from_delivery(
        self, world, capsys
    ) -> None:
        world.rule("voice")
        world.rule("tone@dry")
        world.write_config(MODELS + "defaults: voice tone\n")

        status, found = check_findings(world, capsys)
        delivery = world.start_session()

        assert status == 1
        ((severity, kind, _, _, _),) = found
        assert (severity, kind) == ("error", "variant-without-default")
        assert delivery.context == "text of voice\n"
        assert world.withheld_rules() == ["tone"]


class TestAPoolFileDeliversNothingByBeingThere:
    @pytest.mark.parametrize(
        ("config", "context"),
        [
            ("defaults: voice sorting\n", "text of sorting\ntext of voice\n"),
            ("defaults: all.*\n", "text of sorting\ntext of voice\n"),
            ("", ""),
        ],
        ids=[
            "a pool file no list reaches while the listed rules still arrive",
            "defaults spreading all",
            "a config listing nothing under defaults",
        ],
    )
    def test_the_defaults_list_alone_decides_what_the_main_session_and_every_delegate_receive(
        self, world, config, context
    ) -> None:
        world.rule("voice")
        world.rule("voice@terse")
        world.rule("sorting")
        world.write_config(MODELS + config)

        deliveries = every_context(world)

        assert [d.context for d in deliveries] == [context] * 4


class TestTheReferencesAndRenderFoldersAreReserved:
    def test_rendered_files_in_the_render_folder_become_no_rule_and_draw_no_stray_warning(
        self, world, capsys
    ) -> None:
        world.rule("sorting")
        world.write_config(MODELS + "defaults: all.*\n")
        (world.rulesets / "-render").mkdir()
        (world.rulesets / "-render" / "voice.md").write_text("rendered voice\n", encoding="utf-8")
        (world.rulesets / "references").mkdir()
        (world.rulesets / "references" / "notes.md").write_text(
            "reference notes\n", encoding="utf-8"
        )

        status, found = check_findings(world, capsys)
        delivery = world.start_session()

        assert (status, found) == (0, [])
        assert delivery.context == "text of sorting\n"


class TestOneRulesetsDirectorySitsAtAFixedPathAtUserScope:
    @pytest.mark.parametrize("where", ["a project's own rules folder", "the personal rules folder"])
    def test_the_harnesss_rules_folder_stays_outside_every_composition_and_unchanged(
        self, world, tmp_path, monkeypatch, capsys, where
    ) -> None:
        world.rule("user-rule")
        world.write_config(MODELS + "defaults: all.*\n")
        project = tmp_path / "project"
        project.mkdir()
        harness_rules = (
            project / ".claude" / "rules"
            if where.startswith("a project")
            else world.config / "rules"
        )
        harness_rules.mkdir(parents=True)
        (harness_rules / "testing.md").write_bytes(b"harness rule\r\n\xc3\xa9")
        for inside in (project / "rulesets", project / ".claude" / "rulesets"):
            (inside / "rules").mkdir(parents=True)
            (inside / "rules" / "project-only.md").write_text("project only\n", encoding="utf-8")
            (inside / "config.yaml").write_text("defaults: all.*\n", encoding="utf-8")
        before = {p: p.read_bytes() for p in harness_rules.rglob("*") if p.is_file()}
        monkeypatch.chdir(project)

        session = world.start_session(cwd=str(project))
        delegate = world.start_delegate("critic", cwd=str(project))
        status, found = check_findings(world, capsys)
        rendered = tmp_path / "context.md"
        assert main(["render", "--root", str(world.rulesets), "--out", str(rendered)]) == 0

        assert [session.context, delegate.context] == ["text of user-rule\n"] * 2
        assert (status, found) == (0, [])
        assert rendered.read_text(encoding="utf-8") == (
            "<!-- rule: user-rule -->\ntext of user-rule\n"
        )
        assert {p: p.read_bytes() for p in harness_rules.rglob("*") if p.is_file()} == before


class TestAToggleAndTheEditedPoolReachADelegate:
    def test_the_toggle_all_overrides_a_blocks_exclude_for_a_haiku_delegate(self, world) -> None:
        world.rule("writing-code")
        world.write_config(
            MODELS + "defaults: writing-code\nmodel haiku:\n  exclude: writing-code\n"
        )
        state = Locations(world.config).state
        for session_id in ("toggled", "plain"):
            spawn_log.append_spawn(session_id, "p1", "critic", "haiku", state)
        write_state(Locations(world.config), "toggled", SessionState(Band.ALL))

        toggled = world.start_delegate("critic", session_id="toggled")
        plain = world.start_delegate("critic", session_id="plain")

        assert toggled.context == "text of writing-code\n"
        assert plain.context == ""

    def test_a_delegate_reads_the_edited_rule_text_and_the_flag_a_toggle_set(self, world) -> None:
        world.rule("voice")
        world.rule("security-pass")
        world.write_config(
            "flags: strict\ndefaults: voice\nflag strict:\n  include: security-pass\n"
        )
        world.start_session()
        world.toggle_flags({"strict": "set"})
        world.rule("voice", "edited text of voice\n")

        delegate = world.start_delegate("critic")

        assert "edited text of voice\n" in delegate.context
        assert "text of security-pass\n" in delegate.context


class TestARuleIsUnconditionalText:
    def test_conditional_metadata_in_a_rule_file_is_a_check_error_and_withholds_the_rule(
        self, world, capsys
    ) -> None:
        world.rule("scoped", "---\npaths: ['src/**']\n---\nscoped text\n")
        world.rule("modeled", "---\nmodel: haiku\n---\nmodeled text\n")
        world.rule("broken", "---\npaths: [unclosed\n---\nbroken text\n")
        world.rule("plain", "plain text\n")
        world.write_config(MODELS + "defaults: scoped modeled broken plain\n")

        status, found = check_findings(world, capsys)
        delivery = world.start_session()

        assert status == 1
        assert {f.severity for f in found} == {"error"}
        assert {f.path.name for f in found} == {"scoped.md", "modeled.md", "broken.md"}
        assert [f.kind for f in found if f.path.name == "broken.md"] == ["frontmatter-unparsable"]
        assert delivery.context == "plain text\n"
        assert sorted(world.withheld_rules()) == ["broken", "modeled", "scoped"]

    def test_prose_describing_when_a_rule_applies_is_delivered_as_plain_text_with_no_finding(
        self, world, capsys
    ) -> None:
        text = "on haiku models, keep answers short\n"
        world.rule("brevity", text)
        world.write_config(MODELS + "defaults: brevity\n")
        state = Locations(world.config).state
        spawn_log.append_spawn("s2", "p1", "critic", "haiku", state)

        status, found = check_findings(world, capsys)
        on_opus = world.start_session()
        on_haiku = world.start_delegate("critic", session_id="s2")

        assert (status, found) == (0, [])
        assert [on_opus.context, on_haiku.context] == [text, text]


class TestReservedRulesetsCarryFixedMeanings:
    @pytest.mark.parametrize(
        ("config", "flags", "context", "notice"),
        [
            ("defaults: all.*\n", None, "sorting text\ndefault voice\n", False),
            (
                "flags: one\ndefaults:\nflag one:\n  include: rules.voice\n",
                "one",
                "default voice\n",
                False,
            ),
            (
                "flags: every\ndefaults:\nflag every:\n  include: rules.*\n",
                "every",
                "sorting text\ndefault voice\n",
                False,
            ),
            ("defaults: none.*\n", None, "", True),
            ("defaults: voice none.*\n", None, "default voice\n", False),
        ],
        ids=[
            "the spread of all delivers every pool rule at its default form",
            "rules at a rule's name names that rule",
            "the spread of rules names every rule",
            "the spread of none alone delivers no rule and shows a notice",
            "the spread of none beside a rule adds nothing",
        ],
    )
    def test_the_reserved_ruleset_delivers_what_the_docs_give_it(
        self, world, capsys, config, flags, context, notice
    ) -> None:
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("sorting", "sorting text\n")
        world.write_config(MODELS + config)
        launch_with(world, flags)

        delivery = world.start_session()

        assert delivery.context == context
        assert bool(delivery.messages) == notice
        status, found = check_findings(world, capsys)
        assert (status, [f for f in found if f.severity == "error"]) == (0, [])

    def test_a_declared_all_is_an_error_naming_the_declaration_and_the_spread_still_reaches_every_pool_rule(
        self, world, capsys
    ) -> None:
        world.rule("voice", "voice text\n")
        world.rule("sorting", "sorting text\n")
        world.rule("tone", "tone text\n")
        world.write_config("defaults: all.*\nsets:\n  all: voice sorting\n")

        status, found = check_findings(world, capsys)
        delivery = world.start_session()

        assert status == 1
        ((severity, kind, path, line, _),) = found
        assert (severity, kind, path, line) == (
            "error",
            "reserved-ruleset",
            world.rulesets / "config.yaml",
            3,
        )
        assert delivery.context == "sorting text\ntone text\nvoice text\n"


class TestReferenceForms:
    def test_a_bare_name_means_the_rule_and_the_spread_of_the_same_name_means_the_ruleset(
        self, world, capsys
    ) -> None:
        for stem in ("reviewer", "security-pass", "report-format"):
            world.rule(stem)
        world.write_config(
            "flags: bare spread\n"
            "defaults:\n"
            "sets:\n"
            "  reviewer: security-pass report-format\n"
            "flag bare:\n"
            "  include: reviewer\n"
            "flag spread:\n"
            "  include: reviewer.*\n"
        )

        launch_with(world, "bare")
        bare = world.start_session()
        launch_with(world, "spread")
        spread = world.start_session(session_id="s2")

        status, found = check_findings(world, capsys)
        assert (status, [f for f in found if f.severity == "error"]) == (0, [])
        assert bare.context == "text of reviewer\n"
        assert spread.context == "text of report-format\ntext of security-pass\n"

    def test_every_reference_form_passes_check_in_defaults_a_blocks_list_and_a_rulesets_list(
        self, world, capsys
    ) -> None:
        for stem in ("voice", "voice@terse", "tone"):
            world.rule(stem)
        forms = (
            "    include: voice rules.voice voice@terse group.voice group.*\n    exclude: tone\n"
        )
        top = forms.replace("    ", "  ")
        world.write_config(
            "sets:\n  group: voice\n  inner:\n"
            + forms
            + "flags: f\ndefaults:\n"
            + top
            + "flag f:\n"
            + top
        )
        launch_with(world, "f")

        delivery = world.start_session()

        status, found = check_findings(world, capsys)
        assert (status, [f for f in found if f.severity == "error"]) == (0, [])
        assert delivery.context == "text of voice@terse\n"


class TestAReferenceToAnUndeclaredNameIsSkipped:
    @pytest.mark.parametrize(
        ("config", "flags", "context", "reference", "line"),
        [
            (
                "sets:\n  review: voise voice sorting\ndefaults: review.*\n",
                None,
                "text of sorting\ntext of voice\n",
                "voise",
                3,
            ),
            (
                "flags: f\ndefaults: voice@terse\nflag f:\n  include: voice@brisk\n",
                "f",
                "text of voice@terse\n",
                "voice@brisk",
                5,
            ),
        ],
        ids=["a misspelled member of a ruleset", "a variant the pool lacks"],
    )
    def test_the_reference_is_an_error_and_a_shown_notice_while_every_other_reference_applies(
        self, world, capsys, config, flags, context, reference, line
    ) -> None:
        for stem in ("voice", "voice@terse", "sorting"):
            world.rule(stem)
        world.write_config(MODELS + config)
        launch_with(world, flags)

        status, found = check_findings(world, capsys)
        delivery = world.start_session()

        assert status == 1
        ((severity, kind, _, _, message),) = [f for f in found if f.severity == "error"]
        assert (severity, kind) == ("error", "undeclared-reference")
        assert f"`{reference}`" in message
        assert delivery.context == context
        assert len(delivery.messages) == 1
        assert f"`{reference}`" in delivery.message
        assert f"config line {line}" in delivery.message


class TestAContextReceivesASetOfRulesWithNoDuplicates:
    def test_a_rule_reached_by_defaults_a_spread_and_a_name_arrives_once(self, world) -> None:
        world.rule("report-format", "REPORT FORMAT BODY\n")
        world.rule("voice", "voice text\n")
        world.write_config(
            MODELS + "sets:\n"
            "  group: report-format\n" + "defaults: all.*\n" + "agent auditor:\n"
            "  include: group.*\n"
            "  then:\n"
            "    include: report-format\n"
        )

        delegate = world.start_delegate("auditor")

        assert delegate.context == "REPORT FORMAT BODY\nvoice text\n"
        assert delegate.context.count("REPORT FORMAT BODY") == 1
        (record,) = world.records()
        assert [line["rule"] for line in record["rules"]] == ["report-format", "voice"]


class TestRulesArriveSortedByName:
    def test_delivered_rules_arrive_in_name_order_whatever_order_any_list_names_them(
        self, world
    ) -> None:
        world.rule("writing-code", "writing text\n")
        world.rule("core-rules", "core text\n")
        world.rule("sorting", "sorting text\n")
        world.write_config(
            MODELS + "flags: f\n"
            "defaults: writing-code sorting\n" + "flag f:\n"
            "  include: core-rules\n"
        )
        world.environment["RULESETS_FLAGS"] = "f"

        assert world.start_session().context == "core text\nsorting text\nwriting text\n"

    def test_one_composed_set_yields_byte_identical_text_at_session_start_and_after_a_compaction(
        self, world
    ) -> None:
        bodies = {
            "aa-no-final-newline": "no final newline",
            "bb-crlf": "line one\r\nline two\r\n",
            "cc-non-ascii": "caf\u00e9 \u2014 na\u00efve \u65e5\u672c\n",
            "dd-large": "d" * 4000 + "\n",
            "ee-large": "e" * 4000 + "\n",
            "ff-large": "f" * 4000 + "\n",
        }
        for rule, text in bodies.items():
            world.rule(rule, text)
        world.write_config(MODELS + "defaults: all.*\n")
        first_part = (
            under_marker("aa-no-final-newline", "no final newline")
            + under_marker("bb-crlf", "line one\r\nline two\r\n")
            + under_marker("cc-non-ascii", "caf\u00e9 \u2014 na\u00efve \u65e5\u672c\n")
            + under_marker("dd-large", "d" * 4000 + "\n")
            + under_marker("ee-large", "e" * 4000 + "\n")
        )
        second_part = under_marker("ff-large", "f" * 4000 + "\n")

        started = world.start_session()
        compacted = world.start_session(source="compact")

        def contexts(delivery) -> list[str]:
            return [
                json.loads(delivery.outputs[part])["hookSpecificOutput"]["additionalContext"]
                for part in sorted(delivery.outputs)
                if delivery.outputs[part].strip()
            ]

        assert contexts(started) == [first_part, second_part]
        assert [c.encode() for c in contexts(compacted)] == [c.encode() for c in contexts(started)]
        assert compacted.context.encode() == started.context.encode()


class TestDeclaredNamesAreWhateverTheConfigDeclares:
    def test_a_consistent_renaming_of_rules_rulesets_flags_and_models_leaves_every_contexts_texts_unchanged(
        self, tmp_path
    ) -> None:
        def directory(names: dict[str, str], where: pathlib.Path) -> tuple[World, str]:
            kept = World(where)
            for role, text in (
                ("first", "first role text\n"),
                ("second", "second role text\n"),
                ("third", "third role text\n"),
            ):
                kept.rule(names[role], text)
            kept.write_config(
                f"models: {names['big']} {names['small']}\n"
                f"sets:\n  {names['group']}: {names['third']} {names['first']}\n"
                f"flags: {names['flag']}\n"
                f"defaults: {names['second']}\n"
                f"flag {names['flag']}:\n  include: {names['group']}.*\n"
                f"model {names['small']}:\n  exclude: {names['second']}\n"
            )
            return kept, f"claude-{names['small']}-4-5"

        original = {
            "first": "sorting", "second": "tone", "third": "voice", "group": "review",
            "flag": "strict", "big": "opus", "small": "haiku",
        }  # fmt: skip
        renamed = {
            "first": "aa", "second": "bb", "third": "cc", "group": "gg",
            "flag": "firm", "big": "omega", "small": "zeta",
        }  # fmt: skip
        expected = [
            "second role text\n",
            "first role text\nsecond role text\nthird role text\n",
            "first role text\nthird role text\n",
            "",
        ]

        for number, names in enumerate((original, renamed)):
            kept, small_identifier = directory(names, tmp_path / str(number))
            big_identifier = f"claude-{names['big']}-5-5"
            texts = []
            for session_id, identifier, flagged in (
                ("s1", big_identifier, False),
                ("s2", big_identifier, True),
                ("s3", small_identifier, True),
                ("s4", small_identifier, False),
            ):
                kept.environment.pop("RULESETS_FLAGS", None)
                if flagged:
                    kept.environment["RULESETS_FLAGS"] = names["flag"]
                texts.append(kept.start_session(identifier, session_id=session_id).context)
            assert texts == expected
