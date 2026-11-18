#!/usr/bin/env python3
"""A config.yaml using every reserved key delivers what it says, and a missing or unreadable one delivers every rule.

`docs/config.md` names the reserved keys (`models`, `flags`, `defaults`, `sets`, and condition
blocks), and `docs/delivery.md` says that where `config.yaml` is missing or does not parse,
delivery sends the default form of every rule in the pool. Each case builds its rulesets
directory under `tmp_path` and reads what a context receives. The line each key, reference, and
block is read at is asserted through the `check` errors in `test_check_errors.py`, and nesting
and `then` through `test_ruleset_composition.py`.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_config_parse.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.run import check  # noqa: E402  (path must be set before this import)
from rulesets.compose.composition import compose  # noqa: E402
from rulesets.facts.context import ABSENT, Facts  # noqa: E402
from rulesets.session.state import SessionState  # noqa: E402
from rulesets.source.directory import read_directory  # noqa: E402


def build(tmp_path, text, stems) -> pathlib.Path:
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    if text is not None:
        (root / "config.yaml").write_text(text, encoding="utf-8")
    for stem in stems:
        (root / "rules" / f"{stem}.md").write_text(f"text of {stem}\n", encoding="utf-8")
    return root


def received(root, *, model=ABSENT) -> set[str]:
    facts = Facts(model=model, agent=ABSENT, kind="session", flags=frozenset(), session=ABSENT)
    return {d.rule for d in compose(read_directory(root), facts, SessionState()).rules}


def test_a_config_using_every_reserved_key_and_one_block_delivers_what_it_names(tmp_path) -> None:
    root = build(
        tmp_path,
        "models: opus haiku\n"
        "flags: strict\n"
        "defaults: core.*\n"
        "sets:\n"
        "  core: sorting claims\n"
        "model haiku:\n"
        "  include: voice\n",
        ("sorting", "claims", "voice", "tone"),
    )

    assert check(root).errors == ()
    assert received(root, model="haiku") == {"sorting", "claims", "voice"}
    assert received(root, model="opus") == {"sorting", "claims"}


@pytest.mark.parametrize(
    "config",
    [None, "models: [opus-4-8[1m]]\n"],
    ids=["missing", "does-not-parse"],
)
def test_a_config_that_is_missing_or_does_not_parse_delivers_every_rule(tmp_path, config) -> None:
    root = build(tmp_path, config, ("voice", "tone"))

    assert received(root) == {"voice", "tone"}
