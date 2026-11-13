#!/usr/bin/env python3
"""Tests for the prep-plan skill's `scripts/detect-tools.py`.

Run with `uv run --frozen pytest scripts/tests/test_prep_plan_detect_tools.py`.

Every test builds its own git repository under tmp_path, points HOME and the
XDG directories at an empty directory beside it, turns the global and system
git config off, and replaces PATH with one directory holding a git wrapper and
the stand-in tools the test names, so no test reads the real home or the tools
this machine has installed.
"""

import ast
import json
import os
import pathlib
import shutil
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "features/plugins/prep/skills/prep-plan/scripts/detect-tools.py"
REAL_GIT = shutil.which("git")
GIT = {"tool": "git", "command": "git worktree", "evidence": ["git on PATH"]}


def environment(home, bin_dir) -> dict:
    env = {
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "PATH": str(bin_dir),
    }
    if "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return env


def stand_in(bin_dir, name, output="") -> None:
    """Put a command on the test PATH that prints `output` whatever its arguments."""
    tool = bin_dir / name
    echo_lines = 'while IFS= read -r line; do echo "$line"; done'
    tool.write_text(f"#!/bin/sh\n{echo_lines} <<'EOF'\n{output}\nEOF\n")
    tool.chmod(0o755)


class Machine:
    """One isolated home, PATH, and repository."""

    def __init__(self, tmp_path, branch="main") -> None:
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        git = self.bin / "git"
        git.write_text(f'#!/bin/sh\nexec "{REAL_GIT}" "$@"\n')
        git.chmod(0o755)
        self.repo = tmp_path / "project"
        self.repo.mkdir()
        self.git("init", "-q", "-b", branch)
        self.git("commit", "-q", "--allow-empty", "-m", "init")

    def git(self, *args, cwd=None) -> None:
        subprocess.run(
            [REAL_GIT, "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=cwd or self.repo,
            env=environment(self.home, self.bin),
            check=True,
            capture_output=True,
            text=True,
        )

    def detect(self, where=None) -> tuple:
        result = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "--repo", str(where or self.repo)],
            env=environment(self.home, self.bin),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout), result.stdout


def tools(findings) -> list:
    return [finding["tool"] for finding in findings]


def test_a_machine_with_git_alone_gets_git_worktrees_and_nothing_else(tmp_path) -> None:
    machine = Machine(tmp_path)

    report, _ = machine.detect()

    assert report["jobs"] == {
        "worktrees": [GIT],
        "commit_hooks": [],
        "task_runner": [],
        "tracker": [],
    }
    assert report["repository"] == {
        "root": str(machine.repo.resolve()),
        "primary_checkout": str(machine.repo.resolve()),
        "trunk": "main",
        "trunk_source": "the primary checkout's branch",
        "remote_host": None,
    }


def test_worktrunk_on_the_path_comes_ahead_of_git(tmp_path) -> None:
    machine = Machine(tmp_path)
    stand_in(machine.bin, "wt", "wt - Git worktree management\nDocs: https://worktrunk.dev")
    (machine.repo / ".config").mkdir()
    (machine.repo / ".config/wt.toml").write_text('[[pre-start]]\nsetup = "true"\n')

    report, _ = machine.detect()

    assert report["jobs"]["worktrees"] == [
        {
            "tool": "worktrunk",
            "command": "wt",
            "evidence": ["wt on PATH, its help names worktrunk", ".config/wt.toml"],
        },
        GIT,
    ]


def test_another_program_named_wt_is_not_taken_for_worktrunk(tmp_path) -> None:
    machine = Machine(tmp_path)
    stand_in(machine.bin, "wt", "Windows Terminal")

    report, _ = machine.detect()

    assert report["jobs"]["worktrees"] == [GIT]


def test_a_linked_worktree_reports_the_original_checkout_as_primary(tmp_path) -> None:
    machine = Machine(tmp_path)
    linked = tmp_path / "linked"
    machine.git("worktree", "add", "-q", "-b", "feature", str(linked))

    report, _ = machine.detect(linked)

    assert report["repository"]["root"] == str(linked.resolve())
    assert report["repository"]["primary_checkout"] == str(machine.repo.resolve())
    assert report["repository"]["trunk"] == "main"


def test_the_trunk_is_the_branch_origin_head_names(tmp_path) -> None:
    machine = Machine(tmp_path, branch="develop")
    clone = tmp_path / "clone"
    machine.git("clone", "-q", str(machine.repo), str(clone), cwd=tmp_path)
    machine.git("checkout", "-q", "-b", "feature", cwd=clone)

    report, _ = machine.detect(clone)

    assert report["repository"]["trunk"] == "develop"
    assert report["repository"]["trunk_source"] == "origin/HEAD"


def test_each_hook_manager_is_found_by_its_file(tmp_path) -> None:
    machine = Machine(tmp_path)
    (machine.repo / "lefthook.yml").write_text("pre-commit:\n")
    (machine.repo / ".husky").mkdir()
    (machine.repo / ".pre-commit-config.yaml").write_text("repos: []\n")

    report, _ = machine.detect()

    assert report["jobs"]["commit_hooks"] == [
        {"tool": "lefthook", "command": None, "evidence": ["lefthook.yml"]},
        {"tool": "husky", "command": None, "evidence": [".husky"]},
        {"tool": "pre-commit", "command": None, "evidence": [".pre-commit-config.yaml"]},
    ]


def test_a_hand_written_git_hook_is_found(tmp_path) -> None:
    machine = Machine(tmp_path)
    hook = machine.repo / ".git/hooks/pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text("#!/bin/sh\n")
    hook.chmod(0o755)

    report, _ = machine.detect()

    assert report["jobs"]["commit_hooks"] == [
        {"tool": "git hooks", "command": None, "evidence": ["hooks/pre-commit"]}
    ]


def test_a_hooks_path_setting_is_found(tmp_path) -> None:
    machine = Machine(tmp_path)
    machine.git("config", "core.hooksPath", ".githooks")

    report, _ = machine.detect()

    assert report["jobs"]["commit_hooks"] == [
        {"tool": "git hooks", "command": None, "evidence": ["core.hooksPath=.githooks"]}
    ]


def test_task_runners_report_whether_their_command_is_installed(tmp_path) -> None:
    machine = Machine(tmp_path)
    stand_in(machine.bin, "just")
    (machine.repo / "justfile").write_text("default:\n")
    (machine.repo / "Makefile").write_text("all:\n")
    (machine.repo / "package.json").write_text('{"scripts": {"test": "true"}}')
    (machine.repo / "bun.lock").write_text("")

    report, _ = machine.detect()

    assert report["jobs"]["task_runner"] == [
        {"tool": "just", "command": "just", "evidence": ["justfile"]},
        {"tool": "make", "command": None, "evidence": ["Makefile"]},
        {"tool": "package scripts", "command": None, "evidence": ["package.json", "bun.lock"]},
    ]


def test_a_package_file_without_scripts_is_no_task_runner(tmp_path) -> None:
    machine = Machine(tmp_path)
    (machine.repo / "package.json").write_text('{"name": "x"}')

    report, _ = machine.detect()

    assert report["jobs"]["task_runner"] == []


def test_tracker_commands_are_found_and_the_remote_shows_only_its_host(tmp_path) -> None:
    machine = Machine(tmp_path)
    stand_in(machine.bin, "gh")
    stand_in(machine.bin, "acli")
    machine.git("remote", "add", "origin", "https://someone:hunter2@github.com/org/project.git")

    report, raw = machine.detect()

    assert report["repository"]["remote_host"] == "github.com"
    assert tools(report["jobs"]["tracker"]) == ["gh", "acli"]
    assert report["jobs"]["tracker"][0]["evidence"] == ["gh on PATH", "origin is on github.com"]
    assert "hunter2" not in raw
    assert "someone" not in raw


def test_an_ssh_remote_shows_its_host(tmp_path) -> None:
    machine = Machine(tmp_path)
    machine.git("remote", "add", "origin", "git@gitlab.example.org:org/project.git")

    report, _ = machine.detect()

    assert report["repository"]["remote_host"] == "gitlab.example.org"


def test_outside_a_repository_there_is_no_worktree_tool(tmp_path) -> None:
    machine = Machine(tmp_path)
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "Makefile").write_text("all:\n")

    report, _ = machine.detect(plain)

    assert report["repository"] is None
    assert report["jobs"]["worktrees"] == []
    assert tools(report["jobs"]["task_runner"]) == ["make"]


def test_a_run_writes_nothing_into_the_home_or_the_repository(tmp_path) -> None:
    machine = Machine(tmp_path)
    stand_in(machine.bin, "wt", "worktrunk")
    before = sorted(path.name for path in machine.repo.iterdir())

    machine.detect()

    assert list(machine.home.iterdir()) == []
    assert sorted(path.name for path in machine.repo.iterdir()) == before


def test_the_script_parses_under_python_3_9() -> None:
    ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT), feature_version=(3, 9))
