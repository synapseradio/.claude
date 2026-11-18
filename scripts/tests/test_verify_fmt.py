#!/usr/bin/env python3
"""`scripts/verify/cli.py fmt`, `verify`, and `list --json` against a scratch repository.

fmt resolves its scope to files and hands them to treefmt, or hands treefmt
formatter names for `--lang`; verify runs fmt to completion, then lint and
test for the same scope; list prints the job manifest. Every program is a
stub recording argv and start and end order (see `verify_fixtures`).
"""

import json
import subprocess
import tomllib

import pytest
from verify_fixtures import FILES, Sandbox


@pytest.fixture
def sb(tmp_path) -> Sandbox:
    return Sandbox(tmp_path)


def formatters(args: list[str]) -> set[str]:
    """The formatter names a treefmt argv selects, from `--formatters a,b`, repeated, or `--formatters=a,b`."""
    names = []
    for index, arg in enumerate(args):
        if arg == "--formatters" and index + 1 < len(args):
            names.extend(args[index + 1].split(","))
        elif arg.startswith("--formatters="):
            names.extend(arg.split("=", 1)[1].split(","))
    return set(names)


def treefmt_call(sb) -> dict:
    calls = sb.calls("treefmt")
    assert len(calls) == 1, f"treefmt ran {len(calls)} times: {[c['args'] for c in calls]}"
    return calls[0]


def fmt(sb, *args: str, expect: int = 0) -> subprocess.CompletedProcess:
    return sb.run_expecting("fmt", *args, expect=expect)


class TestFmtScope:
    def test_no_scope_runs_treefmt_over_the_whole_tree(self, sb) -> None:
        fmt(sb)

        call = treefmt_call(sb)
        assert sb.paths_in(call) == [], f"treefmt walks the tree itself: {call['args']}"

    def test_paths_reach_treefmt_as_files(self, sb) -> None:
        fmt(sb, "pkg_a/src/a.py", "README.md")

        assert set(sb.paths_in(treefmt_call(sb))) == {"pkg_a/src/a.py", "README.md"}

    def test_diff_hands_existing_changed_files_and_drops_deleted_ones(self, sb) -> None:
        sb.write("pkg_a/src/a.py", "VALUE = 10\n")
        sb.write("pkg_a/src/new.py", "NEW = 1\n")
        (sb.repo / "pkg_b" / "src" / "b.py").unlink()

        fmt(sb, "--diff")

        call = treefmt_call(sb)
        assert set(sb.paths_in(call)) == {"pkg_a/src/a.py", "pkg_a/src/new.py"}
        assert not any(arg.endswith("pkg_b/src/b.py") for arg in call["args"]), (
            "a deleted file has nothing to format"
        )

    def test_prepush_hands_the_files_of_unpushed_commits(self, sb) -> None:
        sb.add_origin()
        sb.git("push", "-q", "origin", "main")
        sb.write("pkg_a/src/a.py", "VALUE = 10\n")
        sb.commit("pushed change to a")
        sb.git("push", "-q", "-u", "origin", "work")
        sb.write("pkg_b/src/b.py", "VALUE = 20\n")
        sb.commit("unpushed change to b")

        fmt(sb, "--prepush")

        assert sb.paths_in(treefmt_call(sb)) == ["pkg_b/src/b.py"]

    def test_file_hands_every_tracked_file_whose_path_holds_the_substring(self, sb) -> None:
        fmt(sb, "--file", "test_a")

        assert set(sb.paths_in(treefmt_call(sb))) == {
            "pkg_a/tests/test_a1.py",
            "pkg_a/tests/test_a2.py",
            "pkg_a/tests/test_a3.py",
        }

    @pytest.mark.parametrize(
        ("lang", "names"),
        [
            ("py", {"ruff-check", "ruff-format"}),
            ("md", {"rumdl"}),
            ("sh", {"shfmt"}),
            ("bats", {"shfmt"}),
            ("ts", {"biome"}),
            ("json", {"biome"}),
            ("yaml", {"yamlfmt"}),
            ("toml", {"taplo"}),
        ],
    )
    def test_lang_selects_the_formatters_treefmt_toml_runs_on_that_language(
        self, sb, lang, names
    ) -> None:
        fmt(sb, "--lang", lang)

        call = treefmt_call(sb)
        assert formatters(call["args"]) == names, call["args"]
        assert sb.paths_in(call) == [], call["args"]

    def test_k_is_a_usage_error(self, sb) -> None:
        result = fmt(sb, "-k", "name", expect=2)

        assert "-k" in result.stderr, "the usage error names the flag fmt refuses"
        assert sb.calls() == []

    def test_an_empty_diff_exits_zero_without_treefmt(self, sb) -> None:
        fmt(sb, "--diff")

        assert sb.calls("treefmt") == [], "nothing changed, so nothing to format"

    @pytest.mark.parametrize("prog", ["treefmt", "yamlfmt"])
    def test_a_missing_formatter_program_exits_three_naming_just_tools(self, sb, prog) -> None:
        sb.remove_stub(prog)

        result = fmt(sb, expect=3)

        output = result.stdout + result.stderr
        assert prog in output, "the message names the missing program"
        assert "just tools" in output, output


class TestVerify:
    def test_fmt_finishes_before_lint_or_test_starts(self, sb) -> None:
        result = sb.run("verify", "pkg_a/src/a.py")

        assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
        events = sb.events()
        assert events and events[0]["prog"] == "treefmt", [(e["event"], e["prog"]) for e in events]
        treefmt_end = next(
            i for i, e in enumerate(events) if e["prog"] == "treefmt" and e["event"] == "end"
        )
        later = [e for e in events if e["prog"] != "treefmt" and e["event"] == "start"]
        assert later, "lint and test ran after fmt"
        assert all(events.index(e) > treefmt_end for e in later), (
            "lint and test format-check and test the formatted tree"
        )
        assert len([c for c in sb.calls("uv") if "ruff" in c["args"]]) == 1, "lint ran"
        assert len([c for c in sb.calls("uv") if "pytest" in c["args"]]) == 1, "test ran"

    def test_the_exit_is_the_worst_of_its_parts(self, sb) -> None:
        sb.respond("uv", "ruff", "pkg_a/src/a.py:1:1: F401\n", exit_code=1)

        result = sb.run("verify", "pkg_a/src/a.py")

        assert result.returncode == 1, f"exit {result.returncode}: {result.stderr}"
        assert len([c for c in sb.calls("uv") if "pytest" in c["args"]]) == 1, (
            "a lint failure leaves the tests running"
        )

    def test_a_missing_tool_in_fmt_stops_before_lint_and_test(self, sb) -> None:
        sb.remove_stub("treefmt")

        result = sb.run("verify", "pkg_a/src/a.py")

        assert result.returncode == 3, f"exit {result.returncode}: {result.stderr}"
        assert sb.calls() == [], "exit 3 short-circuits"

    def test_a_usage_error_runs_nothing(self, sb) -> None:
        result = sb.run("verify", "--bogus")

        assert result.returncode == 2, f"exit {result.returncode}: {result.stderr}"
        assert "--bogus" in result.stderr
        assert sb.calls() == []

    def test_json_holds_fmt_lint_and_test_parts(self, sb) -> None:
        report = sb.run_json("verify", "pkg_a/src/a.py")

        assert {"fmt", "lint", "test", "exit"} <= set(report), sorted(report)
        assert report["exit"] == 0
        assert "exit" in report["fmt"], report["fmt"]
        assert {suite["name"] for suite in report["test"]["suites"]} == {"py-a"}
        assert {suite["name"] for suite in report["lint"]["suites"]} == {"ruff"}


def test_list_json_prints_the_manifest_and_runs_nothing(sb) -> None:
    result = sb.run("list", "--json")

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    assert sb.calls() == [], "list starts no program"
    listed = {job["name"]: job for job in json.loads(result.stdout)["jobs"]}
    expected = tomllib.loads(FILES["scripts/verify/jobs.toml"])["job"]
    assert set(listed) == {job["name"] for job in expected}
    for job in expected:
        for key in ("kind", "sources", "langs"):
            assert listed[job["name"]][key] == job[key], f"{job['name']} {key}"
