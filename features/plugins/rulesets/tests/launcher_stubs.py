"""Stub interpreters on a `PATH`, and the hook launcher run against them as a hook command runs it."""

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


def path_of(directory: pathlib.Path) -> str:
    """A `PATH` that finds the stubs first. /usr/bin and /bin carry date and the shell's helpers."""

    return f"{directory}:/usr/bin:/bin"


def launch(directory: pathlib.Path, *, announce: bool = False) -> subprocess.CompletedProcess[str]:
    """Run the launcher on a hook script with `PATH` holding the stubs; `announce` is a part-1 entry."""

    environment = {"PATH": path_of(directory), "HOME": str(directory)}
    flag = ["--announce"] if announce else []
    return subprocess.run(
        ["/bin/bash", str(LAUNCHER), *flag, "deliver.py", "--part", "1"],
        input="{}",
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
