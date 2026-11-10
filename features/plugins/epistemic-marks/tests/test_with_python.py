"""Tests for hooks/with-python.sh, the interpreter chooser every hook command
runs through instead of naming an interpreter directly, run from the plugin
root:

    python3.14 -m pytest tests/test_with_python.py -v

Every interpreter here is a mock executable placed in a temporary directory
that becomes the child process's whole PATH, so a test never depends on
which real interpreters happen to be installed on the machine running it.
"""

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
CHOOSER = PLUGIN_ROOT / "hooks" / "with-python.sh"
ESCAPE_HATCH = "EPISTEMIC_MARKS_PYTHON"

PROBE_SCRIPT = "print('PROBE-OK')\n"


def make_executable(path, body):
    path.write_text(body)
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def working_mock(path, real_interpreter):
    """A stand-in that behaves like a real interpreter at or above the floor.

    It answers a `-c` version probe and a script invocation alike by handing
    both to the real interpreter underneath, so it passes with-python.sh's
    usability check and then actually runs whatever script it is given.
    """
    make_executable(path, f'#!/bin/bash\nexec "{real_interpreter}" "$@"\n')


def unusable_mock(path):
    """A stand-in for an interpreter below the floor: found on PATH, but
    fails the version probe every time, the way a pre-3.9 python would."""
    make_executable(path, "#!/bin/bash\nexit 1\n")


def version_reporting_mock(path, real_interpreter, version):
    """A stand-in that reports `version` to a `-c` probe and runs scripts for real.

    The probe is evaluated by the real interpreter with `sys.version_info`
    replaced first, so the launcher's own comparison decides the outcome and
    a probe set too high or too low fails a test. A script invocation passes
    straight through to the real interpreter.
    """
    reported = f"({version[0]}, {version[1]}, 0, 'final', 0)"
    make_executable(
        path,
        "#!/bin/bash\n"
        'if [[ "${1:-}" == -c ]]; then\n'
        f'  exec "{real_interpreter}" -c "import sys; sys.version_info = {reported}; ${{2}}"\n'
        "fi\n"
        f'exec "{real_interpreter}" "$@"\n',
    )


def run_chooser(script, path_dirs, env_extra=None):
    env = {key: value for key, value in os.environ.items() if key not in (ESCAPE_HATCH, "PATH")}
    env["PATH"] = os.pathsep.join(str(d) for d in path_dirs)
    env.update(env_extra or {})
    return subprocess.run(
        ["/bin/bash", str(CHOOSER), str(script)],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


class WithPythonFallsBackWhenThePreferredInterpreterIsAbsent(unittest.TestCase):
    def test_it_execs_python3_when_no_versioned_interpreter_is_on_path(self):
        real = sys.executable
        with tempfile.TemporaryDirectory() as bindir, tempfile.TemporaryDirectory() as scratch:
            bindir = Path(bindir)
            # No versioned interpreter anywhere on this PATH; only a python3 stands in.
            working_mock(bindir / "python3", real)
            script = Path(scratch) / "probe.py"
            script.write_text(PROBE_SCRIPT)

            result = run_chooser(script, [bindir])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "PROBE-OK")


class WithPythonHonorsTheEscapeHatch(unittest.TestCase):
    def test_the_named_interpreter_runs_even_though_every_candidate_fails_its_probe(self):
        real = sys.executable
        with tempfile.TemporaryDirectory() as bindir, tempfile.TemporaryDirectory() as scratch:
            bindir = Path(bindir)
            # Both default candidates are on PATH, but neither can serve the
            # hook: only the escape hatch's own interpreter can. If the
            # chooser ignored the variable and walked its own candidate list
            # instead, this run would exit 1 with no interpreter found.
            unusable_mock(bindir / "python3.14")
            unusable_mock(bindir / "python3")
            named = bindir / "chosen-interpreter"
            working_mock(named, real)
            script = Path(scratch) / "probe.py"
            script.write_text(PROBE_SCRIPT)

            result = run_chooser(script, [bindir], env_extra={ESCAPE_HATCH: str(named)})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "PROBE-OK")


class WithPythonReportsAndExitsNonZeroWhenNothingServes(unittest.TestCase):
    def test_it_names_the_requirement_on_stderr_and_leaves_stdout_empty(self):
        with tempfile.TemporaryDirectory() as bindir, tempfile.TemporaryDirectory() as scratch:
            bindir = Path(bindir)
            unusable_mock(bindir / "python3.14")
            unusable_mock(bindir / "python3")
            script = Path(scratch) / "probe.py"
            script.write_text(PROBE_SCRIPT)

            result = run_chooser(script, [bindir])

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("3.9", result.stderr)
        self.assertIn(ESCAPE_HATCH, result.stderr)


class WithPythonBindsItsFloorFromBothSides(unittest.TestCase):
    def test_an_interpreter_reporting_3_9_serves_the_script(self):
        real = sys.executable
        with tempfile.TemporaryDirectory() as bindir, tempfile.TemporaryDirectory() as scratch:
            bindir = Path(bindir)
            version_reporting_mock(bindir / "python3", real, (3, 9))
            script = Path(scratch) / "probe.py"
            script.write_text(PROBE_SCRIPT)

            result = run_chooser(script, [bindir])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "PROBE-OK")

    def test_an_interpreter_reporting_3_8_is_refused_and_the_floor_is_named(self):
        real = sys.executable
        with tempfile.TemporaryDirectory() as bindir, tempfile.TemporaryDirectory() as scratch:
            bindir = Path(bindir)
            version_reporting_mock(bindir / "python3", real, (3, 8))
            script = Path(scratch) / "probe.py"
            script.write_text(PROBE_SCRIPT)

            result = run_chooser(script, [bindir])

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("3.9", result.stderr)
        self.assertIn(ESCAPE_HATCH, result.stderr)

    def test_a_versioned_interpreter_serves_where_python3_is_unusable(self):
        real = sys.executable
        with tempfile.TemporaryDirectory() as bindir, tempfile.TemporaryDirectory() as scratch:
            bindir = Path(bindir)
            unusable_mock(bindir / "python3")
            working_mock(bindir / "python3.11", real)
            script = Path(scratch) / "probe.py"
            script.write_text(PROBE_SCRIPT)

            result = run_chooser(script, [bindir])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "PROBE-OK")


if __name__ == "__main__":
    unittest.main()
