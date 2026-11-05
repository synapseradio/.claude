#!/usr/bin/env python3
"""A rulesets directory holds a pool of rule files that reach a context only through a list.

Serves the person who writes rules and lists and the engineer who reads check output: the pool
names rules and variants by file name, the reserved rulesets and folders carry fixed meanings, and
the engine reads one directory at user scope and leaves the harness's own rules folders alone.
Each case builds a configuration directory under `tmp_path` and either composes a context from
named facts or runs the hook entries that `hooks/hooks.json` wires, as the harness runs them.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_rules_directories.py`.
"""

import ast
import json
import pathlib
import re
import sys

import pytest
from delivery_world import Delivery, World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import spawn_log  # noqa: E402  (path must be set before this import)
from rulesets.check.findings import (  # noqa: E402
    ReferenceSubject,
    RulesetsSubject,
    RulesetSubject,
    RuleSubject,
)
from rulesets.check.report_format import report_lines  # noqa: E402
from rulesets.check.run import check  # noqa: E402
from rulesets.cli import main  # noqa: E402
from rulesets.compose.applying import applying_lists  # noqa: E402
from rulesets.compose.composition import DeliveredRule, compose  # noqa: E402
from rulesets.compose.precedence import (  # noqa: E402
    Adds,
    Position,
    PositionBand,
    Reach,
    Removes,
)
from rulesets.compose.statements import statements  # noqa: E402
from rulesets.facts.context import ABSENT, Facts  # noqa: E402
from rulesets.facts.kinds import Rank  # noqa: E402
from rulesets.facts.model import fact as model_fact  # noqa: E402
from rulesets.locations import Locations  # noqa: E402
from rulesets.session.state import Band, SessionState, write_state  # noqa: E402
from rulesets.source.directory import Present, read_directory  # noqa: E402
from rulesets.source.expansion import Expander  # noqa: E402
from rulesets.source.pool import read_pool  # noqa: E402

MODELS = "models: ['opus', 'sonnet', 'haiku']\n"


def build(tmp_path, manifest, rules):
    """A rulesets directory with the manifest text and a rule file per stem.

    `rules` maps a stem to its text, or to None for a stem holding the text `text of <stem>`.
    """

    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    (root / "manifest.yaml").write_text(manifest, encoding="utf-8")
    for stem, text in rules.items():
        body = f"text of {stem}\n" if text is None else text
        (root / "rules" / f"{stem}.md").write_text(body, encoding="utf-8")
    return root


def session_facts(*, flags=()):
    return Facts(model=ABSENT, agent=ABSENT, kind="session", flags=frozenset(flags))


@pytest.fixture
def world(tmp_path):
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


def withheld_rules(world: World) -> list[str]:
    return [w["rule"] for record in world.records() for w in record["withheld"]]


class TestTermsAndOutwardVocabulary:
    def test_a_check_message_names_the_rule_and_the_variant_and_no_retired_word(self, tmp_path):
        root = build(tmp_path, "defaults: ['tone']\n", {"tone@dry": None})

        lines = report_lines(check(root))

        (naming,) = [line for line in lines if "variant-without-default" in line]
        assert "rule `tone`" in naming
        assert "variant `dry`" in naming
        assert not re.search(r"\b(tier|stem)s?\b", "\n".join(lines), re.IGNORECASE)


class TestRuleVariantDefaultFormAndPool:
    def test_a_list_naming_a_rule_bare_and_a_list_naming_it_at_a_variant_each_deliver_their_own_file(
        self, world
    ):
        world.rule("voice", "the default voice\n")
        world.rule("voice@terse", "the terse voice\n")
        world.manifest(
            MODELS
            + "flags: ['plain', 'terse']\n"
            + "defaults: []\n"
            + "when:\n"
            + "  - flag plain: ['voice']\n"
            + "  - flag terse: ['voice@terse']\n"
        )

        world.environment["RULESETS_FLAGS"] = "plain"
        bare = world.start_session()
        world.environment["RULESETS_FLAGS"] = "terse"
        at_variant = world.start_session(session_id="s2")

        assert bare.context == "the default voice\n"
        assert at_variant.context == "the terse voice\n"


class TestRulesetFlagBlockAndModel:
    def test_a_block_keyed_on_a_declared_flag_applies_in_a_launch_that_sets_it_and_in_no_other(
        self, world
    ):
        world.rule("security-pass", "check the security\n")
        world.manifest(
            MODELS
            + "rulesets:\n"
            + "  review: ['security-pass']\n"
            + "flags: ['strict']\n"
            + "defaults: []\n"
            + "when:\n"
            + "  - flag strict: ['review:*']\n"
        )

        world.environment["RULESETS_FLAGS"] = "strict"
        launched_with = world.start_session()
        world.environment.pop("RULESETS_FLAGS")
        launched_without = world.start_session(session_id="s2")

        assert launched_with.context == "check the security\n"
        assert launched_without.context == ""


class TestReferenceAndList:
    def test_a_list_holding_a_bare_rule_a_rule_at_a_variant_and_the_remove_of_the_bare_rule_composes_without_it(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['tone', 'voice@terse', '-tone']\n",
            {"tone": None, "voice": None, "voice@terse": None},
        )

        composition = compose(read_directory(root), session_facts(), SessionState())

        assert composition.rules == (DeliveredRule("voice", "terse"),)


class TestStatementAndPosition:
    def test_a_spread_states_an_inclusion_of_every_rule_it_reaches_at_the_blocks_position(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "rulesets:\n"
            "  review: ['voice', 'tone']\n"
            "flags: ['strict']\n"
            "defaults: ['-tone']\n"
            "when:\n"
            "  - flag strict: ['review:*']\n",
            {"voice": None, "tone": None},
        )
        directory = read_directory(root)
        facts = session_facts(flags=["strict"])
        assert isinstance(directory.manifest, Present)
        expander = Expander(
            directory.manifest.manifest.spreadable(), directory.pool.variants_by_rule()
        )

        made = statements(applying_lists(directory, facts, SessionState()), expander)

        tone = [statement for statement in made if statement.rule == "tone"]
        (include,) = [s for s in tone if isinstance(s.says, Adds)]
        (exclude,) = [s for s in tone if isinstance(s.says, Removes)]
        assert include.position == Position(
            PositionBand.DIRECTORY, Rank.FLAG, Reach.THROUGH_RULESET
        )
        assert exclude.position == Position(PositionBand.DIRECTORY, Rank.NONE, Reach.NAMED)
        assert {d.rule for d in compose(directory, facts, SessionState()).rules} == {
            "voice",
            "tone",
        }


class TestThePoolHoldsEveryRuleFile:
    def test_one_rule_is_read_from_a_default_form_and_two_variants(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: []\n",
            {"voice": None, "voice@terse": None, "voice@warm": None},
        )

        pool = read_pool(root)

        assert list(pool.rules) == ["voice"]
        rule = pool.rules["voice"]
        assert rule.default is not None
        assert set(rule.variants) == {"terse", "warm"}

    def test_an_empty_default_form_passes_check_and_delivers_no_text(self, world):
        world.rule("voice", "")
        world.rule("voice@terse", "the terse voice\n")
        world.manifest(MODELS + "defaults: ['voice']\n")

        report = check(world.rulesets)
        delivery = world.start_session()

        assert [e for e in report.errors if e.subject == RuleSubject("voice")] == []
        assert delivery.context == ""
        assert delivery.messages == []
        (record,) = world.records()
        assert [(line["rule"], line["variant"]) for line in record["rules"]] == [("voice", None)]
        assert record["withheld"] == []


class TestAVariantBesideNoDefaultFormIsACheckError:
    def test_a_variant_with_no_default_form_fails_check_and_is_withheld_from_delivery(self, world):
        world.rule("tone@dry")
        world.manifest(MODELS + "defaults: ['tone']\n")

        report = check(world.rulesets)
        delivery = world.start_session()

        assert [e.subject for e in report.errors] == [RuleSubject("tone")]
        assert delivery.context == ""
        assert withheld_rules(world) == ["tone"]
        assert main(["check", "--root", str(world.rulesets)]) == 1


class TestAPoolFileDeliversNothingByBeingThere:
    def test_a_pool_file_no_list_reaches_arrives_in_no_context_and_the_listed_rules_still_do(
        self, world
    ):
        world.rule("voice")
        world.rule("sorting")
        world.manifest(MODELS + "defaults: ['voice', 'sorting']\n")
        world.rule("draft-notes", "scratch thoughts\n")

        deliveries = every_context(world)

        assert [d.context for d in deliveries] == ["text of sorting\ntext of voice\n"] * 4


class TestTheReferencesAndRenderFoldersAreReserved:
    def test_rendered_files_in_the_render_folder_become_no_rule_and_draw_no_stray_warning(
        self, tmp_path
    ):
        root = build(tmp_path, "defaults: ['*']\n", {"sorting": None})
        (root / "-render").mkdir()
        (root / "-render" / "voice.md").write_text("rendered voice\n", encoding="utf-8")
        (root / "-render" / "voice@terse.md").write_text("rendered terse\n", encoding="utf-8")
        (root / "references").mkdir()
        (root / "references" / "notes.md").write_text("reference notes\n", encoding="utf-8")
        (root / "references" / "table.md").write_text("reference table\n", encoding="utf-8")

        pool = read_pool(root)
        report = check(root)

        assert list(pool.rules) == ["sorting"]
        assert report.errors == ()
        assert report.warnings == ()


class TestOneRulesetsDirectorySitsAtAFixedPathAtUserScope:
    def test_a_projects_own_rules_folder_stays_outside_every_composition_and_unchanged(
        self, world, tmp_path, monkeypatch
    ):
        world.rule("user-rule")
        world.manifest(MODELS + "defaults: ['*']\n")
        project = tmp_path / "project"
        harness_rules = project / ".claude" / "rules"
        harness_rules.mkdir(parents=True)
        (harness_rules / "testing.md").write_bytes(b"project testing rule\r\n\xc3\xa9")
        for inside in (project / "rulesets", project / ".claude" / "rulesets"):
            (inside / "rules").mkdir(parents=True)
            (inside / "rules" / "project-only.md").write_text("project only\n", encoding="utf-8")
            (inside / "manifest.yaml").write_text("defaults: ['*']\n", encoding="utf-8")
        before = {p: p.read_bytes() for p in harness_rules.rglob("*") if p.is_file()}
        monkeypatch.chdir(project)

        session = world.start_session(cwd=str(project))
        delegate = world.start_delegate("critic", cwd=str(project))
        report = check(world.rulesets)

        assert [session.context, delegate.context] == ["text of user-rule\n"] * 2
        assert report.errors == ()
        assert {p: p.read_bytes() for p in harness_rules.rglob("*") if p.is_file()} == before
        assert sorted(p.name for p in harness_rules.iterdir()) == ["testing.md"]

    def test_rule_files_another_plugin_placed_in_the_personal_rules_folder_stay_uncomposed_and_unchanged(
        self, world, tmp_path
    ):
        world.rule("user-rule")
        world.manifest(MODELS + "defaults: ['*']\n")
        shipped = world.config / "rules"
        shipped.mkdir()
        (shipped / "shipped-rule.md").write_bytes(b"shipped by a plugin\r\n\xc3\xa9")
        (shipped / "second-rule.md").write_text("second\n", encoding="utf-8")
        before = {p: p.read_bytes() for p in shipped.rglob("*") if p.is_file()}
        context = tmp_path / "context.md"

        session = world.start_session()
        delegate = world.start_delegate("critic")
        report = check(world.rulesets)
        assert main(["render", "--root", str(world.rulesets), "--out", str(context)]) == 0
        assert main(["render", "--root", str(world.rulesets)]) == 0

        assert [session.context, delegate.context] == ["text of user-rule\n"] * 2
        assert report.errors == ()
        assert (
            context.read_text(encoding="utf-8") == "<!-- rule: user-rule -->\ntext of user-rule\n"
        )
        rendered = [p.read_bytes() for p in (world.rulesets / "-render").iterdir()]
        assert rendered
        assert not any(b"shipped" in text or b"second" in text for text in rendered)
        assert {p: p.read_bytes() for p in shipped.rglob("*") if p.is_file()} == before
        assert sorted(p.name for p in shipped.iterdir()) == ["second-rule.md", "shipped-rule.md"]


class TestTheDirectoryAndSessionStateStandInTwoBands:
    def test_the_toggle_all_overrides_a_blocks_exclude_for_a_haiku_delegate(self, world):
        world.rule("writing-code")
        world.manifest(
            MODELS + "defaults: ['writing-code']\nwhen:\n  - model haiku: ['-writing-code']\n"
        )
        state = Locations(world.config).state
        for session_id in ("toggled", "plain"):
            spawn_log.append_spawn(session_id, "p1", "critic", "haiku", state)
        write_state(Locations(world.config), "toggled", SessionState(Band.ALL))

        toggled = world.start_delegate("critic", session_id="toggled")
        plain = world.start_delegate("critic", session_id="plain")

        assert toggled.context == "text of writing-code\n"
        assert plain.context == ""


class TestSessionStateHoldsNoRuleFile:
    def test_a_delegate_reads_the_edited_rule_text_and_the_flag_a_toggle_set(self, world):
        world.rule("voice")
        world.rule("security-pass")
        world.manifest(
            "flags: ['strict']\ndefaults: ['voice']\nwhen:\n  - flag strict: ['security-pass']\n"
        )
        world.start_session()
        world.toggle_flags({"strict": "set"})
        world.rule("voice", "edited text of voice\n")

        delegate = world.start_delegate("critic")

        assert "edited text of voice\n" in delegate.context
        assert "text of security-pass\n" in delegate.context


class TestARuleIsUnconditionalText:
    def test_conditional_metadata_in_a_rule_file_is_a_check_error_and_withholds_the_rule(
        self, world
    ):
        world.rule("scoped", "---\npaths: ['src/**']\n---\nscoped text\n")
        world.rule("modeled", "---\nmodel: haiku\n---\nmodeled text\n")
        world.rule("broken", "---\npaths: [unclosed\n---\nbroken text\n")
        world.rule("plain", "plain text\n")
        world.manifest(MODELS + "defaults: ['scoped', 'modeled', 'broken', 'plain']\n")

        report = check(world.rulesets)
        delivery = world.start_session()

        assert {e.subject for e in report.errors} == {
            RuleSubject("scoped"),
            RuleSubject("modeled"),
            RuleSubject("broken"),
        }
        assert [e.kind for e in report.errors if e.subject == RuleSubject("broken")] == [
            "frontmatter-unparsable"
        ]
        assert delivery.context == "plain text\n"
        assert sorted(withheld_rules(world)) == ["broken", "modeled", "scoped"]

    def test_prose_describing_when_a_rule_applies_is_delivered_as_plain_text_with_no_finding(
        self, world
    ):
        text = "on haiku models, keep answers short\n"
        world.rule("brevity", text)
        world.manifest(MODELS + "defaults: ['brevity']\n")
        state = Locations(world.config).state
        spawn_log.append_spawn("s2", "p1", "critic", "haiku", state)

        report = check(world.rulesets)
        on_opus = world.start_session()
        on_haiku = world.start_delegate("critic", session_id="s2")

        assert (report.errors, report.warnings) == ((), ())
        assert [on_opus.context, on_haiku.context] == [text, text]


class TestReservedRulesetsCarryFixedMeanings:
    def test_the_spread_of_all_delivers_every_pool_rule_at_its_default_form(self, world):
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("sorting", "sorting text\n")
        world.manifest(MODELS + "defaults: ['all:*']\n")

        assert world.start_session().context == "sorting text\ndefault voice\n"

    def test_rules_at_a_rules_name_names_that_rule_and_the_spread_of_rules_names_every_rule(
        self, world
    ):
        world.rule("voice", "voice text\n")
        world.rule("sorting", "sorting text\n")
        world.manifest(
            MODELS
            + "flags: ['one', 'every']\n"
            + "defaults: []\n"
            + "when:\n"
            + "  - flag one: ['rules:voice']\n"
            + "  - flag every: ['rules:*']\n"
        )

        world.environment["RULESETS_FLAGS"] = "one"
        first = world.start_session()
        world.environment["RULESETS_FLAGS"] = "every"
        second = world.start_session(session_id="s2")

        assert first.context == "voice text\n"
        assert second.context == "sorting text\nvoice text\n"

    def test_the_spread_of_none_delivers_no_rule(self, world):
        world.rule("voice")
        world.rule("sorting")
        world.manifest(MODELS + "defaults: ['none:*']\n")

        alone = world.start_session()

        assert check(world.rulesets).errors == ()
        assert "received nothing" in alone.message
        assert alone.context == ""

        world.manifest(MODELS + "defaults: ['voice', 'none:*']\n")

        beside_voice = world.start_session(session_id="s2")

        assert beside_voice.messages == []
        assert beside_voice.context == "text of voice\n"


class TestTheDefaultsRulesetAppliesInEveryContextAtTheLowestPosition:
    def test_defaults_spreading_all_reaches_the_main_session_and_every_delegate(self, world):
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("sorting", "sorting text\n")
        world.manifest(MODELS + "defaults: ['all:*']\n")

        deliveries = every_context(world)

        assert [d.context for d in deliveries] == ["sorting text\ndefault voice\n"] * 4

    def test_a_manifest_listing_nothing_under_defaults_delivers_no_rule_to_any_context(self, world):
        world.rule("voice")
        world.rule("sorting")
        world.manifest(MODELS)

        deliveries = every_context(world)

        assert [d.context for d in deliveries] == [""] * 4


def expander_of(directory) -> Expander:
    assert isinstance(directory.manifest, Present)
    return Expander(directory.manifest.manifest.spreadable(), directory.pool.variants_by_rule())


def made_statements(root, facts):
    directory = read_directory(root)
    return statements(applying_lists(directory, facts, SessionState()), expander_of(directory))


def delivered(root, facts):
    return compose(read_directory(root), facts, SessionState()).rules


class TestDeclaringAReservedNameIsACheckError:
    def test_a_declared_all_is_an_error_naming_the_declaration_and_the_spread_still_reaches_every_pool_rule(
        self, world
    ):
        world.rule("voice", "voice text\n")
        world.rule("sorting", "sorting text\n")
        world.rule("tone", "tone text\n")
        world.manifest("rulesets:\n  all: ['voice', 'sorting']\ndefaults: ['all:*']\n")

        report = check(world.rulesets)
        delivery = world.start_session()

        assert [(e.kind, e.subject, e.line) for e in report.errors] == [
            ("reserved-ruleset", RulesetSubject("all"), 2)
        ]
        assert delivery.context == "sorting text\ntone text\nvoice text\n"


class TestARuleAndARulesetMayShareAName:
    def test_a_bare_name_means_the_rule_and_the_spread_of_the_same_name_means_the_ruleset(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "rulesets:\n  reviewer: ['security-pass', 'report-format']\n"
            "flags: ['bare', 'spread']\ndefaults: []\n"
            "when:\n  - flag bare: ['reviewer']\n  - flag spread: ['reviewer:*']\n",
            {"reviewer": None, "security-pass": None, "report-format": None},
        )

        report = check(root)

        assert report.errors == ()
        assert delivered(root, session_facts(flags=["bare"])) == (DeliveredRule("reviewer", None),)
        assert delivered(root, session_facts(flags=["spread"])) == (
            DeliveredRule("report-format", None),
            DeliveredRule("security-pass", None),
        )


class TestARulesetGroupsRulesByReference:
    def test_every_reference_form_passes_check_in_defaults_a_blocks_list_and_a_rulesets_list(
        self, tmp_path
    ):
        forms = "['voice', 'rules:voice', 'voice@terse', 'group:*', '-tone']"
        root = build(
            tmp_path,
            f"rulesets:\n  group: ['voice']\n  inner: {forms}\n"
            f"flags: ['f']\ndefaults: {forms}\nwhen:\n  - flag f: {forms}\n",
            {"voice": None, "voice@terse": None, "tone": None},
        )

        report = check(root)

        assert report.errors == ()
        assert delivered(root, session_facts(flags=["f"])) == (DeliveredRule("voice", "terse"),)


class TestASpreadYieldsTheEntriesOfTheSpreadRuleset:
    def test_a_ruleset_inside_a_ruleset_yields_the_entries_of_both(self, tmp_path):
        root = build(
            tmp_path,
            "rulesets:\n  review: ['code:*', 'report-format']\n"
            "  code: ['writing-code', 'data-modeling']\ndefaults: ['review:*']\n",
            {"writing-code": None, "data-modeling": None, "report-format": None},
        )
        directory = read_directory(root)
        assert isinstance(directory.manifest, Present)
        defaults = directory.manifest.manifest.spreadable()["defaults"]

        entries = expander_of(directory).expand(defaults).entries

        assert [(e.rule, e.variant) for e in entries] == [
            ("writing-code", None),
            ("data-modeling", None),
            ("report-format", None),
        ]

    def test_a_variant_in_a_spread_ruleset_reaches_the_spreading_list_as_an_include_with_its_variant_set(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "rulesets:\n  auditor: ['report-format@table']\nflags: ['f']\ndefaults: []\n"
            "when:\n  - flag f: ['auditor:*']\n",
            {"report-format": None, "report-format@table": None},
        )

        made = made_statements(root, session_facts(flags=["f"]))

        (statement,) = [s for s in made if s.rule == "report-format"]
        assert statement.says == Adds("table")


class TestASpreadInACycleOfSpreadsReachesNoRule:
    def test_a_two_ruleset_cycle_is_one_error_naming_both_and_neither_spread_reaches_a_rule(
        self, world
    ):
        world.rule("voice")
        world.rule("tone")
        world.rule("sorting")
        world.manifest(
            "rulesets:\n  a: ['b:*', 'voice']\n  b: ['a:*', 'tone']\n"
            "flags: ['other']\ndefaults: ['a:*', 'sorting']\n"
            "when:\n  - flag other: ['b:*']\n"
        )

        report = check(world.rulesets)
        plain = world.start_session()
        world.environment["RULESETS_FLAGS"] = "other"
        flagged = world.start_session(session_id="s2")

        assert [(e.kind, e.subject) for e in report.errors] == [
            ("ruleset-cycle", RulesetsSubject(("a", "b"))),
        ]
        assert all("cycle" in e.message for e in report.errors)
        assert [plain.context, flagged.context] == ["text of sorting\n"] * 2


class TestAReferenceToAnUndeclaredNameIsSkipped:
    def test_a_misspelled_member_is_an_error_and_a_shown_notice_while_every_other_member_applies(
        self, world
    ):
        world.rule("voice")
        world.rule("sorting")
        world.manifest(
            MODELS
            + "rulesets:\n  review:\n    - 'voise'\n    - 'voice'\n    - 'sorting'\n"
            + "defaults: ['review:*']\n"
        )

        report = check(world.rulesets)
        delivery = world.start_session()

        assert [(e.kind, e.subject, e.line) for e in report.errors] == [
            ("undeclared-reference", ReferenceSubject("voise", 4), 4)
        ]
        assert delivery.context == "text of sorting\ntext of voice\n"
        assert len(delivery.messages) == 1
        assert "`voise`" in delivery.message
        assert "manifest line 4" in delivery.message


class TestWithinAListRemovesApplyAfterAdds:
    def test_a_list_yields_the_same_result_with_its_remove_written_before_or_after_its_add(
        self, tmp_path
    ):
        pool = {"voice": None, "sorting": None, "tone": None}
        before = build(tmp_path / "before", "defaults: ['-voice', 'all:*']\n", pool)
        after = build(tmp_path / "after", "defaults: ['all:*', '-voice']\n", pool)

        for root in (before, after):
            assert delivered(root, session_facts()) == (
                DeliveredRule("sorting", None),
                DeliveredRule("tone", None),
            )


class TestARemoveOfARuleAtAVariantTakesThatVariantOutAlone:
    def test_a_variant_remove_leaves_the_rule_on_at_its_default_form(self, world):
        world.rule("voice", "default voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.manifest(MODELS + "defaults: ['voice', 'voice@terse', '-voice@terse']\n")

        assert world.start_session().context == "default voice\n"


class TestARemoveStandsAsAStatementInAnApplyingListAndAsNoneInsideASpreadRuleset:
    def test_a_remove_inside_a_spread_ruleset_subtracts_from_it_and_states_no_exclusion(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "rulesets:\n  lean: ['all:*', '-voice']\nflags: ['f']\ndefaults: ['voice']\n"
            "when:\n  - flag f: ['lean:*']\n",
            {"voice": None, "sorting": None, "tone": None},
        )
        facts = session_facts(flags=["f"])

        made = made_statements(root, facts)

        about_voice = [s for s in made if s.rule == "voice"]
        assert [type(s.says) for s in about_voice] == [Adds]
        assert {s.rule for s in made if isinstance(s.says, Adds)} == {"voice", "sorting", "tone"}
        assert not [s for s in made if isinstance(s.says, Removes)]
        assert [d.rule for d in delivered(root, facts)] == ["sorting", "tone", "voice"]

    def test_a_remove_in_the_blocks_own_list_excludes_the_rule_that_defaults_includes(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['f']\ndefaults: ['voice', 'sorting']\nwhen:\n  - flag f: ['-voice']\n",
            {"voice": None, "sorting": None},
        )
        facts = session_facts(flags=["f"])

        made = made_statements(root, facts)

        (include,) = [s for s in made if s.rule == "voice" and isinstance(s.says, Adds)]
        (exclude,) = [s for s in made if s.rule == "voice" and isinstance(s.says, Removes)]
        assert exclude.position > include.position
        assert delivered(root, facts) == (DeliveredRule("sorting", None),)


class TestExactlyOneVariantOfARuleReachesAContext:
    def test_a_context_receives_the_text_of_the_one_variant_a_block_sets_and_no_other_text_of_the_rule(
        self, world
    ):
        world.rule("voice", "the default voice\n")
        world.rule("voice@terse", "the terse voice\n")
        world.rule("voice@warm", "the warm voice\n")
        world.manifest(MODELS + "flags: ['f']\ndefaults: []\nwhen:\n  - flag f: ['voice@terse']\n")
        world.environment["RULESETS_FLAGS"] = "f"

        assert world.start_session().context == "the terse voice\n"

    def test_a_block_naming_a_variant_the_pool_lacks_is_skipped_with_a_shown_notice(self, world):
        world.rule("voice", "the default voice\n")
        world.rule("voice@terse", "the terse voice\n")
        world.manifest(
            MODELS
            + "flags: ['f']\ndefaults: ['voice@terse']\n"
            + "when:\n  - flag f: ['voice@brisk']\n"
        )
        world.environment["RULESETS_FLAGS"] = "f"

        delivery = world.start_session()

        report = check(world.rulesets)

        assert delivery.context == "the terse voice\n"
        assert delivery.message == (
            "the reference `voice@brisk` at manifest line 5 names `voice@brisk`, "
            "which is not declared; skipped"
        )
        assert [(e.kind, e.subject, e.line) for e in report.errors] == [
            ("undeclared-reference", ReferenceSubject("voice@brisk", 5), 5)
        ]


class TestAContextReceivesASetOfRulesWithNoDuplicates:
    def test_a_rule_reached_by_defaults_a_spread_and_a_name_arrives_once(self, world):
        world.rule("report-format", "REPORT FORMAT BODY\n")
        world.rule("voice", "voice text\n")
        world.manifest(
            MODELS
            + "rulesets:\n  group: ['report-format']\n"
            + "defaults: ['all:*']\n"
            + "when:\n  - agent auditor: ['group:*']\n  - agent auditor: ['report-format']\n"
        )

        delegate = world.start_delegate("auditor")

        assert delegate.context == "REPORT FORMAT BODY\nvoice text\n"
        assert delegate.context.count("REPORT FORMAT BODY") == 1
        (record,) = world.records()
        assert [line["rule"] for line in record["rules"]] == ["report-format", "voice"]


class TestRulesArriveSortedByName:
    def test_delivered_rules_arrive_in_name_order_whatever_order_any_list_names_them(self, world):
        world.rule("writing-code", "writing text\n")
        world.rule("core-rules", "core text\n")
        world.rule("sorting", "sorting text\n")
        world.manifest(
            MODELS
            + "flags: ['f']\ndefaults: ['writing-code', 'sorting']\n"
            + "when:\n  - flag f: ['core-rules']\n"
        )
        world.environment["RULESETS_FLAGS"] = "f"

        assert world.start_session().context == "core text\nsorting text\nwriting text\n"

    def test_one_composed_set_yields_byte_identical_text_at_session_start_and_after_a_compaction(
        self, world
    ):
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
        world.manifest(MODELS + "defaults: ['*']\n")
        first_part = (
            "no final newline"
            "line one\r\nline two\r\n"
            "caf\u00e9 \u2014 na\u00efve \u65e5\u672c\n" + "d" * 4000 + "\n" + "e" * 4000 + "\n"
        )
        second_part = "f" * 4000 + "\n"

        started = world.start_session()
        compacted = world.start_session(source="compact")

        def contexts(delivery):
            return [
                json.loads(delivery.outputs[part])["hookSpecificOutput"]["additionalContext"]
                for part in sorted(delivery.outputs)
                if delivery.outputs[part].strip()
            ]

        assert contexts(started) == [first_part, second_part]
        assert [c.encode() for c in contexts(compacted)] == [c.encode() for c in contexts(started)]
        assert compacted.context.encode() == started.context.encode()


class TestTheEnginesCodeNamesNoContent:
    def test_a_consistent_renaming_of_rules_rulesets_flags_and_models_leaves_every_contexts_texts_unchanged(
        self, tmp_path
    ):
        def directory(names: dict[str, str], where: pathlib.Path) -> tuple[World, str]:
            kept = World(where)
            for role, text in (
                ("first", "first role text\n"),
                ("second", "second role text\n"),
                ("third", "third role text\n"),
            ):
                kept.rule(names[role], text)
            kept.manifest(
                f"models: ['{names['big']}', '{names['small']}']\n"
                f"rulesets:\n  {names['group']}: ['{names['third']}', '{names['first']}']\n"
                f"flags: ['{names['flag']}']\n"
                f"defaults: ['{names['second']}']\n"
                f"when:\n  - flag {names['flag']}: ['{names['group']}:*']\n"
                f"  - model {names['small']}: ['-{names['second']}']\n"
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

    def test_no_string_literal_in_the_engines_code_names_content_outside_the_closed_list(self):
        # The closed list: the prefix `claude-`, the reserved rulesets, and the pins the harness
        # gives its built-in agents. A model family word or a built-in agent name may stand only
        # as one of those pins.
        pins = {"claude-code-guide": "haiku", "statusline-setup": "sonnet"}
        allowed_literals = set(pins) | set(pins.values()) | {"claude-"}
        model_family_words = {"opus", "sonnet", "haiku", "fable"}
        built_in_agent_names = {"explore", "plan"}
        identifier_shape = re.compile(r"claude-[\w\[\]-]+")

        def names_content(literal: str) -> bool:
            words = set(re.findall(r"[a-z0-9]+", literal.lower()))
            return bool(
                words & model_family_words
                or words & {"explore"}
                or literal.strip().lower() in built_in_agent_names
                or identifier_shape.fullmatch(literal)
            )

        sources = sorted((PLUGIN_ROOT / "lib" / "rulesets").rglob("*.py"))
        offenders = [
            f"{source.relative_to(PLUGIN_ROOT)}:{node.lineno}: {node.value[:60]!r}"
            for source in sources
            for node in ast.walk(ast.parse(source.read_text(encoding="utf-8")))
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value not in allowed_literals
            and names_content(node.value)
        ]

        assert sources
        assert offenders == []

    def test_a_built_in_agent_takes_its_harness_pin_as_the_model_fact_when_the_manifest_declares_the_pinned_name(
        self, scene
    ):
        fact = scene.fact("claude-code-guide", models=["opus", "haiku"])

        assert fact == model_fact.Claimed("haiku", "haiku", "built-in-pin")
        assert model_fact.claimed_name(fact) == "haiku"

        statusline = scene.fact("statusline-setup", models=["opus", "sonnet", "haiku"])

        assert statusline == model_fact.Claimed("sonnet", "sonnet", "built-in-pin")
        assert model_fact.claimed_name(statusline) == "sonnet"

    def test_a_built_in_agents_pinned_identifier_stays_unclaimed_when_the_manifest_declares_no_model_names(
        self, world
    ):
        world.rule("voice")
        world.manifest("defaults: []\nwhen:\n  - model haiku: ['voice']\n")

        delivery = world.start_delegate("claude-code-guide")

        assert delivery.context == ""
        (record,) = world.records()
        assert record["model"] == {
            "state": "unclaimed",
            "name": None,
            "identifier": "haiku",
            "source": "built-in-pin",
            "not_a_string": None,
        }
