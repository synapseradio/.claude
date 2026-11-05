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
import re
import subprocess
import sys

import yaml
from delivery_world import World
from tier_corpus import FAMILIES, Corpus, define_agent

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
            "<!-- rule: core-rules -->\ncore rules\n\n"
            "<!-- rule: writing-prose variant: haiku -->\nhaiku prose\n"
        )
        assert opus.read_text(encoding="utf-8") == (
            "<!-- rule: core-rules -->\ncore rules\n\n"
            "<!-- rule: data-modeling -->\nmodel the data\n\n"
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
            b"<!-- rule: core-rules -->\n" + core + b"\n<!-- rule: voice -->\n" + voice
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


def tree_of(world):
    """The text of each file in the render folder, by file name."""

    folder = world.rulesets / "-render"
    return {path.name: path.read_text(encoding="utf-8") for path in folder.iterdir()}


def render_written(world):
    result = render_tree(world)
    assert result.returncode == 0, result.stderr
    return tree_of(world)


class TestEachRenderInTheTreeHoldsItsRulesOnceSortedUnderMarkers:
    def test_a_ruleset_render_holds_its_rules_sorted_and_no_block_changes_it(self, tmp_path):
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("data-modeling", "model data\n")
        world.manifest(
            "models: ['haiku']\n"
            "rulesets:\n"
            "  code: ['writing-code', 'data-modeling']\n"
            "when:\n"
            "  - model haiku: ['-data-modeling']\n"
        )

        tree = render_written(world)

        assert tree["code.md"] == (
            "<!-- rule: data-modeling -->\nmodel data\n\n<!-- rule: writing-code -->\nwrite code\n"
        )

    def test_a_ruleset_render_leaves_out_a_rule_withheld_by_a_check_error(self, tmp_path):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("scoped", "---\nwhen: model haiku\n---\nscoped text\n")
        world.manifest("rulesets:\n  code: ['core-rules', 'scoped']\n")

        tree = render_written(world)

        assert tree["code.md"] == "<!-- rule: core-rules -->\ncore rules\n"


class TestTheTreeHoldsARenderOfTheBaseContext:
    def test_defaults_holds_every_pool_rule_but_the_one_it_removes_and_no_flag_block_adds_it(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("security-pass", "security pass\n")
        world.rule("writing-code", "write code\n")
        world.manifest(
            "flags: ['strict']\n"
            "defaults: ['all:*', '-security-pass']\n"
            "when:\n"
            "  - flag strict: ['security-pass']\n"
        )

        tree = render_written(world)

        assert tree["defaults.md"] == (
            "<!-- rule: core-rules -->\ncore rules\n\n<!-- rule: writing-code -->\nwrite code\n"
        )


class TestTheTreeHoldsARenderOfTheWholePool:
    def test_the_pool_render_holds_every_rule_at_its_default_form(self, tmp_path):
        world = World(tmp_path)
        world.rule("security-pass", "security pass\n")
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.manifest(
            "flags: ['voice-terse']\n"
            "defaults: ['all:*', '-security-pass']\n"
            "when:\n"
            "  - flag voice-terse: ['voice@terse']\n"
        )

        tree = render_written(world)

        assert tree["all.md"] == (
            "<!-- rule: security-pass -->\nsecurity pass\n\n<!-- rule: voice -->\nplain voice\n"
        )


class TestTheTreeHoldsARenderForEachDeclaredRuleset:
    def test_nested_rulesets_flatten_into_a_render_holding_each_rule_once_sorted(self, tmp_path):
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("data-modeling", "model data\n")
        world.manifest(
            "rulesets:\n"
            "  review: ['code:*', 'writing-code']\n"
            "  code: ['writing-code', 'data-modeling']\n"
        )

        tree = render_written(world)

        assert tree["review.md"] == (
            "<!-- rule: data-modeling -->\nmodel data\n\n<!-- rule: writing-code -->\nwrite code\n"
        )

    def test_a_ruleset_render_marks_a_rule_the_ruleset_lists_at_a_variant(self, tmp_path):
        world = World(tmp_path)
        world.rule("audit-method", "audit method\n")
        world.rule("report-format", "report format\n")
        world.rule("report-format@table", "report as a table\n")
        world.manifest("rulesets:\n  auditor: ['audit-method', 'report-format@table']\n")

        tree = render_written(world)

        assert tree["auditor.md"] == (
            "<!-- rule: audit-method -->\naudit method\n\n"
            "<!-- rule: report-format variant: table -->\nreport as a table\n"
        )


class TestTheTreeHoldsAVariantRenderForEachVariantAnAddNames:
    def test_the_base_context_and_the_pool_each_get_a_render_at_the_variant_a_block_names(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.rule("voice@warm", "warm voice\n")
        world.manifest(
            "flags: ['voice-terse']\n"
            "defaults: ['all:*']\n"
            "when:\n"
            "  - flag voice-terse: ['voice@terse']\n"
        )

        tree = render_written(world)

        expected = (
            "<!-- rule: core-rules -->\ncore rules\n\n"
            "<!-- rule: voice variant: terse -->\nterse voice\n"
        )
        assert tree["defaults+voice@terse.md"] == expected
        assert tree["all+voice@terse.md"] == expected
        assert not [name for name, text in tree.items() if "warm" in name or "warm" in text]

    def test_no_variant_render_exists_where_the_ruleset_already_holds_that_variant(self, tmp_path):
        world = World(tmp_path)
        world.rule("report-format", "report format\n")
        world.rule("report-format@table", "report as a table\n")
        world.manifest(
            "defaults: ['report-format']\nrulesets:\n  auditor: ['report-format@table']\n"
        )

        tree = render_written(world)

        assert "auditor+report-format@table.md" not in tree
        assert "defaults+report-format@table.md" in tree

    def test_a_variant_only_a_remove_names_gets_no_render(self, tmp_path):
        world = World(tmp_path)
        world.rule("voice", "plain voice\n")
        world.rule("voice@warm", "warm voice\n")
        world.manifest("defaults: ['voice', '-voice@warm']\n")

        tree = render_written(world)

        assert not [name for name, text in tree.items() if "warm" in name or "warm" in text]


class TestTheTreeLeavesOutRendersForTheReservedNamesNoneAndRules:
    def test_the_tree_holds_all_and_no_render_for_none_or_for_rules(self, tmp_path):
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("voice", "plain voice\n")
        world.manifest("rulesets:\n  code: ['writing-code']\n  tone: ['voice']\n")

        tree = render_written(world)

        assert "none.md" not in tree
        assert "rules.md" not in tree
        assert "all.md" in tree


def edit(path, before, after):
    text = path.read_text(encoding="utf-8")
    assert before in text
    path.write_text(text.replace(before, after), encoding="utf-8")


def split(world, file):
    return run("split", str(file), "--root", str(world.rulesets))


class TestTheReverseSplitWritesEachSectionBackToItsSource:
    def test_an_edit_to_one_section_of_a_context_render_goes_to_that_rules_file_only(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("sorting", "sort things\n")
        world.rule("writing-code", "write code\n")
        world.manifest("defaults: ['core-rules', 'sorting', 'writing-code']\n")
        rendered = tmp_path / "context.md"
        assert render_context(world, rendered).returncode == 0
        before = checksums(world.rulesets)
        edit(
            rendered,
            "<!-- rule: core-rules -->\ncore rules\n",
            "<!-- rule: core-rules -->\nedited rules\n",
        )

        result = split(world, rendered)

        assert result.returncode == 0, result.stderr
        assert (world.rulesets / "rules" / "core-rules.md").read_text(encoding="utf-8") == (
            "edited rules\n"
        )
        after = checksums(world.rulesets)
        unedited = {path for path in before if path.name != "core-rules.md"}
        assert {path: after[path] for path in unedited} == {path: before[path] for path in unedited}
        again = tmp_path / "again.md"
        assert render_context(world, again).returncode == 0
        assert "<!-- rule: core-rules -->\nedited rules\n" in again.read_text(encoding="utf-8")

    def test_an_edited_variant_section_goes_to_the_variant_file_only(self, tmp_path):
        world = World(tmp_path)
        world.rule("voice", "plain voice\n")
        world.rule("voice@terse", "terse voice\n")
        world.manifest(
            "flags: ['voice-terse']\n"
            "defaults: ['all:*']\n"
            "when:\n"
            "  - flag voice-terse: ['voice@terse']\n"
        )
        assert render_tree(world).returncode == 0
        rendered = world.rulesets / "-render" / "all+voice@terse.md"
        before = checksums(world.rulesets)
        edit(
            rendered,
            "<!-- rule: voice variant: terse -->\nterse voice\n",
            "<!-- rule: voice variant: terse -->\nedited terse\n",
        )

        result = split(world, rendered)

        assert result.returncode == 0, result.stderr
        assert (world.rulesets / "rules" / "voice@terse.md").read_text(encoding="utf-8") == (
            "edited terse\n"
        )
        after = outside_the_render_folder(world)
        unedited = {path for path in after if path.name != "voice@terse.md"}
        assert {path: after[path] for path in unedited} == {path: before[path] for path in unedited}

    def test_an_edited_section_in_a_ruleset_render_goes_to_that_rules_file_only(self, tmp_path):
        world = World(tmp_path)
        world.rule("writing-code", "write code\n")
        world.rule("data-modeling", "model data\n")
        world.manifest("rulesets:\n  code: ['writing-code', 'data-modeling']\n")
        assert render_tree(world).returncode == 0
        rendered = world.rulesets / "-render" / "code.md"
        before = outside_the_render_folder(world)
        edit(
            rendered,
            "<!-- rule: writing-code -->\nwrite code\n",
            "<!-- rule: writing-code -->\nwrite well\n",
        )

        result = split(world, rendered)

        assert result.returncode == 0, result.stderr
        assert (world.rulesets / "rules" / "writing-code.md").read_text(encoding="utf-8") == (
            "write well\n"
        )
        after = outside_the_render_folder(world)
        unedited = {path for path in after if path.name != "writing-code.md"}
        assert {path: after[path] for path in unedited} == {path: before[path] for path in unedited}


class TestTheReverseSplitChangesOnlyTheFilesWhoseSectionsWereEdited:
    def test_a_context_render_followed_by_an_unedited_split_leaves_the_pool_as_it_was(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\r\n\n")
        world.rule("voice", "plain voice\n\n")
        world.rule("last", "no trailing newline")
        world.manifest("defaults: ['core-rules', 'voice', 'last']\n")
        before = checksums(world.rulesets)
        rendered = tmp_path / "context.md"

        assert render_context(world, rendered).returncode == 0
        result = split(world, rendered)

        assert result.returncode == 0, result.stderr
        assert checksums(world.rulesets) == before

    def test_the_split_over_every_render_in_the_tree_leaves_the_pool_as_it_was(self, tmp_path):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.rule("voice", "plain voice")
        world.rule("voice@terse", "terse voice\n\n")
        world.rule("last", "no trailing newline")
        world.manifest(
            "flags: ['voice-terse']\n"
            "defaults: ['all:*']\n"
            "rulesets:\n"
            "  tone: ['voice', 'last']\n"
            "when:\n"
            "  - flag voice-terse: ['voice@terse']\n"
        )
        before = checksums(world.rulesets)

        assert render_tree(world).returncode == 0
        for file in sorted((world.rulesets / "-render").iterdir()):
            result = split(world, file)
            assert result.returncode == 0, result.stderr

        assert outside_the_render_folder(world) == {
            path: digest for path, digest in before.items() if path.parts[0] != "-render"
        }


class TestTheReverseSplitRefusesAMalformedRenderedFile:
    def test_a_marker_naming_a_rule_the_pool_lacks_makes_the_split_write_nothing_and_name_it(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.manifest("defaults: ['core-rules']\n")
        rendered = tmp_path / "context.md"
        assert render_context(world, rendered).returncode == 0
        edit(rendered, "core rules\n", "edited rules\n\n<!-- rule: ghost-rule -->\nghost\n")
        before = checksums(world.rulesets)

        result = split(world, rendered)

        assert result.returncode != 0
        assert "ghost-rule" in result.stdout + result.stderr
        assert checksums(world.rulesets) == before

    def test_text_before_the_first_marker_makes_the_split_write_nothing(self, tmp_path):
        world = World(tmp_path)
        world.rule("core-rules", "core rules\n")
        world.manifest("defaults: ['core-rules']\n")
        rendered = tmp_path / "context.md"
        rendered.write_text("a stray line\n<!-- rule: core-rules -->\nedited\n", encoding="utf-8")
        before = checksums(world.rulesets)

        result = split(world, rendered)

        assert result.returncode != 0
        assert checksums(world.rulesets) == before


def adopt(source, out, *expect):
    return run(
        "adopt", "--from", str(source), "--out", str(out), *(f"--expect={e}" for e in expect)
    )


def compare(source, directory, *expect):
    return run("compare", str(source), str(directory), *(f"--expect={e}" for e in expect))


def manifest_of(out):
    return yaml.safe_load((out / "manifest.yaml").read_text(encoding="utf-8"))


def block(manifest, condition):
    """The entries of the `when` item keyed `condition`, or None where no item has that key."""

    return next((item[condition] for item in manifest.get("when", []) if condition in item), None)


def different_lines(result):
    return [line for line in result.stdout.splitlines() if line.startswith("different")]


_MARKER_LINE = re.compile(r"^<!-- rule: (\S+)(?: variant: (\S+))? -->\n", re.MULTILINE)


def rendered_rules(path):
    """The text of each rule in a context render, by rule name."""

    text = path.read_text(encoding="utf-8")
    found = list(_MARKER_LINE.finditer(text))
    rules = {}
    for index, match in enumerate(found):
        last = index + 1 == len(found)
        body = text[match.end() : len(text) if last else found[index + 1].start()]
        rules[match.group(1)] = body if last else body.removesuffix("\n")
    return rules


def delivered_to(out, tmp_path, model, agent=None):
    """The rules and text a context receives from the rulesets directory `out`."""

    target = tmp_path / f"render-{model}-{agent}.md"
    context = ["--model", model, *(["--agent", agent, "--kind", "delegate"] if agent else [])]
    result = run("render", *context, "--out", str(target), "--root", str(out))
    assert result.returncode == 0, result.stderr
    return rendered_rules(target)


class TestAdoptChangesNoSourceFile:
    def test_a_successful_adopt_leaves_every_source_unchanged_and_writes_only_the_output_directory(
        self, tmp_path, monkeypatch
    ):
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
        assert (out / "manifest.yaml").is_file()
        assert (out / "-render").is_dir()

    def test_an_output_directory_inside_the_source_is_refused_with_nothing_written(self, tmp_path):
        corpus = Corpus(tmp_path)
        corpus.body("default", "core-rules")
        out = corpus.root / "adopted"
        before = checksums(corpus.root)

        result = adopt(corpus.root, out)

        assert result.returncode != 0
        assert str(out) in result.stderr
        assert checksums(corpus.root) == before
        assert not out.exists()

    def test_an_output_directory_holding_a_file_is_refused_and_keeps_only_that_file(self, tmp_path):
        rules = tmp_path / "rules"
        rules.mkdir()
        (rules / "claims.md").write_text("claims text\n", encoding="utf-8")
        out = tmp_path / "adopted"
        out.mkdir()
        (out / "notes.txt").write_text("keep me\n", encoding="utf-8")

        result = adopt(rules, out)

        assert result.returncode != 0
        assert str(out) in result.stderr
        assert [path.name for path in out.rglob("*")] == ["notes.txt"]
        assert (out / "notes.txt").read_text(encoding="utf-8") == "keep me\n"


class TestAdoptMapsARulesFolderOrATierCorpusToARulesetsDirectory:
    def test_a_rules_folder_becomes_a_pool_of_unchanged_files_with_defaults_spreading_every_rule(
        self, tmp_path
    ):
        rules = tmp_path / "rules"
        rules.mkdir()
        (rules / "breaks.md").write_bytes(b"breaks text\r\nsecond line\n")
        (rules / "claims.md").write_bytes(b"claims text\n")
        out = tmp_path / "adopted"

        result = adopt(rules, out)

        assert result.returncode == 0, result.stderr
        assert (out / "rules" / "breaks.md").read_bytes() == b"breaks text\r\nsecond line\n"
        assert (out / "rules" / "claims.md").read_bytes() == b"claims text\n"
        assert manifest_of(out)["defaults"] == ["all:*"]
        assert run("check", "--root", str(out)).returncode == 0


class TestAdoptMapsTheFilesOfATierCorpusToThePool:
    def test_a_default_file_lands_in_the_pool_with_the_same_text(self, tmp_path):
        corpus = Corpus(tmp_path)
        text = corpus.body("default", "core-rules", "core rules\r\n")
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert (out / "rules" / "core-rules.md").read_bytes() == text.encode()

    def test_a_tiers_own_text_becomes_a_variant_that_the_models_block_adds(self, tmp_path):
        corpus = Corpus(tmp_path)
        default_text = corpus.body("default", "writing-prose")
        haiku_text = corpus.body("haiku", "writing-prose")
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert (out / "rules" / "writing-prose.md").read_text(encoding="utf-8") == default_text
        assert (out / "rules" / "writing-prose@haiku.md").read_text(encoding="utf-8") == haiku_text
        assert "writing-prose@haiku" in block(manifest_of(out), "model haiku")

    def test_a_stem_only_a_tier_holds_is_skipped_and_named_in_the_report(self, tmp_path):
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


class TestAdoptMapsTheEntriesOfATierCorpusToManifestBlocks:
    def test_a_tiers_exclude_list_becomes_one_remove_per_stem_in_that_models_block(self, tmp_path):
        corpus = Corpus(tmp_path, left_out={"sonnet": ["agent-delegation", "spawn-decision"]})
        for stem in ("agent-delegation", "spawn-decision", "core-rules", "sorting"):
            corpus.body("default", stem)
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert sorted(block(manifest_of(out), "model sonnet")) == [
            "-agent-delegation",
            "-spawn-decision",
        ]

    def test_a_tier_that_includes_every_stem_becomes_a_defaults_spreading_every_rule(
        self, tmp_path
    ):
        corpus = Corpus(tmp_path)
        corpus.body("default", "core-rules")
        corpus.body("default", "sorting")
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert manifest_of(out)["defaults"] == ["all:*"]


class TestAdoptDeclaresAModelNameForEachTier:
    def test_the_manifest_declares_one_model_name_per_tier_in_the_prefix_map(self, tmp_path):
        corpus = Corpus(tmp_path)
        corpus.body("default", "core-rules")
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert sorted(manifest_of(out)["models"]) == sorted(FAMILIES)
        assert sorted(FAMILIES) == ["fable", "haiku", "opus", "sonnet"]

    def test_a_tier_named_for_one_model_declares_the_name_without_its_prefix_and_no_block(
        self, tmp_path
    ):
        corpus = Corpus(tmp_path, extra_tiers=("claude-opus-4-8",))
        corpus.body("default", "core-rules")
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert "opus-4-8" in manifest_of(out)["models"]
        assert block(manifest_of(out), "model opus-4-8") is None


class TestAdoptSkipsPathScopedFiles:
    def test_a_path_scoped_rule_file_stays_out_of_the_pool_and_is_named_in_the_report(
        self, tmp_path
    ):
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


class TestAdoptMapsAnAgentDefinitionsExclusionsToABlock:
    def test_an_excluded_rule_becomes_a_remove_in_that_agents_block_and_the_definition_is_untouched(
        self, tmp_path, monkeypatch
    ):
        config = tmp_path / "config"
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        corpus = Corpus(tmp_path)
        corpus.body("default", "writing-prose")
        corpus.body("default", "core-rules")
        definition = define_agent(config, "eval-runner", ["writing-prose"])
        recorded = definition.read_bytes()
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert definition.read_bytes() == recorded
        assert block(manifest_of(out), "agent eval-runner") == ["-writing-prose"]
        delegate = delivered_to(out, tmp_path, "opus", "eval-runner")
        assert "writing-prose" not in delegate
        assert "core-rules" in delegate


class TestAdoptProvesEveryContextsTextUnchanged:
    def test_adopt_exits_zero_and_every_context_receives_the_rules_and_text_the_corpus_delivers(
        self, tmp_path, monkeypatch
    ):
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
        define_agent(config, "eval-runner", ["writing-prose"])
        define_agent(config, "auditor", ["core-rules"])
        excluded_by = {None: set(), "eval-runner": {"writing-prose"}, "auditor": {"core-rules"}}
        out = tmp_path / "adopted"

        result = adopt(corpus.root, out)

        assert result.returncode == 0, result.stderr
        assert different_lines(result) == []
        for model in FAMILIES:
            for agent, excluded in excluded_by.items():
                expected = {
                    stem: texts.get((model, stem), texts[("default", stem)])
                    for stem in ("core-rules", "writing-prose", "agent-delegation")
                    if stem not in excluded
                    and not (model == "sonnet" and stem == "agent-delegation")
                }
                assert delivered_to(out, tmp_path, model, agent) == expected, (model, agent)

    def test_a_context_delivering_rules_in_another_sequence_is_reported_equal(self, tmp_path):
        corpus = Corpus(tmp_path, order=["writing-code", "core-rules"])
        core = corpus.body("default", "core-rules")
        code = corpus.body("default", "writing-code")
        world = World(tmp_path)
        world.rule("core-rules", core)
        world.rule("writing-code", code)
        world.manifest("models: ['opus', 'sonnet', 'haiku', 'fable']\ndefaults: ['all:*']\n")

        result = compare(corpus.root, world.rulesets)

        assert result.returncode == 0, result.stdout + result.stderr
        assert different_lines(result) == []

    def test_the_model_named_tier_matches_the_corpus_when_the_manifest_declares_its_name(
        self, tmp_path, monkeypatch
    ):
        from rulesets.compare.run import compare as run_compare
        from rulesets.locations import Locations

        corpus = Corpus(tmp_path, extra_tiers=("claude-opus-4-8",))
        default_text = corpus.body("default", "spawn-decision")
        opus_text = corpus.body("opus", "spawn-decision")
        world = World(tmp_path)
        world.rule("spawn-decision", default_text)
        world.rule("spawn-decision@opus", opus_text)
        world.manifest(
            "models: ['opus', 'sonnet', 'haiku', 'fable', 'opus-4-8']\n"
            "defaults: ['all:*']\n"
            "when:\n  - model opus: ['spawn-decision@opus']\n"
        )
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(world.config))
        target = tmp_path / "context.md"
        rendered = run(
            "render",
            "--model",
            "claude-opus-4-8",
            "--out",
            str(target),
            "--root",
            str(world.rulesets),
        )

        report = run_compare(corpus.root, world.rulesets, (), Locations(world.config))

        assert rendered.returncode == 0, rendered.stderr
        assert rendered_rules(target) == {"spawn-decision": default_text}
        context = next(r for r in report.results if r.context.identifier == "claude-opus-4-8")
        assert context.difference is None
        assert compare(corpus.root, world.rulesets).returncode == 0

    def test_the_model_named_tier_takes_opus_when_the_manifest_lacks_its_name(self, tmp_path):
        corpus = Corpus(tmp_path, extra_tiers=("claude-opus-4-8",))
        default_text = corpus.body("default", "spawn-decision")
        opus_text = corpus.body("opus", "spawn-decision")
        world = World(tmp_path)
        world.rule("spawn-decision", default_text)
        world.rule("spawn-decision@opus", opus_text)
        world.manifest(
            "models: ['opus', 'sonnet', 'haiku', 'fable']\n"
            "defaults: ['all:*']\n"
            "when:\n  - model opus: ['spawn-decision@opus']\n"
        )
        target = tmp_path / "context.md"
        rendered = run(
            "render",
            "--model",
            "claude-opus-4-8",
            "--out",
            str(target),
            "--root",
            str(world.rulesets),
        )

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
    ):
        corpus = Corpus(tmp_path, extra_tiers=("claude-opus-4-8",))
        default_text = corpus.body("default", "spawn-decision")
        opus_text = corpus.body("opus", "spawn-decision")
        world = World(tmp_path)
        world.rule("spawn-decision", default_text)
        world.rule("spawn-decision@opus", opus_text)
        world.manifest(
            "models: ['opus', 'sonnet', 'haiku', 'fable', 'opus-4-8']\n"
            "defaults: ['all:*']\n"
            "when:\n  - model opus: ['spawn-decision@opus']\n"
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
    ):
        from rulesets.compare.run import compare as run_compare
        from rulesets.locations import Locations

        world = World(tmp_path)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(world.config))
        define_agent(world.config, "eval-runner", [])
        define_agent(world.config, "auditor", [])
        corpus = Corpus(tmp_path)
        world.rule("core-rules", corpus.body("default", "core-rules"))
        world.manifest("models: ['opus', 'sonnet', 'haiku', 'fable']\ndefaults: ['all:*']\n")
        assert not world.record_files().exists()

        report = run_compare(
            corpus.root, world.rulesets, ("claude-opus-4-8[1m]",), Locations(world.config)
        )

        contexts = {(r.context.identifier, r.context.agent) for r in report.results}
        assert {
            ("claude-opus-4-8[1m]", None),
            ("claude-opus-4-8[1m]", "eval-runner"),
            ("claude-opus-4-8[1m]", "auditor"),
        } <= contexts


class TestTheComparisonReportNamesEachContextThatDiffers:
    def test_the_report_names_a_differing_delegate_context_and_its_first_differing_rule_and_variant(
        self, tmp_path, monkeypatch
    ):
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


class TestTheComparisonRunsAloneAsCompare:
    def test_compare_catches_an_edit_made_to_a_variant_after_adoption(self, tmp_path):
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
