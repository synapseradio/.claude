"""The notices a delivery draws, typed by kind, and which kinds the person is shown."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from rulesets.facts.environment import flag_is_set
from rulesets.source.undeclared import Undeclared

HOST_MANAGED_VARIABLE = "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"

type NoticeKind = Literal[
    "agent-absent",
    "block-skipped",
    "delivery-failure",
    "directory-scaffolded",
    "earlier-rules-remain",
    "key-skipped",
    "launch-flag-undeclared",
    "config-missing",
    "config-unparsable",
    "config-file-old",
    "model-missing",
    "model-unclaimed",
    "nothing-received",
    "per-spawn-ambiguous",
    "per-spawn-unreadable",
    "provider-variable",
    "reference-skipped",
    "rule-left-out",
    "rule-withheld",
    "scaffold-failed",
    "tools-absent",
    "variant-conflict",
]

SHOWN: frozenset[NoticeKind] = frozenset(
    {
        "block-skipped",
        "delivery-failure",
        "directory-scaffolded",
        "key-skipped",
        "launch-flag-undeclared",
        "config-missing",
        "config-unparsable",
        "config-file-old",
        "model-missing",
        "model-unclaimed",
        "nothing-received",
        "reference-skipped",
        "rule-left-out",
        "rule-withheld",
        "scaffold-failed",
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


def variant_conflict_notice(
    rule: str, statements: Iterable[tuple[str, int]], variant: str | None
) -> Notice:
    """The notice for a rule whose sets conflicted: each statement with its config line, and the variant delivered."""

    delivered = "its default form" if variant is None else f"variant `{variant}`"
    stated = ", ".join(f"`{text}` at config line {line}" for text, line in statements)
    return Notice(
        "variant-conflict",
        f"rule `{rule}` sets conflicting variants ({stated}); delivered at {delivered}",
    )


def flag_notice(name: str) -> Notice:
    """The notice for a launch flag the config does not declare."""

    return Notice(
        "launch-flag-undeclared", f"the launch flag `{name}` is not declared and is dropped"
    )


def block_skipped_notice(condition: str, undeclared: Undeclared) -> Notice:
    """The notice for a block whose condition names models or flags the config does not declare."""

    reasons = [
        *(f"`{name}` is not a declared model" for name in undeclared.models),
        *(f"`{name}` is not a declared flag" for name in undeclared.flags),
    ]
    return Notice(
        "block-skipped", f"the block keyed `{condition}` is skipped: {'; '.join(reasons)}"
    )


def key_skipped_notice(key: str, lines: tuple[int, ...]) -> Notice:
    """The notice for a key written more than once in one mapping of the config; every copy is skipped."""

    at = ", ".join(str(line) for line in lines[:-1]) + f" and {lines[-1]}"
    return Notice(
        "key-skipped",
        f"the config writes `{key}` at lines {at} of one mapping, so delivery skips every copy; "
        "a second list under one condition goes under `then`",
    )


def reference_notice(reference: str, line: int, name: str) -> Notice:
    return Notice(
        "reference-skipped",
        f"the reference `{reference}` at config line {line} names `{name}`, which is not declared; skipped",
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


def earlier_rules_remain_notice() -> Notice:
    return Notice(
        "earlier-rules-remain",
        "the rules delivered before this switch remain in the conversation above",
    )


def config_missing_notice(path: str) -> Notice:
    return Notice(
        "config-missing",
        f"the config `{path}` is missing; every rule is delivered at its default form",
    )


def old_config_file_notice(old_path: str, path: str) -> Notice:
    return Notice(
        "config-file-old",
        f"the engine reads only the config `{path}`, and `{old_path}` stands in its place; "
        "every rule is delivered at its default form until the config is written",
    )


def config_unparsable_notice(error: str) -> Notice:
    return Notice(
        "config-unparsable",
        f"the config does not parse ({error}); every rule is delivered at its default form",
    )


def nothing_received_notice() -> Notice:
    return Notice("nothing-received", "the context received nothing: no rule reaches it")


def scaffolded_notice(root: str) -> Notice:
    return Notice(
        "directory-scaffolded",
        f"no rulesets directory existed; an empty one was scaffolded at `{root}`",
    )


def scaffold_failed_notice(root: str, reason: str) -> Notice:
    return Notice(
        "scaffold-failed", f"the rulesets directory could not be scaffolded at `{root}`: {reason}"
    )


def failure_notice(failure: str, command: str) -> Notice:
    return Notice("delivery-failure", f"delivery failed ({failure}); run it again with: {command}")
