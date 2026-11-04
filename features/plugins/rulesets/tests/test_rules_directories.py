#!/usr/bin/env python3
"""A rulesets directory holds a pool of rule files that reach a context only through a list.

Serves the person who writes rules and lists and the engineer who reads check output: the pool
names rules and variants by file name, the reserved rulesets and folders carry fixed meanings, and
the engine reads one directory at user scope and leaves the harness's own rules folders alone.
Each case builds a configuration directory under `tmp_path` and either composes a context from
named facts or runs the hook entries that `hooks/hooks.json` wires, as the harness runs them.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_rules_directories.py`.
"""

import pathlib
import re
import sys

import pytest
from delivery_world import Delivery, World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import spawn_log  # noqa: E402  (path must be set before this import)
from rulesets.check.findings import RuleSubject  # noqa: E402
from rulesets.check.report_format import report_lines  # noqa: E402
from rulesets.check.run import check  # noqa: E402
from rulesets.cli import main  # noqa: E402
from rulesets.compose.applying import applying_lists  # noqa: E402
from rulesets.compose.composition import DeliveredRule, compose  # noqa: E402
from rulesets.compose.precedence import Adds, Removes  # noqa: E402
from rulesets.compose.statements import statements  # noqa: E402
from rulesets.facts.context import Facts  # noqa: E402
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
    return Facts(model=None, agent=None, kind="session", flags=frozenset(flags))


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
        assert include.position > exclude.position
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

        pool = read_pool(root)
        report = check(root)

        assert list(pool.rules) == ["sorting"]
        assert [w for w in report.warnings if w.kind == "stray-directory"] == []


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


class TestARuleIsUnconditionalText:
    def test_conditional_metadata_in_a_rule_file_is_a_check_error_and_withholds_the_rule(
        self, world
    ):
        world.rule("scoped", "---\npaths: ['src/**']\n---\nscoped text\n")
        world.rule("modeled", "---\nmodel: haiku\n---\nmodeled text\n")
        world.rule("plain", "plain text\n")
        world.manifest(MODELS + "defaults: ['scoped', 'modeled', 'plain']\n")

        report = check(world.rulesets)
        delivery = world.start_session()

        assert {e.subject for e in report.errors} == {RuleSubject("scoped"), RuleSubject("modeled")}
        assert delivery.context == "plain text\n"
        assert sorted(withheld_rules(world)) == ["modeled", "scoped"]

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

        assert world.start_session().context == ""


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
