#!/usr/bin/env python3
"""A context receives the rules its applying lists leave on, each at the variant they settle.

The composition serves the engineer who writes a config and the person whose agents receive
the result: a block keyed on a fact reaches the contexts where the key holds, the statements of
every applying list settle each rule's inclusion and variant by position, and check names the
conflicts and layout problems that make a composition surprising. Each case builds its rulesets
directory under `tmp_path` and composes a context from named facts. The orderings come from
`docs/config.md`, "Which statement wins", and the check findings from `docs/commands.md`.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_ruleset_composition.py`.
"""

import pathlib
import re
import sys
from typing import NamedTuple

import pytest
from delivery_world import DECLARED, OPUS, World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import spawn_log  # noqa: E402
from rulesets.cli import main  # noqa: E402
from rulesets.compose.composition import compose  # noqa: E402
from rulesets.facts.context import ABSENT, Facts  # noqa: E402
from rulesets.locations import Locations  # noqa: E402
from rulesets.session.state import Band, SessionState, read_state, write_state  # noqa: E402
from rulesets.source.directory import read_directory  # noqa: E402


def build(tmp_path, config, rules) -> pathlib.Path:
    """A rulesets directory with the config text and a rule file per stem.

    `rules` maps a stem to its text, or to None for a stem holding the text `text of <stem>`.
    """
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    if config is not None:
        (root / "config.yaml").write_text(config, encoding="utf-8")
    for stem, text in rules.items():
        body = f"text of {stem}\n" if text is None else text
        (root / "rules" / f"{stem}.md").write_text(body, encoding="utf-8")
    return root


def context(*, model=None, agent=None, kind="session", flags=(), session=None) -> Facts:
    return Facts(
        model=ABSENT if model is None else model,
        agent=ABSENT if agent is None else agent,
        kind=kind,
        flags=frozenset(flags),
        session=ABSENT if session is None else session,
    )


def received(root, facts, state=None) -> dict[str, str | None]:
    """The rules the context receives, as a mapping of rule name to variant (None: default form)."""
    composition = compose(read_directory(root), facts, state or SessionState())
    return {d.rule: d.variant for d in composition.rules}


class Finding(NamedTuple):
    severity: str
    kind: str
    path: pathlib.Path
    message: str


_FINDING = re.compile(
    r"^(?P<path>.+?)(?::\d+)?: (?P<severity>error|warning) \[(?P<kind>[\w-]+)\] (?P<message>.*)$"
)


def check_findings(root, capsys) -> tuple[int, list[Finding]]:
    """The exit status of `check --root` and each finding line it prints."""
    status = main(["check", "--root", str(root)])
    found = []
    for line in capsys.readouterr().out.splitlines():
        match = _FINDING.match(line)
        assert match, line
        found.append(
            Finding(match["severity"], match["kind"], pathlib.Path(match["path"]), match["message"])
        )
    return status, found


def notice_entries(world, kind) -> list[dict]:
    return [n for r in world.records() for n in r["notices"] if n["kind"] == kind]


VOICE = {"voice": None, "voice@terse": None, "voice@warm": None}

CRITIC = {"agent": "critic", "kind": "delegate"}

# Each row: a config, the rules in the pool, and for each context its facts and the rules and
# variants it receives (None: the default form).
WHICH_STATEMENT_WINS = {
    "a model block removes a rule from every context on that model and no other": (
        "models: opus haiku\ndefaults: writing-code\nmodel haiku:\n  exclude: writing-code\n",
        {"writing-code": None},
        [
            (dict(model="haiku", **CRITIC), {}),
            (dict(model="haiku"), {}),
            (dict(model="opus", **CRITIC), {"writing-code": None}),
            (dict(model="opus"), {"writing-code": None}),
        ],
    ),
    "a rule for one agent on one model reaches that agent on that model only": (
        "models: opus sonnet\ndefaults:\nagent critic and model opus:\n  include: security-pass\n",
        {"security-pass": None},
        [
            (dict(model="opus", **CRITIC), {"security-pass": None}),
            (dict(model="sonnet", **CRITIC), {}),
            (dict(model="opus", agent="auditor", kind="delegate"), {}),
        ],
    ),
    "a ruleset at a variant gives that wording to its agent and the default to others": (
        "defaults: all.*\n"
        "sets:\n"
        "  auditor: report-format@table\n"
        "agent auditor:\n"
        "  include: auditor.*\n",
        {"report-format": None, "report-format@table": None},
        [
            (dict(agent="auditor", kind="delegate"), {"report-format": "table"}),
            (dict(**CRITIC), {"report-format": None}),
            (dict(), {"report-format": None}),
        ],
    ),
    "an include adds, an exclude removes, and a variant exclude strikes alone": (
        "flags: strict\n"
        "defaults: all.* tone@dry\n"
        "flag strict:\n"
        "  include: voice@terse\n"
        "  exclude: writing-code tone@dry\n",
        {"voice": None, "voice@terse": None, "writing-code": None, "tone": None, "tone@dry": None},
        [(dict(flags=["strict"]), {"voice": "terse", "tone": None})],
    ),
    "a rule no applying statement includes stays off": (
        "flags: strict\ndefaults: sorting\nflag strict:\n  include: voice\n",
        {"voice": None, "sorting": None},
        [(dict(), {"sorting": None})],
    ),
    "a block that excludes a rule defaults include leaves it off": (
        "flags: strict\ndefaults: voice\nflag strict:\n  exclude: voice\n",
        {"voice": None},
        [(dict(flags=["strict"]), {}), (dict(), {"voice": None})],
    ),
    "a block that includes a rule defaults exclude turns it on": (
        "flags: a\ndefaults:\n  exclude: voice\nflag a:\n  include: voice\n",
        {"voice": None},
        [(dict(flags=["a"]), {"voice": None}), (dict(), {})],
    ),
    "a rule named in an exclude beats the same rule reached through a set": (
        "flags: a b\ndefaults:\nsets:\n  review: voice\nflag a:\n  include: review.*\n"
        "flag b:\n  exclude: voice\n",
        {"voice": None},
        [(dict(flags=["a", "b"]), {})],
    ),
    "a rule named in an include beats the same rule reached through a set exclude": (
        "flags: a b\ndefaults:\nsets:\n  review: voice\nflag a:\n  include: voice\n"
        "flag b:\n  exclude: review.*\n",
        {"voice": None},
        [(dict(flags=["a", "b"]), {"voice": None})],
    ),
    "an exclude beats an include of the same rule at one rank, listed after it": (
        "flags: a b\ndefaults:\nflag a:\n  include: voice\nflag b:\n  exclude: voice\n",
        {"voice": None},
        [(dict(flags=["a", "b"], **CRITIC), {})],
    ),
    "an exclude beats an include of the same rule at one rank, listed before it": (
        "flags: a b\ndefaults:\nflag b:\n  exclude: voice\nflag a:\n  include: voice\n",
        {"voice": None},
        [(dict(flags=["a", "b"], **CRITIC), {})],
    ),
    "a higher bare include leaves a lower set variant in force": (
        "models: haiku\nflags: strict\ndefaults:\nflag strict:\n  include: voice\n"
        "model haiku:\n  include: voice@terse\n",
        {"voice": None, "voice@terse": None},
        [(dict(model="haiku", flags=["strict"]), {"voice": "terse"})],
    ),
    "a higher strike removes a lower set so the rule arrives at its default form": (
        "flags: voice-terse\ndefaults:\nflag voice-terse:\n  include: voice@terse\n"
        "session abc123:\n  exclude: voice@terse\n",
        {"voice": None, "voice@terse": None},
        [
            (dict(kind="delegate", flags=["voice-terse"], session="abc123"), {"voice": None}),
            (dict(kind="delegate", flags=["voice-terse"]), {"voice": "terse"}),
        ],
    ),
    "a strike at a lower position than the set leaves the set standing": (
        "models: haiku\nflags: voice-terse\ndefaults:\nmodel haiku:\n  exclude: voice@terse\n"
        "flag voice-terse:\n  include: voice@terse\n",
        {"voice": None, "voice@terse": None},
        [(dict(model="haiku", flags=["voice-terse"]), {"voice": "terse"})],
    ),
    "a strike strikes only the variant it names and leaves the rule on": (
        "models: haiku\nflags: strict\ndefaults: voice@warm\nmodel haiku:\n  include: voice@terse\n"
        "flag strict:\n  exclude: voice@terse\n",
        VOICE,
        [
            (dict(model="haiku"), {"voice": "terse"}),
            (dict(model="haiku", flags=["strict"]), {"voice": "warm"}),
        ],
    ),
    "a strike below a set leaves the rule on and the set variant standing": (
        "flags: a\ndefaults:\n  include: voice\n  exclude: voice@terse\nflag a:\n"
        "  include: voice@terse\n",
        {"voice": None, "voice@terse": None},
        [(dict(flags=["a"]), {"voice": "terse"}), (dict(), {"voice": None})],
    ),
    "a third statement striking one of two variants leaves the other in force": (
        "flags: a b c\ndefaults:\nflag a:\n  include: voice@terse\nflag b:\n"
        "  include: voice@warm\nflag c:\n  exclude: voice@warm\n",
        VOICE,
        [(dict(flags=["a", "b", "c"]), {"voice": "terse"})],
    ),
    "an exclude inside a spread ruleset subtracts from it and excludes nothing from the context": (
        "flags: f\ndefaults: voice\nsets:\n  lean:\n    include: all.*\n    exclude: voice\n"
        "flag f:\n  include: lean.*\n",
        {"voice": None, "sorting": None, "tone": None},
        [(dict(flags=["f"]), {"sorting": None, "tone": None, "voice": None})],
    ),
    "a block with both lists includes all but what it excludes": (
        "sets:\n  bash: shell-scripts\nkind session:\n  include: all.*\n"
        "  exclude: bash.shell-scripts\n",
        {"shell-scripts": None, "voice": None, "sorting": None},
        [(dict(), {"voice": None, "sorting": None})],
    ),
    "a nested model test applies only where both conditions hold": (
        "models: opus haiku\ndefaults:\nsets:\n  planning: plan-steps\nagent Plan:\n"
        "  not model haiku:\n    include: planning.*\n",
        {"plan-steps": None},
        [
            (dict(model="opus", agent="Plan", kind="delegate"), {"plan-steps": None}),
            (dict(model="haiku", agent="Plan", kind="delegate"), {}),
        ],
    ),
    "an exclude under then leaves the variant the block set": (
        "models: haiku\ndefaults:\nsets:\n  prose: writing-prose\nmodel haiku:\n"
        "  include: prose.writing-prose@haiku\n  then:\n    exclude: prose.writing-prose\n"
        "agent orchestrator:\n  include: prose.*\n",
        {"writing-prose": None, "writing-prose@haiku": None},
        [(dict(model="haiku", agent="orchestrator", kind="delegate"), {"writing-prose": "haiku"})],
    ),
    "the same exclude in the blocks own list cancels the variant": (
        "models: haiku\ndefaults:\nsets:\n  prose: writing-prose\nmodel haiku:\n"
        "  include: prose.writing-prose@haiku\n  exclude: prose.writing-prose\n"
        "agent orchestrator:\n  include: prose.*\n",
        {"writing-prose": None, "writing-prose@haiku": None},
        [(dict(model="haiku", agent="orchestrator", kind="delegate"), {"writing-prose": None})],
    ),
    "a block keyed on model and kind any stands at agent rank": (
        "models: haiku\ndefaults:\nmodel haiku and kind any:\n  exclude: comments\n"
        "agent general-purpose:\n  include: comments\n",
        {"comments": None},
        [(dict(model="haiku", agent="general-purpose", kind="delegate"), {})],
    ),
    "a nested kind any block stands at agent rank as its flat form does": (
        "models: haiku\ndefaults:\nmodel haiku:\n  kind any:\n    exclude: comments\n"
        "agent general-purpose:\n  include: comments\n",
        {"comments": None},
        [(dict(model="haiku", agent="general-purpose", kind="delegate"), {})],
    ),
    "a then list stands at its blocks rank below an agent block": (
        "models: haiku\ndefaults:\nmodel haiku:\n  then:\n    exclude: writing-prose\n"
        "agent orchestrator:\n  include: writing-prose\n",
        {"writing-prose": None},
        [(dict(model="haiku", agent="orchestrator", kind="delegate"), {"writing-prose": None})],
    ),
}


@pytest.mark.parametrize(
    ("config", "rules", "contexts"),
    list(WHICH_STATEMENT_WINS.values()),
    ids=list(WHICH_STATEMENT_WINS),
)
def test_each_context_receives_the_rules_and_variants_the_statements_at_the_highest_position_settle(
    tmp_path, config, rules, contexts
) -> None:
    root = build(tmp_path, config, rules)

    for facts, expected in contexts:
        assert received(root, context(**facts)) == expected, facts


def test_the_toggle_none_keeps_a_set_flags_include_out_of_a_delegate(tmp_path) -> None:
    root = build(
        tmp_path,
        "flags: strict\ndefaults:\nflag strict:\n  include: security-pass\n",
        {"security-pass": None},
    )
    locations = Locations(tmp_path / "config")
    write_state(locations, "s1", SessionState(Band.NONE))
    delegate = context(agent="critic", kind="delegate", flags=["strict"])

    assert received(root, delegate) == {"security-pass": None}
    assert received(root, delegate, read_state(locations, "s1")) == {}


class TestTwoVariantsSetAtOnePositionAreAConflict:
    @pytest.mark.parametrize(
        ("config", "conflict"),
        [
            (
                "flags: a b\ndefaults:\nflag a:\n  include: voice@terse\nflag b:\n"
                "  include: voice@warm\n",
                True,
            ),
            (
                "models: opus sonnet\ndefaults:\nmodel opus:\n  include: voice@terse\n"
                "model sonnet:\n  include: voice@warm\n",
                False,
            ),
            (
                "flags: a b\ndefaults:\nflag a:\n  include: voice@terse\nflag b:\n"
                "  include: voice@terse\n",
                False,
            ),
            (
                "flags: a b\ndefaults:\nflag a:\n  include: voice@terse\n  then:\n"
                "    exclude: voice@warm\nflag b:\n  include: voice@warm\n",
                False,
            ),
            (
                "flags: a b c\ndefaults:\nflag a:\n  include: voice@terse\nflag b:\n"
                "  include: voice@warm\nflag c:\n  exclude: voice@warm\n",
                True,
            ),
        ],
        ids=[
            "two flags set different variants",
            "blocks for different models",
            "two sets naming the same variant",
            "a third list in the same block strikes one variant",
            "a third block strikes one variant only where its own flag is set",
        ],
    )
    def test_check_fails_naming_both_variants_where_two_blocks_that_can_both_apply_disagree(
        self, tmp_path, capsys, config, conflict
    ) -> None:
        root = build(tmp_path, config, VOICE)

        status, findings = check_findings(root, capsys)

        if conflict:
            assert status == 1
            ((severity, kind, _, message),) = findings
            assert (severity, kind) == ("error", "variant-conflict")
            assert "`voice@terse`" in message
            assert "`voice@warm`" in message
        else:
            assert (status, findings) == (0, [])

    @pytest.mark.parametrize(
        ("lower", "variant"),
        [("model haiku:\n  include: voice@calm\n", "calm"), ("", None)],
        ids=["a lower position agrees on a variant", "no lower position names a variant"],
    )
    def test_delivery_keeps_the_rule_on_at_one_form_and_shows_a_notice_naming_it(
        self, tmp_path, lower, variant
    ) -> None:
        world = World(tmp_path)
        for stem in ("voice", "voice@terse", "voice@warm", "voice@calm"):
            world.rule(stem)
        world.write_config(
            "models: haiku\n"
            "flags: a b\n"
            "defaults:\n"
            "flag a:\n"
            "  include: voice@terse\n"
            "flag b:\n"
            "  include: voice@warm\n" + lower
        )
        world.environment["RULESETS_FLAGS"] = "a,b"

        delivery = world.start_session(model="claude-haiku-4-5")

        assert delivery.context == f"text of voice{f'@{variant}' if variant else ''}\n"
        (notice,) = notice_entries(world, "variant-conflict")
        assert notice["shown"]
        assert "`voice`" in notice["subject"]
        assert notice["subject"] in delivery.message


class TestCheckWarnsAboutTheLayoutOfTheRulesetsDirectory:
    @pytest.mark.parametrize(
        ("directories", "stray"),
        [(["rules/drafts"], "rules/drafts"), (["references", "-render", "drafts"], "drafts")],
        ids=["a directory in the pool", "a directory beside it other than the reserved folders"],
    )
    def test_a_directory_that_holds_no_rule_draws_one_stray_warning_and_a_zero_exit(
        self, tmp_path, capsys, directories, stray
    ) -> None:
        root = build(tmp_path, "defaults: all.*\n", {"voice": None})
        for name in directories:
            (root / name).mkdir()

        status, findings = check_findings(root, capsys)

        assert status == 0
        ((severity, kind, path, _),) = findings
        assert (severity, kind, path) == ("warning", "stray-directory", root / stray)

    def test_a_citation_of_a_missing_file_under_references_draws_a_dangling_warning(
        self, tmp_path, capsys
    ) -> None:
        root = build(
            tmp_path,
            "defaults: all.*\n",
            {"voice": "See `references/table.md` for the table.\n"},
        )

        status, findings = check_findings(root, capsys)

        assert status == 0
        ((severity, kind, path, message),) = findings
        assert (severity, kind, path) == (
            "warning",
            "dangling-reference",
            root / "rules" / "voice.md",
        )
        assert "`references/table.md`" in message


class TestABodyLongerThanThePartBudgetIsACheckError:
    @pytest.mark.parametrize(
        ("name", "size", "others"),
        [("big", 12000, ["alpha", "zeta"]), ("a-rule", 8990, [])],
        ids=["twelve thousand characters", "a body that fits only without its marker"],
    )
    def test_check_fails_naming_the_rule_and_delivery_withholds_it(
        self, tmp_path, capsys, name, size, others
    ) -> None:
        world = World(tmp_path)
        world.rule(name, "x" * size)
        for other in others:
            world.rule(other)
        world.write_config(DECLARED + "defaults: all.*\n")
        root = world.rulesets

        status, findings = check_findings(root, capsys)
        delivery = world.start_session()

        assert status == 1
        ((severity, kind, path, _),) = findings
        assert (severity, kind, path) == ("error", "oversize-body", root / "rules" / f"{name}.md")
        assert delivery.context == "".join(f"text of {other}\n" for other in others)
        assert f"`{name}`" in delivery.message
        assert world.withheld_rules() == [name]


class TestCheckWarnsAboutPartCount:
    @pytest.mark.parametrize(
        ("config", "named"),
        [
            (
                "models: opus haiku\n"
                "flags: strict lint\n"
                "defaults:\n"
                "agent critic and kind delegate and model haiku and flag strict and flag lint:\n"
                "  include: all.*\n",
                ["model haiku, agent critic, kind delegate"],
            ),
            (
                "models: opus\ndefaults: all.*\nmodel opus:\n  exclude: all.*\n",
                ["kind session", "kind delegate"],
            ),
            (None, ["kind session", "kind delegate"]),
            ("defaults: [unclosed\n", ["kind session", "kind delegate"]),
        ],
        ids=[
            "a context named by its model, agent, kind, and flags",
            "a context on a model no declared name claims",
            "a directory with no config",
            "a directory with an unparsable config",
        ],
    )
    def test_a_context_whose_rules_need_more_parts_than_a_delivery_carries_draws_a_warning_naming_it(
        self, tmp_path, capsys, config, named
    ) -> None:
        stems = {f"rule-{number:02d}": "y" * 5000 + "\n" for number in range(11)}
        root = build(tmp_path, config, stems)

        _, findings = check_findings(root, capsys)

        warnings = [f for f in findings if f.kind == "too-many-parts"]
        assert len(warnings) == len(named)
        for warning, fragment in zip(warnings, named, strict=True):
            assert fragment in warning.message


class TestTerms:
    def test_the_delivery_record_names_a_rule_in_the_main_sessions_delivery_and_not_in_a_haiku_delegates(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("writing-code")
        world.write_config(
            DECLARED + "defaults: writing-code\nmodel haiku:\n  exclude: writing-code\n"
        )
        spawn_log.append_spawn("s1", "p1", "critic", "haiku", Locations(world.config).state)

        world.start_session(model=OPUS)
        world.start_delegate("critic")

        named = {r["scope"]: [line["rule"] for line in r["rules"]] for r in world.records()}
        assert named == {"session": ["writing-code"], "delegate": []}
