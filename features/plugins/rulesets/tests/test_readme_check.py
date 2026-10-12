#!/usr/bin/env python3
"""The README's rulesets-directory sections say what the engine does, and each claim runs.

The README serves the person who sets up a rulesets directory and has only that page: the
manifest it shows is the manifest of `tests/fixtures/readme/`, the layout it draws is that
fixture's tree, the `check` command it gives exits zero on that fixture as written, the broken
item it adds draws the line it shows, and the error and warning kinds it lists are the kinds
check can report. A claim that drifts from the code turns one of these cases red.

Run with `python3.14 -m pytest features/rulesets/tests/test_readme_check.py`.
"""

import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import typing

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.findings import ErrorKind, WarningKind  # noqa: E402  (path must be set first)

README = PLUGIN_ROOT / "README.md"
FIXTURE = PLUGIN_ROOT / "tests" / "fixtures" / "readme"
FENCE = re.compile(r"^```(?P<language>\w*)\n(?P<body>.*?)^```$", re.DOTALL | re.MULTILINE)
DOCUMENTED_ROOT = "~/.claude/rulesets"


def section(heading):
    """The README text under one heading, up to the next heading of the same or higher level."""

    level = heading.split(" ", 1)[0]
    lines = README.read_text(encoding="utf-8").splitlines(keepends=True)
    collected, inside, in_fence = [], False, False
    for line in lines:
        if line.startswith("```"):
            in_fence = not in_fence
        is_heading = not in_fence and re.match(r"#+ ", line)
        if is_heading and line.rstrip() == heading:
            inside = True
            continue
        if inside and is_heading and len(line.split(" ", 1)[0]) <= len(level):
            break
        if inside:
            collected.append(line)
    assert collected, f"the README has no section {heading!r}"
    return "".join(collected)


def fences(text, language):
    return [m["body"] for m in FENCE.finditer(text) if m["language"] == language]


def table_first_column(text):
    """The backticked first cell of every table row."""

    return [m[1] for m in re.finditer(r"^\| `([^`]+)` \|", text, re.MULTILINE)]


class TestTheDocumentedManifest:
    def test_the_manifest_the_readme_shows_is_the_fixtures(self):
        (shown,) = fences(section("### The manifest"), "yaml")

        assert shown == (FIXTURE / "manifest.yaml").read_text(encoding="utf-8")


class TestTheDocumentedLayout:
    def test_the_tree_the_readme_draws_is_the_fixtures(self):
        (tree,) = fences(section("### Layout"), "text")

        drawn = {"rules": [], "references": []}
        folder = None
        for line in tree.splitlines():
            name = line.split()[0] if line.split() else ""
            if name in ("rules/", "references/"):
                folder = name.rstrip("/")
            elif name.endswith(".md") and folder:
                drawn[folder].append(name)

        assert drawn == {
            "rules": sorted(path.name for path in (FIXTURE / "rules").iterdir()),
            "references": sorted(path.name for path in (FIXTURE / "references").iterdir()),
        }
        assert "manifest.yaml" in tree


class TestTheDocumentedCheckCommand:
    def documented_command(self):
        (block,) = fences(section("### Checking a rulesets directory"), "bash")
        (line,) = [line for line in block.splitlines() if "tests/fixtures/readme" in line]
        return shlex.split(line)

    def test_the_command_is_run_from_the_plugin_directory_through_the_launcher(self):
        command = self.documented_command()

        assert command[:3] == ["hooks/with-python.sh", "lib/rulesets/cli.py", "check"]

    def test_the_command_exits_zero_on_the_fixture_as_written(self):
        result = subprocess.run(
            self.documented_command(),
            capture_output=True,
            text=True,
            check=False,
            cwd=PLUGIN_ROOT,
        )

        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


class TestTheDocumentedExample:
    def test_the_item_the_readme_adds_draws_the_line_the_readme_shows(self, tmp_path):
        text = section("### Checking a rulesets directory")
        (addition,) = fences(text, "yaml")
        (shown,) = fences(text, "text")
        copy = tmp_path / "rulesets"
        shutil.copytree(FIXTURE, copy)
        with (copy / "manifest.yaml").open("a", encoding="utf-8") as manifest:
            manifest.write(addition)

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "lib" / "rulesets" / "cli.py"),
                "check",
                "--root",
                str(copy),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 1
        assert result.stdout == shown.replace(DOCUMENTED_ROOT, str(copy))


class TestTheDocumentedKinds:
    def test_the_errors_the_readme_lists_are_the_errors_check_reports(self):
        listed = table_first_column(section("#### Errors"))

        assert sorted(listed) == sorted(typing.get_args(ErrorKind.__value__))

    def test_the_warnings_the_readme_lists_are_the_warnings_check_reports(self):
        listed = table_first_column(section("#### Warnings"))

        assert sorted(listed) == sorted(typing.get_args(WarningKind.__value__))
