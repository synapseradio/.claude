"""The notices a delivery draws, typed by kind, and which kinds the person is shown."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from rulesets.facts.environment import flag_is_set

HOST_MANAGED_VARIABLE = "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"

type NoticeKind = Literal[
    "agent-absent",
    "fork-inherits",
    "launch-flag-undeclared",
    "model-missing",
    "model-unclaimed",
    "per-spawn-ambiguous",
    "per-spawn-unreadable",
    "provider-variable",
    "reference-skipped",
    "rule-withheld",
    "variant-conflict",
]

SHOWN: frozenset[NoticeKind] = frozenset(
    {
        "launch-flag-undeclared",
        "model-missing",
        "model-unclaimed",
        "reference-skipped",
        "rule-withheld",
        "variant-conflict",
    }
)


@dataclass(frozen=True)
class Notice:
    """A note, with what it names. `SHOWN` says whether the person sees it."""

    kind: NoticeKind
    subject: str


def provider_notices(env: Mapping[str, str]) -> tuple[Notice, ...]:
    """The notice a host-managed provider draws, named for the variable that is set.

    The harness ignores the model variables of a managed `env` block there
    (https://code.claude.com/docs/en/env-vars.md).
    """

    if flag_is_set(env, HOST_MANAGED_VARIABLE):
        return (Notice("provider-variable", HOST_MANAGED_VARIABLE),)
    return ()


def variant_conflict_notice(rule: str, variant: str | None) -> Notice:
    """The notice for a rule whose sets conflicted, naming the variant delivered."""

    delivered = "its default form" if variant is None else f"variant `{variant}`"
    return Notice(
        "variant-conflict", f"rule `{rule}` sets conflicting variants; delivered at {delivered}"
    )


def flag_notice(name: str) -> Notice:
    """The notice for a launch flag the manifest does not declare."""

    return Notice(
        "launch-flag-undeclared", f"the launch flag `{name}` is not declared and is dropped"
    )


def reference_notice(reference: str, line: int, name: str) -> Notice:
    return Notice(
        "reference-skipped",
        f"the reference `{reference}` at manifest line {line} names `{name}`, which is not declared; skipped",
    )


def withheld_notice(rule: str, error: str) -> Notice:
    return Notice("rule-withheld", f"rule `{rule}` is withheld: {error}")


def absent_agent_notice() -> Notice:
    return Notice("agent-absent", "the agent fact is absent: the session started without `--agent`")


def fork_notice() -> Notice:
    return Notice("fork-inherits", "the fork received no rules because it inherits its parent's")
