#!/usr/bin/env python3
"""A block's condition tests the facts of a context and nothing else.

`docs/config.md` fixes the language: a condition combines fact tests with `and`, `or`, `not`, and
parentheses; several values after one kind hold where any of them holds, so `agent critic
thinkies` reads as `agent critic or agent thinkies` and `not model haiku sonnet` holds only on a
model that is neither; `not` binds tighter than `and`, and `and` tighter than `or`; `kind any`
holds in every session and delegate; and a test of a project, a file, or an environment variable
is a `check` error. Contexts are built in memory, so the evaluation cases touch no disk.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_conditions.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.compose.composition import compose  # noqa: E402
from rulesets.facts.context import ABSENT, Facts  # noqa: E402
from rulesets.session.state import SessionState  # noqa: E402
from rulesets.source.condition import (  # noqa: E402  (path must be set before this import)
    ConditionError,
    Truth,
    evaluate,
    parse_condition,
)
from rulesets.source.directory import read_directory  # noqa: E402

T, F, U = Truth.TRUE, Truth.FALSE, Truth.UNKNOWN


def facts(*, model=None, agent=None, kind="session", flags=()) -> Facts:
    return Facts(
        model=ABSENT if model is None else model,
        agent=ABSENT if agent is None else agent,
        kind=kind,
        flags=frozenset(flags),
    )


def row(text, expected, *, id, **context) -> pytest.param:
    return pytest.param(text, context, expected, id=id)


EVALUATION_CASES = [
    row("agent critic", T, agent="critic", id="agent-test-matches"),
    row("agent critic", F, agent="critic-2", id="agent-test-matches-its-value-exactly"),
    row("agent critic", F, agent="Critic", id="agent-test-is-case-sensitive"),
    row("kind delegate", T, kind="delegate", id="kind-delegate-in-a-delegate"),
    row("kind delegate", F, kind="session", id="kind-delegate-in-a-session"),
    row("model haiku", T, model="haiku", id="model-test-matches"),
    row("model haiku", F, model="opus", id="model-test-fails-on-another-model"),
    row("flag strict", T, flags=["strict", "other"], id="flag-in-force"),
    row("flag strict", F, id="flag-not-in-force"),
    row("not flag strict", T, id="negated-flag-not-in-force"),
    row("not flag strict", F, flags=["strict"], id="negated-flag-in-force"),
    row(
        "flag stirct", F, model="haiku", flags=["strict"], id="misspelled-flag-is-false-everywhere"
    ),
    row("  agent \t critic  ", T, agent="critic", id="any-run-of-whitespace-separates-words"),
    row("agent critic and flag strict", T, agent="critic", flags=["strict"], id="and-with-both"),
    row("agent critic and flag strict", F, agent="critic", id="and-without-the-second"),
    row(
        "agent critic and flag strict",
        F,
        agent="auditor",
        flags=["strict"],
        id="and-without-the-first",
    ),
    row("agent critic or flag strict", T, agent="critic", id="or-with-the-first"),
    row("agent critic or flag strict", T, flags=["strict"], id="or-with-the-second"),
    row("agent critic or flag strict", F, agent="auditor", id="or-with-neither"),
    row("not agent critic", F, agent="critic", id="not-inverts-true"),
    row("not agent critic", T, agent="auditor", id="not-inverts-false"),
    row("not not flag strict", T, flags=["strict"], id="not-may-repeat"),
    row(
        "agent critic or agent auditor and flag strict",
        T,
        agent="critic",
        id="and-binds-tighter-than-or-critic-alone",
    ),
    row(
        "agent critic or agent auditor and flag strict",
        F,
        agent="auditor",
        id="and-binds-tighter-than-or-auditor-without-the-flag",
    ),
    row(
        "agent critic or agent auditor and flag strict",
        T,
        agent="auditor",
        flags=["strict"],
        id="and-binds-tighter-than-or-auditor-with-the-flag",
    ),
    row(
        "agent auditor and flag strict or agent critic",
        T,
        agent="critic",
        id="and-binds-tighter-than-or-when-or-comes-second",
    ),
    row(
        "not agent critic and flag strict", F, agent="critic", id="not-binds-one-test-critic-alone"
    ),
    row(
        "not agent critic and flag strict",
        F,
        agent="critic",
        flags=["strict"],
        id="not-binds-one-test-critic-with-the-flag",
    ),
    row(
        "not agent critic and flag strict",
        T,
        agent="auditor",
        flags=["strict"],
        id="not-binds-one-test-auditor-with-the-flag",
    ),
    row(
        "not agent critic or flag strict",
        T,
        agent="critic",
        flags=["strict"],
        id="not-binds-tighter-than-or",
    ),
    row(
        "(agent critic or agent auditor) and flag strict",
        F,
        agent="critic",
        id="parentheses-override-precedence-without-the-flag",
    ),
    row(
        "(agent critic or agent auditor) and flag strict",
        T,
        agent="critic",
        flags=["strict"],
        id="parentheses-override-precedence-with-the-flag",
    ),
    row("not (agent critic or agent auditor)", F, agent="auditor", id="not-over-a-group-in-it"),
    row("not (agent critic or agent auditor)", T, agent="writer", id="not-over-a-group-outside-it"),
    row(
        "(agent critic)and(flag strict)",
        T,
        agent="critic",
        flags=["strict"],
        id="parentheses-need-no-space",
    ),
    row("((agent critic))", T, agent="critic", id="parentheses-nest"),
    row("agent critic thinkies", T, agent="critic", id="several-values-first"),
    row("agent critic thinkies", T, agent="thinkies", id="several-values-second"),
    row("agent critic thinkies", F, agent="designer", id="several-values-neither"),
    row("not model haiku sonnet", F, model="sonnet", id="not-applies-to-the-whole-group-in-it"),
    row("not model haiku sonnet", T, model="opus", id="not-applies-to-the-whole-group-outside-it"),
    row(
        "agent critic auditor and flag strict",
        T,
        agent="auditor",
        flags=["strict"],
        id="and-joins-a-group-as-one-test",
    ),
    row("kind any", T, kind="session", id="kind-any-in-a-session"),
    row("kind any", T, kind="delegate", id="kind-any-in-a-delegate"),
    row(
        "model haiku and kind any",
        T,
        model="haiku",
        kind="delegate",
        id="kind-any-follows-the-model",
    ),
    row(
        "model haiku and kind any",
        F,
        model="opus",
        kind="delegate",
        id="kind-any-follows-the-model-other",
    ),
    row("model opus-4-8[1m]", T, model="opus-4-8[1m]", id="model-name-with-digits-and-brackets"),
    row("model haiku", U, id="model-test-with-no-model-is-unknown"),
    row("not model haiku", U, id="negated-model-test-with-no-model-is-unknown"),
    row("agent critic", U, id="agent-test-in-a-main-session-is-unknown"),
    row(
        "agent critic and not model haiku",
        U,
        agent="critic",
        id="unknown-model-leaves-the-rest-to-decide",
    ),
    row(
        "agent critic and not model haiku",
        F,
        agent="auditor",
        id="rest-decides-false-despite-unknown-model",
    ),
]

NOT_CONDITIONS = [
    pytest.param("project amboss", "project", id="project"),
    pytest.param("env CI", "env", id="environment-variable"),
    pytest.param("file README.md", "file", id="file"),
    pytest.param("agent critic and project amboss", "project", id="project-inside-a-condition"),
    pytest.param("kind sometimes", "sometimes", id="kind-no-context-carries"),
    pytest.param("(agent critic and flag strict", None, id="unbalanced-parenthesis"),
    pytest.param("agent critic and", None, id="dangling-operator"),
    pytest.param("", None, id="empty"),
    pytest.param("model", None, id="fact-with-no-value"),
    pytest.param("agent critic flag strict", None, id="fact-name-among-the-values"),
]


@pytest.mark.parametrize(("text", "context", "expected"), EVALUATION_CASES)
def test_a_condition_holds_or_not_for_a_contexts_facts(text, context, expected) -> None:
    assert evaluate(parse_condition(text), facts(**context)) is expected


@pytest.mark.parametrize(("text", "named"), NOT_CONDITIONS)
def test_text_that_tests_no_fact_is_a_condition_error(text, named) -> None:
    with pytest.raises(ConditionError) as failure:
        parse_condition(text)

    if named is not None:
        assert named in str(failure.value)


def test_a_block_keyed_on_two_agents_reaches_each_and_no_other(tmp_path) -> None:
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    (root / "rules" / "security-pass.md").write_text("text\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "agent critic thinkies:\n  include: security-pass\n", encoding="utf-8"
    )

    def receives(agent) -> list[str]:
        context = facts(agent=agent, kind="delegate")
        return [d.rule for d in compose(read_directory(root), context, SessionState()).rules]

    assert receives("critic") == ["security-pass"]
    assert receives("thinkies") == ["security-pass"]
    assert receives("designer") == []
