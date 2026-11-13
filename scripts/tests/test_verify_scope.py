#!/usr/bin/env python3
"""Which suites and test files `scripts/verify/cli.py test` selects for each scope.

A wrong selection hands an agent a pass for code no test ran, so each rule
under Scope grammar, `--diff`, `--prepush`, Changed-file to suite, and Empty
selection in the verification plan has a case here. Every case runs the CLI
against a scratch repository whose own `scripts/verify/jobs.toml` holds four
suites and one lint job (see `verify_fixtures.MANIFEST`), with `uv`, `bats`,
and `claude` stubbed, and reads the selection from the JSON report and the
argv each stub received.
"""

import os
import pathlib
import re
import subprocess
import tomllib

import pytest
from verify_fixtures import (
    GIT_LOCATORS,
    PYTEST_NONE_SELECTED,
    REAL_MANIFEST,
    RUN_TIMEOUT,
    WORKTREE,
    Sandbox,
    pair,
    ran,
)


@pytest.fixture
def sb(tmp_path) -> Sandbox:
    return Sandbox(tmp_path)


class TestDiffSelectsFromEverythingChangedSinceTheBase:
    def test_an_unstaged_edit_selects_the_suite_owning_the_file(self, sb) -> None:
        sb.write("pkg_a/src/a.py", "VALUE = 10\n")

        report = sb.run_json("test", "--diff")

        assert ran(report) == {"py-a"}, "an edit left in the working tree is part of the diff"
        assert sb.paths_in(sb.call_for("uv", "pkg_a")) == ["pkg_a/tests"], (
            "a changed source file runs its whole suite"
        )

    def test_a_staged_edit_selects_the_suite_owning_the_file(self, sb) -> None:
        sb.write("pkg_a/src/a.py", "VALUE = 10\n")
        sb.git("add", "pkg_a/src/a.py")

        report = sb.run_json("test", "--diff")

        assert ran(report) == {"py-a"}, "a staged edit is part of the diff"

    def test_a_commit_on_the_branch_selects_the_suite_owning_the_file(self, sb) -> None:
        sb.write("pkg_a/src/a.py", "VALUE = 10\n")
        sb.commit("change a")

        report = sb.run_json("test", "--diff")

        assert ran(report) == {"py-a"}, (
            "a commit since the merge-base with main is part of the diff"
        )

    def test_an_untracked_file_selects_the_suite_whose_glob_holds_it(self, sb) -> None:
        sb.write("pkg_a/src/new.py", "NEW = 1\n")

        report = sb.run_json("test", "--diff")

        assert ran(report) == {"py-a"}, "an untracked file is part of the diff"

    def test_a_change_no_glob_matches_selects_nothing_and_exits_zero(self, sb) -> None:
        sb.write("README.md", "# proj, edited\n")

        result = sb.run("test", "--diff")

        assert result.returncode == 0, (
            f"an empty selection from --diff is a pass, got {result.returncode}: {result.stderr}"
        )
        assert "no suite maps to the changed files" in result.stdout + result.stderr
        assert sb.calls() == [], "no runner starts when no suite is selected"

    def test_a_named_base_replaces_main(self, sb) -> None:
        sb.write("pkg_b/src/b.py", "VALUE = 20\n")
        sb.commit("change b")
        sb.git("branch", "base-here")
        sb.write("pkg_a/src/a.py", "VALUE = 10\n")
        sb.commit("change a")

        report = sb.run_json("test", "--diff", "base-here")

        assert ran(report) == {"py-a"}, "a commit before the named base is outside the diff"

    def test_a_changed_test_file_alone_runs_that_file_alone(self, sb) -> None:
        sb.write("pkg_a/tests/test_a2.py", "def test_two():\n    assert True\n")
        sb.commit("change a test")

        report = sb.run_json("test", "--diff")

        assert ran(report) == {"py-a"}
        assert sb.paths_in(sb.call_for("uv", "pkg_a")) == ["pkg_a/tests/test_a2.py"], (
            "a scope of only test files runs those files under a file-taking runner"
        )

    def test_a_changed_test_file_beside_a_changed_source_runs_the_whole_suite(self, sb) -> None:
        sb.write("pkg_a/tests/test_a2.py", "def test_two():\n    assert True\n")
        sb.write("pkg_a/src/a.py", "VALUE = 10\n")
        sb.commit("change a and a test")

        sb.run_json("test", "--diff")

        assert sb.paths_in(sb.call_for("uv", "pkg_a")) == ["pkg_a/tests"], (
            "a changed source file can break any test of its suite"
        )

    def test_a_deleted_test_file_runs_its_whole_suite(self, sb) -> None:
        sb.git("rm", "-q", "pkg_a/tests/test_a2.py")
        sb.commit("drop a test")

        report = sb.run_json("test", "--diff")

        assert ran(report) == {"py-a"}
        call = sb.call_for("uv", "pkg_a")
        assert sb.paths_in(call) == ["pkg_a/tests"], call["args"]
        assert not any(arg.endswith("test_a2.py") for arg in call["args"]), (
            "a deleted file cannot run alone"
        )

    def test_only_test_files_is_judged_per_suite(self, sb) -> None:
        sb.write("pkg_a/tests/test_a2.py", "def test_two():\n    assert True\n")
        sb.write("pkg_b/src/b.py", "VALUE = 20\n")
        sb.commit("change an a test and b source")

        report = sb.run_json("test", "--diff")

        assert ran(report) == {"py-a", "py-b"}
        assert sb.paths_in(sb.call_for("uv", "pkg_a")) == ["pkg_a/tests/test_a2.py"], (
            "py-a saw only a test file change, whatever py-b saw"
        )
        assert sb.paths_in(sb.call_for("uv", "pkg_b")) == ["pkg_b/tests"]


class TestPrepushSelectsFromCommitsNotYetPushed:
    def test_with_an_upstream_it_diffs_against_the_push_target(self, sb) -> None:
        sb.add_origin()
        sb.git("push", "-q", "origin", "main")
        sb.write("pkg_a/src/a.py", "VALUE = 10\n")
        sb.commit("pushed change to a")
        sb.git("push", "-q", "-u", "origin", "work")
        sb.write("pkg_b/src/b.py", "VALUE = 20\n")
        sb.commit("unpushed change to b")

        report = sb.run_json("test", "--prepush")

        assert ran(report) == {"py-b"}, (
            "a commit already on @{push} is outside the push; origin/main would add py-a"
        )

    def test_without_an_upstream_it_falls_back_to_origin_main_and_says_so(self, sb) -> None:
        sb.add_origin()
        sb.git("checkout", "-q", "main")
        sb.git("push", "-q", "origin", "main")
        sb.write("pkg_a/src/a.py", "VALUE = 10\n")
        sb.commit("local main change to a, never pushed")
        sb.git("checkout", "-q", "work")
        sb.git("reset", "-q", "--hard", "main")
        sb.write("pkg_b/src/b.py", "VALUE = 20\n")
        sb.commit("branch change to b")

        report = sb.run_json("test", "--prepush")

        assert ran(report) == {"py-a", "py-b"}, (
            "the fallback base is the merge-base with origin/main, so the unpushed main "
            "commit counts; local main would leave py-a out"
        )
        assert any("origin/main" in note for note in report["notes"]), (
            f"the report names the base it fell back to, notes were {report['notes']}"
        )


class TestPathsSelectTheirSuites:
    def test_a_pytest_test_file_runs_alone(self, sb) -> None:
        report = sb.run_json("test", "pkg_a/tests/test_a2.py")

        assert ran(report) == {"py-a"}
        assert sb.paths_in(sb.call_for("uv", "pkg_a")) == ["pkg_a/tests/test_a2.py"]

    def test_a_bats_test_file_runs_alone(self, sb) -> None:
        report = sb.run_json("test", "shell/tests/one.bats")

        assert ran(report) == {"sh-bats"}
        assert sb.paths_in(sb.calls("bats")[0]) == ["shell/tests/one.bats"]

    def test_a_source_file_runs_its_whole_suite(self, sb) -> None:
        report = sb.run_json("test", "pkg_b/src/b.py")

        assert ran(report) == {"py-b"}, "a lint job sharing the glob is no test suite"
        assert sb.paths_in(sb.call_for("uv", "pkg_b")) == ["pkg_b/tests"]

    def test_a_directory_runs_every_suite_owning_a_file_inside_it(self, sb) -> None:
        report = sb.run_json("test", "shell")

        assert ran(report) == {"sh-bats"}
        assert sb.paths_in(sb.calls("bats")[0]) == ["shell/tests"]

    def test_a_source_several_suites_glob_runs_each_of_them(self, sb) -> None:
        report = sb.run_json("test", "pyproject.toml")

        assert ran(report) == {"py-a", "py-b"}

    def test_a_single_star_matches_inside_one_directory(self, sb) -> None:
        report = sb.run_json("test", "plugins/x/manifest.json")

        assert ran(report) == {"py-b"}, "plugins/*/manifest.json holds plugins/x/manifest.json"

    def test_a_single_star_never_crosses_a_slash(self, sb) -> None:
        result = sb.run("test", "plugins/x/deep/manifest.json")

        assert result.returncode == 5, (
            f"plugins/*/manifest.json stops at one directory; exit {result.returncode}: {result.stderr}"
        )

    def test_a_missing_path_is_a_usage_error_naming_it(self, sb) -> None:
        result = sb.run("test", "nope/missing.py")

        assert result.returncode == 2, f"exit {result.returncode}: {result.stderr}"
        assert "nope/missing.py" in result.stderr, "the error names the path it could not find"
        assert sb.calls() == []


class TestLangSelectsByLanguage:
    def test_one_language_selects_its_suites(self, sb) -> None:
        report = sb.run_json("test", "--lang", "bats")

        assert ran(report) == {"sh-bats"}

    def test_a_comma_list_selects_each_language(self, sb) -> None:
        report = sb.run_json("test", "--lang", "py,ts")

        assert ran(report) == {"py-a", "py-b", "mod-gauge"}, "the py lint job is no test suite"

    def test_the_flag_repeats(self, sb) -> None:
        report = sb.run_json("test", "--lang", "py", "--lang", "ts")

        assert ran(report) == {"py-a", "py-b", "mod-gauge"}


class TestFileSelectsTestFilesByPath:
    def test_a_substring_runs_the_pytest_files_whose_path_holds_it(self, sb) -> None:
        report = sb.run_json("test", "--file", "test_a2")

        assert ran(report) == {"py-a"}
        assert sb.paths_in(sb.call_for("uv", "pkg_a")) == ["pkg_a/tests/test_a2.py"]

    def test_a_substring_runs_the_bats_files_whose_path_holds_it(self, sb) -> None:
        report = sb.run_json("test", "--file", "one.bats")

        assert ran(report) == {"sh-bats"}
        assert sb.paths_in(sb.calls("bats")[0]) == ["shell/tests/one.bats"]


class TestKSelectsTestCasesByName:
    def test_pytest_receives_the_substring_as_its_k_expression(self, sb) -> None:
        sb.run_json("test", "-k", "a.b")

        for needle in ("pkg_a", "pkg_b"):
            args = sb.call_for("uv", needle)["args"]
            assert pair(args, "-k", "a.b"), f"pytest for {needle} got {args}"

    def test_bats_receives_the_substring_regex_escaped_as_its_filter(self, sb) -> None:
        sb.run_json("test", "-k", "a.b")

        args = sb.calls("bats")[0]["args"]
        assert pair(args, "--filter", r"a\.b"), (
            f"bats reads --filter as a regex, so the dot must match only a dot; got {args}"
        )

    def test_the_mod_runner_runs_whole_when_a_test_literal_holds_the_substring(self, sb) -> None:
        report = sb.run_json("test", "-k", "gauge")

        assert "mod-gauge" in ran(report), (
            'mod/tests/gauge.test.ts holds test("renders the gauge bar"'
        )
        assert sb.paths_in(sb.calls("claude")[0]) == ["mod"]
        assert any("mod-gauge" in note and "cannot narrow" in note for note in report["notes"]), (
            f"the report says the mod runner ran its whole suite, notes were {report['notes']}"
        )

    def test_the_mod_runner_is_skipped_when_no_test_literal_holds_the_substring(self, sb) -> None:
        report = sb.run_json("test", "-k", "a.b")

        assert "mod-gauge" not in ran(report)
        assert sb.calls("claude") == [], "a mod suite with no matching test name never starts"

    def test_a_pytest_suite_selecting_no_test_is_skipped(self, sb) -> None:
        """Pytest exits 5 when it collects no test.

        https://docs.pytest.org/en/stable/reference/exit-codes.html
        """
        sb.respond("uv", "pkg_b", PYTEST_NONE_SELECTED, exit_code=5)

        report = sb.run_json("test", "-k", "a.b")

        suites = {suite["name"]: suite for suite in report["suites"]}
        assert suites["py-b"]["status"] == "skip", suites["py-b"]
        assert report["exit"] == 0, "a skipped suite fails nothing"

    def test_every_suite_skipping_under_an_explicit_scope_exits_five(self, sb) -> None:
        sb.respond("uv", "pytest", PYTEST_NONE_SELECTED, exit_code=5)

        result = sb.run("test", "--lang", "py", "-k", "zzz-no-such-case")

        assert result.returncode == 5, f"exit {result.returncode}: {result.stderr}"
        assert "no test matches" in result.stdout + result.stderr


class TestScopesIntersect:
    def test_a_language_and_a_path_select_what_both_select(self, sb) -> None:
        report = sb.run_json("test", "--lang", "py", "pkg_a/src/a.py")

        assert ran(report) == {"py-a"}

    def test_an_explicit_scope_matching_nothing_exits_five_naming_it(self, sb) -> None:
        result = sb.run("test", "--file", "zzz-no-such-test")

        assert result.returncode == 5, f"exit {result.returncode}: {result.stderr}"
        assert "no test matches" in result.stdout + result.stderr
        assert sb.calls() == []

    def test_scopes_whose_intersection_is_empty_exit_five(self, sb) -> None:
        result = sb.run("test", "--lang", "bats", "pkg_a")

        assert result.returncode == 5, (
            f"bats and pkg_a share no suite, so nothing is selected; exit {result.returncode}: "
            f"{result.stderr}"
        )


# The suite map lefthook.yml applies before push (pre-push `tests` jobs), plus
# the `scripts-bats` suite the verification plan adds. Each suite is keyed by
# its test paths; the value is its runner kind and the source globs it must
# carry. A suite may add globs inside its own test paths and nothing else.
EXPECTED_SUITES = {
    ("features/plugins/rulesets/tests",): (
        "pytest",
        {"features/plugins/rulesets/**", "pyproject.toml", "uv.lock"},
    ),
    ("features/plugins/epistemic-marks/tests",): (
        "pytest",
        {"features/plugins/epistemic-marks/**", "pyproject.toml", "uv.lock"},
    ),
    ("scripts/hooks", "scripts/tests"): (
        "pytest",
        {
            "scripts/**",
            ".claude-plugin/marketplace.json",
            "settings.base.json",
            "features/*/*/.claude-plugin/plugin.json",
            "pyproject.toml",
            "uv.lock",
        },
    ),
    ("features/plugins/warden/tests",): ("bats", {"features/plugins/warden/**"}),
    ("features/plugins/harness-config/tests",): ("bats", {"features/plugins/harness-config/**"}),
    ("features/mods/context-gauge",): ("mod", {"features/mods/context-gauge/**"}),
    ("scripts/render/tests", "scripts/setup/tests"): (
        "bats",
        {
            "scripts/setup.sh",
            "scripts/setup/**",
            "scripts/render.sh",
            "scripts/render/**",
            "scripts/lib/**",
            "scripts/tests/test_helper.bash",
        },
    ),
}


def test_the_real_manifest_carries_the_prepush_suite_map() -> None:
    assert REAL_MANIFEST.is_file(), f"{REAL_MANIFEST} is the job manifest the runner reads"
    jobs = tomllib.loads(REAL_MANIFEST.read_text(encoding="utf-8"))["job"]
    suites = {
        tuple(sorted(job["tests"])): (job["kind"], set(job["sources"]))
        for job in jobs
        if job["kind"] != "lint"
    }

    assert set(suites) == set(EXPECTED_SUITES), "the manifest holds exactly the seven suites"
    for tests, (kind, sources) in EXPECTED_SUITES.items():
        actual_kind, actual_sources = suites[tests]
        assert actual_kind == kind, f"{tests} runs under {kind}"
        missing = sources - actual_sources
        assert not missing, f"{tests} lost source globs {missing}, so a push touching them skips it"
        extra = {
            glob
            for glob in actual_sources - sources
            if not any(glob.startswith(f"{path}/") or glob == path for path in tests)
        }
        assert not extra, f"{tests} gained source globs {extra} outside its own test paths"


def lefthook_selects(glob: str, paths: list[str]) -> set[str]:
    """The paths lefthook's default matcher selects for `glob`.

    Lefthook compiles each glob with gobwas and no separators and lowercases
    pattern and path, so `*` crosses `/` and case is ignored.
    https://github.com/evilmartians/lefthook/blob/master/internal/run/controller/filter/filter.go
    https://github.com/gobwas/glob/blob/master/glob.go
    """
    pattern = ""
    index = 0
    while index < len(glob):
        char = glob[index]
        if char == "*":
            pattern += ".*"
            while index + 1 < len(glob) and glob[index + 1] == "*":
                index += 1
        elif char == "?":
            pattern += "."
        elif char == "{":
            close = glob.index("}", index)
            pattern += "(?:" + "|".join(map(re.escape, glob[index + 1 : close].split(","))) + ")"
            index = close
        else:
            pattern += re.escape(char)
        index += 1
    compiled = re.compile(pattern.lower())
    return {path for path in paths if compiled.fullmatch(path.lower())}


def manifest_selects(glob: str, paths: list[str]) -> set[str]:
    return {path for path in paths if pathlib.PurePosixPath(path).full_match(glob)}


def tracked_files() -> list[str]:
    env = {key: value for key, value in os.environ.items() if key not in GIT_LOCATORS}
    return subprocess.run(
        ["git", "-C", str(WORKTREE), "ls-files"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=RUN_TIMEOUT,
    ).stdout.splitlines()


def test_every_suite_glob_selects_the_tracked_files_lefthook_selects() -> None:
    assert REAL_MANIFEST.is_file(), f"{REAL_MANIFEST} is the job manifest the runner reads"
    jobs = tomllib.loads(REAL_MANIFEST.read_text(encoding="utf-8"))["job"]
    tracked = tracked_files()

    differing = {
        (job["name"], glob): (
            sorted(manifest_selects(glob, tracked) ^ lefthook_selects(glob, tracked))[:5]
        )
        for job in jobs
        if job["kind"] != "lint"
        for glob in job["sources"]
        if manifest_selects(glob, tracked) != lefthook_selects(glob, tracked)
    }
    assert differing == {}, (
        "these globs select different tracked files than the pre-push hook did, "
        f"first differing paths shown: {differing}"
    )


# The glob each pre-commit lint command in lefthook.yml carried before the
# hooks called the runner, keyed by the lint job that took over its check.
# Lefthook globs accept {a,b} alternatives, PurePath.full_match does not, so
# one hook glob became several `**/*.ext` sources on its job.
# https://docs.python.org/3/library/pathlib.html#pathlib-pattern-language
REPLACED_LINT_GLOBS = {
    "biome": "*.{js,jsx,mjs,cjs,ts,tsx,mts,cts,json,jsonc}",
    "markdownlint": "*.md",
    "ruff": "*.py",
    "yamllint": "*.{yaml,yml}",
    "taplo": "*.toml",
    "shellcheck": "*.{sh,bash,bats}",
}


def test_every_lint_job_selects_the_tracked_files_its_hook_glob_selected() -> None:
    assert REAL_MANIFEST.is_file(), f"{REAL_MANIFEST} is the job manifest the runner reads"
    jobs = {
        job["name"]: job
        for job in tomllib.loads(REAL_MANIFEST.read_text(encoding="utf-8"))["job"]
        if job["kind"] == "lint"
    }
    tracked = tracked_files()

    assert set(REPLACED_LINT_GLOBS) <= set(jobs), (
        f"lint jobs {sorted(set(REPLACED_LINT_GLOBS) - set(jobs))} are missing from the manifest"
    )
    differing = {}
    for name, hook_glob in REPLACED_LINT_GLOBS.items():
        selected = set().union(*(manifest_selects(glob, tracked) for glob in jobs[name]["sources"]))
        hooked = lefthook_selects(hook_glob, tracked)
        if selected != hooked:
            differing[name] = sorted(selected ^ hooked)[:5]
    assert differing == {}, (
        "these lint jobs check different tracked files than the commit hook did, "
        f"first differing paths shown: {differing}"
    )
