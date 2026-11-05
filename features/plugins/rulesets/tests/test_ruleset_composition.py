#!/usr/bin/env python3
"""A context receives the rules its applying lists leave on, each at the variant they settle.

The composition serves the engineer who writes a manifest and the person whose agents receive
the result: a block keyed on a fact reaches the contexts where the key holds, the statements of
every applying list settle each rule's inclusion and variant by position, and check names the
conflicts and layout problems that make a composition surprising. Each case builds its rulesets
directory under `tmp_path` and composes a context from named facts.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_ruleset_composition.py`.
"""

import pathlib
import sys

from delivery_world import DECLARED, OPUS, World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import spawn_log  # noqa: E402
from rulesets.check.findings import ContextSubject, ReferencesSubject, ReferenceSubject  # noqa: E402
from rulesets.check.report_format import finding_line  # noqa: E402
from rulesets.check.run import check  # noqa: E402
from rulesets.cli import main  # noqa: E402
from rulesets.compose.composition import compose  # noqa: E402  (path must be set before this import)
from rulesets.delivery.parts import pack_parts  # noqa: E402
from rulesets.delivery.rule_bodies import bodies_of  # noqa: E402
from rulesets.facts.context import ABSENT, UNCLAIMED, Facts  # noqa: E402
from rulesets.locations import Locations  # noqa: E402
from rulesets.session.state import Band, SessionState, read_state, write_state  # noqa: E402
from rulesets.source.directory import read_directory  # noqa: E402
from rulesets.source.manifest import read_manifest  # noqa: E402


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


def context(*, model=None, agent=None, kind="session", flags=(), session=None):
    return Facts(
        model=ABSENT if model is None else model,
        agent=ABSENT if agent is None else agent,
        kind=kind,
        flags=frozenset(flags),
        session=ABSENT if session is None else session,
    )


def composed(root, facts, state=None):
    return compose(read_directory(root), facts, state or SessionState())


def notice_entries(world, kind):
    return [n for r in world.records() for n in r["notices"] if n["kind"] == kind]


def received(root, facts, state=None):
    """The rules the context receives, as a mapping of rule name to variant (None: default form)."""

    return {d.rule: d.variant for d in composed(root, facts, state).rules}


class TestBlocksApplyWhereTheirKeyEvaluatesTrue:
    def test_a_model_block_removes_a_rule_from_every_context_on_that_model(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['opus', 'haiku']\n"
            "defaults: ['writing-code']\n"
            "when:\n"
            "  - model haiku: ['-writing-code']\n",
            {"writing-code": None},
        )

        contexts = [
            context(model="haiku", agent="critic", kind="delegate"),
            context(model="haiku", agent="auditor", kind="delegate"),
            context(model="haiku"),
        ]

        assert [received(root, facts) for facts in contexts] == [{}, {}, {}]

    def test_a_model_block_leaves_the_rule_in_contexts_on_another_model(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['opus', 'haiku']\n"
            "defaults: ['writing-code']\n"
            "when:\n"
            "  - model haiku: ['-writing-code']\n",
            {"writing-code": None},
        )

        contexts = [
            context(model="opus", agent="critic", kind="delegate"),
            context(model="opus", agent="auditor", kind="delegate"),
            context(model="opus"),
        ]

        assert [received(root, facts) for facts in contexts] == [{"writing-code": None}] * 3

    def test_a_rule_for_one_agent_on_one_model_reaches_that_agent_on_that_model_only(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "models: ['opus', 'sonnet']\n"
            "defaults: []\n"
            "when:\n"
            "  - agent critic and model opus: ['security-pass']\n",
            {"security-pass": None},
        )

        critic_on_opus = context(model="opus", agent="critic", kind="delegate")
        critic_on_sonnet = context(model="sonnet", agent="critic", kind="delegate")
        auditor_on_opus = context(model="opus", agent="auditor", kind="delegate")

        assert received(root, critic_on_opus) == {"security-pass": None}
        assert received(root, critic_on_sonnet) == {}
        assert received(root, auditor_on_opus) == {}

    def test_a_ruleset_at_a_variant_gives_that_wording_to_its_agent_and_the_default_to_others(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "rulesets:\n"
            "  auditor: ['report-format@table']\n"
            "defaults: ['*']\n"
            "when:\n"
            "  - agent auditor: ['auditor:*']\n",
            {"report-format": None, "report-format@table": None},
        )

        auditor = context(agent="auditor", kind="delegate")
        critic = context(agent="critic", kind="delegate")
        main = context()

        assert received(root, auditor) == {"report-format": "table"}
        assert received(root, critic) == {"report-format": None}
        assert received(root, main) == {"report-format": None}


class TestEachApplyingListYieldsStatements:
    def test_adds_include_removes_exclude_and_a_variant_remove_strikes_alone(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['strict']\n"
            "defaults: ['*', 'tone@dry']\n"
            "when:\n"
            "  - flag strict: ['voice@terse', '-writing-code', '-tone@dry']\n",
            {
                "voice": None,
                "voice@terse": None,
                "writing-code": None,
                "tone": None,
                "tone@dry": None,
            },
        )

        assert received(root, context(flags=["strict"])) == {"voice": "terse", "tone": None}


class TestTheStatementAtTheHigherPositionDecides:
    def test_a_block_that_removes_a_rule_defaults_include_leaves_it_off(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['strict']\ndefaults: ['voice']\nwhen:\n  - flag strict: ['-voice']\n",
            {"voice": None},
        )

        assert received(root, context(flags=["strict"])) == {}
        assert received(root, context()) == {"voice": None}

    def test_a_block_that_includes_a_rule_defaults_exclude_turns_it_on(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['a']\ndefaults: ['-voice']\nwhen:\n  - flag a: ['voice']\n",
            {"voice": None},
        )

        assert received(root, context(flags=["a"])) == {"voice": None}
        assert received(root, context()) == {}

    def test_the_toggle_none_keeps_a_set_flags_include_out_of_a_delegate(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['strict']\ndefaults: []\nwhen:\n  - flag strict: ['security-pass']\n",
            {"security-pass": None},
        )
        locations = Locations(tmp_path / "config")
        write_state(locations, "s1", SessionState(Band.NONE))
        delegate = context(agent="critic", kind="delegate", flags=["strict"])

        assert received(root, delegate) == {"security-pass": None}
        assert received(root, delegate, read_state(locations, "s1")) == {}

    def test_a_rule_named_in_an_exclude_beats_the_same_rule_reached_through_a_ruleset(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['a', 'b']\n"
            "rulesets:\n"
            "  review: ['voice']\n"
            "defaults: []\n"
            "when:\n"
            "  - flag a: ['review:*']\n"
            "  - flag b: ['-voice']\n",
            {"voice": None},
        )

        assert received(root, context(flags=["a", "b"])) == {}

    def test_a_rule_named_in_an_include_beats_the_same_rule_reached_through_a_ruleset_exclude(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['a', 'b']\n"
            "rulesets:\n"
            "  review: ['voice']\n"
            "defaults: []\n"
            "when:\n"
            "  - flag a: ['voice']\n"
            "  - flag b: ['-review:*']\n",
            {"voice": None},
        )

        assert received(root, context(flags=["a", "b"])) == {"voice": None}

    def test_an_exclude_beats_an_include_of_the_same_rule_at_one_rank(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['a', 'b']\ndefaults: []\nwhen:\n  - flag a: ['voice']\n  - flag b: ['-voice']\n",
            {"voice": None},
        )
        critic = context(agent="critic", kind="delegate", flags=["a", "b"])

        assert received(root, critic) == {}

    def test_an_exclude_listed_before_an_include_of_the_same_rule_at_one_rank_still_wins(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['a', 'b']\ndefaults: []\nwhen:\n  - flag b: ['-voice']\n  - flag a: ['voice']\n",
            {"voice": None},
        )
        critic = context(agent="critic", kind="delegate", flags=["a", "b"])

        assert received(root, critic) == {}


class TestABareStatementDecidesInclusionAlone:
    def test_a_higher_bare_add_leaves_a_lower_set_variant_in_force(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['haiku']\nflags: ['strict']\ndefaults: []\n"
            "when:\n  - flag strict: ['voice']\n  - model haiku: ['voice@terse']\n",
            {"voice": None, "voice@terse": None},
        )

        assert received(root, context(model="haiku", flags=["strict"])) == {"voice": "terse"}


class TestAStrikeDecidesOnlyAgainstTheVariantItNames:
    def test_a_higher_strike_removes_a_lower_set_so_the_rule_arrives_at_its_default_form(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['voice-terse']\n"
            "defaults: []\n"
            "when:\n"
            "  - flag voice-terse: ['voice@terse']\n"
            "  - session abc123: ['-voice@terse']\n",
            {"voice": None, "voice@terse": None},
        )
        delegate = context(kind="delegate", flags=["voice-terse"], session="abc123")

        assert received(root, delegate) == {"voice": None}
        assert received(root, context(kind="delegate", flags=["voice-terse"])) == {"voice": "terse"}

    def test_a_strike_at_a_lower_position_than_the_set_leaves_the_set_standing(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['haiku']\n"
            "flags: ['voice-terse']\n"
            "defaults: []\n"
            "when:\n"
            "  - model haiku: ['-voice@terse']\n"
            "  - flag voice-terse: ['voice@terse']\n",
            {"voice": None, "voice@terse": None},
        )

        assert received(root, context(model="haiku", flags=["voice-terse"])) == {"voice": "terse"}

    def test_a_strike_leaves_the_rule_on_and_strikes_only_the_variant_it_names(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['haiku']\n"
            "flags: ['strict']\n"
            "defaults: ['voice@warm']\n"
            "when:\n"
            "  - model haiku: ['voice@terse']\n"
            "  - flag strict: ['-voice@terse']\n",
            {"voice": None, "voice@terse": None, "voice@warm": None},
        )

        assert received(root, context(model="haiku")) == {"voice": "terse"}
        assert received(root, context(model="haiku", flags=["strict"])) == {"voice": "warm"}

    def test_a_strike_below_a_set_leaves_the_rule_on_and_the_set_variant_standing(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['a']\ndefaults: ['voice', '-voice@terse']\nwhen:\n  - flag a: ['voice@terse']\n",
            {"voice": None, "voice@terse": None},
        )

        assert received(root, context(flags=["a"])) == {"voice": "terse"}
        assert received(root, context()) == {"voice": None}


class TestTheManifestDeclaresFlags:
    def test_a_flags_key_lists_the_declared_flags_and_check_reports_no_error(self, tmp_path):
        root = build(tmp_path, "flags: ['strict', 'terse']\ndefaults: []\n", {})

        assert read_manifest(root).flags == ("strict", "terse")
        assert check(root).errors == ()


class TestTwoVariantsSetAtOnePositionAreAConflict:
    def test_check_reports_an_error_naming_the_rule_and_both_statements(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['a', 'b']\n"
            "defaults: []\n"
            "when:\n"
            "  - flag a: ['voice@terse']\n"
            "  - flag b: ['voice@warm']\n",
            {"voice": None, "voice@terse": None, "voice@warm": None},
        )

        (error,) = check(root).errors

        assert error.kind == "variant-conflict"
        assert error.subject == ReferencesSubject(
            (ReferenceSubject("voice@terse", 4), ReferenceSubject("voice@warm", 5))
        )
        assert "`voice`" in error.message
        assert main(["check", "--root", str(root)]) == 1

    def test_check_reports_no_conflict_between_blocks_for_different_models(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['opus', 'sonnet']\n"
            "defaults: []\n"
            "when:\n"
            "  - model opus: ['voice@terse']\n"
            "  - model sonnet: ['voice@warm']\n",
            {"voice": None, "voice@terse": None, "voice@warm": None},
        )

        assert check(root).errors == ()

    def test_delivery_takes_the_variant_a_lower_position_agrees_on_and_draws_a_shown_notice(
        self, tmp_path
    ):
        world = World(tmp_path)
        for stem in ("voice", "voice@terse", "voice@warm", "voice@calm"):
            world.rule(stem)
        world.manifest(
            "models: ['haiku']\n"
            "flags: ['a', 'b']\n"
            "defaults: []\n"
            "when:\n"
            "  - flag a: ['voice@terse']\n"
            "  - flag b: ['voice@warm']\n"
            "  - model haiku: ['voice@calm']\n"
        )
        world.environment["RULESETS_FLAGS"] = "a,b"

        delivery = world.start_session(model="claude-haiku-4-5")

        assert delivery.context == "text of voice@calm\n"
        (notice,) = notice_entries(world, "variant-conflict")
        assert notice["shown"]
        assert "voice" in notice["subject"]
        assert "calm" in notice["subject"]
        assert notice["subject"] in delivery.message

    def test_delivery_with_no_lower_variant_gives_the_default_form_keeps_the_rule_on_and_draws_a_notice(
        self, tmp_path
    ):
        world = World(tmp_path)
        for stem in ("voice", "voice@terse", "voice@warm"):
            world.rule(stem)
        world.manifest(
            DECLARED
            + "flags: ['a', 'b']\n"
            + "defaults: []\n"
            + "when:\n"
            + "  - flag a: ['voice@terse']\n"
            + "  - flag b: ['voice@warm']\n"
        )
        world.environment["RULESETS_FLAGS"] = "a,b"

        delivery = world.start_session()

        assert delivery.context == "text of voice\n"
        (notice,) = notice_entries(world, "variant-conflict")
        assert notice["shown"]
        assert "voice" in notice["subject"]
        assert "default form" in notice["subject"]
        assert notice["subject"] in delivery.message

    def test_two_sets_naming_the_same_variant_are_no_conflict(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['a', 'b']\n"
            "defaults: []\n"
            "when:\n"
            "  - flag a: ['voice@terse']\n"
            "  - flag b: ['voice@terse']\n",
            {"voice": None, "voice@terse": None},
        )

        composition = composed(root, context(flags=["a", "b"]))

        assert composition.conflicts == ()
        assert [(d.rule, d.variant) for d in composition.rules] == [("voice", "terse")]
        assert check(root).errors == ()

    def test_a_third_statement_striking_one_of_two_variants_leaves_no_conflict(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['a', 'b', 'c']\n"
            "defaults: []\n"
            "when:\n"
            "  - flag a: ['voice@terse']\n"
            "  - flag b: ['voice@warm']\n"
            "  - flag c: ['-voice@warm']\n",
            {"voice": None, "voice@terse": None, "voice@warm": None},
        )

        composition = composed(root, context(flags=["a", "b", "c"]))

        assert composition.conflicts == ()
        assert [(d.rule, d.variant) for d in composition.rules] == [("voice", "terse")]

    def test_a_third_block_that_applies_wherever_both_apply_and_strikes_one_variant_is_no_conflict(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['a', 'b']\n"
            "defaults: []\n"
            "when:\n"
            "  - flag a: ['voice@terse']\n"
            "  - flag b: ['voice@warm']\n"
            "  - flag a: ['-voice@warm']\n",
            {"voice": None, "voice@terse": None, "voice@warm": None},
        )

        assert composed(root, context(flags=["a", "b"])).conflicts == ()
        assert check(root).errors == ()

    def test_a_third_block_that_strikes_one_variant_only_where_its_own_flag_is_set_leaves_the_conflict_elsewhere(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['a', 'b', 'c']\n"
            "defaults: []\n"
            "when:\n"
            "  - flag a: ['voice@terse']\n"
            "  - flag b: ['voice@warm']\n"
            "  - flag c: ['-voice@warm']\n",
            {"voice": None, "voice@terse": None, "voice@warm": None},
        )

        assert [e.kind for e in check(root).errors] == ["variant-conflict"]


class TestRulesWithNoSetStatementTakeTheirDefaultForm:
    def test_an_included_rule_no_list_sets_arrives_at_its_default_form(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['*']\n",
            {"voice": None, "voice@terse": None, "sorting": None},
        )

        assert received(root, context()) == {"sorting": None, "voice": None}

    def test_a_rule_no_applying_statement_includes_stays_off(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['strict']\ndefaults: ['sorting']\nwhen:\n  - flag strict: ['voice']\n",
            {"voice": None, "sorting": None},
        )

        assert received(root, context()) == {"sorting": None}


class TestCheckWarnsAboutTheLayoutOfTheRulesetsDirectory:
    def test_a_directory_in_the_pool_draws_a_stray_directory_warning_and_a_zero_exit(
        self, tmp_path
    ):
        root = build(tmp_path, "defaults: ['*']\n", {"voice": None})
        (root / "rules" / "drafts").mkdir()

        (warning,) = check(root).warnings

        assert (warning.kind, warning.file) == ("stray-directory", root / "rules" / "drafts")
        assert main(["check", "--root", str(root)]) == 0

    def test_the_reserved_folders_beside_the_pool_draw_no_stray_warning_and_another_directory_does(
        self, tmp_path
    ):
        root = build(tmp_path, "defaults: ['*']\n", {"voice": None})
        for name in ("references", "-render", "drafts"):
            (root / name).mkdir()

        (warning,) = check(root).warnings

        assert (warning.kind, warning.file) == ("stray-directory", root / "drafts")
        assert main(["check", "--root", str(root)]) == 0

    def test_a_new_rule_file_needs_no_position_and_arrives_in_name_order(self, tmp_path):
        root = build(tmp_path, "defaults: ['*']\n", {"alpha": None, "zeta": None})
        before = check(root)
        (root / "rules" / "middle.md").write_text("text of middle\n", encoding="utf-8")

        report = check(root)

        assert report == before
        assert list(received(root, context())) == ["alpha", "middle", "zeta"]

    def test_a_body_opening_with_another_rules_marker_draws_a_misnamed_body_warning(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['*']\n",
            {"voice": "<!-- rule: sorting -->\ntext\n", "sorting": None},
        )

        (warning,) = check(root).warnings

        assert (warning.kind, warning.file) == (
            "marker-for-another-rule",
            root / "rules" / "voice.md",
        )
        assert main(["check", "--root", str(root)]) == 0


class TestCheckWarnsAboutBodySizeAndReferences:
    def test_a_body_past_the_part_budget_draws_an_oversize_warning_and_is_carried_alone(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['*']\n",
            {"alpha": None, "big": "x" * 12000 + "\n", "zeta": None},
        )

        (warning,) = check(root).warnings
        directory = read_directory(root)
        composition = compose(directory, context(), SessionState())
        parts = pack_parts(bodies_of(composition, directory.pool))

        assert (warning.kind, warning.file) == ("oversize-body", root / "rules" / "big.md")
        assert main(["check", "--root", str(root)]) == 0
        assert [[body.rule for body in part.bodies] for part in parts] == [
            ["alpha"],
            ["big"],
            ["zeta"],
        ]

    def test_a_context_whose_rules_need_more_parts_than_a_delivery_carries_draws_a_warning_naming_it(
        self, tmp_path
    ):
        stems = {f"rule-{number:02d}": "y" * 9500 + "\n" for number in range(11)}
        root = build(
            tmp_path,
            "models: ['opus', 'haiku']\n"
            "flags: ['strict', 'lint']\n"
            "defaults: []\n"
            "when:\n"
            "  - agent critic and kind delegate and model haiku and flag strict and flag lint:"
            " ['*']\n",
            stems,
        )

        warnings = [w for w in check(root).warnings if w.kind == "too-many-parts"]

        assert [w.subject for w in warnings] == [
            ContextSubject(Facts("haiku", "critic", "delegate", frozenset({"strict", "lint"})))
        ]
        assert "model haiku, agent critic, kind delegate" in finding_line(warnings[0])
        assert main(["check", "--root", str(root)]) == 0

    def test_a_context_on_a_model_no_declared_name_claims_draws_a_warning_naming_it(self, tmp_path):
        stems = {f"rule-{number:02d}": "y" * 9500 + "\n" for number in range(11)}
        root = build(
            tmp_path,
            "models: ['opus']\ndefaults: ['*']\nwhen:\n  - model opus: ['-*']\n",
            stems,
        )

        warnings = [w for w in check(root).warnings if w.kind == "too-many-parts"]

        assert [w.subject for w in warnings] == [
            ContextSubject(Facts(UNCLAIMED, ABSENT, "session", frozenset())),
            ContextSubject(Facts(UNCLAIMED, ABSENT, "delegate", frozenset())),
        ]

    def test_a_directory_with_no_manifest_draws_the_warning_for_the_every_rule_context(
        self, tmp_path
    ):
        stems = {f"rule-{number:02d}": "y" * 9500 + "\n" for number in range(11)}
        root = build(tmp_path, "", stems)
        (root / "manifest.yaml").unlink()

        warnings = [w for w in check(root).warnings if w.kind == "too-many-parts"]

        assert [w.subject for w in warnings] == [
            ContextSubject(Facts(UNCLAIMED, ABSENT, "session", frozenset())),
            ContextSubject(Facts(UNCLAIMED, ABSENT, "delegate", frozenset())),
        ]

    def test_a_directory_with_an_unparsable_manifest_draws_the_warning_for_the_every_rule_context(
        self, tmp_path
    ):
        stems = {f"rule-{number:02d}": "y" * 9500 + "\n" for number in range(11)}
        root = build(tmp_path, "defaults: [unclosed\n", stems)

        report = check(root)

        assert [e.kind for e in report.errors] == ["manifest-unparsable"]
        assert len([w for w in report.warnings if w.kind == "too-many-parts"]) == 2

    def test_a_citation_of_a_missing_file_under_references_draws_a_dangling_warning(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['*']\n",
            {"voice": "See `references/table.md` for the table.\n"},
        )

        (warning,) = check(root).warnings

        assert (warning.kind, warning.file) == ("dangling-reference", root / "rules" / "voice.md")
        assert "`references/table.md`" in warning.message
        assert main(["check", "--root", str(root)]) == 0


class TestTerms:
    def test_the_delivery_record_names_a_rule_in_the_main_sessions_delivery_and_not_in_a_haiku_delegates(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("writing-code")
        world.manifest(
            DECLARED + "defaults: ['writing-code']\nwhen:\n  - model haiku: ['-writing-code']\n"
        )
        spawn_log.append_spawn("s1", "p1", "critic", "haiku", Locations(world.config).state)

        world.start_session(model=OPUS)
        world.start_delegate("critic")

        named = {r["scope"]: [line["rule"] for line in r["rules"]] for r in world.records()}
        assert named == {"session": ["writing-code"], "delegate": []}
