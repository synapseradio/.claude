"""The one plain run whose output is saved byte for byte in `verify_samples/plain-run.txt`.

The scenario covers every line the plain display prints: the header, a PASS, a
FAIL with its failing id, a SKIP from the planner, a SKIP from pytest's exit 5,
and the tally. `normalize` replaces what differs from one run to the next: each
suite's seconds and the run's log paths.
"""

import re
import subprocess

from verify_fixtures import PYTEST_NONE_SELECTED, PYTEST_ONE_FAILURE, Sandbox

SCENARIO_ARGS = ("test", "--serial", "-k", "a.b")
RUN_DIRECTORY = re.compile(r"/[^\s=]*/proj-work/\d{8}-\d{6}-\d+")
SECONDS = re.compile(r"\b\d+\.\ds\b")


def run_scenario(sb: Sandbox) -> subprocess.CompletedProcess:
    sb.respond("uv", "pkg_a", PYTEST_ONE_FAILURE, exit_code=1)
    sb.respond("uv", "pkg_b", PYTEST_NONE_SELECTED, exit_code=5)
    return sb.run(*SCENARIO_ARGS)


def normalize(text: str) -> str:
    return SECONDS.sub("<seconds>s", RUN_DIRECTORY.sub("<run-dir>", text))
