#!/usr/bin/env -S uv run --frozen
"""Tests for `scripts/scratchpad-path.py`.

Run with `.venv/bin/python -m pytest scripts/tests/test_scratchpad_path.py`.

Every test builds its own git repository under tmp_path, points HOME at a
directory beside it, and fixes the clock through SCRATCHPAD_PATH_NOW, so no
test reads or writes the real `~/.scratchpad`.
"""

import os
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "scratchpad-path.py"
NOW = "2026-09-20T14:45:00"


def git(cwd, *args) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def make_repo(root, name="project", branch="main") -> pathlib.Path:
    repo = root / name
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", branch)
    git(
        repo,
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "init",
    )
    return repo


def run(cwd, home, *args, now=NOW) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key != "SCRATCHPAD_PATH_NOW"
    }
    env.update({"HOME": str(home), "SCRATCHPAD_PATH_NOW": now})
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_scratchpad_path_prints_the_branch_directory_and_timestamped_file(tmp_path) -> None:
    repo = make_repo(tmp_path)
    home = tmp_path / "home"
    result = run(repo, home, "condense-rules")
    assert result.returncode == 0, result.stderr
    expected = home / ".scratchpad" / "project" / "main" / "condense-rules__02-45PM_20-09-2026.md"
    assert result.stdout.strip() == str(expected)


def test_scratchpad_path_creates_the_directory_but_not_the_file(tmp_path) -> None:
    repo = make_repo(tmp_path)
    home = tmp_path / "home"
    result = run(repo, home, "notes")
    path = pathlib.Path(result.stdout.strip())
    assert path.parent.is_dir(), "the caller writes the file next"
    assert not path.exists(), "the timestamp marks the first write"


def test_scratchpad_path_drops_the_branch_directory_on_a_detached_head(tmp_path) -> None:
    repo = make_repo(tmp_path)
    git(repo, "checkout", "-q", "--detach")
    home = tmp_path / "home"
    result = run(repo, home, "notes")
    assert result.stdout.strip() == str(
        home / ".scratchpad" / "project" / "notes__02-45PM_20-09-2026.md"
    )


def test_scratchpad_path_names_the_main_repository_from_a_linked_worktree(tmp_path) -> None:
    repo = make_repo(tmp_path)
    worktree = tmp_path / "elsewhere" / "feature-dir"
    git(repo, "worktree", "add", "-q", "-b", "feature/x", str(worktree))
    home = tmp_path / "home"
    result = run(worktree, home, "notes")
    expected = home / ".scratchpad" / "project" / "feature" / "x" / "notes__02-45PM_20-09-2026.md"
    assert result.stdout.strip() == str(expected), "$repo comes from the common git dir"


@pytest.mark.parametrize(
    ("now", "stamp"),
    [
        ("2026-09-20T14:45:00", "02-45PM_20-09-2026"),
        ("2026-01-05T09:07:00", "09-07AM_05-01-2026"),
    ],
)
def test_scratchpad_path_stamps_hh_mm_ampm_then_day_month_year(tmp_path, now, stamp) -> None:
    repo = make_repo(tmp_path)
    result = run(repo, tmp_path / "home", "notes", now=now)
    assert result.stdout.strip().endswith(f"notes__{stamp}.md")


def test_scratchpad_path_fails_outside_a_git_repository(tmp_path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    result = run(plain, tmp_path / "home", "notes")
    assert result.returncode != 0
    assert "git repository" in result.stderr, "the harness path applies outside a repository"


def test_scratchpad_path_fails_without_a_slug(tmp_path) -> None:
    repo = make_repo(tmp_path)
    result = run(repo, tmp_path / "home")
    assert result.returncode != 0
