#!/usr/bin/env python3
"""A reference names rules, and a list of them expands into entries and statements.

The expander serves the engineer writing the fold and the checks: given a list as the
config wrote it, they read back which rules at which variants it adds, which excludes
and strikes it states, and which references it could not resolve, without re-deriving the
reference forms, the reserved rulesets, or the rule that removes follow adds. Each case
builds its pool and config under `tmp_path`.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_references.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.run import check  # noqa: E402  (path must be set before this import)
from rulesets.compose.composition import compose  # noqa: E402
from rulesets.facts.context import ABSENT, Facts  # noqa: E402
from rulesets.session.state import SessionState  # noqa: E402
from rulesets.source.config import parse_config  # noqa: E402
from rulesets.source.directory import read_directory  # noqa: E402
from rulesets.source.expansion import (  # noqa: E402
    Expander,
    MalformedReference,
    OldFormReference,
    RuleOutsideRuleset,
    UnknownRule,
    UnknownRuleset,
    UnknownVariant,
)
from rulesets.source.pool import read_pool  # noqa: E402
from rulesets.source.reference import (  # noqa: E402
    MalformedTarget,
    OldFormTarget,
    RuleTarget,
    SpreadTarget,
    parse_reference,
)

PATH = pathlib.Path("config.yaml")


def world(tmp_path, config_text, *stems):
    """The parsed config and an expander over a pool holding a file for each stem."""

    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    for stem in stems:
        (root / "rules" / f"{stem}.md").write_text(f"text of {stem}\n", encoding="utf-8")
    parsed = parse_config(config_text, PATH)
    pool = read_pool(root)
    return parsed, Expander(parsed.spreadable(), pool.variants_by_rule())


def build(tmp_path, config_text, *stems):
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    (root / "config.yaml").write_text(config_text, encoding="utf-8")
    for stem in stems:
        (root / "rules" / f"{stem}.md").write_text(f"text of {stem}\n", encoding="utf-8")
    return root


def received(root):
    """What a main session receives, as a mapping of rule name to variant (None: default form)."""

    facts = Facts(model=ABSENT, agent=ABSENT, kind="session", flags=frozenset(), session=ABSENT)
    composition = compose(read_directory(root), facts, SessionState())
    return {d.rule: d.variant for d in composition.rules}


def pairs(entries):
    return [(entry.rule, entry.variant) for entry in entries]


def removed(removals):
    return [(removal.rule, removal.variant) for removal in removals]


class TestReferenceForms:
    @pytest.mark.parametrize(
        ("text", "target"),
        [
            ("voice", RuleTarget("voice", None)),
            ("voice@terse", RuleTarget("voice", "terse")),
            ("prose.voice", RuleTarget("voice", None, "prose")),
            ("prose.voice@terse", RuleTarget("voice", "terse", "prose")),
            ("rules.voice", RuleTarget("voice", None)),
            ("all.voice@terse", RuleTarget("voice", "terse")),
            ("code.*", SpreadTarget("code")),
            ("all.*", SpreadTarget("all")),
            ("rules.*", SpreadTarget("rules")),
        ],
    )
    def test_each_form_names_what_it_means(self, text, target):
        reference = parse_reference(text, 7)

        assert reference.target == target
        assert reference.remove is False
        assert (reference.text, reference.line) == (text, 7)

    def test_a_reference_under_exclude_removes_and_is_quoted_with_its_key(self):
        reference = parse_reference("bash.shell-scripts", 3, remove=True)

        assert reference.target == RuleTarget("shell-scripts", None, "bash")
        assert reference.remove is True
        assert reference.quoted == "exclude bash.shell-scripts"
        assert parse_reference("planning.*", 4).quoted == "include planning.*"

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "voice@",
            "@terse",
            "foo:bar",
            ".voice",
            "prose.",
            "a.b.c",
            "code.*x",
            "code.*@terse",
            "voice@a@b",
        ],
    )
    def test_text_that_is_no_form_is_malformed_and_says_so(self, text):
        reference = parse_reference(text, 1)

        assert isinstance(reference.target, MalformedTarget)
        assert reference.target.reason

    def test_a_dash_inside_a_name_is_part_of_the_name(self):
        assert parse_reference("writing-code-review", 1).target == RuleTarget(
            "writing-code-review", None
        )

    @pytest.mark.parametrize(
        ("text", "advice"),
        [
            ("reasoning:*", "`reasoning.*`"),
            ("rules:voice", "`rules.voice`"),
            ("*", "`all.*`"),
            ("-voice", "`voice` belongs under `exclude`"),
        ],
    )
    def test_an_old_form_names_the_form_that_replaces_it(self, text, advice):
        target = parse_reference(text, 1).target

        assert isinstance(target, OldFormTarget)
        assert advice in target.advice


class TestTheOldReferenceFormsAreSkipped:
    def test_an_old_form_spread_is_skipped_and_named_while_the_rest_apply(self, tmp_path):
        parsed, expander = world(
            tmp_path,
            "sets:\n  reasoning: voice\nflag a:\n  include: reasoning:* sorting\n",
            "voice",
            "sorting",
        )

        expansion = expander.expand(parsed.blocks[0].references)

        assert pairs(expansion.entries) == [("sorting", None)]
        (problem,) = expansion.problems
        assert isinstance(problem, OldFormReference)
        assert "`reasoning.*`" in problem.advice

    def test_a_remove_sign_is_skipped_and_points_to_exclude(self, tmp_path):
        parsed, expander = world(
            tmp_path, "flag a:\n  include: -voice sorting\n", "voice", "sorting"
        )

        expansion = expander.expand(parsed.blocks[0].references)

        assert pairs(expansion.entries) == [("sorting", None)]
        assert expansion.removals == ()
        (problem,) = expansion.problems
        assert "`voice` belongs under `exclude`" in problem.advice


class TestASetQualifiedReference:
    def test_a_qualified_rule_carries_its_sets_variant(self, tmp_path):
        text = "sets:\n  auditor: report-format@table\nflag a:\n  include: auditor.report-format\n"
        parsed, expander = world(tmp_path, text, "report-format", "report-format@table")

        assert pairs(expander.expand(parsed.blocks[0].references).entries) == [
            ("report-format", "table")
        ]

    def test_a_qualified_rule_with_its_own_variant_takes_that_variant(self, tmp_path):
        text = (
            "sets:\n  auditor: report-format@table\n"
            "flag a:\n  include: auditor.report-format@list\n"
        )
        parsed, expander = world(
            tmp_path, text, "report-format", "report-format@table", "report-format@list"
        )

        assert pairs(expander.expand(parsed.blocks[0].references).entries) == [
            ("report-format", "list")
        ]

    def test_a_rule_outside_the_named_set_is_skipped_and_named(self, tmp_path):
        text = "sets:\n  code: writing-code\nflag a:\n  include: code.resolving-input voice\n"
        parsed, expander = world(tmp_path, text, "writing-code", "resolving-input", "voice")

        expansion = expander.expand(parsed.blocks[0].references)

        assert pairs(expansion.entries) == [("voice", None)]
        (problem,) = expansion.problems
        assert isinstance(problem, RuleOutsideRuleset)
        assert (problem.ruleset, problem.rule) == ("code", "resolving-input")

    def test_a_qualified_exclude_removes_the_rule_at_every_variant(self, tmp_path):
        text = (
            "sets:\n  prose: writing-prose\n"
            "flag a:\n  include: writing-prose@haiku\n  exclude: prose.writing-prose\n"
        )
        parsed, expander = world(tmp_path, text, "writing-prose", "writing-prose@haiku")

        expansion = expander.expand(parsed.blocks[0].references)

        assert expansion.entries == ()
        assert removed(expansion.removals) == [("writing-prose", None)]

    def test_a_bare_name_outside_every_set_still_names_the_rule(self, tmp_path):
        text = "sets:\n  code: writing-code\nflag a:\n  include: bash-commands\n"
        parsed, expander = world(tmp_path, text, "writing-code", "bash-commands")

        assert pairs(expander.expand(parsed.blocks[0].references).entries) == [
            ("bash-commands", None)
        ]


class TestAListIncludesAndExcludes:
    def test_a_list_including_and_excluding_one_rule_keeps_the_rest(self, tmp_path):
        root = build(
            tmp_path,
            "defaults:\n  include: tone voice@terse\n  exclude: tone\n",
            "tone",
            "voice",
            "voice@terse",
        )

        assert received(root) == {"voice": "terse"}

    def test_a_set_excluding_one_rule_of_a_spread_reaches_every_other(self, tmp_path):
        root = build(
            tmp_path,
            "sets:\n"
            "  prose: voice tone\n"
            "  lean:\n"
            "    include: all.*\n"
            "    exclude: prose.voice\n"
            "kind session:\n"
            "  include: lean.*\n",
            "voice",
            "tone",
            "sorting",
        )

        assert received(root) == {"tone": None, "sorting": None}

    def test_every_reference_form_in_every_list_draws_no_error(self, tmp_path):
        forms = (
            "    include: voice prose.voice voice@terse prose.voice@terse prose.*\n"
            "    exclude: tone\n"
        )
        root = build(
            tmp_path,
            "defaults:\n" + forms.replace("    ", "  ") + "sets:\n"
            "  prose: voice tone\n"
            "  mixed:\n" + forms + "kind session:\n" + forms.replace("    ", "  "),
            "voice",
            "voice@terse",
            "tone",
        )

        assert check(root).errors == ()


class TestReservedRulesetsCarryFixedMeanings:
    def test_all_spreads_every_pool_rule_without_a_variant(self, tmp_path):
        parsed, expander = world(
            tmp_path, "defaults: all.*\n", "voice", "voice@terse", "sorting", "writing-code"
        )

        expansion = expander.expand(parsed.defaults.references)

        assert pairs(expansion.entries) == [
            ("sorting", None),
            ("voice", None),
            ("writing-code", None),
        ]

    def test_excluding_all_takes_every_rule_the_list_adds(self, tmp_path):
        parsed, expander = world(
            tmp_path,
            ("defaults:\n  include: voice sorting\n  exclude: all.*\n"),
            "voice",
            "sorting",
        )

        expansion = expander.expand(parsed.defaults.references)

        assert expansion.entries == ()
        assert removed(expansion.removals) == [("sorting", None), ("voice", None)]

    def test_all_inside_a_ruleset_is_spread_with_the_ruleset(self, tmp_path):
        text = (
            "sets:\n"
            "  everything:\n"
            "    include: all.*\n"
            "    exclude: voice\n"
            "flag a:\n"
            "  include: everything.*\n"
        )
        parsed, expander = world(tmp_path, text, "voice", "sorting")

        expansion = expander.expand(parsed.blocks[0].references)

        assert pairs(expansion.entries) == [("sorting", None)]

    def test_rules_spreads_the_pool_too(self, tmp_path):
        parsed, expander = world(tmp_path, "defaults: rules.*\n", "voice", "sorting")

        assert pairs(expander.expand(parsed.defaults.references).entries) == [
            ("sorting", None),
            ("voice", None),
        ]

    def test_none_holds_no_rule(self, tmp_path):
        parsed, expander = world(tmp_path, "defaults: none.*\n", "voice")

        expansion = expander.expand(parsed.defaults.references)

        assert expansion.entries == ()
        assert expansion.problems == ()

    def test_a_reserved_name_declared_leaves_its_reserved_meaning(self, tmp_path):
        text = "defaults: all.*\nsets:\n  all: voice\n"
        parsed, expander = world(tmp_path, text, "voice", "sorting")

        expansion = expander.expand(parsed.defaults.references)

        assert pairs(expansion.entries) == [("sorting", None), ("voice", None)]

    def test_defaults_spreads_as_the_top_level_list_even_where_declared_under_rulesets(
        self, tmp_path
    ):
        text = "defaults: voice\nsets:\n  defaults: sorting\nflag a:\n  include: defaults.*\n"
        parsed, expander = world(tmp_path, text, "voice", "sorting")

        expansion = expander.expand(parsed.blocks[0].references)

        assert pairs(expansion.entries) == [("voice", None)]

    def test_a_rule_and_a_ruleset_may_share_a_name(self, tmp_path):
        text = (
            "sets:\n"
            "  reviewer: report-format\n"
            "flag a:\n"
            "  include: reviewer\n"
            "flag b:\n"
            "  include: reviewer.*\n"
        )
        parsed, expander = world(tmp_path, text, "reviewer", "report-format")

        bare, spread = (expander.expand(item.references) for item in parsed.blocks)

        assert pairs(bare.entries) == [("reviewer", None)]
        assert pairs(spread.entries) == [("report-format", None)]
        assert bare.problems == spread.problems == ()


class TestARulesetGroupsRulesByReference:
    def test_a_rule_in_two_rulesets_arrives_once(self, tmp_path):
        text = (
            "sets:\n"
            "  reviewer: report-format\n"
            "  auditor: report-format\n"
            "flag a:\n"
            "  include: reviewer.* auditor.*\n"
        )
        parsed, expander = world(tmp_path, text, "report-format")

        assert pairs(expander.expand(parsed.blocks[0].references).entries) == [
            ("report-format", None)
        ]

    def test_a_spread_reaches_through_nested_rulesets(self, tmp_path):
        text = (
            "sets:\n"
            "  code: writing-code data-modeling\n"
            "  review: code.* report-format\n"
            "flag a:\n"
            "  include: review.*\n"
        )
        parsed, expander = world(tmp_path, text, "writing-code", "data-modeling", "report-format")

        assert pairs(expander.expand(parsed.blocks[0].references).entries) == [
            ("writing-code", None),
            ("data-modeling", None),
            ("report-format", None),
        ]

    def test_a_variant_in_a_ruleset_travels_with_the_spread(self, tmp_path):
        text = "sets:\n  auditor: report-format@table\nflag a:\n  include: auditor.*\n"
        parsed, expander = world(tmp_path, text, "report-format", "report-format@table")

        assert pairs(expander.expand(parsed.blocks[0].references).entries) == [
            ("report-format", "table")
        ]

    def test_a_member_nobody_declares_is_skipped_and_named_while_the_rest_apply(self, tmp_path):
        text = "sets:\n  tone: voise sorting\nflag a:\n  include: tone.*\n"
        parsed, expander = world(tmp_path, text, "voice", "sorting")

        own = expander.expand(parsed.rulesets["tone"].references)
        spread = expander.expand(parsed.blocks[0].references)

        assert pairs(own.entries) == [("sorting", None)]
        assert [(p.reference.text, p.reference.line) for p in own.problems] == [("voise", 2)]
        assert isinstance(own.problems[0], UnknownRule)
        assert own.problems[0].rule == "voise"
        assert pairs(spread.entries) == [("sorting", None)]
        assert spread.problems == ()

    def test_a_spread_of_a_ruleset_nobody_declares_is_skipped_and_named(self, tmp_path):
        parsed, expander = world(tmp_path, "defaults: nope.* voice\n", "voice")

        expansion = expander.expand(parsed.defaults.references)

        assert pairs(expansion.entries) == [("voice", None)]
        assert [p.reference.text for p in expansion.problems] == ["nope.*"]
        assert isinstance(expansion.problems[0], UnknownRuleset)
        assert expansion.problems[0].ruleset == "nope"

    def test_a_variant_nobody_declares_is_skipped_and_named(self, tmp_path):
        parsed, expander = world(tmp_path, "defaults: voice@brisk sorting\n", "voice", "sorting")

        expansion = expander.expand(parsed.defaults.references)

        assert pairs(expansion.entries) == [("sorting", None)]
        assert [p.reference.text for p in expansion.problems] == ["voice@brisk"]
        assert isinstance(expansion.problems[0], UnknownVariant)
        assert (expansion.problems[0].rule, expansion.problems[0].variant) == ("voice", "brisk")

    def test_a_reference_that_is_no_form_is_skipped_and_named(self, tmp_path):
        parsed, expander = world(tmp_path, "defaults: foo:bar voice\n", "voice")

        expansion = expander.expand(parsed.defaults.references)

        assert pairs(expansion.entries) == [("voice", None)]
        assert [p.reference.text for p in expansion.problems] == ["foo:bar"]
        assert isinstance(expansion.problems[0], MalformedReference)
        assert expansion.problems[0].reason

    def test_a_rule_with_only_variants_is_still_a_declared_rule(self, tmp_path):
        parsed, expander = world(tmp_path, "defaults: tone@dry tone\n", "tone@dry")

        expansion = expander.expand(parsed.defaults.references)

        assert pairs(expansion.entries) == [("tone", "dry"), ("tone", None)]
        assert expansion.problems == ()

    def test_an_entry_names_the_reference_it_came_from(self, tmp_path):
        text = "defaults: tone.* sorting\nsets:\n  tone: voice\n"
        parsed, expander = world(tmp_path, text, "voice", "sorting")

        via_spread, direct = expander.expand(parsed.defaults.references).entries

        assert via_spread.source == parsed.defaults.references[0]
        assert direct.source == parsed.defaults.references[1]


class TestARulesetCycle:
    def test_a_spread_of_either_ruleset_in_a_cycle_reaches_no_rule(self, tmp_path):
        text = "sets:\n  a: b.*\n  b: a.*\nflag x:\n  include: a.*\nflag y:\n  include: b.*\n"
        parsed, expander = world(tmp_path, text, "voice")

        for item in parsed.blocks:
            assert expander.expand(item.references).entries == ()

    def test_a_ruleset_in_a_cycle_reaches_none_of_its_own_rules_either(self, tmp_path):
        text = "sets:\n  a: b.* voice\n  b: a.*\nflag x:\n  include: a.*\n"
        parsed, expander = world(tmp_path, text, "voice")

        assert expander.expand(parsed.blocks[0].references).entries == ()

    def test_a_ruleset_spreading_into_a_cycle_keeps_its_other_rules(self, tmp_path):
        text = "sets:\n  a: b.*\n  b: a.*\n  c: a.* sorting\nflag x:\n  include: c.*\n"
        parsed, expander = world(tmp_path, text, "sorting")

        assert pairs(expander.expand(parsed.blocks[0].references).entries) == [("sorting", None)]
        assert expander.cycle_of("c") == ()

    def test_a_ruleset_spreading_itself_is_a_cycle(self, tmp_path):
        text = "sets:\n  a: a.* voice\nflag x:\n  include: a.*\n"
        parsed, expander = world(tmp_path, text, "voice")

        assert expander.expand(parsed.blocks[0].references).entries == ()
        assert expander.cycle_of("a") == ("a",)

    def test_a_cycle_through_a_remove_is_a_cycle(self, tmp_path):
        text = "sets:\n  a:\n    exclude: b.*\n  b: a.*\nflag x:\n  include: a.*\n"
        parsed, expander = world(tmp_path, text, "voice")

        assert expander.expand(parsed.blocks[0].references).entries == ()
        assert expander.cycle_of("a") == expander.cycle_of("b") == ("a", "b")

    def test_a_cycle_through_defaults_holds_defaults_and_the_ruleset(self, tmp_path):
        text = "defaults: loop.* voice\nsets:\n  loop: defaults.*\n"
        parsed, expander = world(tmp_path, text, "voice")

        assert pairs(expander.expand(parsed.defaults.references).entries) == [("voice", None)]
        assert expander.cycle_of("defaults") == expander.cycle_of("loop") == ("defaults", "loop")

    def test_a_longer_cycle_names_every_member(self, tmp_path):
        text = "sets:\n  a: b.*\n  b: c.*\n  c: a.*\n  d: a.*\n"
        _, expander = world(tmp_path, text, "voice")

        assert expander.cycle_of("b") == ("a", "b", "c")
        assert expander.cycle_of("d") == ()

    def test_rulesets_in_no_cycle_report_none(self, tmp_path):
        _, expander = world(tmp_path, ("sets:\n  a: b.*\n  b: voice\n"), "voice")

        assert expander.cycle_of("a") == expander.cycle_of("b") == ()
        assert expander.cycle_of("nobody") == ()


class TestWithinAListRemovesApplyAfterAdds:
    def test_a_remove_before_an_add_yields_what_the_other_order_yields(self, tmp_path):
        before, expander_before = world(
            tmp_path / "x", ("defaults:\n  include: all.*\n  exclude: voice\n"), "voice", "sorting"
        )
        after, expander_after = world(
            tmp_path / "y", ("defaults:\n  include: all.*\n  exclude: voice\n"), "voice", "sorting"
        )

        assert pairs(expander_before.expand(before.defaults.references).entries) == [
            ("sorting", None)
        ]
        assert pairs(expander_after.expand(after.defaults.references).entries) == [
            ("sorting", None)
        ]

    def test_a_remove_before_a_named_add_still_removes_it(self, tmp_path):
        parsed, expander = world(
            tmp_path,
            ("defaults:\n  include: voice sorting\n  exclude: voice\n"),
            "voice",
            "sorting",
        )

        assert pairs(expander.expand(parsed.defaults.references).entries) == [("sorting", None)]

    def test_a_remove_of_a_rule_takes_every_variant_entry_for_it(self, tmp_path):
        parsed, expander = world(
            tmp_path,
            ("defaults:\n  include: voice@terse voice@warm voice\n  exclude: voice\n"),
            "voice",
            "voice@terse",
            "voice@warm",
        )

        assert expander.expand(parsed.defaults.references).entries == ()

    def test_a_remove_of_a_variant_keeps_the_rule_and_sets_no_variant(self, tmp_path):
        parsed, expander = world(
            tmp_path,
            ("defaults:\n  include: voice voice@terse\n  exclude: voice@terse\n"),
            "voice",
            "voice@terse",
        )

        assert pairs(expander.expand(parsed.defaults.references).entries) == [("voice", None)]

    def test_a_remove_of_the_only_variant_added_keeps_the_rule_bare(self, tmp_path):
        parsed, expander = world(
            tmp_path,
            ("defaults:\n  include: voice@terse\n  exclude: voice@terse\n"),
            "voice",
            "voice@terse",
        )

        assert pairs(expander.expand(parsed.defaults.references).entries) == [("voice", None)]

    def test_a_remove_of_a_variant_leaves_a_different_variant_in_place(self, tmp_path):
        parsed, expander = world(
            tmp_path,
            ("defaults:\n  include: voice@terse\n  exclude: voice@warm\n"),
            "voice",
            "voice@terse",
            "voice@warm",
        )

        assert pairs(expander.expand(parsed.defaults.references).entries) == [("voice", "terse")]

    def test_a_remove_of_a_spread_removes_each_rule_it_reaches_with_its_variants(self, tmp_path):
        text = (
            "defaults:\n"
            "  include: all.* voice@warm\n"
            "  exclude: tone.*\n"
            "sets:\n"
            "  tone: voice@terse sorting\n"
        )
        parsed, expander = world(
            tmp_path, text, "voice", "voice@terse", "voice@warm", "sorting", "writing-code"
        )

        assert pairs(expander.expand(parsed.defaults.references).entries) == [
            ("writing-code", None)
        ]

    def test_a_remove_that_names_nothing_the_list_added_removes_nothing(self, tmp_path):
        parsed, expander = world(
            tmp_path, ("defaults:\n  include: voice\n  exclude: sorting\n"), "voice", "sorting"
        )

        assert pairs(expander.expand(parsed.defaults.references).entries) == [("voice", None)]

    def test_the_same_rule_added_twice_is_one_entry(self, tmp_path):
        parsed, expander = world(tmp_path, "defaults: voice rules.voice all.*\n", "voice")

        assert pairs(expander.expand(parsed.defaults.references).entries) == [("voice", None)]

    def test_a_bare_add_and_a_variant_add_stay_two_entries(self, tmp_path):
        parsed, expander = world(tmp_path, "defaults: voice voice@terse\n", "voice", "voice@terse")

        assert pairs(expander.expand(parsed.defaults.references).entries) == [
            ("voice", None),
            ("voice", "terse"),
        ]


class TestARemoveIsAStatementOutsideASpreadRuleset:
    def test_a_remove_states_an_exclusion_of_its_rule(self, tmp_path):
        parsed, expander = world(
            tmp_path, ("model haiku:\n  exclude: writing-code\n"), "writing-code"
        )

        expansion = expander.expand(parsed.blocks[0].references)

        assert removed(expansion.removals) == [("writing-code", None)]
        assert expansion.removals[0].source == parsed.blocks[0].references[0]

    def test_a_remove_at_a_variant_states_a_strike(self, tmp_path):
        parsed, expander = world(
            tmp_path, ("flag a:\n  exclude: voice@terse\n"), "voice", "voice@terse"
        )

        assert removed(expander.expand(parsed.blocks[0].references).removals) == [
            ("voice", "terse")
        ]

    def test_a_remove_of_a_spread_states_an_exclusion_for_each_rule_it_reaches(self, tmp_path):
        text = "sets:\n  code: writing-code data-modeling\nmodel haiku:\n  exclude: code.*\n"
        parsed, expander = world(tmp_path, text, "writing-code", "data-modeling")

        expansion = expander.expand(parsed.blocks[0].references)

        assert removed(expansion.removals) == [("writing-code", None), ("data-modeling", None)]
        assert expansion.entries == ()

    def test_a_remove_the_list_also_adds_against_still_stands_as_a_statement(self, tmp_path):
        parsed, expander = world(
            tmp_path, ("defaults:\n  include: voice\n  exclude: voice\n"), "voice"
        )

        expansion = expander.expand(parsed.defaults.references)

        assert expansion.entries == ()
        assert removed(expansion.removals) == [("voice", None)]

    def test_a_remove_inside_a_spread_ruleset_only_subtracts_from_its_entries(self, tmp_path):
        text = (
            "defaults: voice\n"
            "sets:\n"
            "  lean:\n"
            "    include: all.*\n"
            "    exclude: voice\n"
            "flag a:\n"
            "  include: lean.*\n"
        )
        parsed, expander = world(tmp_path, text, "voice", "sorting", "writing-code")

        expansion = expander.expand(parsed.blocks[0].references)

        assert pairs(expansion.entries) == [("sorting", None), ("writing-code", None)]
        assert expansion.removals == ()

    def test_a_remove_that_names_nothing_declared_is_skipped_and_named(self, tmp_path):
        parsed, expander = world(
            tmp_path, ("defaults:\n  include: all.*\n  exclude: voise voice@brisk\n"), "voice"
        )

        expansion = expander.expand(parsed.defaults.references)

        assert [p.reference.text for p in expansion.problems] == ["voise", "voice@brisk"]
        assert expansion.removals == ()
        assert pairs(expansion.entries) == [("voice", None)]


class TestAListNamingTwoVariantsOfOneRule:
    def test_the_two_references_that_set_them_are_a_conflict(self, tmp_path):
        parsed, expander = world(
            tmp_path,
            ("flag a:\n  include: voice@terse voice@warm report-format\n"),
            "voice",
            "voice@terse",
            "voice@warm",
            "report-format",
        )

        expansion = expander.expand(parsed.blocks[0].references)

        (conflict,) = expansion.conflicts
        assert conflict.rule == "voice"
        assert [entry.source.text for entry in conflict.entries] == ["voice@terse", "voice@warm"]
        assert pairs(expansion.without_conflicts) == [("report-format", None)]

    def test_two_sets_that_agree_are_no_conflict(self, tmp_path):
        text = "sets:\n  tone: voice@terse\nflag a:\n  include: tone.* voice@terse\n"
        parsed, expander = world(tmp_path, text, "voice", "voice@terse")

        expansion = expander.expand(parsed.blocks[0].references)

        assert expansion.conflicts == ()
        assert pairs(expansion.entries) == [("voice", "terse")]

    def test_a_struck_variant_is_no_conflict(self, tmp_path):
        parsed, expander = world(
            tmp_path,
            ("defaults:\n  include: voice@terse voice@warm\n  exclude: voice@warm\n"),
            "voice",
            "voice@terse",
            "voice@warm",
        )

        expansion = expander.expand(parsed.defaults.references)

        assert expansion.conflicts == ()
        assert pairs(expansion.entries) == [("voice", "terse"), ("voice", None)]

    def test_a_conflict_through_a_spread_names_the_spreads_entry_for_the_rule(self, tmp_path):
        text = "sets:\n  tone: voice@terse sorting\nflag a:\n  include: tone.* voice@warm\n"
        parsed, expander = world(tmp_path, text, "voice", "voice@terse", "voice@warm", "sorting")

        expansion = expander.expand(parsed.blocks[0].references)

        (conflict,) = expansion.conflicts
        spread, direct = parsed.blocks[0].references
        assert [(e.rule, e.variant, e.source) for e in conflict.entries] == [
            ("voice", "terse", spread),
            ("voice", "warm", direct),
        ]
        assert pairs(expansion.without_conflicts) == [("sorting", None)]

    def test_statements_in_different_lists_are_no_conflict(self, tmp_path):
        text = "flag a:\n  include: voice@terse\nflag b:\n  include: voice@warm\n"
        parsed, expander = world(tmp_path, text, "voice", "voice@terse", "voice@warm")

        assert all(expander.expand(item.references).conflicts == () for item in parsed.blocks)

    def test_a_ruleset_holding_a_conflict_spreads_without_it(self, tmp_path):
        text = "sets:\n  tone: voice@terse voice@warm sorting\nflag a:\n  include: tone.*\n"
        parsed, expander = world(tmp_path, text, "voice", "voice@terse", "voice@warm", "sorting")

        outer = expander.expand(parsed.blocks[0].references)

        assert pairs(outer.entries) == [("sorting", None)]
        assert outer.conflicts == ()
        assert len(expander.expand(parsed.rulesets["tone"].references).conflicts) == 1
