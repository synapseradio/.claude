#!/usr/bin/env python3
"""Check warns about what is legal but probably not meant, and a warning never fails a check.

The check serves the engineer who edits rule files and a config. `docs/commands.md` lists what
it warns about: a rule no add includes, a rule whose text names another rule (in backticks, by
file name, as a link to its file, or as "rule name" or "the name rule"; a bare word is no mention),
a stray directory, a file path a rule cites that the directory does not hold (a path with a
`<placeholder>` segment is no citation), and a rule file that opens on a marker for another rule
or another form of its own. Each warning names its kind, subject, file, and line, and leaves the
errors empty. Each case builds its rulesets directory under `tmp_path`.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_check_warnings.py`.
"""

import pathlib

import pytest
from rulesets.check.findings import (
    DirectorySubject,
    RulePairSubject,
    RuleSubject,
    Subject,
)
from rulesets.check.run import check

CONFIG = "config.yaml"
NEVER = "never-included"
CROSS = "cross-reference"
MARKER = "marker-for-another-rule"
DANGLING = "dangling-reference"
EXTERNAL = "external-reference"
STRAY = "stray-directory"


def rules(*stems) -> dict[str, str]:
    return {f"rules/{stem}.md": f"text of {stem}\n" for stem in stems}


def build(tmp_path, files) -> pathlib.Path:
    """A rulesets directory holding `files`, a mapping of relative path to text; None makes a directory."""
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    for relative, text in files.items():
        if text is None:
            (root / relative).mkdir(parents=True)
        else:
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text, encoding="utf-8")
    return root


def relative(subject: Subject, root: pathlib.Path) -> Subject:
    """The subject, with a directory's path taken relative to the root."""
    if isinstance(subject, DirectorySubject):
        return DirectorySubject(subject.path.relative_to(root))
    return subject


def warned(root) -> list[tuple]:
    """Each warning as (kind, subject, file relative to the root, line), in a stable order."""
    found = [
        (w.kind, relative(w.subject, root), str(w.file.relative_to(root)), w.line)
        for w in check(root).warnings
    ]
    return sorted(found, key=lambda warning: (warning[0], repr(warning[1]), warning[2]))


def warning(kind, subject, file=None, line=None) -> tuple:
    """A wanted warning; a file or line left as None goes unasserted."""
    return (kind, subject, file, line)


def agrees(found, wanted) -> bool:
    wanted = sorted(wanted, key=lambda w: (w[0], repr(w[1]), w[2] or ""))
    return len(found) == len(wanted) and all(
        f[:2] == w[:2] and w[2] in (None, f[2]) and w[3] in (None, f[3])
        for f, w in zip(found, wanted, strict=True)
    )


def pair(name, other) -> RulePairSubject:
    return RulePairSubject(name, other)


def voice(name="voice") -> RuleSubject:
    return RuleSubject(name)


WARN_CASES = [
    pytest.param(
        {
            CONFIG: "defaults:\n  include: all.*\n  exclude: security\n",
            **rules("voice", "security"),
        },
        [warning(NEVER, voice("security"), "rules/security.md")],
        id="rule-the-defaults-remove-and-nothing-adds",
    ),
    pytest.param(
        {CONFIG: "defaults:\n", **rules("a", "b")},
        [warning(NEVER, voice("a")), warning(NEVER, voice("b"))],
        id="config-that-adds-nothing-leaves-every-rule-unreached",
    ),
    pytest.param(
        {CONFIG: "# nothing yet\n", **rules("a")}, [warning(NEVER, voice("a"))], id="empty-config"
    ),
    pytest.param(
        {CONFIG: "defaults:\n", **rules("voice", "voice@terse", "voice@warm")},
        [warning(NEVER, voice())],
        id="rule-with-variants-named-once",
    ),
    pytest.param(
        {
            CONFIG: "defaults:\n  include: all.*\n  exclude: voice\nsets:\n  tone: other\n",
            **rules("voice", "other"),
        },
        [warning(NEVER, voice())],
        id="rule-removed-in-the-list-that-spreads-it",
    ),
    pytest.param(
        {"rules/voice.md": "Intro.\n\nSee `sorting` before you write.\n", **rules("sorting")},
        [warning(CROSS, pair("voice", "sorting"), "rules/voice.md", 3)],
        id="cross-reference-names-both-rules-file-and-line",
    ),
    pytest.param(
        {
            **rules("sorting", "voice"),
            "rules/voice@terse.md": "See `sorting`.\n",
        },
        [warning(CROSS, pair("voice", "sorting"), "rules/voice@terse.md", 1)],
        id="cross-reference-in-a-variant-names-the-variant-file",
    ),
    pytest.param(
        {"rules/a.md": "uses `b`\n", "rules/b.md": "uses `a`\n"},
        [warning(CROSS, pair("a", "b")), warning(CROSS, pair("b", "a"))],
        id="two-rules-naming-each-other",
    ),
    pytest.param(
        {"rules/a.md": "`b` and `c`\n", **rules("b", "c")},
        [warning(CROSS, pair("a", "b")), warning(CROSS, pair("a", "c"))],
        id="one-rule-naming-two-others",
    ),
    pytest.param(
        {"rules/voice.md": "<!-- rule: voice -->\ntext\n", **rules("sorting")},
        [],
        id="own-marker-line-is-no-mention",
    ),
    pytest.param(
        {"rules/voice.md": "<!-- rule: sorting -->\ntext\n", **rules("sorting")},
        [warning(MARKER, voice(), "rules/voice.md", 1)],
        id="marker-for-another-rule-is-no-cross-reference",
    ),
    pytest.param(
        {**rules("voice"), "rules/voice@terse.md": "<!-- rule: voice -->\ntext\n"},
        [warning(MARKER, voice(), "rules/voice@terse.md", 1)],
        id="variant-marking-the-default-form",
    ),
    pytest.param(
        {**rules("voice"), "rules/voice@terse.md": "<!-- rule: voice variant: warm -->\ntext\n"},
        [warning(MARKER, voice(), "rules/voice@terse.md", 1)],
        id="variant-marking-another-variant",
    ),
    pytest.param(
        {"rules/voice.md": "<!-- rule: voice variant: terse -->\ntext\n"},
        [warning(MARKER, voice(), "rules/voice.md", 1)],
        id="default-form-marking-a-variant",
    ),
    pytest.param(
        {**rules("voice"), "rules/drafts": None},
        [warning(STRAY, DirectorySubject(pathlib.Path("rules/drafts")))],
        id="directory-inside-the-pool",
    ),
    pytest.param(
        {**rules("voice"), "renders": None},
        [warning(STRAY, DirectorySubject(pathlib.Path("renders")))],
        id="directory-beside-the-pool",
    ),
    pytest.param(
        {"rules/voice.md": "Intro.\n\nOpen `~/.claude/rulesets/references/table.md` in full.\n"},
        [warning(DANGLING, voice(), "rules/voice.md", 3)],
        id="cited-corpus-file-that-is-not-there",
    ),
    pytest.param(
        {"rules/voice.md": "Text.\nOpen `references/table.md` in full.\n"},
        [warning(DANGLING, voice(), "rules/voice.md", 2)],
        id="relative-citation-under-references-that-is-not-there",
    ),
    pytest.param(
        {"rules/voice.md": "Text.\nSee `~/notes/x.md` first.\n"},
        [warning(EXTERNAL, voice(), "rules/voice.md", 2)],
        id="home-path-outside-the-configuration-directory",
    ),
    pytest.param(
        {"rules/voice.md": "Read `/etc/hosts` before editing.\n"},
        [warning(EXTERNAL, voice(), "rules/voice.md", 1)],
        id="absolute-path",
    ),
    pytest.param(
        {"rules/voice.md": "Read `/opt/data/a<b.md` and `~/notes/x>y.md` and `/opt/<a/b>.md`.\n"},
        [warning(EXTERNAL, voice())] * 3,
        id="concrete-paths-beside-an-unrelated-angle-bracket",
    ),
    pytest.param(
        {
            **rules("voice"),
            "rules/voice@terse.md": "Open `~/.claude/rulesets/references/gone.md`.\n",
        },
        [warning(DANGLING, voice(), "rules/voice@terse.md")],
        id="citation-in-a-variant-names-the-variant-file",
    ),
    pytest.param(
        {
            "rules/voice.md": "`~/.claude/rulesets/references/a.md`\n"
            "`~/.claude/rulesets/references/b.md`\n"
        },
        [warning(DANGLING, voice(), None, 1), warning(DANGLING, voice(), None, 2)],
        id="each-citation-in-a-body-is-a-warning",
    ),
    pytest.param(
        {
            CONFIG: "defaults: voice\n",
            "rules/voice.md": "Run `security` first.\n",
            **rules("security"),
        },
        [warning(CROSS, pair("voice", "security")), warning(NEVER, voice("security"))],
        id="rule-no-add-includes-and-rule-naming-another-draw-both",
    ),
]

SILENT_CASES = [
    pytest.param(
        {
            CONFIG: "defaults: voice\nflag never-set:\n  include: security\n",
            **rules("voice", "security"),
        },
        id="rule-reached-only-by-an-item-that-never-applies",
    ),
    pytest.param(
        {CONFIG: "defaults: outer.*\nsets:\n  outer: inner.*\n  inner: voice\n", **rules("voice")},
        id="rule-added-through-nested-sets",
    ),
    pytest.param(
        {CONFIG: "defaults: voice\nflag quiet:\n  exclude: voice\n", **rules("voice")},
        id="remove-in-an-item-does-not-undo-an-add-elsewhere",
    ),
    pytest.param(
        {CONFIG: "defaults: other\nsets:\n  tone: voice\n", **rules("voice", "other")},
        id="add-in-a-set-nothing-spreads",
    ),
    pytest.param({CONFIG: "defaults: all.*\n", **rules("a", "b", "c")}, id="spread-of-all"),
    pytest.param(rules("a", "b"), id="missing-config-includes-every-rule"),
    pytest.param(
        {CONFIG: "models: [opus-4-8[1m]]\n", **rules("voice")}, id="config-that-does-not-parse"
    ),
    pytest.param(
        {"rules/a.md": "writing-code.md and rule code-review\n", **rules("code")},
        id="name-inside-a-longer-hyphenated-word",
    ),
    pytest.param(
        {"rules/voice.md": "See writing-code.md, code-review.md and code.mdx.\n", **rules("code")},
        id="file-name-inside-a-longer-name",
    ),
    pytest.param(
        {"rules/voice.md": "The voice rule keeps voice short.\n"},
        id="rule-naming-itself",
    ),
    pytest.param(
        {
            "rules/voice.md": "Check before reporting. Search comments too. Per agent-delegation.\n",
            **rules("reporting", "comments", "agent-delegation"),
        },
        id="bare-word-is-no-mention",
    ),
    pytest.param(
        {"rules/voice@terse.md": "Read the newest handoff note.\n", **rules("handoff", "voice")},
        id="bare-word-in-a-variant",
    ),
    pytest.param(
        {"rules/voice@terse.md": "<!-- rule: voice variant: terse -->\ntext\n", **rules("voice")},
        id="variant-marking-its-own-form",
    ),
    pytest.param(
        {"rules/voice.md": "text\n<!-- rule: sorting -->\n"}, id="marker-below-the-first-line"
    ),
    pytest.param(
        {**rules("voice"), "references": None}, id="references-folder-is-no-stray-directory"
    ),
    pytest.param(
        {
            "rules/voice.md": "Open `~/.claude/rulesets/references/table.md` and `references/table.md`.\n",
            "references/table.md": "table\n",
        },
        id="cited-file-that-is-there",
    ),
    pytest.param(
        {"rules/voice.md": "Open `~/.claude/references/table.md`, `~/.claude/rules/testing.md`.\n"},
        id="path-under-the-configuration-directory-outside-the-corpus",
    ),
    pytest.param(
        {
            "rules/voice.md": "Write `/tmp/<skill>-<slug>.md`, `~/notes/<topic>/x.md`, "
            "and `references/<name>.md`.\n"
        },
        id="path-holding-a-placeholder-segment",
    ),
    pytest.param(
        {"rules/voice.md": "See `https://example.com/docs/page` and `//cdn.example.com/a/b`.\n"},
        id="url-is-no-path",
    ),
    pytest.param(
        {"rules/voice.md": "Type `/` or `/clear`, name `src/api/users`, run `cd ~/x`, or `~/`.\n"},
        id="inline-code-that-only-resembles-a-path",
    ),
    pytest.param(
        {
            CONFIG: "defaults: all.*\n",
            **rules("voice", "voice@terse"),
            "rules/sorting.md": "<!-- rule: sorting -->\nOrder things.\n",
            "references": None,
        },
        id="clean-directory",
    ),
]


@pytest.mark.parametrize(("files", "wanted"), WARN_CASES)
def test_each_suspect_state_draws_a_warning_and_leaves_errors_empty(
    tmp_path, files, wanted
) -> None:
    root = build(tmp_path, files)

    found = warned(root)

    assert check(root).errors == (), "a warning never fails the run"
    assert agrees(found, wanted), f"found {found}, wanted {wanted}"


@pytest.mark.parametrize("files", SILENT_CASES)
def test_a_state_that_is_no_cause_for_warning_draws_none(tmp_path, files) -> None:
    root = build(tmp_path, files)

    assert check(root).warnings == ()


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Follow `sorting` first.\n", id="name-in-backticks"),
        pytest.param("Open `sorting.md` first.\n", id="backticked-file-name"),
        pytest.param("Open sorting.md first.\n", id="bare-file-name"),
        pytest.param("Open `sorting@terse.md` first.\n", id="backticked-variant-file-name"),
        pytest.param("Open sorting@terse.md first.\n", id="bare-variant-file-name"),
        pytest.param("See [the order](../rules/sorting.md).\n", id="link-to-the-file"),
        pytest.param("See [the order](sorting@terse.md#top).\n", id="link-to-a-variant-file"),
        pytest.param("Apply rule sorting first.\n", id="rule-name-bare"),
        pytest.param("Apply rule `sorting` first.\n", id="rule-name-backticked"),
        pytest.param("Apply the sorting rule first.\n", id="the-name-rule-bare"),
        pytest.param("Apply the `sorting` rule first.\n", id="the-name-rule-backticked"),
    ],
)
def test_each_form_that_names_another_rule_draws_a_cross_reference_warning(tmp_path, text) -> None:
    root = build(tmp_path, {**rules("sorting"), "rules/voice.md": text})

    (found,) = warned(root)

    assert found[:2] == (CROSS, pair("voice", "sorting"))
    assert found[3] == 1
