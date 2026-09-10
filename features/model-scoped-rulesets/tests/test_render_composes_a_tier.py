#!/usr/bin/env python3
"""A tier's render shows what that tier reads, not what its directory holds.

Delivery composes a tier from its own bodies falling back to the default
tier's, so a tier directory holding one override still delivers every stem in
the order list. The render used to read the tier directory alone, so the same
corpus rendered a file carrying that one stem. The render is meant to be the
read view -- `build_forward_plan` says so in as many words -- and a read view
missing twenty-six of twenty-seven rules is worse than none, because it looks
like an answer.

The gap was invisible to every existing check. `resolve.py check` and
`render --check` both verify that the render matches what the render code
would produce, which a render carrying nothing satisfies perfectly.

Run with
`python3.14 -m pytest features/model-scoped-rulesets/tests/test_render_composes_a_tier.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import render, resolve  # noqa: E402

ORDER = ("alpha", "beta", "zeta")


def _body(name: str, text: str) -> str:
    return f"<!-- rule: {name} -->\n\n## {name}\n\n{text}"


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def pruned(tmp_path):
    """A corpus where one tier overrides a single stem and inherits the rest.

    This is the layout the corpus is meant to have: a body sits outside
    `default/` only where it differs. Every other stem the tier delivers
    resolves to the default tier's file.
    """

    config_root = tmp_path / "claude"
    _write(config_root / "CLAUDE.md", "## Hello\n\nPlay.\n")
    corpus = config_root / "rulesets"
    for stem in ORDER:
        _write(corpus / "default" / f"{stem}.md", f"{_body(stem, f'{stem} holds.')}\n")
    _write(corpus / "sonnet" / "beta.md", f"{_body('beta', 'beta holds, for sonnet.')}\n")
    _write(
        corpus / "manifest.yaml",
        "tiers:\n"
        + "".join(f'  {tier}:\n    include: "*"\n' for tier in ("default", "sonnet"))
        + "order:\n"
        + "".join(f"  - {stem}\n" for stem in ORDER),
    )
    return render.RenderTargets(config_root=config_root, corpus_root=corpus, order=ORDER)


def _stems_in(content: str) -> list[str]:
    """The rule markers the render carries, in the order they appear."""

    import re

    return re.findall(r"<!-- rule: ([a-z0-9-]+) -->", content)


class TestATierRenderCarriesWhatTheTierDelivers:
    def test_the_render_carries_every_stem_composition_yields_in_order(self, pruned):
        """The property the whole render exists for."""

        targets = pruned.for_tier("sonnet")
        composition = resolve.compose("sonnet", pruned.corpus_root)

        content = render.build_forward_plan(targets.for_tier("sonnet"), check=True)
        rendered = next(generated for generated in content if generated.path == targets.render_path)

        assert _stems_in(rendered.content) == list(ORDER), (
            "a tier's render is the view of what that tier reads, and delivery composes "
            f"{sorted(composition.body_paths)} for it, so a render carrying "
            f"{_stems_in(rendered.content)} tells a reader their session loads rules it does not"
        )

    def test_composition_yields_every_stem_the_order_names(self, pruned):
        """The other half: the render can only be right if composition is."""

        composition = resolve.compose("sonnet", pruned.corpus_root)

        assert tuple(composition.stems) == ORDER, (
            f"delivery composes {tuple(composition.stems)} where the order names {ORDER}, "
            "so the two views disagree before the render is even built"
        )
        assert composition.findings == (), (
            f"composition reported {composition.findings}, so a stem resolves to no body"
        )

    def test_the_overriding_body_wins_over_the_default_one(self, pruned):
        """Composition is a fallback, not a replacement: the override still wins."""

        targets = pruned.for_tier("sonnet")
        rendered = next(
            generated
            for generated in render.build_forward_plan(targets, check=True)
            if generated.path == targets.render_path
        )

        assert "beta holds, for sonnet." in rendered.content, (
            "the tier's own body is the reason the tier exists, and a compose that "
            "reached past it would deliver the default text instead"
        )
        assert "alpha holds." in rendered.content, (
            "a stem the tier does not override still reaches it from the default tier"
        )
