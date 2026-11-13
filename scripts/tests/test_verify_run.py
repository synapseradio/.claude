#!/usr/bin/env python3
"""What `scripts/verify/cli.py test` starts, what it prints, and how it exits.

The runner programs are stubs (see `verify_fixtures`) that record their argv
and environment and print canned pytest `-rf` or bats TAP output, so each case
checks the runner's own work: the commands it builds, the environment it hands
them, the report it prints, and its exit code.
"""

import fcntl
import importlib
import json
import pathlib
import re
import signal
from dataclasses import dataclass

import pytest
from verify_fixtures import (
    BATS_TWO_FAILURES,
    GIT_LOCATORS,
    PYTEST_ONE_FAILURE,
    RUN_TIMEOUT,
    Sandbox,
    find_line,
    indented_block,
    load_cli,
    pair,
)
from verify_plain_run import normalize, run_scenario
from verify_stubs import (
    install_real_pytest,
    install_sleeper,
    is_alive,
    kill_leftovers,
    sleeper_pids,
)

SECONDS = r"\d+(?:\.\d+)?s"
PYTEST_FAILURE_LINE = "FAILED pkg_a/tests/test_a1.py::test_two - AssertionError: boom"


@pytest.fixture
def sb(tmp_path) -> Sandbox:
    return Sandbox(tmp_path)


class TestEveryChildRunsOutsideTheCallersRepository:
    def test_no_runner_inherits_a_variable_that_locates_a_repository(self, sb) -> None:
        """Git hands a hook run from a linked worktree GIT_DIR and GIT_INDEX_FILE.

        A suite's scratch repository would then write into the real one.
        https://git-scm.com/docs/githooks
        """
        git_dir = sb.repo / ".git"
        located = {
            "GIT_DIR": str(git_dir),
            "GIT_INDEX_FILE": str(git_dir / "index"),
            "GIT_PREFIX": "",
            "GIT_WORK_TREE": str(sb.repo),
            "GIT_COMMON_DIR": str(git_dir),
        }

        result = sb.run("test", "--lang", "py,bats,ts", extra_env=located)

        assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
        for prog in ("uv", "bats", "claude"):
            calls = sb.calls(prog)
            assert calls, f"{prog} never ran, so its environment went unchecked"
            for call in calls:
                leaked = [name for name in GIT_LOCATORS if name in call["env"]]
                assert leaked == [], f"{prog} {call['args']} inherited {leaked}"


class TestRunnerCommands:
    def test_pytest_runs_through_uv_with_the_cache_plugin_off_and_a_failure_summary(
        self, sb
    ) -> None:
        sb.run_json("test", "pkg_a")

        args = sb.call_for("uv", "pkg_a")["args"]
        assert args[:3] == ["run", "--frozen", "pytest"], args
        assert pair(args, "-p", "no:cacheprovider"), (
            f"concurrent pytest runs sharing a rootdir write the same .pytest_cache: {args}"
        )
        assert "-rf" in args, f"failing ids come from the FAILED lines -rf prints: {args}"

    def test_bats_reports_in_tap(self, sb) -> None:
        sb.run_json("test", "shell")

        args = sb.calls("bats")[0]["args"]
        assert pair(args, "--formatter", "tap"), f"failing ids come from TAP not ok lines: {args}"

    def test_the_mod_runner_takes_the_suite_folder(self, sb) -> None:
        sb.run_json("test", "mod")

        call = sb.calls("claude")[0]
        assert call["args"][:2] == ["plugin", "test"], call["args"]
        assert sb.paths_in(call) == ["mod"]


class TestTextReport:
    def run_one_failing_one_passing(self, sb) -> list[str]:
        sb.respond("uv", "pkg_a", PYTEST_ONE_FAILURE, exit_code=1)
        result = sb.run("test", "pkg_a", "shell")
        assert result.returncode == 1, f"exit {result.returncode}: {result.stderr}"
        return result.stdout.splitlines()

    def test_a_run_prints_a_header_a_line_per_suite_its_failing_ids_and_a_tally(self, sb) -> None:
        lines = self.run_one_failing_one_passing(sb)

        assert re.fullmatch(r"verify: 2 suites, logs in \S+", lines[0]), lines[0]
        find_line(lines, rf"PASS sh-bats \(bats, 3 passed, {SECONDS}\)")
        index, _ = find_line(
            lines, rf"FAIL py-a \(pytest, [^)]*\b1 failed\b[^)]*, {SECONDS}\) log=\S+"
        )
        assert indented_block(lines, index) == [PYTEST_FAILURE_LINE], (
            "the FAILED lines of pytest -rf follow the suite's FAIL line, indented"
        )
        assert lines[-1] == "verify: 1 passed, 1 failed, 0 skipped"

    def test_a_failing_suite_names_its_log_inside_the_run_directory(self, sb) -> None:
        lines = self.run_one_failing_one_passing(sb)

        run_dir = pathlib.Path(re.fullmatch(r"verify: \d+ suites, logs in (\S+)", lines[0])[1])
        _, match = find_line(lines, r"FAIL py-a \(.*\) log=(\S+)")
        log = pathlib.Path(match[1])

        assert run_dir.resolve().parent == sb.logs / "proj-work", (
            "logs sit under <log root>/<repo>-<branch>/"
        )
        assert re.fullmatch(r"\d{8}-\d{6}-\d+", run_dir.name), run_dir.name
        assert log.resolve() == run_dir.resolve() / "py-a.log"
        assert PYTEST_FAILURE_LINE in log.read_text(), "the log holds the runner's own output"

    def test_bats_failures_are_its_not_ok_lines(self, sb) -> None:
        sb.respond("bats", "shell", BATS_TWO_FAILURES, exit_code=1)

        result = sb.run("test", "shell")

        assert result.returncode == 1, f"exit {result.returncode}: {result.stderr}"
        lines = result.stdout.splitlines()
        index, _ = find_line(
            lines, rf"FAIL sh-bats \(bats, [^)]*\b2 failed\b[^)]*, {SECONDS}\) log=\S+"
        )
        assert indented_block(lines, index) == [
            "not ok 2 second case fails",
            "not ok 4 fourth case fails",
        ], "TAP comment lines are diagnostics, not failing ids"

    def test_at_most_twenty_failing_ids_follow_a_failure(self, sb) -> None:
        failures = "".join(
            f"FAILED pkg_a/tests/test_a1.py::test_{n:02d} - AssertionError\n" for n in range(25)
        )
        sb.respond("uv", "pkg_a", f"{failures}25 failed in 0.50s\n", exit_code=1)

        result = sb.run("test", "pkg_a")

        assert result.returncode == 1, f"exit {result.returncode}: {result.stderr}"
        lines = result.stdout.splitlines()
        index, _ = find_line(lines, r"FAIL py-a \(.*")
        block = indented_block(lines, index)
        assert len(block) == 20, f"{len(block)} failing ids printed"
        assert block[0] == "FAILED pkg_a/tests/test_a1.py::test_00 - AssertionError"


class TestJsonReport:
    def test_json_replaces_the_text_with_one_object(self, sb) -> None:
        sb.respond("uv", "pkg_a", PYTEST_ONE_FAILURE, exit_code=1)

        result = sb.run("test", "pkg_a", "shell", "--json")

        assert result.returncode == 1, f"exit {result.returncode}: {result.stderr}"
        report = json.loads(result.stdout)
        assert {"logs", "suites", "summary", "exit", "notes"} <= set(report), sorted(report)
        assert report["summary"] == {"passed": 1, "failed": 1, "skipped": 0}
        assert report["exit"] == 1
        suites = {suite["name"]: suite for suite in report["suites"]}
        assert set(suites) == {"py-a", "sh-bats"}

        failed = suites["py-a"]
        assert failed["runner"] == "pytest"
        assert failed["status"] == "fail"
        assert failed["counts"]["failed"] == 1 and failed["counts"]["passed"] == 2, failed["counts"]
        assert failed["failures"] == [PYTEST_FAILURE_LINE]
        assert pathlib.Path(failed["log"]).is_file()
        assert isinstance(failed["seconds"], (int, float))
        assert isinstance(failed["command"], list) and "pytest" in failed["command"], (
            "the report carries the exact argv it ran"
        )

        passed = suites["sh-bats"]
        assert passed["status"] == "pass"
        assert passed["failures"] == []


def test_list_prints_the_selection_and_its_commands_and_runs_nothing(sb) -> None:
    result = sb.run("test", "pkg_a", "--list")

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    assert sb.calls() == [], "--list starts no runner"
    assert "py-a" in result.stdout
    assert any("pytest" in line and "pkg_a/tests" in line for line in result.stdout.splitlines()), (
        f"--list prints the command it would run:\n{result.stdout}"
    )


class TestExitCodes:
    def test_zero_when_every_selected_suite_passes(self, sb) -> None:
        result = sb.run("test", "pkg_b")

        assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
        assert result.stdout.splitlines()[-1] == "verify: 1 passed, 0 failed, 0 skipped"

    def test_one_when_a_runner_exits_nonzero_without_naming_a_failed_test(self, sb) -> None:
        sb.respond("uv", "pkg_b", "ERROR collecting pkg_b/tests/test_b1.py\n1 error in 0.05s\n", 2)

        result = sb.run("test", "pkg_b")

        assert result.returncode == 1, (
            f"the runner's exit code decides the verdict, not the lines it printed; "
            f"exit {result.returncode}: {result.stderr}"
        )
        find_line(result.stdout.splitlines(), r"FAIL py-b \(.*")

    def test_two_for_an_unknown_flag(self, sb) -> None:
        result = sb.run("test", "--bogus")

        assert result.returncode == 2, f"exit {result.returncode}: {result.stderr}"
        assert "--bogus" in result.stderr, "the usage error names the flag it refused"
        assert sb.calls() == []

    @pytest.mark.parametrize(
        ("prog", "scope", "provider"),
        [("bats", "shell", "just tools"), ("claude", "mod", "Claude Code")],
    )
    def test_three_when_a_selected_runner_is_missing_naming_what_provides_it(
        self, sb, prog, scope, provider
    ) -> None:
        sb.remove_stub(prog)

        result = sb.run("test", scope)

        output = result.stdout + result.stderr
        assert result.returncode == 3, f"exit {result.returncode}: {result.stderr}"
        assert prog in output, "the message names the missing program"
        assert provider in output, (
            f"the Brewfile behind just tools installs bats; claude comes with Claude Code: {output}"
        )

    def test_five_when_an_explicit_scope_selects_no_suite(self, sb) -> None:
        result = sb.run("test", "--lang", "md")

        assert result.returncode == 5, f"exit {result.returncode}: {result.stderr}"
        assert "no test matches" in result.stdout + result.stderr


SAMPLES = pathlib.Path(__file__).parent
PLAIN_RUN_SAMPLE = SAMPLES / "verify_samples" / "plain-run.txt"
PYTEST_VERBOSE_SAMPLE = (SAMPLES / "progress_samples" / "pytest.txt").read_text()
BATS_TIMING_SAMPLE = (SAMPLES / "progress_samples" / "bats-tap-timing.txt").read_text()


def test_a_plain_run_prints_what_the_runner_printed_before_progress_was_added(tmp_path) -> None:
    """The sample is the output of the runner at commit 1d827c2, captured through the sandbox before the wiring changed."""
    result = run_scenario(Sandbox(tmp_path))

    assert normalize(result.stdout) == PLAIN_RUN_SAMPLE.read_text(encoding="utf-8")


class TestVerbose:
    def run_piped(self, sb) -> list[str]:
        sb.respond("uv", "pkg_a", PYTEST_VERBOSE_SAMPLE, exit_code=1)
        sb.respond("bats", "shell", BATS_TIMING_SAMPLE, exit_code=1)
        process = sb.popen("test", "pkg_a", "shell", "--verbose")
        out, err = process.communicate(timeout=RUN_TIMEOUT)
        assert process.returncode == 1, f"exit {process.returncode}: {err.decode()}"
        return out.decode().splitlines()

    def test_each_suite_prints_its_pytest_tree_right_after_its_verdict(self, sb) -> None:
        lines = self.run_piped(sb)

        verdict, _ = find_line(lines, r"FAIL py-a \(.*")
        tree, _ = find_line(lines, r"✗ py-a")
        assert lines[tree - 1].startswith(
            "  FAILED tests/test_sample.py::test_rejects_wrong_sum"
        ), "the tree follows the suite's verdict and its failing ids, before the next suite's line"
        assert tree > verdict
        assert lines[tree : tree + 5] == [
            "✗ py-a",
            "  tests/test_sample.py",
            "    ✓ test_adds_numbers",
            "    ✗ test_rejects_wrong_sum",
            "    ○ test_skipped_case",
        ]

    def test_each_suite_prints_its_bats_tree_with_the_seconds_each_test_took(self, sb) -> None:
        lines = self.run_piped(sb)

        tree, _ = find_line(lines, r"✗ sh-bats")
        assert lines[tree - 1].startswith("  not ok 2 rejects wrong sum"), (
            "the tree follows the suite's verdict and its failing ids"
        )
        assert lines[tree : tree + 4] == [
            "✗ sh-bats",
            "  ✓ adds numbers (0.002s)",
            "  ✗ rejects wrong sum (0.001s)",
            "  ○ skipped case (0.002s)",
        ]


class TestAnInterruptedRun:
    @dataclass(frozen=True)
    class Aftermath:
        code: int
        pids: list[int]
        alive: list[int]
        held_slots: list[str]

    def interrupt_a_sleeping_suite(self, sb) -> Aftermath:
        install_sleeper(sb, "uv")
        process = sb.popen("test", "pkg_a", extra_env={"VERIFY_SLOTS": "3"})
        pids: list[int] = []
        try:
            pids = sleeper_pids(sb)
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=RUN_TIMEOUT)
            alive = [pid for pid in pids if is_alive(pid)]
            return self.Aftermath(process.returncode, pids, alive, held_slots(sb, 3))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=RUN_TIMEOUT)
            kill_leftovers(pids)

    def test_sigint_ends_the_run_with_130(self, sb) -> None:
        aftermath = self.interrupt_a_sleeping_suite(sb)

        assert aftermath.code == 130, f"exit {aftermath.code}"

    def test_sigint_leaves_neither_the_suite_nor_its_child_running(self, sb) -> None:
        aftermath = self.interrupt_a_sleeping_suite(sb)

        assert aftermath.alive == [], (
            f"processes {aftermath.alive} of {aftermath.pids} outlived the interrupted run"
        )

    def test_sigint_leaves_every_slot_free(self, sb) -> None:
        aftermath = self.interrupt_a_sleeping_suite(sb)

        assert aftermath.held_slots == [], (
            f"slots still held after the interrupted run exited: {aftermath.held_slots}"
        )


def held_slots(sb: Sandbox, size: int) -> list[str]:
    held = []
    for index in range(size):
        with open(sb.slot(index), "a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                held.append(sb.slot(index).name)
    return held


class TestAJsonRun:
    @pytest.mark.parametrize("flags", [("--json",), ("--verbose", "--json")])
    def test_stdout_holds_one_json_object_and_nothing_else(self, sb, flags) -> None:
        sb.respond("uv", "pkg_a", PYTEST_VERBOSE_SAMPLE, exit_code=1)
        sb.respond("bats", "shell", BATS_TIMING_SAMPLE, exit_code=1)

        process = sb.popen("test", "pkg_a", "shell", *flags)
        out, err = process.communicate(timeout=RUN_TIMEOUT)

        assert process.returncode == 1, f"exit {process.returncode}: {err.decode()}"
        decoder = json.JSONDecoder()
        text = out.decode()
        report, end = decoder.raw_decode(text)
        assert isinstance(report, dict) and {"suites", "summary", "exit"} <= set(report), report
        assert text[end:].strip() == "", f"stdout carries text after the object: {text[end:]!r}"
        assert text[:1] == "{", f"stdout carries text before the object: {text[:80]!r}"


SLOW_SUITE = {
    ".gitignore": "node_modules/\n",
    "pyproject.toml": '[project]\nname = "proj"\n',
    "scripts/verify/jobs.toml": (
        '[[job]]\nname = "slow"\nkind = "pytest"\ntests = ["slow/tests"]\n'
        'sources = ["slow/**"]\nlangs = ["py"]\n'
    ),
    "slow/tests/test_stalls.py": (
        "import time\n\n\n"
        "def test_stalls_past_the_limit():\n    time.sleep(4)\n\n\n"
        "def test_returns_at_once():\n    pass\n"
    ),
}


class TestATestPastTheLimit:
    def test_a_test_sleeping_past_the_limit_fails_by_its_name(self, tmp_path, monkeypatch) -> None:
        """The limit is 10 seconds in the runner; the case shortens it to 1 so that it needs 4 seconds, not 11.

        https://pypi.org/project/pytest-timeout/
        """
        load_cli()
        tasks = importlib.import_module("tasks")
        monkeypatch.setattr(tasks, "TEST_TIMEOUT_SECONDS", 1, raising=False)
        sb = Sandbox(tmp_path, SLOW_SUITE)
        install_real_pytest(sb)

        result = sb.run("test", "--json")

        (suite,) = json.loads(result.stdout)["suites"]
        assert suite["status"] == "fail", f"a test outlasting the limit passed: {suite}"
        assert len(suite["failures"]) == 1, suite["failures"]
        assert "slow/tests/test_stalls.py::test_stalls_past_the_limit" in suite["failures"][0], (
            f"the failing id names the test that was stopped: {suite['failures']}"
        )
