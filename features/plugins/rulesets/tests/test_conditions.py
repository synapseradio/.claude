#!/usr/bin/env python3
"""A `when` item's condition tests the facts of a context and nothing else.

The conditions module serves the engineer writing check and the fold: given the text an item
is keyed on, they read back a tree of fact tests, learn from a precise error why a condition
is no condition, and evaluate the tree over a context's facts without re-deriving operator
precedence or what an absent fact means. Contexts are built in memory, so no case touches disk.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_conditions.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.facts.context import Facts  # noqa: E402
from rulesets.source.condition import (  # noqa: E402  (path must be set before this import)
    And,
    ConditionError,
    FactTest,
    Not,
    Or,
    evaluate,
    fact_tests,
    parse_condition,
)


def facts(*, model=None, agent=None, kind="session", flags=()):
    return Facts(model=model, agent=agent, kind=kind, flags=frozenset(flags))


def holds(text, **context):
    return evaluate(parse_condition(text), facts(**context))


MODEL_HAIKU = FactTest("model", "haiku")
AGENT_CRITIC = FactTest("agent", "critic")
AGENT_AUDITOR = FactTest("agent", "auditor")
FLAG_STRICT = FactTest("flag", "strict")


class TestEachFactTestNamesAFactAndAValue:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("model haiku", FactTest("model", "haiku")),
            ("agent eval-runner", FactTest("agent", "eval-runner")),
            ("kind session", FactTest("kind", "session")),
            ("kind delegate", FactTest("kind", "delegate")),
            ("kind fork", FactTest("kind", "fork")),
            ("flag voice-terse", FactTest("flag", "voice-terse")),
        ],
    )
    def test_each_fact_kind_parses_to_a_test(self, text, expected):
        assert parse_condition(text) == expected

    def test_a_model_name_may_hold_digits_and_brackets(self):
        assert parse_condition("model opus-4-8[1m]") == FactTest("model", "opus-4-8[1m]")

    def test_a_name_may_hold_underscores_and_dots(self):
        assert parse_condition("flag no_color.v2") == FactTest("flag", "no_color.v2")

    def test_any_run_of_whitespace_separates_the_words(self):
        assert parse_condition("  agent \t critic  ") == AGENT_CRITIC

    def test_a_test_matches_on_its_value_exactly(self):
        assert holds("agent critic", agent="critic") is True
        assert holds("agent critic", agent="critic-2") is False
        assert holds("agent critic", agent="Critic") is False

    def test_a_kind_test_matches_the_context_kind(self):
        assert holds("kind delegate", kind="delegate") is True
        assert holds("kind delegate", kind="session") is False
        assert holds("kind fork", kind="fork") is True
        assert holds("kind session", kind="fork") is False

    def test_a_model_test_matches_the_claimed_model_name(self):
        assert holds("model haiku", model="haiku") is True
        assert holds("model haiku", model="opus") is False

    def test_a_flag_test_is_true_where_the_flag_is_in_force(self):
        assert holds("flag strict", flags=["strict", "other"]) is True


class TestTestsCombineWithAndOrNotAndParentheses:
    def test_and_needs_both_tests(self):
        assert holds("agent critic and flag strict", agent="critic", flags=["strict"]) is True
        assert holds("agent critic and flag strict", agent="critic") is False
        assert holds("agent critic and flag strict", flags=["strict"]) is False

    def test_or_needs_either_test(self):
        assert holds("agent critic or flag strict", agent="critic") is True
        assert holds("agent critic or flag strict", flags=["strict"]) is True
        assert holds("agent critic or flag strict") is False

    def test_not_inverts_a_test(self):
        assert holds("not agent critic", agent="critic") is False
        assert holds("not agent critic", agent="auditor") is True

    def test_not_may_repeat(self):
        assert parse_condition("not not flag strict") == Not(Not(FLAG_STRICT))
        assert holds("not not flag strict", flags=["strict"]) is True
        assert holds("not not flag strict") is False

    def test_a_run_of_ands_and_a_run_of_ors_group_to_the_left(self):
        assert parse_condition("agent a and agent b and agent c") == And(
            And(FactTest("agent", "a"), FactTest("agent", "b")), FactTest("agent", "c")
        )
        assert parse_condition("agent a or agent b or agent c") == Or(
            Or(FactTest("agent", "a"), FactTest("agent", "b")), FactTest("agent", "c")
        )


class TestOperatorPrecedence:
    def test_and_binds_tighter_than_or(self):
        parsed = parse_condition("agent critic or agent auditor and flag strict")

        assert parsed == Or(AGENT_CRITIC, And(AGENT_AUDITOR, FLAG_STRICT))

    def test_and_binds_tighter_than_or_when_or_comes_second(self):
        parsed = parse_condition("agent auditor and flag strict or agent critic")

        assert parsed == Or(And(AGENT_AUDITOR, FLAG_STRICT), AGENT_CRITIC)

    def test_a_critic_without_the_flag_passes_where_or_is_the_looser_operator(self):
        text = "agent critic or agent auditor and flag strict"

        assert holds(text, agent="critic") is True
        assert holds(text, agent="auditor") is False
        assert holds(text, agent="auditor", flags=["strict"]) is True

    def test_not_binds_tighter_than_and(self):
        parsed = parse_condition("not agent critic and flag strict")

        assert parsed == And(Not(AGENT_CRITIC), FLAG_STRICT)

    def test_a_critic_without_the_flag_fails_where_not_binds_one_test(self):
        text = "not agent critic and flag strict"

        assert holds(text, agent="critic") is False
        assert holds(text, agent="auditor", flags=["strict"]) is True
        assert holds(text, agent="critic", flags=["strict"]) is False

    def test_not_binds_tighter_than_or(self):
        assert parse_condition("not agent critic or flag strict") == Or(
            Not(AGENT_CRITIC), FLAG_STRICT
        )


class TestParenthesesGroup:
    def test_parentheses_override_precedence(self):
        parsed = parse_condition("(agent critic or agent auditor) and flag strict")

        assert parsed == And(Or(AGENT_CRITIC, AGENT_AUDITOR), FLAG_STRICT)

    def test_a_critic_with_the_flag_not_in_force_is_false(self):
        text = "(agent critic or agent auditor) and flag strict"

        assert holds(text, agent="critic") is False
        assert holds(text, agent="critic", flags=["strict"]) is True

    def test_not_over_a_group_inverts_the_group(self):
        text = "not (agent critic or agent auditor)"

        assert parse_condition(text) == Not(Or(AGENT_CRITIC, AGENT_AUDITOR))
        assert holds(text, agent="auditor") is False
        assert holds(text, agent="writer") is True

    def test_parentheses_need_no_space_beside_them(self):
        assert parse_condition("(agent critic)and(flag strict)") == And(AGENT_CRITIC, FLAG_STRICT)

    def test_parentheses_nest(self):
        text = "((agent critic))"

        assert parse_condition(text) == AGENT_CRITIC


class TestATestOverAnAbsentFactIsFalseAndItsNegationTrue:
    def test_a_model_test_with_no_model_is_false(self):
        assert holds("model haiku", model=None) is False

    def test_a_negated_model_test_with_no_model_is_true(self):
        assert holds("not model haiku", model=None) is True

    def test_a_negation_over_a_missing_model_lets_the_rest_of_the_condition_decide(self):
        text = "agent critic and not model haiku"

        assert holds(text, agent="critic", model=None) is True
        assert holds(text, agent="critic", model="opus") is True
        assert holds(text, agent="critic", model="haiku") is False

    def test_an_agent_test_in_a_plain_main_session_is_false(self):
        assert holds("agent critic", agent=None) is False

    def test_a_negated_agent_test_in_a_plain_main_session_is_true(self):
        assert holds("not agent critic", agent=None) is True


class TestFlagsAreNeverAbsent:
    def test_a_flag_not_in_force_is_false(self):
        assert holds("flag strict", flags=[]) is False

    def test_a_negated_flag_not_in_force_is_true(self):
        assert holds("not flag strict", flags=[]) is True

    def test_a_misspelled_flag_is_false_in_every_context(self):
        for context in (
            {},
            {"flags": ["strict"]},
            {"agent": "critic", "kind": "delegate"},
            {"model": "haiku", "flags": ["strict", "voice-terse"]},
        ):
            assert holds("flag stirct", **context) is False

    def test_a_negated_flag_in_force_is_false(self):
        assert holds("not flag strict", flags=["strict"]) is False


class TestAConditionTestsFactsOnly:
    @pytest.mark.parametrize(
        ("text", "named"),
        [
            ("project amboss", "project"),
            ("env CI", "env"),
            ("file README.md", "file"),
            ("branch main", "branch"),
            ("Model haiku", "Model"),
            ("agent critic and project amboss", "project"),
            ("not env CI", "env"),
        ],
    )
    def test_a_test_of_anything_but_a_fact_is_an_error_naming_it(self, text, named):
        with pytest.raises(ConditionError) as failure:
            parse_condition(text)

        assert named in str(failure.value)

    def test_the_error_lists_the_facts_a_condition_can_test(self):
        with pytest.raises(ConditionError) as failure:
            parse_condition("project amboss")

        for fact in ("model", "agent", "kind", "flag"):
            assert fact in str(failure.value)

    def test_a_kind_other_than_session_delegate_or_fork_is_an_error_naming_it(self):
        with pytest.raises(ConditionError) as failure:
            parse_condition("kind subagent")

        assert "subagent" in str(failure.value)


class TestTextThatIsNoConditionIsAnError:
    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "(agent critic and flag strict",
            "agent critic and flag strict)",
            "()",
            "agent critic and",
            "or agent critic",
            "and",
            "not",
            "agent critic not flag strict",
            "agent critic flag strict",
            "agent critic AND flag strict",
            "agent critic and and flag strict",
            "model",
            "flag",
            "agent and",
            "flag (strict)",
            "agent not",
            "agent critic, flag strict",
        ],
    )
    def test_each_malformed_text_raises(self, text):
        with pytest.raises(ConditionError):
            parse_condition(text)

    def test_an_error_carries_a_message_a_person_can_act_on(self):
        with pytest.raises(ConditionError) as failure:
            parse_condition("(agent critic and flag strict")

        assert failure.value.reason
        assert "(agent critic and flag strict" not in failure.value.reason
        assert str(failure.value) == failure.value.reason

    def test_an_unbalanced_open_parenthesis_says_so(self):
        with pytest.raises(ConditionError) as failure:
            parse_condition("(agent critic and flag strict")

        assert "parenthes" in failure.value.reason

    def test_an_empty_condition_says_so(self):
        with pytest.raises(ConditionError) as failure:
            parse_condition("")

        assert "empty" in failure.value.reason


class TestFactTestsListWhatACheckMustVerify:
    def test_every_test_in_the_condition_comes_back_in_reading_order(self):
        parsed = parse_condition("agent critic and not (model haiku or flag strict) or kind fork")

        assert fact_tests(parsed) == (
            AGENT_CRITIC,
            MODEL_HAIKU,
            FLAG_STRICT,
            FactTest("kind", "fork"),
        )

    def test_a_single_test_lists_itself(self):
        assert fact_tests(parse_condition("model hiaku")) == (FactTest("model", "hiaku"),)

    def test_a_test_written_twice_comes_back_twice(self):
        parsed = parse_condition("model haiku or not model haiku")

        assert fact_tests(parsed) == (MODEL_HAIKU, MODEL_HAIKU)
