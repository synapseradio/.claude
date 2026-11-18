#!/usr/bin/env -S uv run --frozen
"""The pool delivers a rule under its file name up to any `@`, and delivers nothing by existing.

`docs/config.md` says a rule's name is its file name up to any `@`, a variant file
`name@variant.md` is a form of that rule, a file in the pool delivers nothing by being there, and
the engine never reads `references/` or `-render/` as rules. The warnings and errors the pool's
layout draws are asserted in `test_check_warnings.py` and `test_check_errors.py`. Each case
builds its rulesets directory under `tmp_path`.

Run with `uv run --frozen pytest features/plugins/rulesets/tests/test_config_pool.py`.
"""

import pathlib

from rulesets.compose.composition import compose
from rulesets.facts.context import ABSENT, Facts
from rulesets.session.state import SessionState
from rulesets.source.directory import read_directory


def build(tmp_path, files) -> pathlib.Path:
    """A rulesets directory holding `files`, a mapping of relative path to text."""
    root = tmp_path / "rulesets"
    root.mkdir()
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def received(root, *, flags=()) -> dict[str, str | None]:
    facts = Facts(
        model=ABSENT, agent=ABSENT, kind="session", flags=frozenset(flags), session=ABSENT
    )
    return {d.rule: d.variant for d in compose(read_directory(root), facts, SessionState()).rules}


def test_a_rule_is_named_by_its_file_name_up_to_the_at_sign_and_only_markdown_files_are_rules(
    tmp_path,
) -> None:
    root = build(
        tmp_path,
        {
            "config.yaml": "flags: terse\ndefaults: all.*\nflag terse:\n  include: a-b_c@d-e\n",
            "rules/a-b_c.md": "x",
            "rules/a-b_c@d-e.md": "y",
            "rules/notes.txt": "not a rule",
            "references/table@variant.md": "not a rule",
        },
    )

    assert received(root) == {"a-b_c": None}
    assert received(root, flags=["terse"]) == {"a-b_c": "d-e"}


def test_a_rule_file_delivers_nothing_unless_the_config_reaches_it(tmp_path) -> None:
    root = build(
        tmp_path,
        {"config.yaml": "defaults: voice\n", "rules/voice.md": "x", "rules/tone.md": "y"},
    )

    assert received(root) == {"voice": None}
