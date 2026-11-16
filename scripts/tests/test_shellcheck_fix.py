"""What `scripts/verify/shellcheck_fix.py` does to the shell files it is handed, run against the real shellcheck."""

import os
import pathlib
import shutil
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "verify" / "shellcheck_fix.py"

pytestmark = pytest.mark.skipif(
    shutil.which("shellcheck") is None, reason="shellcheck comes from just tools"
)


def run(
    repo: pathlib.Path, *paths: str, path: str = os.environ["PATH"]
) -> subprocess.CompletedProcess:
    env = {
        "PATH": path,
        "HOME": str(repo.parent / "home"),
        "XDG_CONFIG_HOME": str(repo.parent / "xdg-config"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "LANG": "C.UTF-8",
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), *paths],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.fixture
def repo(tmp_path) -> pathlib.Path:
    root = tmp_path / "repo"
    (root / "bin").mkdir(parents=True)
    (tmp_path / "home").mkdir()
    return root


def test_a_missing_shellcheck_exits_three_naming_the_recipe_that_provides_it(
    repo, tmp_path
) -> None:
    (repo / "bin" / "greet.sh").write_text('#!/bin/bash\necho "$1"\n')
    empty = tmp_path / "empty-path"
    empty.mkdir()

    result = run(repo, "bin/greet.sh", path=str(empty))

    assert result.returncode == 3, result.stdout + result.stderr
    assert "shellcheck" in result.stderr and "just tools" in result.stderr, result.stderr


def test_a_finding_shellcheck_can_fix_is_rewritten_and_the_run_passes(repo) -> None:
    script = repo / "bin" / "greet.sh"
    script.write_text("#!/bin/bash\necho $1\n")

    result = run(repo, "bin/greet.sh")

    assert script.read_text() == '#!/bin/bash\necho "$1"\n'
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_finding_without_a_fix_is_reported_and_the_run_fails(repo) -> None:
    script = repo / "bin" / "unused.sh"
    script.write_text("#!/bin/bash\nunused=1\n")

    result = run(repo, "bin/unused.sh")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "SC2034" in result.stdout, result.stdout
    assert script.read_text() == "#!/bin/bash\nunused=1\n"


def test_fixes_apply_and_unfixable_findings_still_report_in_one_run(repo) -> None:
    (repo / "bin" / "greet.sh").write_text("#!/bin/bash\necho $1\n")
    (repo / "bin" / "unused.sh").write_text("#!/bin/bash\nunused=1\n")

    result = run(repo, "bin/greet.sh", "bin/unused.sh")

    assert (repo / "bin" / "greet.sh").read_text() == '#!/bin/bash\necho "$1"\n'
    assert result.returncode == 1, result.stdout + result.stderr
    assert "SC2034" in result.stdout and "SC2086" not in result.stdout, result.stdout


def test_a_clean_file_is_left_byte_for_byte_and_the_run_passes(repo) -> None:
    script = repo / "bin" / "clean.sh"
    script.write_text('#!/bin/bash\necho "$1"\n')

    result = run(repo, "bin/clean.sh")

    assert result.returncode == 0, result.stdout + result.stderr
    assert script.read_text() == '#!/bin/bash\necho "$1"\n'
