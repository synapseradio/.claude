#!/usr/bin/env python3
"""The hook launcher runs delivery only on Python 3.12 or later with pyyaml.

A person's machine may hold several interpreters, and the newest one on the
path decides whether their sessions start with rules. Each case puts stub
interpreters on `PATH`, each answering the launcher's probe as one real
interpreter would, and runs `hooks/with-python.sh` as a hook command does.

Run with `python3.14 -m pytest features/rulesets/tests/test_launcher.py`.
"""

import os
import pathlib
import subprocess

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
LAUNCHER = PLUGIN_ROOT / "hooks" / "with-python.sh"

# The stub answers a `-c` probe the way an interpreter of its version would:
# a probe importing yaml fails where the stub has none, and a probe comparing
# against (3, N) fails where the stub's minor version is below N. Any other
# call is the hook script being run, which the stub reports on stdout.
STUB = """#!/bin/bash
if [[ "$1" == "-c" ]]; then
  if [[ "$2" == *yaml* && "{has_yaml}" != "yes" ]]; then
    exit 1
  fi
  if [[ "$2" =~ \\(3,\\ ([0-9]+)\\) ]] && (( {minor} < BASH_REMATCH[1] )); then
    exit 1
  fi
  exit 0
fi
echo "ran by {name}: $*"
"""


def stub(directory: pathlib.Path, name: str, minor: int, has_yaml: bool) -> None:
    path = directory / name
    path.write_text(
        STUB.format(name=name, minor=minor, has_yaml="yes" if has_yaml else "no"),
        encoding="utf-8",
    )
    path.chmod(0o755)


def launch(directory: pathlib.Path) -> subprocess.CompletedProcess:
    # /usr/bin and /bin carry date and the shell builtins' helpers. Every
    # scenario stubs python3, so a system python3 in /usr/bin never answers.
    environment = {"PATH": f"{directory}:/usr/bin:/bin", "HOME": str(directory)}
    return subprocess.run(
        ["/bin/bash", str(LAUNCHER), "deliver.py", "--part", "1"],
        input="{}",
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def test_only_python_3_11_installed(tmp_path):
    stub(tmp_path, "python3", minor=11, has_yaml=True)

    result = launch(tmp_path)

    assert result.returncode == 0, "a hook exiting non-zero reports an error in every session"
    assert result.stdout == "", "the session starts without the engine's rules"
    assert "3.12" in result.stderr, "stderr names the requirement the person must meet"


def test_python_3_12_with_the_yaml_library(tmp_path):
    stub(tmp_path, "python3.12", minor=12, has_yaml=True)
    stub(tmp_path, "python3", minor=11, has_yaml=True)

    result = launch(tmp_path)

    assert result.returncode == 0
    assert result.stdout == "ran by python3.12: deliver.py --part 1\n"


def test_python_3_12_without_the_yaml_library(tmp_path):
    stub(tmp_path, "python3.12", minor=12, has_yaml=False)
    stub(tmp_path, "python3", minor=13, has_yaml=True)

    result = launch(tmp_path)

    assert result.stdout == "ran by python3: deliver.py --part 1\n", (
        "the launcher skips an interpreter that cannot import yaml"
    )


def test_no_interpreter_with_the_yaml_library(tmp_path):
    stub(tmp_path, "python3.12", minor=12, has_yaml=False)
    stub(tmp_path, "python3", minor=14, has_yaml=False)

    result = launch(tmp_path)

    assert result.returncode == 0
    assert result.stdout == ""
    assert "3.12" in result.stderr


def test_the_stub_shadows_every_system_interpreter(tmp_path):
    names = {"python3", "python3.12", "python3.13", "python3.14"}
    found = {
        name for name in names for root in ("/usr/bin", "/bin") if os.path.exists(f"{root}/{name}")
    }

    assert found <= {"python3"}, (
        f"a system interpreter outside the stubs would answer the probe: {sorted(found)}"
    )
