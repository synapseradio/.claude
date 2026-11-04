"""The notices a delivery draws, typed by kind, and which kinds the person is shown."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from rulesets.facts.environment import flag_is_set

HOST_MANAGED_VARIABLE = "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"

type NoticeKind = Literal[
    "per-spawn-ambiguous", "per-spawn-unreadable", "provider-variable", "variant-conflict"
]

SHOWN: frozenset[NoticeKind] = frozenset({"variant-conflict"})


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
