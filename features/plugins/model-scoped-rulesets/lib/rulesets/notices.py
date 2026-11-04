"""The notices a delivery's record carries, typed by kind."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from rulesets.facts.environment import flag_is_set

HOST_MANAGED_VARIABLE = "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"

type NoticeKind = Literal["per-spawn-ambiguous", "per-spawn-unreadable", "provider-variable"]


@dataclass(frozen=True)
class Notice:
    """A record-only note, with what it names."""

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
