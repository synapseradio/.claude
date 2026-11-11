"""Parse the reference forms a config list is written in.

A list is the words a config writes under `defaults`, a set, or a block's `include` and
`exclude`. Parsing here reads the text of one word and judges nothing about whether the rule
or set it names exists.
"""

from __future__ import annotations

import dataclasses

RESERVED_RULESETS = ("defaults", "all", "rules", "none")
_NOT_A_FORM = "not a reference form; write rule, rule@variant, set.rule, set.rule@variant, or set.*"


@dataclasses.dataclass(frozen=True)
class RuleTarget:
    """A rule, at a variant or at none. `ruleset` is the set a `set.rule` reference names, else None."""

    rule: str
    variant: str | None
    ruleset: str | None = None


@dataclasses.dataclass(frozen=True)
class SpreadTarget:
    ruleset: str


@dataclasses.dataclass(frozen=True)
class MalformedTarget:
    reason: str


@dataclasses.dataclass(frozen=True)
class OldFormTarget:
    """A word in a reference form the config no longer reads. `advice` says what to write instead."""

    advice: str


type Target = RuleTarget | SpreadTarget | MalformedTarget | OldFormTarget


@dataclasses.dataclass(frozen=True)
class Reference:
    """One reference as written: its word, its file line, whether `exclude` holds it, and what it names."""

    text: str
    line: int
    remove: bool
    target: Target

    @property
    def quoted(self) -> str:
        """The reference as the config writes it, after the key of the list that holds it."""

        return f"{'exclude' if self.remove else 'include'} {self.text}"


def _old_form_advice(text: str) -> str | None:
    """What to write in place of a word in a form the config no longer reads, or None."""

    if text.startswith("-") and len(text) > 1:
        return f"`{text.removeprefix('-')}` belongs under `exclude`, without the `-`"
    if text == "*":
        return "write `all.*` to spread every rule"
    if text.endswith(":*") and text.count(":") == 1 and len(text) > 2:
        return f"write `{text.removesuffix(':*')}.*` to spread a set"
    if text.startswith("rules:") and text.count(":") == 1 and len(text) > 6:
        return f"write `rules.{text.removeprefix('rules:')}` to name a rule of the pool"
    return None


def _is_name(text: str) -> bool:
    return bool(text) and not any(mark in text for mark in ".@*:")


def _target(text: str) -> Target:
    if (advice := _old_form_advice(text)) is not None:
        return OldFormTarget(advice)
    name, at, variant = text.partition("@")
    if at and not _is_name(variant):
        return MalformedTarget(_NOT_A_FORM)
    head, dot, tail = name.partition(".")
    if not dot:
        return RuleTarget(head, variant or None) if _is_name(head) else MalformedTarget(_NOT_A_FORM)
    if not _is_name(head):
        return MalformedTarget(_NOT_A_FORM)
    if tail == "*" and not at:
        return SpreadTarget(head)
    if not _is_name(tail):
        return MalformedTarget(_NOT_A_FORM)
    if head in ("all", "rules"):
        return RuleTarget(tail, variant or None)
    return RuleTarget(tail, variant or None, head)


def parse_reference(text: str, line: int, *, remove: bool = False) -> Reference:
    """Parse one word of a list: `voice`, `voice@terse`, `prose.voice`, `prose.voice@terse`, `prose.*`.

    `all.rule` and `rules.rule` name a rule of the pool, and `all.*` spreads every rule. A word
    in an old form, `-voice`, `*`, `prose:*`, or `rules:voice`, parses to an OldFormTarget, and
    any other text that is no form to a MalformedTarget, so a caller reports it instead of
    catching an exception.
    """

    return Reference(text=text, line=line, remove=remove, target=_target(text))
