"""What the engine delivers to one context of a comparison."""

from __future__ import annotations

from rulesets.compare.delivered_text import DeliveredText
from rulesets.compare.matrix import ContextKey
from rulesets.compose.composition import compose
from rulesets.facts.named_context import named_context
from rulesets.session.state import SessionState
from rulesets.source.directory import Present, RulesetsDirectory


def engine_rules(directory: RulesetsDirectory, context: ContextKey) -> dict[str, DeliveredText]:
    """The bytes of each rule the directory delivers to the context, at the variant it delivers."""

    manifest = directory.manifest.manifest if isinstance(directory.manifest, Present) else None
    kind = "delegate" if context.agent else "session"
    facts = named_context(context.identifier, context.agent, kind, (), (), manifest)
    found: dict[str, DeliveredText] = {}
    for delivered in compose(directory, facts, SessionState()).rules:
        rule = directory.pool.rules[delivered.rule]
        file = rule.variants[delivered.variant] if delivered.variant else rule.default
        if file is not None:
            found[delivered.rule] = DeliveredText(file.text.encode("utf-8"), delivered.variant)
    return found
