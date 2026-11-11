#!/usr/bin/env python3
"""Check warns about what is legal but probably not meant, and a warning never fails a check.

The check serves the engineer who edits rule files and a config: it tells them of a rule no
list adds, a rule whose text names another rule, a directory nothing reads, a body that marks
the wrong rule, and a citation of a file that cannot be handed
over. Each warning names its kind, subject, file, and line, and leaves the errors empty. Each
case builds its rulesets directory under `tmp_path`.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_check_warnings.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.findings import DirectorySubject, RulePairSubject, RuleSubject  # noqa: E402
from rulesets.check.run import check  # noqa: E402  (path must be set before this import)


def build(tmp_path, config=None, stems=(), bodies=None):
    """A rulesets directory with the config text, a file per stem, and any given bodies."""

    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    if config is not None:
        (root / "config.yaml").write_text(config, encoding="utf-8")
    texts = {stem: f"text of {stem}\n" for stem in stems} | (bodies or {})
    for stem, text in texts.items():
        (root / "rules" / f"{stem}.md").write_text(text, encoding="utf-8")
    return root


def warnings_of(root, kind=None):
    return [w for w in check(root).warnings if kind is None or w.kind == kind]


def subjects_of(root, kind):
    return [warning.subject for warning in warnings_of(root, kind)]


class TestARuleNoAddAnywhereIncludes:
    def test_a_rule_the_defaults_remove_and_nothing_adds_is_named_with_its_file(self, tmp_path):
        root = build(
            tmp_path,
            "defaults:\n  include: all.*\n  exclude: security\n",
            stems=["voice", "security"],
        )

        (warning,) = warnings_of(root, "never-included")
        assert warning.subject == RuleSubject("security")
        assert warning.file == root / "rules" / "security.md"

    def test_a_rule_reached_only_by_an_item_that_never_applies_is_included(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: voice\nflag never-set:\n  include: security\n",
            stems=["voice", "security"],
        )

        assert warnings_of(root, "never-included") == []

    def test_a_rule_added_by_name_is_included(self, tmp_path):
        root = build(tmp_path, "defaults: voice\n", stems=["voice"])

        assert warnings_of(root, "never-included") == []

    def test_a_rule_added_through_a_ruleset_is_included(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: tone.*\nsets:\n  tone: voice\n",
            stems=["voice"],
        )

        assert warnings_of(root, "never-included") == []

    def test_a_rule_added_through_nested_rulesets_is_included(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: outer.*\nsets:\n  outer: inner.*\n  inner: voice\n",
            stems=["voice"],
        )

        assert warnings_of(root, "never-included") == []

    def test_every_rule_is_included_by_the_spread_of_all(self, tmp_path):
        root = build(tmp_path, "defaults: all.*\n", stems=["a", "b", "c"])

        assert warnings_of(root, "never-included") == []

    def test_a_missing_config_includes_every_rule(self, tmp_path):
        root = build(tmp_path, stems=["a", "b"])

        assert warnings_of(root, "never-included") == []

    def test_a_config_that_adds_nothing_leaves_every_rule_unreached(self, tmp_path):
        root = build(tmp_path, "defaults:\n", stems=["a", "b"])

        assert subjects_of(root, "never-included") == [RuleSubject("a"), RuleSubject("b")]

    def test_an_empty_config_leaves_every_rule_unreached(self, tmp_path):
        root = build(tmp_path, "# nothing yet\n", stems=["a"])

        assert subjects_of(root, "never-included") == [RuleSubject("a")]

    def test_a_rule_with_variants_is_named_once(self, tmp_path):
        root = build(tmp_path, "defaults:\n", stems=["voice", "voice@terse", "voice@warm"])

        assert subjects_of(root, "never-included") == [RuleSubject("voice")]

    def test_a_remove_in_an_item_does_not_undo_an_add_elsewhere(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: voice\nflag quiet:\n  exclude: voice\n",
            stems=["voice"],
        )

        assert warnings_of(root, "never-included") == []

    def test_an_add_in_a_ruleset_nothing_spreads_still_includes_its_rule(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: other\nsets:\n  tone: voice\n",
            stems=["voice", "other"],
        )

        assert warnings_of(root, "never-included") == []

    def test_a_rule_removed_in_the_list_that_spreads_it_is_unreached(self, tmp_path):
        root = build(
            tmp_path,
            "defaults:\n  include: all.*\n  exclude: voice\nsets:\n  tone: other\n",
            stems=["voice", "other"],
        )

        assert subjects_of(root, "never-included") == [RuleSubject("voice")]

    def test_a_config_that_does_not_parse_draws_no_inclusion_warning(self, tmp_path):
        root = build(tmp_path, "models: [opus-4-8[1m]]\n", stems=["voice"])

        assert warnings_of(root, "never-included") == []


class TestARuleWhoseTextNamesAnotherRule:
    def test_the_warning_names_both_rules_and_the_first_match(self, tmp_path):
        root = build(
            tmp_path,
            stems=["sorting"],
            bodies={"voice": "# voice\n\nKeep it short.\nSee `sorting` before you write.\n"},
        )

        (warning,) = warnings_of(root, "cross-reference")
        assert warning.subject == RulePairSubject("voice", "sorting")
        assert warning.file == root / "rules" / "voice.md"
        assert warning.line == 4
        assert "voice" in warning.message
        assert "sorting" in warning.message

    def test_only_the_first_match_is_reported(self, tmp_path):
        root = build(
            tmp_path,
            stems=["sorting"],
            bodies={"voice": "`sorting`\n`sorting`\n`sorting`\n"},
        )

        (warning,) = warnings_of(root, "cross-reference")
        assert warning.line == 1

    def test_the_first_match_may_sit_in_a_variant(self, tmp_path):
        root = build(
            tmp_path,
            stems=["sorting", "voice"],
            bodies={"voice@terse": "<!-- rule: voice variant: terse -->\nSee `sorting`.\n"},
        )

        (warning,) = warnings_of(root, "cross-reference")
        assert warning.file == root / "rules" / "voice@terse.md"
        assert warning.line == 2

    def test_the_default_form_is_searched_before_the_variants(self, tmp_path):
        root = build(
            tmp_path,
            stems=["sorting"],
            bodies={"voice": "See `sorting`.\n", "voice@terse": "Also `sorting`.\n"},
        )

        (warning,) = warnings_of(root, "cross-reference")
        assert warning.file == root / "rules" / "voice.md"

    def test_two_rules_naming_each_other_draw_two_warnings(self, tmp_path):
        root = build(tmp_path, bodies={"a": "uses `b`\n", "b": "uses `a`\n"})

        assert subjects_of(root, "cross-reference") == [
            RulePairSubject("a", "b"),
            RulePairSubject("b", "a"),
        ]

    def test_one_rule_naming_two_others_draws_a_warning_for_each(self, tmp_path):
        root = build(tmp_path, stems=["b", "c"], bodies={"a": "`b` and `c`\n"})

        assert subjects_of(root, "cross-reference") == [
            RulePairSubject("a", "b"),
            RulePairSubject("a", "c"),
        ]

    def test_a_rule_naming_itself_draws_no_warning(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "The voice rule keeps voice short.\n"})

        assert warnings_of(root, "cross-reference") == []

    def test_a_name_inside_a_longer_hyphenated_word_is_no_match(self, tmp_path):
        root = build(
            tmp_path, stems=["code"], bodies={"a": "writing-code.md and rule code-review\n"}
        )

        assert warnings_of(root, "cross-reference") == []

    def test_a_hyphenated_rule_name_matches_whole(self, tmp_path):
        root = build(tmp_path, stems=["writing-code"], bodies={"a": "Follow `writing-code`.\n"})

        assert subjects_of(root, "cross-reference") == [RulePairSubject("a", "writing-code")]

    def test_a_hyphenated_rule_name_inside_a_longer_name_is_no_match(self, tmp_path):
        root = build(tmp_path, stems=["writing-code"], bodies={"a": "rule writing-code-review\n"})

        assert warnings_of(root, "cross-reference") == []

    def test_an_underscore_continues_a_name(self, tmp_path):
        root = build(tmp_path, stems=["voice"], bodies={"a": "rule voice_tone and _voice.md\n"})

        assert warnings_of(root, "cross-reference") == []

    def test_a_digit_continues_a_name(self, tmp_path):
        root = build(tmp_path, stems=["voice"], bodies={"a": "rule voice2 and 2voice.md\n"})

        assert warnings_of(root, "cross-reference") == []

    def test_a_rule_name_made_of_digits_and_underscores_matches_whole(self, tmp_path):
        root = build(tmp_path, stems=["rule_2"], bodies={"a": "apply `rule_2` here\n"})

        assert subjects_of(root, "cross-reference") == [RulePairSubject("a", "rule_2")]

    def test_the_match_is_case_sensitive(self, tmp_path):
        root = build(tmp_path, stems=["voice"], bodies={"a": "`Voice`, rule VOICE and Voice.md\n"})

        assert warnings_of(root, "cross-reference") == []

    def test_punctuation_ends_a_name(self, tmp_path):
        root = build(
            tmp_path, stems=["voice"], bodies={"a": "Keep (rule voice), then the voice rule.\n"}
        )

        assert subjects_of(root, "cross-reference") == [RulePairSubject("a", "voice")]

    def test_a_dot_in_a_rule_name_is_a_dot_and_nothing_wider(self, tmp_path):
        root = build(tmp_path, stems=["v1.2"], bodies={"a": "`v1x2` and rule v1x2\n"})

        assert warnings_of(root, "cross-reference") == []

    def test_a_rule_whose_text_names_no_rule_draws_no_warning(self, tmp_path):
        root = build(tmp_path, stems=["voice"], bodies={"a": "Nothing to see here.\n"})

        assert warnings_of(root, "cross-reference") == []

    def test_the_marker_line_is_no_mention(self, tmp_path):
        root = build(
            tmp_path,
            stems=["sorting"],
            bodies={"voice": "<!-- rule: sorting -->\ntext\n"},
        )

        assert warnings_of(root, "cross-reference") == []


class TestARuleNamedOnlyInAReferenceForm:
    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("Follow `sorting` first.\n", id="name-in-backticks"),
            pytest.param("Open `sorting.md` first.\n", id="backticked-file-name"),
            pytest.param("Open sorting.md first.\n", id="bare-file-name"),
            pytest.param("Open `sorting@terse.md` first.\n", id="backticked-variant-file-name"),
            pytest.param("Open sorting@terse.md first.\n", id="bare-variant-file-name"),
            pytest.param("See [the order](../rules/sorting.md).\n", id="link-to-the-file"),
            pytest.param("See [the order](sorting@terse.md#top).\n", id="link-to-a-variant-file"),
            pytest.param("Apply rule sorting first.\n", id="rule-name-bare"),
            pytest.param("Apply rule `sorting` first.\n", id="rule-name-backticked"),
            pytest.param("Apply the sorting rule first.\n", id="the-name-rule-bare"),
            pytest.param("Apply the `sorting` rule first.\n", id="the-name-rule-backticked"),
        ],
    )
    def test_each_reference_form_draws_a_warning(self, tmp_path, text):
        root = build(tmp_path, stems=["sorting"], bodies={"voice": text})

        (warning,) = warnings_of(root, "cross-reference")
        assert warning.subject == RulePairSubject("voice", "sorting")
        assert warning.line == 1

    def test_a_bare_single_word_name_draws_no_warning(self, tmp_path):
        root = build(
            tmp_path,
            stems=["reporting", "comments"],
            bodies={"voice": "Check before reporting. Search comments too.\n"},
        )

        assert warnings_of(root, "cross-reference") == []

    def test_a_bare_hyphenated_name_draws_no_warning(self, tmp_path):
        root = build(
            tmp_path,
            stems=["agent-delegation"],
            bodies={"voice": "Hand it over per agent-delegation here.\n"},
        )

        assert warnings_of(root, "cross-reference") == []

    def test_a_bare_name_in_a_variant_draws_no_warning(self, tmp_path):
        root = build(
            tmp_path,
            stems=["handoff", "voice"],
            bodies={"voice@terse": "Read the newest handoff note.\n"},
        )

        assert warnings_of(root, "cross-reference") == []

    def test_a_bare_mention_before_a_reference_form_is_not_the_first_match(self, tmp_path):
        root = build(
            tmp_path,
            stems=["sorting"],
            bodies={"voice": "sorting first.\nThen `sorting`.\n"},
        )

        (warning,) = warnings_of(root, "cross-reference")
        assert warning.line == 2

    def test_a_file_name_inside_a_longer_name_is_no_match(self, tmp_path):
        root = build(
            tmp_path,
            stems=["code"],
            bodies={"voice": "See writing-code.md, code-review.md and code.mdx.\n"},
        )

        assert warnings_of(root, "cross-reference") == []

    def test_a_phrase_around_a_longer_name_is_no_match(self, tmp_path):
        root = build(
            tmp_path,
            stems=["voice"],
            bodies={"a": "Apply rule voice-over, rule Voice, and the voice rules.\n"},
        )

        assert warnings_of(root, "cross-reference") == []


class TestAStrayDirectory:
    def test_a_directory_inside_the_pool_is_a_warning(self, tmp_path):
        root = build(tmp_path, stems=["voice"])
        (root / "rules" / "drafts").mkdir()

        (warning,) = warnings_of(root, "stray-directory")
        assert warning.subject == DirectorySubject(root / "rules" / "drafts")
        assert warning.file == root / "rules" / "drafts"
        assert check(root).errors == ()

    def test_a_directory_beside_the_pool_is_a_warning(self, tmp_path):
        root = build(tmp_path, stems=["voice"])
        (root / "renders").mkdir()

        assert subjects_of(root, "stray-directory") == [DirectorySubject(root / "renders")]

    def test_the_reserved_references_folder_is_no_stray_directory(self, tmp_path):
        root = build(tmp_path, stems=["voice"])
        (root / "references").mkdir()

        assert warnings_of(root, "stray-directory") == []


class TestABodyMarkingAnotherRule:
    def test_a_default_form_marking_another_rule_is_a_warning_at_line_one(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "<!-- rule: sorting -->\ntext\n"})

        (warning,) = warnings_of(root, "marker-for-another-rule")
        assert warning.subject == RuleSubject("voice")
        assert warning.file == root / "rules" / "voice.md"
        assert warning.line == 1

    def test_a_variant_marking_the_default_form_of_its_rule_is_a_warning(self, tmp_path):
        root = build(
            tmp_path,
            stems=["voice"],
            bodies={"voice@terse": "<!-- rule: voice -->\ntext\n"},
        )

        (warning,) = warnings_of(root, "marker-for-another-rule")
        assert warning.file == root / "rules" / "voice@terse.md"

    def test_a_variant_marking_another_variant_is_a_warning(self, tmp_path):
        root = build(
            tmp_path,
            stems=["voice"],
            bodies={"voice@terse": "<!-- rule: voice variant: warm -->\ntext\n"},
        )

        assert len(warnings_of(root, "marker-for-another-rule")) == 1

    def test_a_default_form_marking_a_variant_is_a_warning(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "<!-- rule: voice variant: terse -->\ntext\n"})

        assert len(warnings_of(root, "marker-for-another-rule")) == 1

    def test_a_variant_marking_its_own_form_draws_nothing(self, tmp_path):
        root = build(
            tmp_path,
            stems=["voice"],
            bodies={"voice@terse": "<!-- rule: voice variant: terse -->\ntext\n"},
        )

        assert warnings_of(root, "marker-for-another-rule") == []

    def test_a_default_form_marking_its_own_rule_draws_nothing(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "<!-- rule: voice -->\ntext\n"})

        assert warnings_of(root, "marker-for-another-rule") == []

    def test_a_body_with_no_marker_draws_nothing(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "text only\n"})

        assert warnings_of(root, "marker-for-another-rule") == []

    def test_a_marker_below_the_first_line_is_not_read(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "text\n<!-- rule: sorting -->\n"})

        assert warnings_of(root, "marker-for-another-rule") == []

    def test_a_marker_for_another_rule_is_no_cross_reference_warning(self, tmp_path):
        root = build(
            tmp_path, stems=["sorting"], bodies={"voice": "<!-- rule: sorting -->\ntext\n"}
        )

        assert [w.kind for w in warnings_of(root)] == ["marker-for-another-rule"]


class TestABodyCitingAFileTheCorpusCannotHandOver:
    def test_a_cited_file_that_is_not_there_dangles(self, tmp_path):
        root = build(
            tmp_path,
            bodies={"voice": "Intro.\n\nOpen `~/.claude/rulesets/references/table.md` in full.\n"},
        )

        (warning,) = warnings_of(root, "dangling-reference")
        assert warning.subject == RuleSubject("voice")
        assert warning.file == root / "rules" / "voice.md"
        assert warning.line == 3
        assert "table.md" in warning.message
        assert check(root).errors == ()

    def test_a_cited_file_that_is_there_draws_nothing(self, tmp_path):
        root = build(
            tmp_path,
            bodies={"voice": "Open `~/.claude/rulesets/references/table.md` in full.\n"},
        )
        (root / "references").mkdir()
        (root / "references" / "table.md").write_text("table\n", encoding="utf-8")

        assert warnings_of(root, "dangling-reference") == []

    def test_a_relative_citation_under_references_dangles_where_the_file_is_not_there(
        self, tmp_path
    ):
        root = build(tmp_path, bodies={"voice": "Text.\nOpen `references/table.md` in full.\n"})

        (warning,) = warnings_of(root, "dangling-reference")
        assert warning.subject == RuleSubject("voice")
        assert warning.line == 2
        assert "`references/table.md`" in warning.message
        assert warnings_of(root, "external-reference") == []

    def test_a_relative_citation_under_references_draws_nothing_where_the_file_is_there(
        self, tmp_path
    ):
        root = build(tmp_path, bodies={"voice": "Open `references/table.md` in full.\n"})
        (root / "references").mkdir()
        (root / "references" / "table.md").write_text("table\n", encoding="utf-8")

        assert check(root).warnings == ()

    def test_a_path_under_the_configuration_directory_is_not_external(self, tmp_path):
        root = build(
            tmp_path,
            bodies={"voice": "Text.\nOpen `~/.claude/references/table.md` in full.\n"},
        )

        assert warnings_of(root, "external-reference") == []
        assert warnings_of(root, "dangling-reference") == []

    def test_a_home_path_outside_the_configuration_directory_is_external(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "Text.\nSee `~/notes/x.md` first.\n"})

        (warning,) = warnings_of(root, "external-reference")
        assert warning.subject == RuleSubject("voice")
        assert warning.file == root / "rules" / "voice.md"
        assert warning.line == 2
        assert "~/notes/x.md" in warning.message
        assert warnings_of(root, "dangling-reference") == []

    def test_an_absolute_path_is_external(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "Read `/etc/hosts` before editing.\n"})

        (warning,) = warnings_of(root, "external-reference")
        assert warning.line == 1
        assert "/etc/hosts" in warning.message

    def test_a_path_holding_a_placeholder_segment_is_no_citation(self, tmp_path):
        root = build(
            tmp_path,
            bodies={
                "voice": (
                    "Write `/tmp/<skill>-<slug>.md`, `~/notes/<topic>/x.md`, "
                    "and `references/<name>.md`.\n"
                )
            },
        )

        assert warnings_of(root, "external-reference") == []
        assert warnings_of(root, "dangling-reference") == []

    def test_a_concrete_path_beside_an_unrelated_angle_bracket_is_external(self, tmp_path):
        root = build(
            tmp_path,
            bodies={"voice": "Read `/opt/data/a<b.md` and `~/notes/x>y.md` and `/opt/<a/b>.md`.\n"},
        )

        assert len(warnings_of(root, "external-reference")) == 3

    def test_a_corpus_reference_that_exists_draws_nothing(self, tmp_path):
        root = build(
            tmp_path,
            bodies={"voice": "Open `~/.claude/rulesets/references/a.md` in full.\n"},
        )
        (root / "references").mkdir()
        (root / "references" / "a.md").write_text("a\n", encoding="utf-8")

        report = check(root)

        assert report.warnings == ()
        assert report.errors == ()

    def test_a_path_inside_the_configuration_directory_but_outside_the_corpus_draws_nothing(
        self, tmp_path
    ):
        root = build(tmp_path, bodies={"voice": "See `~/.claude/rules/testing.md`.\n"})

        assert warnings_of(root, "external-reference") == []
        assert warnings_of(root, "dangling-reference") == []

    def test_a_url_is_no_path(self, tmp_path):
        root = build(
            tmp_path,
            bodies={"voice": "See `https://example.com/docs/page` and `//cdn.example.com/a/b`.\n"},
        )

        assert warnings_of(root, "external-reference") == []

    def test_inline_code_that_only_resembles_a_path_draws_nothing(self, tmp_path):
        root = build(
            tmp_path,
            bodies={
                "voice": "Type `/` or `/clear`, name `src/api/users`, run `cd ~/x`, or `~/`.\n"
            },
        )

        assert warnings_of(root, "external-reference") == []
        assert warnings_of(root, "dangling-reference") == []

    def test_a_citation_in_a_variant_names_the_variant_file(self, tmp_path):
        root = build(
            tmp_path,
            stems=["voice"],
            bodies={"voice@terse": "Open `~/.claude/rulesets/references/gone.md`.\n"},
        )

        (warning,) = warnings_of(root, "dangling-reference")
        assert warning.file == root / "rules" / "voice@terse.md"

    def test_each_citation_in_a_body_is_a_warning(self, tmp_path):
        cite = "`~/.claude/rulesets/references/{}.md`\n"
        root = build(tmp_path, bodies={"voice": cite.format("a") + cite.format("b")})

        assert [w.line for w in warnings_of(root, "dangling-reference")] == [1, 2]

    def test_a_body_citing_nothing_draws_nothing(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "No citations.\n"})

        assert warnings_of(root, "dangling-reference") == []
        assert warnings_of(root, "external-reference") == []


class TestWarningsOnly:
    def test_a_rule_no_add_includes_and_a_rule_naming_another_draw_two_warnings(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: voice\n",
            stems=["security"],
            bodies={"voice": "Run `security` first.\n"},
        )

        report = check(root)

        assert sorted(w.kind for w in report.warnings) == ["cross-reference", "never-included"]
        assert report.errors == ()

    def test_a_clean_rulesets_directory_reports_nothing(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: all.*\n",
            stems=["voice", "voice@terse", "sorting"],
            bodies={"sorting": "<!-- rule: sorting -->\nOrder things.\n"},
        )
        (root / "references").mkdir()

        report = check(root)

        assert (report.errors, report.warnings) == ((), ())

    def test_a_new_rule_file_reached_by_the_spread_of_all_draws_no_layout_finding(self, tmp_path):
        root = build(tmp_path, "defaults: all.*\n", stems=["old", "brand-new"])

        assert warnings_of(root) == []
