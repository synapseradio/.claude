"""What the engine delivers to one context of a comparison, each rule under its marker."""

from __future__ import annotations

from rulesets.compare.delivered_text import DeliveredText
from rulesets.compare.matrix import ContextKey
from rulesets.compose.composition import compose
from rulesets.facts.named_context import named_context
from rulesets.session.state import SessionState
from rulesets.source.directory import Present, RulesetsDirectory
from rulesets.source.marker import delivered


def engine_rules(directory: RulesetsDirectory, context: ContextKey) -> dict[str, DeliveredText]:
    """The bytes of each rule the directory delivers to the context, at the variant it delivers."""

    manifest = directory.manifest.manifest if isinstance(directory.manifest, Present) else None
    kind = "delegate" if context.agent else "session"
    facts = named_context(context.identifier, context.agent, kind, (), (), manifest)
    found: dict[str, DeliveredText] = {}
    for entry in compose(directory, facts, SessionState()).rules:
        rule = directory.pool.rules[entry.rule]
        file = rule.variants[entry.variant] if entry.variant else rule.default
        if file is not None:
            text = delivered(entry.rule, file.text)
            found[entry.rule] = DeliveredText(text.encode("utf-8"), entry.variant)
    return found
