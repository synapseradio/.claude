#!/usr/bin/env python3
"""The `check` command prints every error and warning of one run and fails only on an error.

The command serves the person who edits a rulesets directory and runs check before trusting a
delivery, and the pre-push job that runs it unattended: each finding arrives on one line with
its file and line, in the words the engine uses outward, and the exit status says whether an
error stands. Each case builds its rulesets directory under `tmp_path` and calls the command
line's `main` in-process; one case runs `cli.py` as a script, since its subject is the script's
process starting outside the library's directory.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_cli_check.py`.
"""

import os
import pathlib
import subprocess
import sys

import pytest
from delivery_world import CLI, run_cli


def build(tmp_path, config=None, stems=(), bodies=None) -> pathlib.Path:
    """A rulesets directory with the config text, a file per stem, and any given bodies."""
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    if config is not None:
        (root / "config.yaml").write_text(config, encoding="utf-8")
    texts = {stem: f"text of {stem}\n" for stem in stems} | (bodies or {})
    for stem, text in texts.items():
        (root / "rules" / f"{stem}.md").write_text(text, encoding="utf-8")
    return root


def run(*arguments) -> subprocess.CompletedProcess[str]:
    return run_cli([str(argument) for argument in arguments], os.environ)


def check(root) -> subprocess.CompletedProcess[str]:
    return run("check", "--root", str(root))


def lines_of(result) -> list[str]:
    return result.stdout.splitlines()


def findings_of(result) -> list[tuple[str, str, str]]:
    """Each printed line as its location, severity, and kind."""
    found = []
    for line in lines_of(result):
        location, rest = line.split(": ", 1)
        severity, kind = rest.split(" ")[:2]
        found.append((location, severity, kind.strip("[]")))
    return found


class TestCheckPrintsEveryFindingAndFailsOnlyOnAnError:
    def test_every_error_is_printed_on_its_own_line_with_file_and_line_and_the_exit_is_one(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            "defaults: ghost\nsets:\n  a: b.*\n  b: a.*\nproject amboss:\n  include: voice\n",
            stems=["voice"],
        )

        result = check(root)

        assert result.returncode == 1
        config = root / "config.yaml"
        assert sorted(findings_of(result)) == [
            (f"{config}:1", "error", "undeclared-reference"),
            (f"{config}:3", "error", "ruleset-cycle"),
            (f"{config}:5", "error", "condition-invalid"),
        ]

    def test_warnings_alone_are_printed_and_the_exit_is_zero(self, tmp_path) -> None:
        root = build(
            tmp_path,
            "defaults: voice\n",
            stems=["security"],
            bodies={"voice": "Run `security` first.\n"},
        )

        result = check(root)

        assert result.returncode == 0
        assert sorted(severity for _, severity, _ in findings_of(result)) == ["warning", "warning"]
        assert "[never-included]" in result.stdout
        assert "[cross-reference]" in result.stdout

    def test_a_clean_directory_prints_nothing_and_exits_zero(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: all.*\n", stems=["voice", "voice@terse"])

        result = check(root)

        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")

    def test_the_command_runs_from_any_working_directory(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: ghost\n")

        result = subprocess.run(
            [sys.executable, str(CLI), "check", "--root", str(root)],
            capture_output=True,
            text=True,
            check=False,
            cwd=tmp_path,
        )

        assert result.returncode == 1
        assert "ghost" in result.stdout


class TestTheOutwardVocabulary:
    def test_no_message_names_a_tier_a_stem_or_an_internal_type(self, tmp_path) -> None:
        root = build(
            tmp_path,
            "defaults: ghost voice@terse voice@warm\n"
            "sets:\n"
            "  a: a.*\n"
            "  all:\n"
            "project x:\n"
            "  include: voice\n"
            "model nova:\n"
            "  include: voice\n"
            "bad:\n"
            "project: y\n"
            "when:\n"
            "  - flag a: [voice]\n",
            stems=["tone@dry", "voice", "voice@terse", "voice@warm"],
            bodies={"loud": "---\nmodel: haiku\n---\n" + "x" * 9_500},
        )
        (root / "rules" / "drafts").mkdir()

        output = check(root).stdout.replace(str(root), "")

        assert output
        for word in ("tier", "stem", "Subject", "Target", "Expansion", "PoolFile", "Config("):
            assert word not in output

    def test_a_qualified_reference_is_quoted_as_the_config_writes_it_at_its_own_line(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            "sets:\n"
            "  code: writing-code\n"
            "agent critic:\n"
            "  include:\n"
            "    code.writing-code\n"
            "    code.resolving-input\n"
            "  exclude: voice\n",
            stems=["writing-code", "resolving-input", "voice"],
        )

        (line,) = [line for line in lines_of(check(root)) if ": error " in line]

        assert line.startswith(f"{root / 'config.yaml'}:6: error [undeclared-reference]")
        assert "`code.resolving-input`" in line
        assert ":*" not in check(root).stdout
        assert " `-" not in check(root).stdout


class TestUsage:
    def test_a_root_that_is_no_directory_exits_two_and_names_it(self, tmp_path) -> None:
        missing = tmp_path / "nowhere"

        result = check(missing)

        assert result.returncode == 2
        assert str(missing) in result.stderr
        assert result.stdout == ""

    @pytest.mark.parametrize(
        "arguments",
        [("check",), ("frobnicate", "--root", "."), ()],
        ids=["no-root", "unknown-command", "no-command"],
    )
    def test_a_call_the_command_line_cannot_read_exits_two(self, arguments) -> None:
        assert run(*arguments).returncode == 2


class TestAManifestYamlWithNoConfigYaml:
    def test_check_reports_an_error_naming_both_files_and_exits_non_zero(self, tmp_path) -> None:
        root = build(tmp_path, stems=["voice"])
        (root / "manifest.yaml").write_text("defaults: ['voice']\n", encoding="utf-8")

        result = check(root)

        assert result.returncode == 1
        (line,) = [line for line in lines_of(result) if ": error " in line]
        assert line.startswith(f"{root / 'manifest.yaml'}: error [config-file]")
        assert "`config.yaml`" in line
