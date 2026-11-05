#!/usr/bin/env python3
"""A person sees their composed rules as plain files and hands them to a tool that knows no rulesets.

Serves the person who leaves the engine, edits through a composed view, or gates a push on a
current render tree. Each case builds a rulesets directory under `tmp_path`, runs the `eject` or
`render` subcommand as a script, and reads the files and the lines it prints. Expected values come
from the specs and the fixture files, never from the engine's own composition.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_adoption_and_render.py`.
"""

import hashlib
import pathlib
import subprocess
import sys

from delivery_world import World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "lib" / "rulesets" / "cli.py"


def run(*arguments):
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        capture_output=True,
        text=True,
        check=False,
        cwd=CLI.parent,
    )


def checksums(root):
    """The SHA-256 of every file under `root`, by its path relative to `root`."""

    return {
        path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def eject(world, out):
    return run("eject", "--out", str(out), "--root", str(world.rulesets))


class TestEjectWritesTheBaseContextAsPlainFiles:
    def test_file_names_sort_into_delivery_sequence_and_each_file_holds_its_rules_text(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("core-rules", "core rules\n")
        world.rule("sorting", "sort things\n")
        world.manifest("defaults: ['writing-code', 'core-rules', 'sorting']\n")
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

    def test_a_rule_only_a_flag_set_block_gives_a_variant_is_ejected_at_its_default_form(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("voice@warm", "warm voice\n")
        world.manifest(
            "flags: ['voice-terse']\n"
            "defaults: ['voice']\n"
            "when:\n"
            "  - flag voice-terse: ['voice@terse']\n"
            "  - not flag voice-terse: ['voice@warm']\n"
        )
        out = tmp_path / "ejected"

        result = eject(world, out)

        assert result.returncode == 0, result.stderr
        assert [path.name for path in out.iterdir()] == ["voice.md"]
        assert (out / "voice.md").read_text(encoding="utf-8") == "plain voice\n"

    def test_no_file_in_the_rulesets_directory_changes(self, tmp_path):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.manifest(
            "models: ['haiku']\ndefaults: ['core-rules']\nwhen:\n  - model haiku: ['voice']\n"
        )
        (world.rulesets / "notes.txt").write_text("unrelated\n", encoding="utf-8")
        before = checksums(world.rulesets)

        result = eject(world, tmp_path / "ejected")

        assert result.returncode == 0, result.stderr
        assert checksums(world.rulesets) == before


class TestEjectLeavesOutEachWithheldRule:
    def test_a_rule_withheld_by_a_check_error_gets_no_file_and_is_named_with_its_error(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("scoped", "---\nwhen: model haiku\n---\nscoped text\n")
        world.manifest("defaults: ['core-rules', 'scoped']\n")
        out = tmp_path / "ejected"

        result = eject(world, out)

        assert result.returncode == 0, result.stderr
        assert [path.name for path in out.iterdir()] == ["core-rules.md"]
        named = [line for line in result.stdout.splitlines() if "scoped" in line]
        assert len(named) == 1
        assert "`when`" in named[0]
        assert "condition" in named[0]


class TestEjectReportsWhatPlainFilesCannotCarry:
    def test_the_report_lists_each_block_and_each_variant_with_its_file_and_line(self, tmp_path):
        world = World(tmp_path)
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.manifest(
            "models: ['haiku']\n"  # line 1
            "defaults: ['voice']\n"  # line 2
            "when:\n"  # line 3
            "  - model haiku: ['-voice']\n"  # line 4
        )

        result = eject(world, tmp_path / "ejected")

        assert result.returncode == 0, result.stderr
        lines = result.stdout.splitlines()
        manifest_line = f"{world.rulesets / 'manifest.yaml'}:4:"
        variant_line = f"{world.rulesets / 'rules' / 'voice@terse.md'}:1:"
        assert [line for line in lines if line.startswith(manifest_line)] == [
            f"{manifest_line} block `model haiku` is not carried by plain files"
        ]
        assert [line for line in lines if line.startswith(variant_line)] == [
            f"{variant_line} variant `terse` of rule `voice` is not carried by plain files"
        ]


def render_context(world, out, *context):
    return run("render", *context, "--out", str(out), "--root", str(world.rulesets))


def explained(world, rule, model):
    """What explain reports for `rule` in a context on `model`: `off`, `default`, or the variant."""

    result = run("explain", rule, "--model", model, "--root", str(world.rulesets))
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    if "inclusion: on" not in lines:
        return "off"
    variant = next(line for line in lines if line.startswith("variant:"))
    return variant.removeprefix("variant: ") if "none set" not in variant else "default"


def sections(rendered):
    """The rule and variant named by each marker line of a render, in file order."""

    found = []
    for line in rendered.splitlines():
        if line.startswith("<!-- rule: ") and line.endswith(" -->"):
            words = line.removeprefix("<!-- rule: ").removesuffix(" -->").split(" variant: ")
            found.append((words[0], words[1] if len(words) == 2 else "default"))
    return found


class TestRenderWritesOneContextsComposedText:
    def test_two_contexts_on_different_models_each_get_their_own_rules_and_variants(self, tmp_path):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("data-modeling", "model the data\n")
        world.rule("writing-prose", "default prose\n")
        world.rule("writing-prose@haiku", "haiku prose\n")
        world.manifest(
            "models: ['haiku', 'opus']\n"
            "defaults: ['writing-prose', 'data-modeling', 'core-rules']\n"
            "when:\n"
            "  - model haiku: ['-data-modeling', 'writing-prose@haiku']\n"
        )
        haiku, opus = tmp_path / "haiku.md", tmp_path / "opus.md"

        assert render_context(world, haiku, "--model", "haiku").returncode == 0
        assert render_context(world, opus, "--model", "opus").returncode == 0

        assert haiku.read_text(encoding="utf-8") == (
            "<!-- rule: core-rules -->\ncore rules\n"
            "<!-- rule: writing-prose variant: haiku -->\nhaiku prose\n"
        )
        assert opus.read_text(encoding="utf-8") == (
            "<!-- rule: core-rules -->\ncore rules\n"
            "<!-- rule: data-modeling -->\nmodel the data\n"
            "<!-- rule: writing-prose -->\ndefault prose\n"
        )
        for model, file in (("haiku", haiku), ("opus", opus)):
            received = dict(sections(file.read_text(encoding="utf-8")))
            for rule in ("core-rules", "data-modeling", "writing-prose"):
                assert received.get(rule, "off") == explained(world, rule, model)

    def test_a_rule_the_context_receives_and_check_withholds_gets_no_marker_and_no_text(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("scoped", "---\nwhen: model haiku\n---\nscoped text\n")
        world.manifest("defaults: ['core-rules', 'scoped']\n")
        out = tmp_path / "context.md"

        result = render_context(world, out)

        assert result.returncode == 0, result.stderr
        assert out.read_text(encoding="utf-8") == "<!-- rule: core-rules -->\ncore rules\n"


class TestRenderMarksEachRulesTextInAContextRender:
    def test_a_marker_line_precedes_the_exact_bytes_of_each_rules_file(self, tmp_path):
        world = World(tmp_path)
        core = b"core rules\r\n\xc3\xa9cole\n"
        voice = b"plain voice\n\n"
        (world.rulesets / "rules" / "core-rules.md").write_bytes(core)
        (world.rulesets / "rules" / "voice.md").write_bytes(voice)
        world.manifest("defaults: ['voice', 'core-rules']\n")
        out = tmp_path / "context.md"

        assert render_context(world, out).returncode == 0

        assert out.read_bytes() == (
            b"<!-- rule: core-rules -->\n" + core + b"<!-- rule: voice -->\n" + voice
        )

    def test_the_marker_names_a_set_variant_and_the_text_is_that_variants_file(self, tmp_path):
        world = World(tmp_path)
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.manifest(
            "flags: ['voice-terse']\n"
            "defaults: ['voice']\n"
            "when:\n"
            "  - flag voice-terse: ['voice@terse']\n"
        )
        out = tmp_path / "context.md"

        result = render_context(world, out, "--flag", "voice-terse")

        assert result.returncode == 0, result.stderr
        assert out.read_text(encoding="utf-8") == (
            "<!-- rule: voice variant: terse -->\nterse voice\n"
        )


def render_tree(world, *options):
    return run("render", *options, "--root", str(world.rulesets))


def outside_the_render_folder(world):
    return {
        path: digest
        for path, digest in checksums(world.rulesets).items()
        if path.parts[0] != "-render"
    }


class TestRenderWritesRulesetRendersToAReservedFolder:
    def test_a_render_of_a_ruleset_no_longer_declared_is_removed_from_the_reserved_folder(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("audit-method", "audit method\n")
        world.manifest("defaults: ['audit-method']\n")
        folder = world.rulesets / "-render"
        folder.mkdir()
        (folder / "auditor.md").write_text("<!-- rule: audit-method -->\nold\n", encoding="utf-8")
        (folder / "auditor+audit-method@table.md").write_text("old\n", encoding="utf-8")

        result = render_tree(world)

        assert result.returncode == 0, result.stderr
        assert [path.name for path in folder.iterdir() if "auditor" in path.name] == []

    def test_no_file_outside_the_reserved_folder_changes_and_none_is_added_or_removed(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.manifest("defaults: ['writing-code']\n")
        (world.rulesets / "notes.txt").write_text("unrelated\n", encoding="utf-8")
        (world.rulesets / "references").mkdir()
        (world.rulesets / "references" / "table.md").write_text("a table\n", encoding="utf-8")
        before = outside_the_render_folder(world)

        result = render_tree(world)

        assert result.returncode == 0, result.stderr
        assert (world.rulesets / "-render").is_dir()
        assert outside_the_render_folder(world) == before


class TestRendersCheckModeFailsOnAStaleTree:
    def test_check_mode_passes_on_a_fresh_tree_and_fails_naming_the_render_after_a_byte_change(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("core-rules", "core rules\n")
        world.manifest("defaults: ['writing-code', 'core-rules']\n")
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
