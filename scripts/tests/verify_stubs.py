"""Stub programs for runner tests that need a process to stay alive, to rendezvous with its siblings, or to be real pytest.

`Sandbox` installs stubs that start, print canned output, and exit at once.
These replace one program of a sandbox's PATH with a stub that behaves
differently; each leaves its records in the sandbox's `stub-state` directory.
"""

import json
import os
import signal
import sys
import time

from verify_fixtures import BATS_PASS, CLAUDE_PASS, PYTEST_PASS, RUN_TIMEOUT, Sandbox

BARRIER = """\
#!{python}
import json, pathlib, sys, time

state = pathlib.Path({state!r})
starts = state / "starts.jsonl"
with open(starts, "a", encoding="utf-8") as log:
    log.write(json.dumps({{"prog": pathlib.Path(sys.argv[0]).name, "args": sys.argv[1:]}}) + "\\n")
deadline = time.monotonic() + {patience}
while time.monotonic() < deadline and len(starts.read_text().splitlines()) < {expected}:
    time.sleep(0.02)
sys.stdout.write({output!r})
"""

SLEEPER = """\
#!{python}
import os, pathlib, subprocess, time

state = pathlib.Path({state!r})
child = subprocess.Popen(["sleep", "30"])
(state / "pids.tmp").write_text(f"{{os.getpid()}} {{child.pid}}")
os.replace(state / "pids.tmp", state / "pids")
time.sleep(30)
"""

REAL_PYTEST = """\
#!{python}
import os, sys

args = sys.argv[1:]
assert args[:3] == ["run", "--frozen", "pytest"], args
os.execv({python!r}, [{python!r}, "-m", "pytest", *args[3:]])
"""

BARRIER_OUTPUT = {"uv": PYTEST_PASS, "bats": BATS_PASS, "claude": CLAUDE_PASS}
BARRIER_PATIENCE_SECONDS = 4


def write_stub(sb: Sandbox, prog: str, body: str) -> None:
    path = sb.stubs / prog
    path.write_text(body)
    path.chmod(0o755)


def install_barrier_stubs(sb: Sandbox, expected: int) -> None:
    """Make `uv`, `bats`, and `claude` log their argv, then wait until `expected` stubs have started before they print and exit."""
    for prog, output in BARRIER_OUTPUT.items():
        write_stub(
            sb,
            prog,
            BARRIER.format(
                python=sys.executable,
                state=str(sb.state),
                patience=BARRIER_PATIENCE_SECONDS,
                expected=expected,
                output=output,
            ),
        )


def barrier_starts(sb: Sandbox) -> list[dict]:
    """The `prog` and `args` of each barrier stub that has started, in start order."""
    path = sb.state / "starts.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def install_sleeper(sb: Sandbox, prog: str) -> None:
    """Make `prog` start a child `sleep`, record both process ids in `stub-state/pids`, and sleep."""
    write_stub(sb, prog, SLEEPER.format(python=sys.executable, state=str(sb.state)))


def sleeper_pids(sb: Sandbox, timeout: float = RUN_TIMEOUT) -> list[int]:
    """The stub's process id and its child's, once the sleeper has recorded them."""
    pids = sb.state / "pids"
    deadline = time.monotonic() + timeout
    while not pids.exists():
        assert time.monotonic() < deadline, "the sleeping stub never started"
        time.sleep(0.02)
    return [int(pid) for pid in pids.read_text().split()]


def install_real_pytest(sb: Sandbox) -> None:
    """Make `uv run --frozen pytest ...` run the interpreter's own pytest with the rest of the arguments."""
    write_stub(sb, "uv", REAL_PYTEST.format(python=sys.executable))


def is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def kill_leftovers(pids: list[int]) -> None:
    for pid in pids:
        if is_alive(pid):
            os.kill(pid, signal.SIGKILL)
