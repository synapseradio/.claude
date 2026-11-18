#!/usr/bin/env -S uv run --frozen
"""Check reports every illegal state of a rulesets directory as an error with its subject.

The check serves the engineer who edits a config or a rule file and runs check before
trusting a delivery. `docs/commands.md` lists the states that are errors: a variant with no
default form, a cycle among sets, a reference to a name nothing declares, a condition that tests
anything but a fact, a rule file past the part budget, frontmatter that carries a condition,
conflicting variants, a condition key written twice, a config in an older layout, and a config
YAML cannot read. Each error names its kind, the subject delivery will disable, and the file and
line to open, and one run reports every error together. Each case builds its rulesets directory
under `tmp_path`; message wording is not asserted, since only the kind, subject, file, and line
are promised.

Run with `uv run --frozen pytest features/plugins/rulesets/tests/test_check_errors.py`.
"""

import pathlib

import pytest
from rulesets.check.findings import (
    BlockSubject,
    ConfigSubject,
    KeySubject,
    ReferencesSubject,
    ReferenceSubject,
    RulesetsSubject,
    RulesetSubject,
    RuleSubject,
)
from rulesets.check.run import check
from rulesets.compose.composition import compose
from rulesets.facts.context import ABSENT, Facts
from rulesets.session.state import SessionState
from rulesets.source.directory import read_directory

CONFIG = "config.yaml"
VOICE_FILES = {"rules/voice.md": "text of voice\n"}
VARIANTS = {
    f"rules/{name}.md": f"text of {name}\n" for name in ("voice", "voice@terse", "voice@warm")
}
RULE_KEYS = [
    "paths",
    "when",
    "model",
    "models",
    "agent",
    "agents",
    "kind",
    "kinds",
    "flag",
    "flags",
]


def build(tmp_path, files) -> pathlib.Path:
    """A rulesets directory holding `files`, a mapping of relative path to text or bytes."""
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    for relative, content in files.items():
        data = content if isinstance(content, bytes) else content.encode("utf-8")
        (root / relative).write_bytes(data)
    return root


def errors_of(root) -> list[tuple]:
    """Each error as (kind, subject, file relative to the root, line), in a stable order."""
    found = [
        (error.kind, error.subject, str(error.file.relative_to(root)), error.line)
        for error in check(root).errors
    ]
    return sorted(found, key=repr)


def expected(*errors) -> list[tuple]:
    """Each wanted error as (kind, subject, line) or (kind, subject, line, file).

    A line of None leaves the line unasserted, and the file defaults to the config.
    """
    return sorted([(e[0], e[1], e[3] if len(e) > 3 else CONFIG, e[2]) for e in errors], key=repr)


def matches(found, wanted) -> bool:
    return len(found) == len(wanted) and all(
        f[:3] == w[:3] and (w[3] is None or f[3] == w[3])
        for f, w in zip(found, wanted, strict=True)
    )


def case(files, *errors, id) -> pytest.param:
    return pytest.param(files, expected(*errors), id=id)


ERROR_CASES = [
    case(
        {CONFIG: "sets:\n  a: b.*\n  b: a.*\n  c: voice\n", **VOICE_FILES},
        ("ruleset-cycle", RulesetsSubject(("a", "b")), 2),
        id="cycle-names-every-set-in-it",
    ),
    case(
        {CONFIG: "sets:\n  a: b.*\n  b: a.*\n  c: a.*\n"},
        ("ruleset-cycle", RulesetsSubject(("a", "b")), 2),
        id="set-spreading-into-a-cycle-is-no-error",
    ),
    case(
        {CONFIG: "sets:\n  a: a.*\n"},
        ("ruleset-cycle", RulesetsSubject(("a",)), 2),
        id="self-spread",
    ),
    case(
        {CONFIG: "defaults: a.*\nsets:\n  a: defaults.*\n"},
        ("ruleset-cycle", RulesetsSubject(("a", "defaults")), 1),
        id="cycle-through-defaults",
    ),
    case(
        {CONFIG: "defaults: voice@terse voice@warm\n", **VARIANTS},
        (
            "variant-conflict",
            ReferencesSubject(
                (ReferenceSubject("voice@terse", 1), ReferenceSubject("voice@warm", 1))
            ),
            1,
        ),
        id="variant-conflict-in-defaults",
    ),
    case(
        {CONFIG: "sets:\n  tone: voice@terse voice@warm\n", **VARIANTS},
        (
            "variant-conflict",
            ReferencesSubject(
                (ReferenceSubject("voice@terse", 2), ReferenceSubject("voice@warm", 2))
            ),
            2,
        ),
        id="variant-conflict-in-a-set",
    ),
    case(
        {CONFIG: "flags: a\nflag a:\n  include: voice@terse voice@warm\n", **VARIANTS},
        (
            "variant-conflict",
            ReferencesSubject(
                (ReferenceSubject("voice@terse", 3), ReferenceSubject("voice@warm", 3))
            ),
            3,
        ),
        id="variant-conflict-in-a-block",
    ),
    case(
        {CONFIG: "project amboss:\n  include: voice\n", **VOICE_FILES},
        ("condition-invalid", BlockSubject("project amboss"), 1),
        id="condition-tests-a-project",
    ),
    case(
        {CONFIG: "(agent critic and flag strict:\n  include: voice\n", **VOICE_FILES},
        ("condition-invalid", BlockSubject("(agent critic and flag strict"), 1),
        id="condition-does-not-parse",
    ),
    case(
        {
            CONFIG: "flags: ok\nflag ok:\n  include: voice\n  project x:\n    include: voice\n",
            **VOICE_FILES,
        },
        ("condition-invalid", BlockSubject("flag ok and project x"), 4),
        id="nested-block-named-by-combined-condition",
    ),
    case(
        {CONFIG: "defaults: voice\nprojekt:\n  include: voice\n", **VOICE_FILES},
        ("condition-invalid", BlockSubject("projekt"), 2),
        id="top-level-key-tests-no-fact",
    ),
    case(
        {CONFIG: "models: opus\nmodel hiaku:\n  include: voice\n", **VOICE_FILES},
        ("unknown-model", BlockSubject("model hiaku"), 2),
        id="undeclared-model",
    ),
    case(
        {CONFIG: "model haiku:\n  include: voice\n", **VOICE_FILES},
        ("unknown-model", BlockSubject("model haiku"), 1),
        id="no-models-declared-declares-none",
    ),
    case(
        {CONFIG: "models: opus\nnot model nova:\n  include: voice\n", **VOICE_FILES},
        ("unknown-model", BlockSubject("not model nova"), 2),
        id="negated-undeclared-model",
    ),
    case(
        {CONFIG: "model nova or model luna:\n  include: voice\n", **VOICE_FILES},
        ("unknown-model", BlockSubject("model nova or model luna"), 1),
        id="several-undeclared-models-one-error",
    ),
    case(
        {CONFIG: "models: opus\nmodel opus opus-9:\n  include: voice\n", **VOICE_FILES},
        ("unknown-model", BlockSubject("model opus opus-9"), 2),
        id="undeclared-value-in-a-group",
    ),
    case(
        {CONFIG: "agent critic: voice\n", **VOICE_FILES},
        ("block-shape", BlockSubject("agent critic"), 1),
        id="block-holding-one-word",
    ),
    case(
        {CONFIG: "agent critic: {}\n"},
        ("block-shape", BlockSubject("agent critic"), 1),
        id="block-holding-empty-mapping",
    ),
    case(
        {CONFIG: "agent critic:\n"},
        ("block-shape", BlockSubject("agent critic"), 1),
        id="block-holding-nothing",
    ),
    case(
        {CONFIG: "agent critic:\n  - voice\n", **VOICE_FILES},
        ("block-shape", BlockSubject("agent critic"), 1),
        id="block-holding-a-dash-list",
    ),
    case(
        {CONFIG: "defaults: voice\nproject: amboss\n", **VOICE_FILES},
        ("block-shape", BlockSubject("project"), 2),
        id="top-level-key-holding-one-word",
    ),
    case(
        {CONFIG: "agent critic: voice\ndefaults: ghost\n", **VOICE_FILES},
        ("block-shape", BlockSubject("agent critic"), 1),
        ("undeclared-reference", ReferenceSubject("ghost", 2), 2),
        id="rest-of-config-still-checks",
    ),
    case(
        {CONFIG: "defaults: voice ghost\n", **VOICE_FILES},
        ("undeclared-reference", ReferenceSubject("ghost", 1), 1),
        id="undeclared-rule",
    ),
    case(
        {
            CONFIG: "agent critic:\n  include:\n    voice\n    tone\n    ghost\n",
            **VOICE_FILES,
            "rules/tone.md": "t\n",
        },
        ("undeclared-reference", ReferenceSubject("ghost", 5), 5),
        id="reference-cited-at-its-own-line",
    ),
    case(
        {CONFIG: "defaults: voice@loud\n", **VARIANTS},
        ("undeclared-reference", ReferenceSubject("voice@loud", 1), 1),
        id="undeclared-variant",
    ),
    case(
        {CONFIG: "defaults: phantom.*\n", **VOICE_FILES},
        ("undeclared-reference", ReferenceSubject("phantom.*", 1), 1),
        id="undeclared-set",
    ),
    case(
        {CONFIG: "defaults:\n  include: all.*\n  exclude: ghost\n", **VOICE_FILES},
        ("undeclared-reference", ReferenceSubject("ghost", 3), 3),
        id="exclude-of-undeclared-rule",
    ),
    case(
        {CONFIG: "flags: a\nsets:\n  code: ghost\nflag a:\n  include: spook\n", **VOICE_FILES},
        ("undeclared-reference", ReferenceSubject("ghost", 3), 3),
        ("undeclared-reference", ReferenceSubject("spook", 5), 5),
        id="undeclared-in-a-set-and-a-block",
    ),
    case(
        {CONFIG: "defaults: a.* b.*\nsets:\n  a: ghost\n  b: a.*\n", **VOICE_FILES},
        ("undeclared-reference", ReferenceSubject("ghost", 3), 3),
        id="reached-by-two-spreads-reported-once",
    ),
    case(
        {CONFIG: "defaults: foo:bar\n"},
        ("malformed-reference", ReferenceSubject("foo:bar", 1), 1),
        id="text-that-is-no-reference-form",
    ),
    case(
        {CONFIG: "sets:\n  code:\n    a: b\n  tone: voice\n", **VOICE_FILES},
        ("ruleset-shape", RulesetSubject("code"), 2),
        id="set-holding-another-key",
    ),
    case(
        {CONFIG: "sets:\n  code.extra: voice\n", **VOICE_FILES},
        ("ruleset-name", RulesetSubject("code.extra"), 2),
        id="set-name-holding-a-dot",
    ),
    case(
        {CONFIG: "sets:\n  defaults:\n  all:\n  rules:\n  none:\n"},
        ("reserved-ruleset", RulesetSubject("defaults"), 2),
        ("reserved-ruleset", RulesetSubject("all"), 3),
        ("reserved-ruleset", RulesetSubject("rules"), 4),
        ("reserved-ruleset", RulesetSubject("none"), 5),
        id="each-reserved-set-name",
    ),
    case(
        {
            CONFIG: "defaults: voice\n",
            "rules/voice.md": "---\ndescription: tone\nmodel: haiku\n---\ntext\n",
        },
        ("rule-condition", RuleSubject("voice"), 3, "rules/voice.md"),
        id="frontmatter-names-a-condition",
    ),
    case(
        {"rules/voice.md": "text\n", "rules/voice@terse.md": "---\nagent: critic\n---\ntext\n"},
        ("rule-condition", RuleSubject("voice"), 2, "rules/voice@terse.md"),
        id="condition-in-a-variant-file",
    ),
    case(
        {"rules/voice.md": b"---\r\nmodel: haiku\r\n---"},
        ("rule-condition", RuleSubject("voice"), 2, "rules/voice.md"),
        id="crlf-fence-closed-without-newline",
    ),
    *[
        case(
            {"rules/voice.md": f"---\n{key}: x\n---\ntext\n"},
            ("rule-condition", RuleSubject("voice"), 2, "rules/voice.md"),
            id=f"frontmatter-key-{key}",
        )
        for key in RULE_KEYS
    ],
    case(
        {"rules/tone@dry.md": "Be dry.\n"},
        ("variant-without-default", RuleSubject("tone"), None, "rules/tone@dry.md"),
        id="variant-without-default-form",
    ),
    case(
        {"rules/voice.md": b"Speak \xff\xfe plainly.\n"},
        ("unreadable-file", RuleSubject("voice"), None, "rules/voice.md"),
        id="rule-file-not-utf8",
    ),
    case(
        {CONFIG: "when: x\n", "rules/voice.md": b"\xff"},
        ("old-layout", KeySubject("when"), 1),
        ("unreadable-file", RuleSubject("voice"), None, "rules/voice.md"),
        id="rule-file-errors-arrive-with-config-errors",
    ),
    case(
        {CONFIG: "defaults: voice\nwhen:\n  - flag a: ['voice']\n", **VOICE_FILES},
        ("old-layout", KeySubject("when"), 2),
        id="old-when-key",
    ),
    case(
        {CONFIG: "rulesets:\n  code: voice\n", **VOICE_FILES},
        ("old-layout", KeySubject("rulesets"), 1),
        id="old-rulesets-key",
    ),
    case(
        {
            CONFIG: 'sets:\n  reasoning: voice\n  lookup: tone\nagent critic:\n  include: ["reasoning.*", "lookup.*"]\n',
            **VOICE_FILES,
            "rules/tone.md": "t\n",
        },
        ("list-shape", KeySubject("include"), 5),
        id="bracketed-list-of-quoted-entries",
    ),
    case(
        {CONFIG: "defaults:\n  - voice\n  - tone\n", **VOICE_FILES, "rules/tone.md": "t\n"},
        ("list-shape", KeySubject("defaults"), 2),
        id="dash-list",
    ),
    case(
        {CONFIG: "models: [opus, sonnet]\n"},
        ("list-shape", KeySubject("models"), 1),
        id="bracketed-model-list",
    ),
    case(
        {CONFIG: "defaults:\n  all: true\n"},
        ("key-shape", KeySubject("defaults"), 1),
        id="defaults-holding-another-key",
    ),
    case(
        {CONFIG: "models:\n  a: b\nflags:\n  c: d\ndefaults:\n  e: f\nsets: x\n"},
        ("key-shape", KeySubject("models"), 1),
        ("key-shape", KeySubject("flags"), 3),
        ("key-shape", KeySubject("defaults"), 5),
        ("key-shape", KeySubject("sets"), 7),
        id="each-declaration-key-has-a-shape",
    ),
    case(
        {CONFIG: "defaults: voice\nmodels: [opus, opus-4-8[1m]]\n", **VOICE_FILES},
        ("config-unparsable", ConfigSubject(), 2),
        id="brackets-in-a-model-name",
    ),
    case(
        {CONFIG: b"defaults: all.*\nmodels: \xff\n"},
        ("config-unparsable", ConfigSubject(), 2),
        id="config-not-utf8",
    ),
    case(
        {CONFIG: "- defaults\n- models\n"},
        ("config-unparsable", ConfigSubject(), 1),
        id="config-top-level-is-a-list",
    ),
    case(
        {CONFIG: "models: [opus-4-8[1m]]\n", "rules/tone@dry.md": "x\n"},
        ("config-unparsable", ConfigSubject(), 1),
        ("variant-without-default", RuleSubject("tone"), None, "rules/tone@dry.md"),
        id="rule-file-errors-still-reported-beside-an-unparsable-config",
    ),
    case(
        {CONFIG: "agent critic:\n  include:\n    voice\n    *\n", **VOICE_FILES},
        ("old-reference", ReferenceSubject("*", 4), 4),
        id="bare-star-under-include",
    ),
    case(
        {CONFIG: "defaults: *\n"},
        ("config-unparsable", ConfigSubject(), 1),
        id="bare-star-opening-a-value",
    ),
    case(
        {"rules/voice.md": "x" * 12_000},
        ("oversize-body", RuleSubject("voice"), None, "rules/voice.md"),
        id="body-of-twelve-thousand-characters",
    ),
    case(
        {"rules/voice.md": "x" * 8_979},
        ("oversize-body", RuleSubject("voice"), None, "rules/voice.md"),
        id="one-character-past-the-budget",
    ),
    case(
        {"rules/voice.md": "text\n", "rules/voice@long.md": "x" * 9_500},
        ("oversize-body", RuleSubject("voice"), None, "rules/voice@long.md"),
        id="oversize-variant-names-its-own-file",
    ),
    case(
        {
            CONFIG: "defaults: ghost\nsets:\n  a: b.*\n  b: a.*\nproject amboss:\n  include: voice\n",
            **VOICE_FILES,
        },
        ("undeclared-reference", ReferenceSubject("ghost", 1), 1),
        ("ruleset-cycle", RulesetsSubject(("a", "b")), 3),
        ("condition-invalid", BlockSubject("project amboss"), 5),
        id="one-run-reports-every-error",
    ),
]

SILENT_CASES = [
    pytest.param(
        {CONFIG: "defaults: voice@terse voice@terse\n", **VARIANTS}, id="one-variant-named-twice"
    ),
    pytest.param(
        {
            CONFIG: "defaults:\n  include: voice@terse voice@warm\n  exclude: voice@warm\n",
            **VARIANTS,
        },
        id="strike-leaves-one-variant",
    ),
    pytest.param(
        {
            CONFIG: "models: opus sonnet\nmodel opus:\n  include: voice@terse\nmodel sonnet:\n  include: voice@warm\n",
            **VARIANTS,
        },
        id="blocks-for-different-models-setting-different-variants",
    ),
    pytest.param(
        {CONFIG: "agent eval-runner:\n  include: voice\n", **VOICE_FILES},
        id="agent-nobody-declares",
    ),
    pytest.param(
        {CONFIG: "flags: strict\nflag strict:\n  include: voice\n", **VOICE_FILES},
        id="declared-flag-nobody-sets",
    ),
    pytest.param(
        {
            CONFIG: "models: haiku\n(agent a or kind delegate) and not model haiku:\n  include: voice\n",
            **VOICE_FILES,
        },
        id="correct-condition",
    ),
    pytest.param(
        {CONFIG: "models: opus\nmodel opus:\n  include: voice\n", **VOICE_FILES},
        id="declared-model",
    ),
    pytest.param(
        {CONFIG: "defaults: voice@terse tone.*\nsets:\n  tone: voice\n", **VARIANTS},
        id="declared-variant-and-set",
    ),
    pytest.param(
        {"rules/tone.md": "t\n", "rules/tone@dry.md": "d\n"}, id="variant-beside-its-default"
    ),
    pytest.param(
        {"rules/voice.md": "---\ndescription: tone\n---\ntext\n"},
        id="frontmatter-without-a-condition",
    ),
    pytest.param(
        {CONFIG: "models: opus opus-4-8[1m]\n"}, id="model-name-holding-brackets-written-as-a-word"
    ),
    # 8,978 characters plus the 22-character marker line make the 9,000 `docs/commands.md` allows.
    pytest.param({"rules/voice.md": "x" * 8_978}, id="body-exactly-at-the-budget"),
    pytest.param(VOICE_FILES, id="missing-config-reads-as-every-rule"),
    pytest.param({}, id="directory-holding-nothing"),
    pytest.param(
        {
            CONFIG: "models: haiku\ndefaults:\n  include: all.*\n  exclude: security\nsets:\n  code: voice\n"
            "model haiku:\n  include: voice@terse\n",
            **VARIANTS,
            "rules/security.md": "s\n",
        },
        id="clean-directory",
    ),
]


@pytest.mark.parametrize(("files", "wanted"), ERROR_CASES)
def test_each_illegal_state_is_an_error_with_its_kind_subject_file_and_line(
    tmp_path, files, wanted
) -> None:
    found = errors_of(build(tmp_path, files))

    assert matches(found, wanted), f"found {found}, wanted {wanted}"


@pytest.mark.parametrize("files", SILENT_CASES)
def test_a_legal_state_draws_no_error(tmp_path, files) -> None:
    assert errors_of(build(tmp_path, files)) == []


def test_a_condition_written_twice_is_one_error_naming_the_second_line_and_delivers_neither_block(
    tmp_path,
) -> None:
    filler = "".join(f"# line {n}\n" for n in range(2, 20))
    config = (
        f"models: haiku\n{filler}model haiku:\n  include: voice\n"
        + "".join(f"# line {n}\n" for n in range(22, 30))
        + "model haiku:\n  include: tone\n"
    )
    root = build(tmp_path, {CONFIG: config, **VOICE_FILES, "rules/tone.md": "t\n"})
    facts = Facts(model="haiku", agent=ABSENT, kind="session", flags=frozenset(), session=ABSENT)

    delivered = compose(read_directory(root), facts, SessionState()).rules

    assert errors_of(root) == [("duplicate-key", KeySubject("model haiku"), CONFIG, 20)]
    assert [rule.rule for rule in delivered] == []
