#!/usr/bin/env -S uv run --frozen
"""A list of references in config.yaml delivers the rules `docs/config.md` says it names.

`docs/config.md` fixes the reference forms (`voice`, `voice@terse`, `review.voice`,
`review.voice@terse`, `review.*`, `all.*`), the reserved sets (`all`, `rules`, `none`), and
exclusion, where `exclude: voice@terse` strikes a variant and leaves the rule's inclusion as it
was. Each case builds a pool and config under `tmp_path` and reads what a main session receives,
as a mapping of rule name to variant (None: the default form). A reference that resolves to
nothing is skipped while the rest of its list applies (`docs/delivery.md`), and a word in an older
form draws a `check` error that names the form to write instead (`docs/config.md`).

Run with `uv run --frozen pytest features/plugins/rulesets/tests/test_references.py`.
"""

import pathlib

import pytest
from rulesets.check.run import check
from rulesets.compose.composition import compose
from rulesets.facts.context import ABSENT, Facts
from rulesets.session.state import SessionState
from rulesets.source.directory import read_directory


def build(tmp_path, config_text, *stems) -> pathlib.Path:
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    (root / "config.yaml").write_text(config_text, encoding="utf-8")
    for stem in stems:
        (root / "rules" / f"{stem}.md").write_text(f"text of {stem}\n", encoding="utf-8")
    return root


def received(root) -> dict[str, str | None]:
    """What a main session receives, as a mapping of rule name to variant (None: default form)."""
    facts = Facts(model=ABSENT, agent=ABSENT, kind="session", flags=frozenset(), session=ABSENT)
    composition = compose(read_directory(root), facts, SessionState())
    return {d.rule: d.variant for d in composition.rules}


def delivers(config, stems, wanted, *, id) -> pytest.param:
    return pytest.param(config, stems, wanted, id=id)


DELIVERY_CASES = [
    delivers(
        "defaults: all.*\n",
        ("voice", "voice@terse", "sorting"),
        {"sorting": None, "voice": None},
        id="all-spreads-every-rule-at-its-default-form",
    ),
    delivers(
        "defaults: rules.*\n",
        ("voice", "sorting"),
        {"sorting": None, "voice": None},
        id="rules-spreads-the-pool-too",
    ),
    delivers("defaults: none.*\n", ("voice",), {}, id="none-holds-no-rule"),
    delivers(
        "defaults: rules.voice all.sorting\n",
        ("voice", "sorting"),
        {"voice": None, "sorting": None},
        id="all-and-rules-qualify-a-pool-rule",
    ),
    delivers(
        "defaults: voice@terse\n",
        ("voice", "voice@terse"),
        {"voice": "terse"},
        id="a-reference-sets-a-variant",
    ),
    delivers(
        "sets:\n  auditor: report-format@table\ndefaults: auditor.*\n",
        ("report-format", "report-format@table"),
        {"report-format": "table"},
        id="a-variant-in-a-set-travels-with-the-spread",
    ),
    delivers(
        "sets:\n  auditor: report-format@table\ndefaults: auditor.report-format\n",
        ("report-format", "report-format@table"),
        {"report-format": "table"},
        id="a-qualified-rule-carries-its-sets-variant",
    ),
    delivers(
        "sets:\n  auditor: report-format@table\ndefaults: auditor.report-format@list\n",
        ("report-format", "report-format@table", "report-format@list"),
        {"report-format": "list"},
        id="a-qualified-rule-with-its-own-variant-takes-it",
    ),
    delivers(
        "sets:\n  code: writing-code data-modeling\n  review: code.* report-format\n"
        "defaults: review.*\n",
        ("writing-code", "data-modeling", "report-format", "voice"),
        {"writing-code": None, "data-modeling": None, "report-format": None},
        id="a-spread-reaches-through-nested-sets",
    ),
    delivers(
        "sets:\n  code: writing-code\ndefaults: code.resolving-input voice\n",
        ("writing-code", "resolving-input", "voice"),
        {"voice": None},
        id="a-rule-outside-the-named-set-is-skipped",
    ),
    delivers(
        "defaults: tone voice@terse\nkind session:\n  exclude: tone\n",
        ("tone", "voice", "voice@terse"),
        {"voice": "terse"},
        id="an-exclude-in-a-block-removes-a-rule-the-defaults-add",
    ),
    delivers(
        "defaults:\n  include: tone voice@terse\n  exclude: tone\n",
        ("tone", "voice", "voice@terse"),
        {"voice": "terse"},
        id="exclude-removes-a-rule-the-same-list-adds",
    ),
    delivers(
        "defaults:\n  include: voice sorting\n  exclude: all.*\n",
        ("voice", "sorting"),
        {},
        id="excluding-all-takes-every-rule-the-list-adds",
    ),
    delivers(
        "defaults:\n  include: voice voice@terse\n  exclude: voice@terse\n",
        ("voice", "voice@terse"),
        {"voice": None},
        id="excluding-a-variant-keeps-the-rule-at-its-default-form",
    ),
    delivers(
        "defaults:\n  include: voice@terse\n  exclude: voice@terse\n",
        ("voice", "voice@terse"),
        {"voice": None},
        id="excluding-the-only-variant-added-keeps-the-rule",
    ),
    delivers(
        "defaults:\n  include: voice@terse\n  exclude: voice@warm\n",
        ("voice", "voice@terse", "voice@warm"),
        {"voice": "terse"},
        id="excluding-another-variant-leaves-the-variant-in-place",
    ),
    delivers(
        "defaults:\n  include: voice@terse voice\n  exclude: voice\n",
        ("voice", "voice@terse"),
        {},
        id="excluding-a-rule-takes-every-variant-of-it",
    ),
    delivers(
        "defaults:\n  include: all.* voice@warm\n  exclude: tone.*\nsets:\n  tone: voice@terse sorting\n",
        ("voice", "voice@terse", "voice@warm", "sorting", "writing-code"),
        {"writing-code": None},
        id="excluding-a-spread-removes-each-rule-it-reaches",
    ),
    delivers(
        "sets:\n  prose: voice tone\n  lean:\n    include: all.*\n    exclude: prose.voice\n"
        "kind session:\n  include: lean.*\n",
        ("voice", "tone", "sorting"),
        {"tone": None, "sorting": None},
        id="a-set-excluding-one-rule-of-a-spread",
    ),
    delivers(
        "defaults: a.* voice\nsets:\n  a: b.*\n  b: a.*\n",
        ("voice",),
        {"voice": None},
        id="a-cycle-among-sets-reaches-no-rule-and-the-rest-applies",
    ),
    delivers(
        "defaults: nope.* voice@brisk foo:bar sorting\n",
        ("voice", "sorting"),
        {"sorting": None},
        id="references-that-resolve-to-nothing-are-skipped",
    ),
    delivers(
        "sets:\n  reasoning: voice\nkind session:\n  include: reasoning:* sorting\n",
        ("voice", "sorting"),
        {"sorting": None},
        id="an-old-form-word-is-skipped-and-the-rest-applies",
    ),
]

OLD_FORMS = [
    pytest.param(
        "sets:\n  reasoning: voice\ndefaults: reasoning:*\n", "`reasoning.*`", id="set-with-a-colon"
    ),
    pytest.param("defaults: rules:voice\n", "`rules.voice`", id="rules-with-a-colon"),
    pytest.param("defaults: *\n", "`all.*`", id="bare-star"),
    pytest.param("defaults: -voice\n", "`exclude`", id="leading-dash"),
]


@pytest.mark.parametrize(("config", "stems", "wanted"), DELIVERY_CASES)
def test_a_list_of_references_delivers_what_the_config_reference_says(
    tmp_path, config, stems, wanted
) -> None:
    assert received(build(tmp_path, config, *stems)) == wanted


@pytest.mark.parametrize(("config", "advice"), OLD_FORMS)
def test_a_word_in_an_older_form_draws_a_check_error_naming_the_form_to_write_instead(
    tmp_path, config, advice
) -> None:
    root = build(tmp_path, config, "voice")

    messages = [error.message for error in check(root).errors]

    assert any(advice in message for message in messages), messages


def test_every_reference_form_in_every_list_draws_no_error(tmp_path) -> None:
    forms = (
        "    include: voice prose.voice voice@terse prose.voice@terse prose.*\n    exclude: tone\n"
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
