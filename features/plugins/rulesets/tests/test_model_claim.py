#!/usr/bin/env python3
"""A declared model name claims the identifiers the harness reports for it.

Serves the person who writes a config: they declare model names in `models`, write
`model opus-4-8` in a `when` key, and expect each identifier the harness reports to reach the
right item. The rules are the ones `docs/config.md` gives under `models`: a declared name `n`
claims `claude-n` and every identifier that continues it with `-` or `[`, the longer name wins
where two claim one identifier, and an identifier no name claims tests false in every `model`
condition. Every case passes its own `models` list, since the engine holds no model name.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_model_claim.py`.
"""

import pytest
from rulesets.facts.model import claim as model_claim
from rulesets.facts.model import fact as model_fact

DECLARED = ["opus", "sonnet", "haiku", "fable", "opus-4-8", "opus-4-8[1m]"]
WITHOUT_1M = [name for name in DECLARED if name != "opus-4-8[1m]"]


@pytest.mark.parametrize(
    ("identifier", "models", "claimed_by"),
    [
        ("claude-opus-5-5[1m]", WITHOUT_1M, "opus"),
        ("claude-opus[1m]", ["opus"], "opus"),
        ("claude-opus", ["opus"], "opus"),
        ("opus", WITHOUT_1M, "opus"),
        ("claude-opus-4-8", ["opus", "opus-4-8"], "opus-4-8"),
        ("claude-opus-4-8", ["opus-4-8", "opus"], "opus-4-8"),
        ("claude-opus-5-5[1m]", ["opus", "opus-4-8"], "opus"),
        ("claude-opus-4-8[1m]", WITHOUT_1M, "opus-4-8"),
        ("claude-opus-4-8[1m]", DECLARED, "opus-4-8[1m]"),
        ("claude-nova-1", [*DECLARED, "nova"], "nova"),
        ("claude-sonnet-5", ["sonnet", "sonnet"], "sonnet"),
        ("claude-opusx", WITHOUT_1M, None),
        ("claude-opus", ["opus-4-8"], None),
        ("claude-opus-4-8", ["opus-4-8[1m]"], None),
        ("some-vendor-opus-1", ["opus"], None),
        ("opus-4-8-preview", ["opus", "opus-4-8"], None),
        ("claude-nova-1", DECLARED, None),
        ("claude-opus-4-8", [], None),
        ("haiku", ["opus"], None),
    ],
    ids=[
        "a continuation at a bracket claims for the shorter name",
        "a bracket right after the name is a boundary",
        "the prefix and name alone are claimed",
        "an identifier equal to a name takes it",
        "the longest name wins",
        "the longest name wins whatever the declared order",
        "a shorter name still claims other identifiers",
        "a 1m identifier follows its base name",
        "a declared 1m name wins as the longer name",
        "an undeclared name claims once the config lists it",
        "a name declared twice claims as once",
        "a continuation that is not a boundary stays unclaimed",
        "a longer name does not claim a shorter identifier",
        "a declared 1m name does not claim the identifier without the suffix",
        "an identifier not opening on the prefix is unclaimed",
        "an identifier equal to no name stays unclaimed",
        "an undeclared name stays unclaimed",
        "an empty config claims nothing",
        "an alias no declared name equals stays unclaimed",
    ],
)
def test_an_identifier_is_claimed_by_the_declared_name_the_config_documents(
    identifier, models, claimed_by
) -> None:
    fact = model_claim.claim_model(identifier, "harness-reported", models)

    assert model_fact.claimed_name(fact) == claimed_by
