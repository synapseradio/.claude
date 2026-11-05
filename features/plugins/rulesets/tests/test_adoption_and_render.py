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
