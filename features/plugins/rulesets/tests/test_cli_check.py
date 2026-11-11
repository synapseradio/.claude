#!/usr/bin/env python3
"""The `check` command prints every error and warning of one run and fails only on an error.

The command serves the person who edits a rulesets directory and runs check before trusting a
delivery, and the pre-push job that runs it unattended: each finding arrives on one line with
its file and line, in the words the engine uses outward, and the exit status says whether an
error stands. Each case builds its rulesets directory under `tmp_path` and runs `cli.py` as a
script, as the skill and the job do.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_cli_check.py`.
"""

import pathlib
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "lib" / "rulesets" / "cli.py"


def build(tmp_path, config=None, stems=(), bodies=None):
    """A rulesets directory with the config text, a file per stem, and any given bodies."""

    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    if config is not None:
        (root / "config.yaml").write_text(config, encoding="utf-8")
    texts = {stem: f"text of {stem}\n" for stem in stems} | (bodies or {})
    for stem, text in texts.items():
        (root / "rules" / f"{stem}.md").write_text(text, encoding="utf-8")
    return root


def run(*arguments):
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        capture_output=True,
        text=True,
        check=False,
        cwd=CLI.parent,
    )


def check(root):
    return run("check", "--root", str(root))


def lines_of(result):
    return result.stdout.splitlines()


def findings_of(result):
    """Each printed line as its location, severity, and kind."""

    found = []
    for line in lines_of(result):
        location, rest = line.split(": ", 1)
        severity, kind = rest.split(" ")[:2]
        found.append((location, severity, kind.strip("[]")))
    return found


class TestSeveralProblemsAtOnce:
    def test_every_error_of_the_run_is_printed_and_the_exit_is_non_zero(self, tmp_path):
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

    def test_each_finding_sits_on_one_line_with_its_file_and_line(self, tmp_path):
        root = build(tmp_path, "defaults: ghost\n")

        result = check(root)

        (line,) = lines_of(result)
        assert line.startswith(f"{root / 'config.yaml'}:1: error [undeclared-reference]")
        assert "ghost" in line

    def test_errors_are_printed_before_warnings(self, tmp_path):
        root = build(tmp_path, "defaults:\nproject x:\n  include: voice\n", stems=["voice", "tone"])

        severities = [severity for _, severity, _ in findings_of(check(root))]

        assert severities == ["error", "warning"]


class TestWarningsOnly:
    def test_both_warnings_are_printed_and_the_exit_is_zero(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: voice\n",
            stems=["security"],
            bodies={"voice": "Run `security` first.\n"},
        )

        result = check(root)

        assert result.returncode == 0
        assert len(lines_of(result)) == 2
        assert all(": warning " in line for line in lines_of(result))
        assert "[never-included]" in result.stdout
        assert "[cross-reference]" in result.stdout

    def test_a_finding_without_a_line_names_the_file_alone(self, tmp_path):
        root = build(tmp_path, "defaults:\n", stems=["voice"])

        (line,) = lines_of(check(root))

        assert line.startswith(f"{root / 'rules' / 'voice.md'}: warning [never-included]")

    def test_a_warning_with_a_line_names_it(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "<!-- rule: sorting -->\ntext\n"})

        (line,) = lines_of(check(root))

        assert line.startswith(
            f"{root / 'rules' / 'voice.md'}:1: warning [marker-for-another-rule]"
        )


class TestACleanRulesetsDirectory:
    def test_nothing_is_printed_and_the_exit_is_zero(self, tmp_path):
        root = build(tmp_path, "defaults: all.*\n", stems=["voice", "voice@terse"])

        result = check(root)

        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")

    def test_a_directory_with_no_config_and_no_rules_is_clean(self, tmp_path):
        root = tmp_path / "empty"
        root.mkdir()

        result = check(root)

        assert (result.returncode, result.stdout) == (0, "")


class TestAConfigThatDoesNotParse:
    def test_the_failure_is_printed_with_its_line_and_the_exit_is_non_zero(self, tmp_path):
        root = build(tmp_path, "defaults: [voice]\nmodels: [opus-4-8[1m]]\n", stems=["voice"])

        result = check(root)

        assert result.returncode == 1
        (line,) = lines_of(result)
        assert line.startswith(f"{root / 'config.yaml'}:2: error [config-unparsable]")


class TestARuleFileThatIsNotUtf8:
    def test_the_file_is_printed_as_an_error_and_the_exit_is_non_zero(self, tmp_path):
        root = build(tmp_path, stems=["other"])
        (root / "rules" / "voice.md").write_bytes(b"Speak \xff plainly.\n")

        result = check(root)

        assert (result.returncode, result.stderr) == (1, "")
        (line,) = lines_of(result)
        assert line.startswith(
            f"{root / 'rules' / 'voice.md'}: error [unreadable-file] rule `voice`"
        )


class TestTheOutwardVocabulary:
    def test_a_variant_with_no_default_form_names_the_rule_and_the_variant(self, tmp_path):
        root = build(tmp_path, stems=["tone@dry"])

        (line,) = lines_of(check(root))

        assert "rule `tone`" in line
        assert "variant `dry`" in line
        assert "default form" in line

    def test_no_message_names_a_tier_a_stem_or_an_internal_type(self, tmp_path):
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

    def test_a_block_is_called_a_block_and_names_its_file_and_line(self, tmp_path):
        root = build(
            tmp_path,
            "flags: a\nflag a:\n  include: voice\nenv CI:\n  include: voice\n",
            stems=["voice"],
        )

        (line,) = lines_of(check(root))

        assert line.startswith(
            f"{root / 'config.yaml'}:4: error [condition-invalid] block `env CI`"
        )

    def test_a_rule_error_is_called_a_rule(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "---\nmodel: haiku\n---\ntext\n"})

        (line,) = lines_of(check(root))

        assert f"{root / 'rules' / 'voice.md'}:2: error [rule-condition] rule `voice`" in line

    def test_a_ruleset_and_a_key_are_called_a_ruleset_and_a_key(self, tmp_path):
        root = build(tmp_path, "sets:\n  none:\nwhen: x\n")

        first, second = lines_of(check(root))

        assert "ruleset `none`" in first
        assert "key `when`" in second

    def test_a_qualified_reference_is_quoted_as_the_config_writes_it_at_its_own_line(
        self, tmp_path
    ):
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
        assert "ruleset `code` holds no rule `resolving-input`" in line
        assert ":*" not in check(root).stdout
        assert " `-" not in check(root).stdout

    def test_a_variant_conflict_names_both_references(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: voice@terse voice@warm\n",
            stems=["voice", "voice@terse", "voice@warm"],
        )

        (line,) = [line for line in lines_of(check(root)) if ": error " in line]

        assert "`voice@terse`" in line
        assert "`voice@warm`" in line


class TestUsage:
    def test_a_root_that_is_no_directory_exits_two_and_names_it(self, tmp_path):
        missing = tmp_path / "nowhere"

        result = check(missing)

        assert result.returncode == 2
        assert str(missing) in result.stderr
        assert result.stdout == ""

    def test_a_root_that_is_a_file_exits_two(self, tmp_path):
        file = tmp_path / "file.txt"
        file.write_text("x", encoding="utf-8")

        assert check(file).returncode == 2

    def test_check_without_a_root_exits_two(self):
        result = run("check")

        assert result.returncode == 2
        assert "--root" in result.stderr

    def test_an_unknown_command_exits_two(self, tmp_path):
        assert run("frobnicate", "--root", str(tmp_path)).returncode == 2

    def test_no_command_exits_two(self):
        assert run().returncode == 2

    def test_the_command_runs_from_any_working_directory(self, tmp_path):
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


class TestAManifestYamlWithNoConfigYaml:
    def test_check_reports_an_error_naming_both_files_and_exits_non_zero(self, tmp_path):
        root = build(tmp_path, stems=["voice"])
        (root / "manifest.yaml").write_text("defaults: ['voice']\n", encoding="utf-8")

        result = check(root)

        assert result.returncode == 1
        (line,) = [line for line in lines_of(result) if ": error " in line]
        assert line.startswith(f"{root / 'manifest.yaml'}: error [config-file]")
        assert "`config.yaml`" in line
