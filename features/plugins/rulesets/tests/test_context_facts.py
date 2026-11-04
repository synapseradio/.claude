#!/usr/bin/env python3
"""A context carries facts, and a block's condition tests them: known, false, or unknown.

Serves the engineer who writes a manifest keyed on model, agent, flag, and session, and the
person whose sessions and delegates receive the result: a declared model name claims the
identifiers it prefixes, a block takes the rank of its highest fact, an unclaimed model tests
false, and a missing one tests unknown so that no block keyed on it applies. Integration cases
run the hook entries over a configuration directory under `tmp_path`; unit cases claim
identifiers and evaluate conditions in memory.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_context_facts.py`.
"""

import pathlib
import sys

import pytest
from delivery_world import DECLARED, World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.report_format import report_lines  # noqa: E402
from rulesets.check.run import check  # noqa: E402
from rulesets.facts.context import ABSENT, UNCLAIMED, Facts  # noqa: E402
from rulesets.facts.model import claim as model_claim  # noqa: E402
from rulesets.facts.model import fact as model_fact  # noqa: E402
from rulesets.source.condition import evaluate, parse_condition  # noqa: E402


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def pin_agent_model(world, agent, model):
    """An agent definition under the configuration directory that pins its model."""

    path = world.config / "agents" / f"{agent}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {agent}\nmodel: {model}\n---\nbody\n", encoding="utf-8")


def received(delivery, stems):
    """The stems whose body the delivery carries, in the order given."""

    return [stem for stem in stems if f"text of {stem}\n" in delivery.context]


def claim(identifier, models):
    return model_claim.claim_model(identifier, "harness-reported", models, {})


def truth(text, *, model="missing", agent=None, flags=()):
    """The condition's value as a name: TRUE, FALSE, or UNKNOWN.

    `model` is a claimed name, "unclaimed", or "missing".
    """

    standing = {"missing": ABSENT, "unclaimed": UNCLAIMED}.get(model, model)
    facts = Facts(
        model=standing,
        agent=ABSENT if agent is None else agent,
        kind="session",
        flags=frozenset(flags),
    )
    return evaluate(parse_condition(text), facts).name


def report_for(world):
    return "\n".join(report_lines(check(world.rulesets)))


class TestFactKindsAndTheirRanks:
    def test_each_fact_kinds_block_beats_the_exclude_one_rank_below_it(self, world):
        stems = ["security-pass", "voice", "tone", "sorting"]
        for stem in stems:
            world.rule(stem)
        world.manifest(
            "models: ['haiku']\n"
            "flags: ['strict']\n"
            "defaults: ['-security-pass']\n"
            "when:\n"
            "  - model haiku: ['security-pass', '-voice']\n"
            "  - agent critic: ['voice', '-tone']\n"
            "  - flag strict: ['tone', '-sorting']\n"
            "  - session abc123: ['sorting']\n"
        )
        pin_agent_model(world, "critic", "haiku")
        world.environment["RULESETS_FLAGS"] = "strict"

        delivery = world.start_delegate("critic", session_id="abc123")

        assert received(delivery, stems) == stems

    def test_a_block_takes_the_rank_of_its_highest_fact(self, world):
        world.rule("security-pass")
        world.manifest(
            "models: ['haiku']\n"
            "when:\n"
            "  - model haiku: ['-security-pass']\n"
            "  - model haiku and agent critic: ['security-pass']\n"
        )
        pin_agent_model(world, "critic", "haiku")

        delivery = world.start_delegate("critic")

        assert received(delivery, ["security-pass"]) == ["security-pass"]


class TestEachFactKindHasADefinedValue:
    def test_a_delegate_on_a_claimed_model_has_the_model_agent_and_kind_facts(self, world):
        world.rule("voice")
        world.manifest("models: ['haiku']\ndefaults: ['voice']\n")
        pin_agent_model(world, "critic", "haiku")

        world.start_delegate("critic")

        (record,) = world.records()
        assert (record["model"]["name"], record["agent"], record["kind"]) == (
            "haiku",
            "critic",
            "delegate",
        )

    def test_an_identifier_no_declared_name_claims_is_the_model_fact(self):
        fact = claim("claude-nova-1", ["opus", "haiku"])

        assert fact == model_fact.Unclaimed("claude-nova-1", "harness-reported")


class TestConditionsCombineFactTests:
    def test_and_binds_tighter_than_or_so_a_critic_without_the_flag_receives_the_rule(self, world):
        world.rule("security-pass")
        world.manifest(
            "flags: ['strict']\n"
            "defaults: []\n"
            "when:\n"
            "  - agent critic or agent auditor and flag strict: ['security-pass']\n"
        )

        delivery = world.start_delegate("critic")

        assert received(delivery, ["security-pass"]) == ["security-pass"]

    def test_parentheses_group_so_a_critic_without_the_flag_does_not_apply(self, world):
        world.rule("security-pass")
        world.manifest(
            "flags: ['strict']\n"
            "defaults: []\n"
            "when:\n"
            "  - (agent critic or agent auditor) and flag strict: ['security-pass']\n"
        )

        delivery = world.start_delegate("critic")

        assert received(delivery, ["security-pass"]) == []
        assert truth("(agent critic or agent auditor) and flag strict", agent="critic") == "FALSE"

    def test_a_negated_model_test_holds_for_a_critic_on_another_claimed_model(self):
        assert truth("agent critic and not model haiku", agent="critic", model="opus") == "TRUE"


class TestConditionsTestFactsOnly:
    def test_a_project_test_is_a_check_error_and_the_block_applies_nowhere(self, world):
        world.rule("voice")
        world.manifest("defaults: []\nwhen:\n  - project amboss: ['voice']\n")

        report = report_for(world)

        assert "error" in report
        assert "`project amboss`" in report
        assert received(world.start_session(), ["voice"]) == []
        assert received(world.start_delegate("critic"), ["voice"]) == []

    def test_an_environment_variable_test_is_a_check_error_naming_the_condition(self, world):
        world.rule("voice")
        world.manifest("when:\n  - env CI: ['voice']\n")

        report = report_for(world)

        assert "error" in report
        assert "`env CI`" in report

    def test_unbalanced_parentheses_are_a_check_error_naming_the_condition(self, world):
        world.rule("voice")
        world.manifest("when:\n  - (agent critic and flag strict: ['voice']\n")

        report = report_for(world)

        assert "error" in report
        assert "`(agent critic and flag strict`" in report


class TestAConditionNamingAnUndeclaredModelOrFlagIsSkippedWithANotice:
    def test_a_misspelled_model_is_a_check_error_and_delivery_skips_the_block_with_a_notice(
        self, world
    ):
        world.rule("voice")
        world.rule("tone")
        world.manifest(
            "models: ['haiku']\n"
            "defaults: []\n"
            "when:\n"
            "  - model hiaku: ['tone']\n"
            "  - model haiku: ['voice']\n"
        )

        report = report_for(world)
        delivery = world.start_session(model="claude-haiku-4-5")

        assert "error" in report
        assert "hiaku" in report
        assert received(delivery, ["voice", "tone"]) == ["voice"]
        assert delivery.message is not None
        assert "hiaku" in delivery.message
        (record,) = world.records()
        assert record["withheld"] == []

    def test_an_agent_nobody_declares_is_no_check_error(self, world):
        world.rule("voice")
        world.manifest("when:\n  - agent eval-runner: ['voice']\n")

        assert check(world.rulesets).errors == ()


class TestADeclaredModelNameClaimsTheIdentifiersItPrefixes:
    def test_the_longest_declared_name_wins(self):
        fact = claim("claude-opus-4-8", ["opus", "opus-4-8"])

        assert model_fact.claimed_name(fact) == "opus-4-8"

    def test_a_shorter_name_still_claims_other_identifiers(self):
        fact = claim("claude-opus-5-5[1m]", ["opus", "opus-4-8"])

        assert model_fact.claimed_name(fact) == "opus"

    def test_a_continuation_that_is_not_a_boundary_claims_nothing(self):
        assert isinstance(claim("claude-opusx", ["opus"]), model_fact.Unclaimed)

    def test_an_alias_equal_to_a_declared_name_takes_that_name(self):
        fact = claim("haiku", ["haiku"])

        assert model_fact.claimed_name(fact) == "haiku"


class TestAnIdentifierEndingIn1mFollowsItsBaseNameUnlessA1mNameIsDeclared:
    def test_a_declared_1m_name_wins_as_the_longer_name(self):
        fact = claim("claude-opus-4-8[1m]", ["opus-4-8", "opus-4-8[1m]"])

        assert model_fact.claimed_name(fact) == "opus-4-8[1m]"


class TestAModelNameDeclaredTwiceIsNotAnError:
    def test_a_name_declared_twice_draws_no_check_error_and_claims_as_once(self, world):
        world.rule("voice")
        world.manifest("models: ['sonnet', 'sonnet']\ndefaults: ['voice']\n")

        once = claim("claude-sonnet-5-5", ["sonnet"])
        twice = claim("claude-sonnet-5-5", ["sonnet", "sonnet"])

        assert check(world.rulesets).errors == ()
        assert model_fact.claimed_name(twice) == "sonnet"
        assert twice == once


class TestTheEngineHoldsNoModelName:
    def test_a_manifest_declaring_no_model_claims_nothing(self):
        for identifier in ("claude-opus-4-8", "claude-haiku-5"):
            assert isinstance(claim(identifier, []), model_fact.Unclaimed)

    def test_declaring_a_new_model_name_gives_sessions_on_it_the_rules_declared_for_it(self, world):
        world.rule("fresh")
        world.manifest("models: ['opus-5']\ndefaults: []\nwhen:\n  - model opus-5: ['fresh']\n")

        on_new = world.start_session(model="claude-opus-5-0")
        on_old = world.start_session(model="claude-opus-4-8", session_id="s2")

        assert received(on_new, ["fresh"]) == ["fresh"]
        assert received(on_old, ["fresh"]) == []
        assert world.records("s1")[0]["model"]["name"] == "opus-5"


class TestAnUnclaimedIdentifierTestsFalseAndAMissingOneTestsUnknown:
    def test_a_non_claude_identifier_receives_the_defaults_and_the_negated_block(self, world):
        stems = ["writing-code", "security-pass", "voice"]
        for stem in stems:
            world.rule(stem)
        world.manifest(
            "models: ['haiku']\n"
            "defaults: ['writing-code']\n"
            "when:\n"
            "  - model haiku: ['security-pass']\n"
            "  - not model haiku: ['voice']\n"
        )

        delivery = world.start_session(model="glm-5")

        assert received(delivery, stems) == ["writing-code", "voice"]
        assert delivery.message is not None
        assert "glm-5" in delivery.message
        assert "glm-5" not in delivery.context

    def test_a_claude_model_before_its_name_is_declared_draws_a_shown_notice(self, world):
        world.rule("writing-code")
        world.manifest("models: ['haiku']\ndefaults: ['writing-code']\n")

        delivery = world.start_session(model="claude-nova-1")

        assert received(delivery, ["writing-code"]) == ["writing-code"]
        assert delivery.message is not None
        assert "claude-nova-1" in delivery.message
        assert "claude-nova-1" not in delivery.context
        (record,) = world.records()
        assert record["model"]["state"] == "unclaimed"

    def test_an_unclaimed_model_tests_false_and_its_negation_true(self):
        assert truth("model haiku", model="unclaimed") == "FALSE"
        assert truth("not model haiku", model="unclaimed") == "TRUE"


class TestAMissingModelIdentifierMakesEveryModelTestUnknown:
    def test_a_session_with_no_identifier_source_has_a_missing_model_and_a_shown_notice(
        self, world
    ):
        world.rule("voice")
        world.manifest(DECLARED + "defaults: []\nwhen:\n  - not model haiku: ['voice']\n")

        delivery = world.start_session(model=None)

        assert received(delivery, ["voice"]) == []
        assert delivery.message is not None
        assert "no model identifier was available" in delivery.message
        (record,) = world.records()
        assert record["model"]["state"] == "missing"

    def test_a_missing_model_makes_a_test_and_its_negation_unknown(self):
        assert truth("model haiku", model="missing") == "UNKNOWN"
        assert truth("not model haiku", model="missing") == "UNKNOWN"


class TestDeliveryCompletesWhenTheModelIsUnclaimedOrMissing:
    def test_a_block_testing_no_unknown_fact_applies_while_the_model_is_missing(self, world):
        world.rule("voice")
        world.manifest("flags: ['strict']\ndefaults: []\nwhen:\n  - flag strict: ['voice']\n")
        world.environment["RULESETS_FLAGS"] = "strict"

        delivery = world.start_session(model=None)

        assert received(delivery, ["voice"]) == ["voice"]
        (record,) = world.records()
        assert record["model"]["state"] == "missing"
