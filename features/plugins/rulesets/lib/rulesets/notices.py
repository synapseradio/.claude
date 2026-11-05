"""The notices a delivery draws, typed by kind, and which kinds the person is shown."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from rulesets.facts.environment import flag_is_set
from rulesets.source.undeclared import Undeclared

HOST_MANAGED_VARIABLE = "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"

type NoticeKind = Literal[
    "agent-absent",
    "block-skipped",
    "fork-inherits",
    "fork-parent-missing",
    "launch-flag-undeclared",
    "model-missing",
    "model-unclaimed",
    "per-spawn-ambiguous",
    "per-spawn-unreadable",
    "provider-variable",
    "reference-skipped",
    "rule-left-out",
    "rule-withheld",
    "tools-absent",
    "variant-conflict",
]

SHOWN: frozenset[NoticeKind] = frozenset(
    {
        "block-skipped",
        "fork-parent-missing",
        "launch-flag-undeclared",
        "model-missing",
        "model-unclaimed",
        "reference-skipped",
        "rule-left-out",
        "rule-withheld",
        "variant-conflict",
    }
)


@dataclass(frozen=True)
class Notice:
    """A note, with what it names. `SHOWN` says whether the person sees it."""

    kind: NoticeKind
    subject: str


def disregarded_variable_notices(env: Mapping[str, str], variable: str) -> tuple[Notice, ...]:
    """The notice naming `variable` as set, where a host-managed provider may have disregarded it."""

    if flag_is_set(env, HOST_MANAGED_VARIABLE):
        return (Notice("provider-variable", variable),)
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


def block_skipped_notice(condition: str, undeclared: Undeclared) -> Notice:
    """The notice for a block whose condition names models or flags the manifest does not declare."""

    reasons = [
        *(f"`{name}` is not a declared model" for name in undeclared.models),
        *(f"`{name}` is not a declared flag" for name in undeclared.flags),
    ]
    return Notice(
        "block-skipped", f"the block keyed `{condition}` is skipped: {'; '.join(reasons)}"
    )


def reference_notice(reference: str, line: int, name: str) -> Notice:
    return Notice(
        "reference-skipped",
        f"the reference `{reference}` at manifest line {line} names `{name}`, which is not declared; skipped",
    )


def left_out_notice(rule: str) -> Notice:
    return Notice(
        "rule-left-out", f"rule `{rule}` is left out of the delivery: no part carries its body"
    )


def withheld_notice(rule: str, error: str) -> Notice:
    return Notice("rule-withheld", f"rule `{rule}` is withheld: {error}")


def absent_agent_notice() -> Notice:
    return Notice("agent-absent", "the agent fact is absent: the session started without `--agent`")


def absent_tools_notice(agent: str | None) -> Notice:
    if agent is None:
        return Notice("tools-absent", "the tools fact is absent: the context has no agent type")
    return Notice(
        "tools-absent",
        f"the tools fact is absent: no definition file registers its agent type `{agent}`",
    )


def fork_parent_missing_notice() -> Notice:
    return Notice(
        "fork-parent-missing",
        "the parent of this forked session was not found: it starts with empty session state",
    )


def fork_notice() -> Notice:
    return Notice("fork-inherits", "the fork received no rules because it inherits its parent's")
