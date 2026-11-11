#!/usr/bin/env python3
"""A model identifier claims the declared name an item's `model` test will match.

Serves the person who writes a config: they declare model names in `models`,
write `model opus-4-8` in a `when` key, and expect each identifier the harness
reports to reach the right item. The table at the end of design.md "Models" is
the first group below, row for row. Every case passes its own `models` list,
since the engine holds no model name.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_model_claim.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.facts.model import claim as model_claim  # noqa: E402  (path must be set first)
from rulesets.facts.model import fact as model_fact  # noqa: E402

DECLARED = ["opus", "sonnet", "haiku", "fable", "opus-4-8", "opus-4-8[1m]"]
WITHOUT_1M = [name for name in DECLARED if name != "opus-4-8[1m]"]


def claim(identifier, models):
    return model_claim.claim_model(identifier, "harness-reported", models)


class TestTheIdentifierTable:
    @pytest.mark.parametrize(
        ("identifier", "models", "name"),
        [
            ("claude-opus-5-5[1m]", WITHOUT_1M, "opus"),
            ("claude-opus-4-8", WITHOUT_1M, "opus-4-8"),
            ("claude-opus-4-8[1m]", WITHOUT_1M, "opus-4-8"),
            ("claude-opus-4-8[1m]", DECLARED, "opus-4-8[1m]"),
            ("opus", WITHOUT_1M, "opus"),
        ],
        ids=[
            "a continuation at a bracket claims for the shorter name",
            "the longest name wins",
            "a 1m identifier follows its base name",
            "a declared 1m name wins as the longer name",
            "an identifier equal to a name takes it",
        ],
    )
    def test_a_claimed_row(self, identifier, models, name):
        assert claim(identifier, models) == model_fact.Claimed(name, identifier, "harness-reported")

    def test_a_continuation_that_is_not_a_boundary_stays_unclaimed(self):
        assert claim("claude-opusx", WITHOUT_1M) == model_fact.Unclaimed(
            "claude-opusx", "harness-reported"
        )

    def test_an_undeclared_name_stays_unclaimed_until_the_config_lists_it(self):
        assert isinstance(claim("claude-nova-1", DECLARED), model_fact.Unclaimed)

        assert claim("claude-nova-1", [*DECLARED, "nova"]) == model_fact.Claimed(
            "nova", "claude-nova-1", "harness-reported"
        )

    def test_no_identifier_from_any_source_is_missing(self):
        assert claim(None, DECLARED) == model_fact.Missing()


class TestTheBoundary:
    @pytest.mark.parametrize("models", [["opus", "opus-4-8"], ["opus-4-8", "opus"]])
    def test_the_longest_name_wins_whatever_the_declared_order(self, models):
        assert model_fact.claimed_name(claim("claude-opus-4-8", models)) == "opus-4-8"

    @pytest.mark.parametrize("models", [["opus", "opus-4-8"], ["opus-4-8", "opus"]])
    def test_a_shorter_name_still_claims_other_identifiers(self, models):
        assert model_fact.claimed_name(claim("claude-opus-5-5[1m]", models)) == "opus"

    def test_a_bracket_right_after_the_name_is_a_boundary(self):
        assert model_fact.claimed_name(claim("claude-opus[1m]", ["opus"])) == "opus"

    def test_an_identifier_that_is_the_prefix_and_name_alone_is_claimed(self):
        assert model_fact.claimed_name(claim("claude-opus", ["opus"])) == "opus"

    def test_a_longer_name_does_not_claim_a_shorter_identifier(self):
        assert isinstance(claim("claude-opus", ["opus-4-8"]), model_fact.Unclaimed)

    def test_a_declared_1m_name_does_not_claim_the_identifier_without_the_suffix(self):
        assert model_fact.claimed_name(claim("claude-opus-4-8", ["opus-4-8[1m]"])) is None

    def test_an_identifier_that_does_not_open_on_the_prefix_is_claimed_only_by_equality(self):
        assert isinstance(claim("some-vendor-opus-1", ["opus"]), model_fact.Unclaimed)
        assert isinstance(claim("opus-4-8-preview", ["opus", "opus-4-8"]), model_fact.Unclaimed)


class TestTheConfigHoldsEveryName:
    def test_a_name_declared_twice_claims_as_declared_once(self):
        twice = claim("claude-sonnet-5", ["sonnet", "sonnet"])

        assert twice == claim("claude-sonnet-5", ["sonnet"])
        assert model_fact.claimed_name(twice) == "sonnet"

    def test_a_name_nobody_declares_claims_nothing(self):
        outcome = claim("claude-fable-1", ["opus", "sonnet", "haiku"])

        assert outcome == model_fact.Unclaimed("claude-fable-1", "harness-reported")

    def test_an_empty_config_claims_no_identifier(self):
        for identifier in ("claude-opus-5-5", "opus", "claude-haiku-4-5"):
            assert isinstance(claim(identifier, []), model_fact.Unclaimed)


class TestAnAliasIsClaimedAsReported:
    def test_an_alias_equal_to_a_declared_name_takes_that_name_and_keeps_its_text(self):
        assert claim("haiku", ["haiku"]) == model_fact.Claimed("haiku", "haiku", "harness-reported")

    def test_an_alias_no_declared_name_equals_stays_unclaimed_with_its_text(self):
        assert claim("haiku", ["opus"]) == model_fact.Unclaimed("haiku", "harness-reported")


class TestAnIdentifierThatIsNotAString:
    @pytest.mark.parametrize(
        ("value", "type_name"),
        [(12345, "int"), ({"id": "claude-opus-5"}, "dict"), (["opus"], "list"), (0, "int")],
    )
    def test_leaves_the_model_missing_with_its_value_and_type(self, value, type_name):
        outcome = claim(value, DECLARED)

        assert outcome == model_fact.Missing(model_fact.NotAString(value, "harness-reported"))
        assert outcome.not_a_string.type_name == type_name
        assert model_fact.claimed_name(outcome) is None

    def test_missing_names_the_source_of_the_offending_value(self):
        outcome = model_claim.claim_model(12345, "switch-target", DECLARED)

        assert outcome.source == "switch-target"

    def test_missing_for_want_of_any_source_names_the_absence(self):
        assert model_fact.Missing().source == "no-identifier"


class TestTheModelFactDerivesFactsModel:
    def test_a_claimed_identifier_gives_its_name(self):
        assert model_fact.claimed_name(claim("claude-haiku-4-5", DECLARED)) == "haiku"

    def test_an_unclaimed_identifier_and_a_missing_model_give_none(self):
        assert model_fact.claimed_name(claim("claude-nova-1", DECLARED)) is None
        assert model_fact.claimed_name(claim(None, DECLARED)) is None
