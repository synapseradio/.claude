#!/usr/bin/env python3
"""What `scripts/verify/cli.py test` starts, what it prints, and how it exits.

The runner programs are stubs (see `verify_fixtures`) that record their argv
and environment and print canned pytest `-rf` or bats TAP output, so each case
checks the runner's own work: the commands it builds, the environment it hands
them, the report it prints, and its exit code.
"""

import json
import pathlib
import re

import pytest
from verify_fixtures import (
    BATS_TWO_FAILURES,
    GIT_LOCATORS,
    PYTEST_ONE_FAILURE,
    Sandbox,
    find_line,
    indented_block,
    pair,
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
