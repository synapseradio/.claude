"""The render tree's contents: each file name with the text render writes to it."""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping

from rulesets.compose.base_context import base_composition
from rulesets.compose.composition import expander_of
from rulesets.compose.withheld import withheld
from rulesets.render.list_render import Held, render_held
from rulesets.source.directory import Present, RulesetsDirectory
from rulesets.source.reference import RuleTarget


def _held(entries: Iterable[tuple[str, str | None]], barred: Collection[str]) -> Held:
    """The entries as one variant per rule, a named variant winning, without the barred rules."""

    held: dict[str, str | None] = {}
    for rule, variant in entries:
        if rule not in barred and (variant is not None or rule not in held):
            held[rule] = variant
    return held


def _safe_name(name: str) -> bool:
    """Whether a ruleset name makes a file directly inside the render folder."""

    return not (name.startswith(".") or "/" in name or "\\" in name)


def _bases(directory: RulesetsDirectory) -> dict[str, Held]:
    """The rules each base render holds, by render name: defaults, all, and each declared ruleset."""

    barred = withheld(directory.pool)
    bases = {
        "defaults": _held(((r.rule, r.variant) for r in base_composition(directory).rules), barred),
        "all": _held(((rule, None) for rule in directory.pool.rules), barred),
    }
    if isinstance(directory.manifest, Present):
        expander = expander_of(directory)
        for name, ruleset in directory.manifest.manifest.rulesets.items():
            if _safe_name(name):
                entries = expander.expand(ruleset.references).entries
                bases[name] = _held(((e.rule, e.variant) for e in entries), barred)
    return bases


def _variants_added(directory: RulesetsDirectory) -> dict[str, set[str]]:
    """Each rule's variants that some add in the manifest names."""

    named: dict[str, set[str]] = {}
    if isinstance(directory.manifest, Present):
        for references in directory.manifest.manifest.written_lists():
            for reference in references:
                match reference.target:
                    case RuleTarget(rule, str() as variant) if not reference.remove:
                        named.setdefault(rule, set()).add(variant)
    return named


def render_tree(directory: RulesetsDirectory) -> Mapping[str, str]:
    """The renders of the tree by file name, with no block applied in any of them."""

    pool = directory.pool
    added = _variants_added(directory)
    tree: dict[str, str] = {}
    for name, held in _bases(directory).items():
        tree[f"{name}.md"] = render_held(held, pool)
        for rule in held:
            for variant in sorted(added.get(rule, set()) & pool.rules[rule].variants.keys()):
                if held[rule] != variant:
                    tree[f"{name}+{rule}@{variant}.md"] = render_held({**held, rule: variant}, pool)
    return tree
