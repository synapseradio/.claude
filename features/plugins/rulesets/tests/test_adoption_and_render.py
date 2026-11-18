#!/usr/bin/env -S uv run --frozen
"""A person sees their composed rules as plain files and hands them to a tool that knows no rulesets.

Serves the person who leaves the engine, edits through a composed view, or gates a push on a
current render tree. Each case builds a rulesets directory under `tmp_path`, runs the `eject`,
`render`, `split`, `adopt`, or `compare` subcommand as a script, and reads the files and the lines
it prints. Expected values come from `docs/commands.md` and the fixture files, never from the
engine's own composition.

Run with `uv run --frozen pytest features/plugins/rulesets/tests/test_adoption_and_render.py`.
"""

import hashlib
import pathlib
import re
import subprocess
import sys

import pytest
from delivery_world import World
from tier_corpus import FAMILIES, Corpus, define_agent

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "lib" / "rulesets" / "cli.py"


def run(*arguments) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        capture_output=True,
        text=True,
        check=False,
        cwd=CLI.parent,
    )


def checksums(root) -> dict[pathlib.Path, str]:
    """The SHA-256 of every file under `root`, by its path relative to `root`."""
    return {
        path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def eject(world, out) -> subprocess.CompletedProcess[str]:
    return run("eject", "--out", str(out), "--root", str(world.rulesets))


class TestEjectWritesTheBaseContextAsPlainFiles:
    def test_file_names_sort_into_delivery_sequence_and_each_file_holds_its_rules_text(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("core-rules", "core rules\n")
        world.rule("sorting", "sort things\n")
        world.write_config("defaults: writing-code core-rules sorting\n")
        (world.rulesets / "notes.txt").write_text("unrelated\n", encoding="utf-8")
        before = checksums(world.rulesets)
        out = tmp_path / "ejected"

        result = eject(world, out)

        assert result.returncode == 0, result.stderr
        assert sorted(path.name for path in out.iterdir()) == [
            "core-rules.md",
            "sorting.md",
            "writing-code.md",
        ]
        assert (out / "core-rules.md").read_text(encoding="utf-8") == "core rules\n"
        assert (out / "sorting.md").read_text(encoding="utf-8") == "sort things\n"
        assert (out / "writing-code.md").read_text(encoding="utf-8") == "write code\n"
        delivered = world.start_session().context
        assert "".join(path.read_text(encoding="utf-8") for path in sorted(out.iterdir())) == (
            delivered
        )
        assert checksums(world.rulesets) == before

    def test_a_rule_only_a_flag_set_block_gives_a_variant_is_ejected_at_its_default_form(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("voice@warm", "warm voice\n")
        world.write_config(
            "flags: voice-terse\n"
            "defaults: voice\n"
            "flag voice-terse:\n"
            "  include: voice@terse\n"
            "not flag voice-terse:\n"
            "  include: voice@warm\n"
        )
        out = tmp_path / "ejected"

        result = eject(world, out)

        assert result.returncode == 0, result.stderr
        assert [path.name for path in out.iterdir()] == ["voice.md"]
        assert (out / "voice.md").read_text(encoding="utf-8") == "plain voice\n"

    def test_a_rule_withheld_by_a_check_error_gets_no_file_and_is_named(self, tmp_path) -> None:
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("scoped", "---\nwhen: model haiku\n---\nscoped text\n")
        world.write_config("defaults: core-rules scoped\n")
        out = tmp_path / "ejected"

        result = eject(world, out)

        assert result.returncode == 0, result.stderr
        assert [path.name for path in out.iterdir()] == ["core-rules.md"]
        assert len([line for line in result.stdout.splitlines() if "scoped" in line]) == 1

    def test_the_report_lists_each_block_and_each_variant_with_its_file_and_line(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.write_config("models: haiku\ndefaults: voice\nmodel haiku:\n  exclude: voice\n")

        result = eject(world, tmp_path / "ejected")

        assert result.returncode == 0, result.stderr
        lines = result.stdout.splitlines()
        config_line = f"{world.rulesets / 'config.yaml'}:3:"
        variant_line = f"{world.rulesets / 'rules' / 'voice@terse.md'}:1:"
        assert [line for line in lines if line.startswith(config_line)] == [
            f"{config_line} block `model haiku` is not carried by plain files"
        ]
        assert [line for line in lines if line.startswith(variant_line)] == [
            f"{variant_line} variant `terse` of rule `voice` is not carried by plain files"
        ]


def render_context(world, out, *context) -> subprocess.CompletedProcess[str]:
    return run("render", *context, "--out", str(out), "--root", str(world.rulesets))


class TestRenderWritesOneContextsComposedText:
    def test_two_contexts_on_different_models_each_get_their_own_rules_and_variants(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("data-modeling", "model the data\n")
        world.rule("writing-prose", "default prose\n")
        world.rule("writing-prose@haiku", "haiku prose\n")
        world.write_config(
            "models: haiku opus\n"
            "defaults: writing-prose data-modeling core-rules\n"
            "model haiku:\n"
            "  include: writing-prose@haiku\n"
            "  exclude: data-modeling\n"
        )
        haiku, opus = tmp_path / "haiku.md", tmp_path / "opus.md"

        assert render_context(world, haiku, "--model", "haiku").returncode == 0
        assert render_context(world, opus, "--model", "opus").returncode == 0

        assert haiku.read_text(encoding="utf-8") == (
            "<!-- rule: core-rules -->\ncore rules\n\n"
            "<!-- rule: writing-prose variant: haiku -->\nhaiku prose\n"
        )
        assert opus.read_text(encoding="utf-8") == (
            "<!-- rule: core-rules -->\ncore rules\n\n"
            "<!-- rule: data-modeling -->\nmodel the data\n\n"
            "<!-- rule: writing-prose -->\ndefault prose\n"
        )

    def test_a_rule_the_context_receives_and_check_withholds_gets_no_marker_and_no_text(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("scoped", "---\nwhen: model haiku\n---\nscoped text\n")
        world.write_config("defaults: core-rules scoped\n")
        out = tmp_path / "context.md"

        result = render_context(world, out)

        assert result.returncode == 0, result.stderr
        assert out.read_text(encoding="utf-8") == "<!-- rule: core-rules -->\ncore rules\n"

    def test_a_marker_line_precedes_the_exact_bytes_of_each_rules_file(self, tmp_path) -> None:
        world = World(tmp_path)
        core = b"core rules\r\n\xc3\xa9cole\n"
        voice = b"plain voice\n\n"
        (world.rulesets / "rules" / "core-rules.md").write_bytes(core)
        (world.rulesets / "rules" / "voice.md").write_bytes(voice)
        world.write_config("defaults: voice core-rules\n")
        out = tmp_path / "context.md"

        assert render_context(world, out).returncode == 0

        assert out.read_bytes() == (
            b"<!-- rule: core-rules -->\n" + core + b"\n<!-- rule: voice -->\n" + voice
        )


def render_tree(world, *options) -> subprocess.CompletedProcess[str]:
    return run("render", *options, "--root", str(world.rulesets))


def outside_the_render_folder(world) -> dict[pathlib.Path, str]:
    return {
        path: digest
        for path, digest in checksums(world.rulesets).items()
        if path.parts[0] != "-render"
    }


class TestRenderWritesTheTreeToAReservedFolder:
    def test_the_folder_loses_a_render_no_longer_declared_and_no_file_outside_it_changes(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("audit-method", "audit method\n")
        world.write_config("defaults: audit-method\n")
        (world.rulesets / "notes.txt").write_text("unrelated\n", encoding="utf-8")
        (world.rulesets / "references").mkdir()
        (world.rulesets / "references" / "table.md").write_text("a table\n", encoding="utf-8")
        folder = world.rulesets / "-render"
        folder.mkdir()
        (folder / "auditor.md").write_text("<!-- rule: audit-method -->\nold\n", encoding="utf-8")
        (folder / "auditor+audit-method@table.md").write_text("old\n", encoding="utf-8")
        before = outside_the_render_folder(world)

        result = render_tree(world)

        assert result.returncode == 0, result.stderr
        assert [path.name for path in folder.iterdir() if "auditor" in path.name] == []
        assert outside_the_render_folder(world) == before

    def test_check_mode_passes_on_a_fresh_tree_and_fails_naming_the_render_after_a_byte_change(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("core-rules", "core rules\n")
        world.write_config("defaults: writing-code core-rules\n")
        assert render_tree(world).returncode == 0
        assert render_tree(world, "--check").returncode == 0
        (world.rulesets / "rules" / "writing-code.md").write_text("write c0de\n", encoding="utf-8")
        before = checksums(world.rulesets)

        result = render_tree(world, "--check")

        assert result.returncode != 0
        holding = [
            path.name
            for path in (world.rulesets / "-render").iterdir()
            if "<!-- rule: writing-code -->\nwrite code\n" in path.read_text(encoding="utf-8")
        ]
        assert holding
        for name in holding:
            assert any(name in line for line in result.stdout.splitlines())
        assert checksums(world.rulesets) == before


def tree_of(world) -> dict[str, str]:
    """The text of each file in the render folder, by file name."""
    folder = world.rulesets / "-render"
    return {path.name: path.read_text(encoding="utf-8") for path in folder.iterdir()}


def render_written(world) -> dict[str, str]:
    result = render_tree(world)
    assert result.returncode == 0, result.stderr
    return tree_of(world)


class TestTheTreeHoldsEachRenderDocumented:
    def test_the_base_context_the_pool_and_each_variant_an_include_names_each_get_a_render(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("security-pass", "security pass\n")
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("voice@warm", "warm voice\n")
        world.rule("voice@loud", "loud voice\n")
        world.write_config(
            "flags: voice-terse strict\n"
            "defaults:\n"
            "  include: all.*\n"
            "  exclude: security-pass voice@warm\n"
            "flag voice-terse:\n"
            "  include: voice@terse\n"
            "flag strict:\n"
            "  include: security-pass\n"
        )

        tree = render_written(world)

        base = "<!-- rule: core-rules -->\ncore rules\n\n"
        terse = "<!-- rule: voice variant: terse -->\nterse voice\n"
        plain = "<!-- rule: voice -->\nplain voice\n"
        security = "<!-- rule: security-pass -->\nsecurity pass\n\n"
        assert tree == {
            "defaults.md": base + plain,
            "all.md": base + security + plain,
            "defaults+voice@terse.md": base + terse,
            "all+voice@terse.md": base + security + terse,
        }

    def test_each_set_gets_a_render_flattening_nested_sets_and_marking_listed_variants(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("data-modeling", "model data\n")
        world.rule("audit-method", "audit method\n")
        world.rule("report-format", "report format\n")
        world.rule("report-format@table", "report as a table\n")
        world.write_config(
            "models: haiku\n"
            "defaults: report-format\n"
            "sets:\n"
            "  code: writing-code data-modeling\n"
            "  review: code.* writing-code\n"
            "  auditor: audit-method report-format@table\n"
            "model haiku:\n"
            "  exclude: data-modeling\n"
        )

        tree = render_written(world)

        code = (
            "<!-- rule: data-modeling -->\nmodel data\n\n<!-- rule: writing-code -->\nwrite code\n"
        )
        assert tree["code.md"] == code
        assert tree["review.md"] == code
        assert tree["auditor.md"] == (
            "<!-- rule: audit-method -->\naudit method\n\n"
            "<!-- rule: report-format variant: table -->\nreport as a table\n"
        )
        assert "defaults+report-format@table.md" in tree
        assert "auditor+report-format@table.md" not in tree
        assert "none.md" not in tree
        assert "rules.md" not in tree


def edit(path, before, after) -> None:
    text = path.read_text(encoding="utf-8")
    assert before in text
    path.write_text(text.replace(before, after), encoding="utf-8")


def split(world, file) -> subprocess.CompletedProcess[str]:
    return run("split", str(file), "--root", str(world.rulesets))


SPLIT_WORLD_CONFIG = (
    "flags: voice-terse\n"
    "defaults: all.*\n"
    "sets:\n"
    "  code: writing-code data-modeling\n"
    "flag voice-terse:\n"
    "  include: voice@terse\n"
)


class TestTheReverseSplitWritesEachSectionBackToItsSource:
    @pytest.mark.parametrize(
        ("render", "marker", "old", "new", "source"),
        [
            (
                "defaults.md",
                "<!-- rule: core-rules -->\n",
                "core rules\n",
                "edited rules\n",
                "core-rules.md",
            ),
            (
                "all+voice@terse.md",
                "<!-- rule: voice variant: terse -->\n",
                "terse voice\n",
                "edited terse\n",
                "voice@terse.md",
            ),
            (
                "code.md",
                "<!-- rule: writing-code -->\n",
                "write code\n",
                "write well\n",
                "writing-code.md",
            ),
        ],
        ids=["context render", "variant section", "set render"],
    )
    def test_an_edit_to_one_section_goes_to_that_rules_file_only(
        self, tmp_path, render, marker, old, new, source
    ) -> None:
        world = World(tmp_path)
        for name, text in (
            ("core-rules", "core rules\n"),
            ("writing-code", "write code\n"),
            ("data-modeling", "model data\n"),
            ("voice", "plain voice\n"),
            ("voice@terse", "terse voice\n"),
        ):
            world.rule(name, text)
        world.write_config(SPLIT_WORLD_CONFIG)
        assert render_tree(world).returncode == 0
        rendered = world.rulesets / "-render" / render
        before = outside_the_render_folder(world)
        edit(rendered, marker + old, marker + new)

        result = split(world, rendered)

        assert result.returncode == 0, result.stderr
        assert (world.rulesets / "rules" / source).read_text(encoding="utf-8") == new
        after = outside_the_render_folder(world)
        untouched = {path for path in before if path.name != source}
        assert {path: after[path] for path in untouched} == {
            path: before[path] for path in untouched
        }

    def test_the_split_over_every_render_in_the_tree_leaves_the_pool_as_it_was(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        world.rule("core-rules", "core rules\r\n\n")
        world.rule("voice", "plain voice\n\n")
        world.rule("voice@terse", "terse voice")
        world.rule("last", "no trailing newline")
        world.write_config(
            "flags: voice-terse\n"
            "defaults: all.*\n"
            "sets:\n"
            "  tone: voice last\n"
            "flag voice-terse:\n"
            "  include: voice@terse\n"
        )
        before = outside_the_render_folder(world)

        assert render_tree(world).returncode == 0
        for file in sorted((world.rulesets / "-render").iterdir()):
            result = split(world, file)
            assert result.returncode == 0, result.stderr

        assert outside_the_render_folder(world) == before


class TestTheReverseSplitRefusesAMalformedRenderedFile:
    @pytest.mark.parametrize(
        ("content", "named"),
        [
            ("a stray line\n<!-- rule: core-rules -->\nedited\n", None),
            (
                "<!-- rule: core-rules -->\nedited\n\n<!-- rule: ghost-rule -->\nghost\n",
                "ghost-rule",
            ),
        ],
        ids=["text before the first marker", "a marker naming a rule the pool lacks"],
    )
    def test_the_split_writes_nothing_and_exits_nonzero(self, tmp_path, content, named) -> None:
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.write_config("defaults: core-rules\n")
        rendered = tmp_path / "context.md"
        rendered.write_text(content, encoding="utf-8")
        before = checksums(world.rulesets)

        result = split(world, rendered)

        assert result.returncode != 0
        if named:
            assert named in result.stdout + result.stderr
        assert checksums(world.rulesets) == before


def adopt(source, out, *expect) -> subprocess.CompletedProcess[str]:
    return run(
        "adopt", "--from", str(source), "--out", str(out), *(f"--expect={e}" for e in expect)
    )


def compare(source, directory, *expect) -> subprocess.CompletedProcess[str]:
    return run("compare", str(source), str(directory), *(f"--expect={e}" for e in expect))


def different_lines(result) -> list[str]:
    return [line for line in result.stdout.splitlines() if line.startswith("different")]


def compared_count(result) -> int:
    match = re.search(r"compared (\d+) contexts", result.stdout)
    assert match, result.stdout
    return int(match.group(1))


_MARKER_LINE = re.compile(r"^<!-- rule: (\S+)(?: variant: (\S+))? -->\n", re.MULTILINE)


def rendered_rules(path) -> dict[str, str]:
    """The text of each rule in a context render, by rule name."""
    text = path.read_text(encoding="utf-8")
    found = list(_MARKER_LINE.finditer(text))
    rules = {}
    for index, match in enumerate(found):
        last = index + 1 == len(found)
        body = text[match.end() : len(text) if last else found[index + 1].start()]
        rules[match.group(1)] = body if last else body.removesuffix("\n")
    return rules


def delivered_to(out, tmp_path, model, agent=None) -> dict[str, str]:
    """The rules and text a context receives from the rulesets directory `out`."""
    target = tmp_path / f"render-{model}-{agent}.md"
    context = ["--model", model, *(["--agent", agent, "--kind", "delegate"] if agent else [])]
    result = run("render", *context, "--out", str(target), "--root", str(out))
    assert result.returncode == 0, result.stderr
    return rendered_rules(target)


class TestAdoptChangesNoSourceFile:
    def test_a_successful_adopt_leaves_every_source_unchanged_and_writes_only_the_output_directory(
        self, tmp_path, monkeypatch
    ) -> None:
        config = tmp_path / "config"
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        corpus = Corpus(tmp_path, left_out={"sonnet": ["spawn-decision"]})
        corpus.body("default", "core-rules")
        corpus.body("default", "spawn-decision")
        corpus.body("haiku", "core-rules")
        define_agent(config, "eval-runner", ["core-rules"])
        define_agent(config, "auditor", [])
        out = tmp_path / "adopted"
        out.mkdir()
        before = checksums(tmp_path)

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        outside = {
            path: digest
            for path, digest in checksums(tmp_path).items()
            if not path.is_relative_to("adopted")
        }
        assert outside == before
        assert (out / "rules").is_dir()
        assert (out / "config.yaml").is_file()

    @pytest.mark.parametrize("output", ["inside the source", "already holding a file"])
    def test_an_output_directory_that_is_unfit_is_refused_with_exit_2_and_nothing_written(
        self, tmp_path, output
    ) -> None:
        rules = tmp_path / "rules"
        rules.mkdir()
        (rules / "claims.md").write_text("claims text\n", encoding="utf-8")
        if output == "inside the source":
            out = rules / "adopted"
        else:
            out = tmp_path / "adopted"
            out.mkdir()
            (out / "notes.txt").write_text("keep me\n", encoding="utf-8")
        before = checksums(tmp_path)

        result = adopt(rules, out)

        assert result.returncode == 2
        assert str(out) in result.stderr
        assert checksums(tmp_path) == before
        assert out.exists() == (output == "already holding a file")


class TestAdoptMapsASourceToARulesetsDirectory:
    def test_a_rules_folder_becomes_a_pool_of_unchanged_files_every_context_receives(
        self, tmp_path
    ) -> None:
        rules = tmp_path / "rules"
        rules.mkdir()
        (rules / "breaks.md").write_bytes(b"breaks text\r\nsecond line\n")
        (rules / "claims.md").write_bytes(b"claims text\n")
        out = tmp_path / "adopted"

        result = adopt(rules, out)

        assert result.returncode == 0, result.stderr
        assert (out / "rules" / "breaks.md").read_bytes() == b"breaks text\r\nsecond line\n"
        assert (out / "rules" / "claims.md").read_bytes() == b"claims text\n"
        assert set(delivered_to(out, tmp_path, "opus")) == {"breaks", "claims"}
        assert run("check", "--root", str(out)).returncode == 0

    def test_a_source_files_own_marker_and_the_blank_line_after_it_stay_out_of_the_pool(
        self, tmp_path
    ) -> None:
        corpus = Corpus(tmp_path)
        marker = "<!-- rule: core-rules -->\n\n"
        corpus.raw("default", "core-rules", marker + "default text\n")
        corpus.raw("haiku", "core-rules", marker + "haiku text\n")
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert (out / "rules" / "core-rules.md").read_bytes() == b"default text\n"
        assert (out / "rules" / "core-rules@haiku.md").read_bytes() == b"haiku text\n"

    def test_an_opening_line_that_is_not_the_files_own_marker_stays_and_the_context_differs(
        self, tmp_path
    ) -> None:
        corpus = Corpus(tmp_path)
        corpus.raw("default", "voice", "<!-- rule: sorting -->\nvoice text\n")
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert (out / "rules" / "voice.md").read_bytes() == b"<!-- rule: sorting -->\nvoice text\n"
        assert result.returncode != 0
        assert any("voice" in line for line in different_lines(result))

    def test_a_stem_only_a_tier_holds_is_skipped_and_named_in_the_report(self, tmp_path) -> None:
        corpus = Corpus(tmp_path)
        corpus.body("default", "core-rules")
        corpus.body("haiku", "extra")
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        named = [line for line in result.stdout.splitlines() if "haiku/extra.md" in line]
        assert len(named) == 1
        assert "skipped" in named[0]
        assert not [path for path in (out / "rules").iterdir() if path.name.startswith("extra")]

    def test_a_path_scoped_rule_file_stays_out_of_the_pool_and_is_named_in_the_report(
        self, tmp_path
    ) -> None:
        rules = tmp_path / "rules"
        rules.mkdir()
        (rules / "testing.md").write_text(
            '---\npaths:\n  - "**/*.test.ts"\n---\ntest rules\n', encoding="utf-8"
        )
        (rules / "claims.md").write_text("claims text\n", encoding="utf-8")
        out = tmp_path / "adopted"

        result = adopt(rules, out)

        assert result.returncode == 0, result.stderr
        assert [path.name for path in (out / "rules").iterdir()] == ["claims.md"]
        named = [line for line in result.stdout.splitlines() if "testing.md" in line]
        assert len(named) == 1
        assert "skipped" in named[0]


class TestAdoptProvesEveryContextsTextUnchanged:
    def test_adopt_exits_zero_and_every_context_receives_the_rules_and_text_the_corpus_delivers(
        self, tmp_path, monkeypatch
    ) -> None:
        config = tmp_path / "config"
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        corpus = Corpus(tmp_path, left_out={"sonnet": ["agent-delegation"]})
        texts = {
            (tier, stem): corpus.body(tier, stem)
            for tier, stem in [
                ("default", "core-rules"),
                ("default", "writing-prose"),
                ("default", "agent-delegation"),
                ("haiku", "writing-prose"),
            ]
        }
        definition = define_agent(config, "eval-runner", ["writing-prose"])
        recorded = definition.read_bytes()
        define_agent(config, "auditor", ["core-rules"])
        excluded_by = {None: set(), "eval-runner": {"writing-prose"}, "auditor": {"core-rules"}}
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert different_lines(result) == []
        assert definition.read_bytes() == recorded
        for model in FAMILIES:
            for agent, excluded in excluded_by.items():
                expected = {
                    stem: texts.get((model, stem), texts[("default", stem)])
                    for stem in ("core-rules", "writing-prose", "agent-delegation")
                    if stem not in excluded
                    and not (model == "sonnet" and stem == "agent-delegation")
                }
                assert delivered_to(out, tmp_path, model, agent) == expected, (model, agent)

    def test_a_context_delivering_rules_in_another_sequence_is_reported_equal(
        self, tmp_path
    ) -> None:
        corpus = Corpus(tmp_path, order=["writing-code", "core-rules"])
        core = corpus.body("default", "core-rules")
        code = corpus.body("default", "writing-code")
        world = World(tmp_path)
        world.rule("core-rules", core)
        world.rule("writing-code", code)
        world.write_config("models: opus sonnet haiku fable\ndefaults: all.*\n")

        result = compare(corpus.root, world.rulesets)

        assert result.returncode == 0, result.stdout + result.stderr
        assert different_lines(result) == []

    def test_the_model_named_tier_matches_the_corpus_when_the_config_declares_its_name(
        self, tmp_path, monkeypatch
    ) -> None:
        corpus = Corpus(tmp_path, extra_tiers=("claude-opus-4-8",))
        default_text = corpus.body("default", "spawn-decision")
        opus_text = corpus.body("opus", "spawn-decision")
        world = World(tmp_path)
        world.rule("spawn-decision", default_text)
        world.rule("spawn-decision@opus", opus_text)
        world.write_config(
            "models: opus sonnet haiku fable opus-4-8\n"
            "defaults: all.*\n"
            "model opus:\n"
            "  include: spawn-decision@opus\n"
        )
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(world.config))
        target = tmp_path / "context.md"

        rendered = render_context(world, target, "--model", "claude-opus-4-8")
        result = compare(corpus.root, world.rulesets)

        assert rendered.returncode == 0, rendered.stderr
        assert rendered_rules(target) == {"spawn-decision": default_text}
        assert result.returncode == 0, result.stdout + result.stderr

    def test_the_model_named_tier_takes_opus_when_the_config_lacks_its_name(self, tmp_path) -> None:
        corpus = Corpus(tmp_path, extra_tiers=("claude-opus-4-8",))
        default_text = corpus.body("default", "spawn-decision")
        opus_text = corpus.body("opus", "spawn-decision")
        world = World(tmp_path)
        world.rule("spawn-decision", default_text)
        world.rule("spawn-decision@opus", opus_text)
        world.write_config(
            "models: opus sonnet haiku fable\n"
            "defaults: all.*\n"
            "model opus:\n"
            "  include: spawn-decision@opus\n"
        )
        target = tmp_path / "context.md"

        rendered = render_context(world, target, "--model", "claude-opus-4-8")
        result = compare(corpus.root, world.rulesets)

        assert rendered.returncode == 0, rendered.stderr
        assert rendered_rules(target) == {"spawn-decision": opus_text}
        assert result.returncode != 0
        named = [line for line in different_lines(result) if "claude-opus-4-8" in line]
        assert len(named) == 1
        assert "spawn-decision" in named[0]
        assert "opus" in named[0].split("spawn-decision", 1)[1]

    def test_an_expected_difference_is_listed_while_the_comparison_exits_zero(
        self, tmp_path, monkeypatch
    ) -> None:
        corpus = Corpus(tmp_path, extra_tiers=("claude-opus-4-8",))
        default_text = corpus.body("default", "spawn-decision")
        opus_text = corpus.body("opus", "spawn-decision")
        world = World(tmp_path)
        world.rule("spawn-decision", default_text)
        world.rule("spawn-decision@opus", opus_text)
        world.write_config(
            "models: opus sonnet haiku fable opus-4-8\n"
            "defaults: all.*\n"
            "model opus:\n"
            "  include: spawn-decision@opus\n"
        )
        world.start_session(model="claude-opus-4-8[1m]")
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(world.config))

        expected = compare(corpus.root, world.rulesets, "claude-opus-4-8[1m]")
        unexpected = compare(corpus.root, world.rulesets)

        assert expected.returncode == 0, expected.stdout + expected.stderr
        listed = [line for line in expected.stdout.splitlines() if "claude-opus-4-8[1m]" in line]
        assert len(listed) == 1
        assert "spawn-decision" in listed[0]
        assert different_lines(expected) == []
        assert unexpected.returncode != 0


class TestTheComparisonMatrixCrossesModelsAndAgents:
    def test_an_identifier_passed_with_expect_joins_the_matrix_for_each_agent_and_for_no_agent(
        self, tmp_path, monkeypatch
    ) -> None:
        world = World(tmp_path)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(world.config))
        define_agent(world.config, "eval-runner", [])
        define_agent(world.config, "auditor", [])
        corpus = Corpus(tmp_path)
        world.rule("core-rules", corpus.body("default", "core-rules"))
        world.write_config("models: opus sonnet haiku fable\ndefaults: all.*\n")

        without = compare(corpus.root, world.rulesets)
        with_expect = compare(corpus.root, world.rulesets, "claude-opus-4-8[1m]")

        assert compared_count(with_expect) - compared_count(without) == 3


class TestTheComparisonReportNamesEachContextThatDiffers:
    def test_the_report_names_a_differing_delegate_context_and_its_first_differing_rule_and_variant(
        self, tmp_path, monkeypatch
    ) -> None:
        config = tmp_path / "config"
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        corpus = Corpus(tmp_path)
        corpus.body("default", "core-rules")
        corpus.body("default", "writing-prose")
        corpus.body("haiku", "writing-prose", "---\nwhen: model haiku\n---\nhaiku prose\n")
        define_agent(config, "eval-runner", ["core-rules"])
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode != 0
        named = [
            line for line in different_lines(result) if "eval-runner" in line and "haiku" in line
        ]
        assert len(named) == 1
        assert "writing-prose" in named[0]
        assert "variant haiku" in named[0]

    def test_compare_catches_an_edit_made_to_a_variant_after_adoption(self, tmp_path) -> None:
        corpus = Corpus(tmp_path)
        corpus.body("default", "writing-prose")
        corpus.body("haiku", "writing-prose")
        out = tmp_path / "adopted"
        assert adopt(corpus.root, out).returncode == 0
        assert compare(corpus.root, out).returncode == 0
        with (out / "rules" / "writing-prose@haiku.md").open("a", encoding="utf-8") as edited:
            edited.write("an edit made later\n")

        result = compare(corpus.root, out)

        assert result.returncode != 0
        first = different_lines(result)[0]
        assert "haiku" in first
        assert "writing-prose" in first
        assert "variant haiku" in first
