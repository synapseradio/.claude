#!/usr/bin/env -S uv run --frozen
"""Which suites and test files `scripts/verify/cli.py test` selects for each scope.

A wrong selection hands an agent a pass for code no test ran, so each rule
under Scope grammar, `--diff`, `--prepush`, Changed-file to suite, and Empty
selection in the verification plan has a case here. Every case runs the CLI
against a scratch repository whose own `scripts/verify/jobs.toml` holds four
suites and one lint job (see `verify_fixtures.MANIFEST`), with `uv`, `bats`,
and `claude` stubbed, and reads the selection from the JSON report and the
argv each stub received.
"""

import pytest
from verify_fixtures import (
    PYTEST_NONE_SELECTED,
    Sandbox,
    pair,
    ran,
)


@pytest.fixture
def sb(tmp_path) -> Sandbox:
    return Sandbox(tmp_path)


class TestDiffSelectsFromEverythingChangedSinceTheBase:
    @pytest.mark.parametrize(
        "change",
        [
            pytest.param(
                lambda sb: sb.write("pkg_a/src/a.py", "VALUE = 10\n"),
                id="an unstaged edit",
            ),
            pytest.param(
                lambda sb: (
                    sb.write("pkg_a/src/a.py", "VALUE = 10\n"),
                    sb.git("add", "pkg_a/src/a.py"),
                ),
                id="a staged edit",
            ),
            pytest.param(
                lambda sb: (
                    sb.write("pkg_a/src/a.py", "VALUE = 10\n"),
                    sb.commit("change a"),
                ),
                id="a commit since the merge-base with main",
            ),
            pytest.param(
                lambda sb: sb.write("pkg_a/src/new.py", "NEW = 1\n"),
                id="an untracked file",
            ),
        ],
    )
    def test_every_kind_of_change_since_the_base_selects_the_suite_owning_the_file(
        self, sb, change
    ) -> None:
        change(sb)

        report = sb.run_json("test", "--diff")

        assert ran(report) == {"py-a"}, "the diff holds everything changed since the base"
        assert sb.paths_in(sb.call_for("uv", "pkg_a")) == ["pkg_a/tests"], (
            "a changed source file runs its whole suite"
        )

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
    @pytest.mark.parametrize(
        ("path", "suite", "program", "needle"),
        [
            ("pkg_a/tests/test_a2.py", "py-a", "uv", "pkg_a"),
            ("shell/tests/one.bats", "sh-bats", "bats", None),
        ],
        ids=["a pytest test file", "a bats test file"],
    )
    def test_a_test_file_runs_alone(self, sb, path, suite, program, needle) -> None:
        report = sb.run_json("test", path)

        call = sb.call_for(program, needle) if needle else sb.calls(program)[0]
        assert ran(report) == {suite}
        assert sb.paths_in(call) == [path]

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
    @pytest.mark.parametrize(
        ("flags", "suites"),
        [
            (["--lang", "bats"], {"sh-bats"}),
            (["--lang", "py,ts"], {"py-a", "py-b", "mod-gauge"}),
            (["--lang", "py", "--lang", "ts"], {"py-a", "py-b", "mod-gauge"}),
        ],
        ids=["one language", "a comma list", "a repeated flag"],
    )
    def test_languages_select_their_test_suites(self, sb, flags, suites) -> None:
        report = sb.run_json("test", *flags)

        assert ran(report) == suites, "a lint job sharing a language is no test suite"


class TestFileSelectsTestFilesByPath:
    @pytest.mark.parametrize(
        ("substring", "suite", "program", "needle", "expected"),
        [
            ("test_a2", "py-a", "uv", "pkg_a", "pkg_a/tests/test_a2.py"),
            ("one.bats", "sh-bats", "bats", None, "shell/tests/one.bats"),
        ],
        ids=["a pytest file", "a bats file"],
    )
    def test_a_substring_runs_the_test_files_whose_path_holds_it(
        self, sb, substring, suite, program, needle, expected
    ) -> None:
        report = sb.run_json("test", "--file", substring)

        call = sb.call_for(program, needle) if needle else sb.calls(program)[0]
        assert ran(report) == {suite}
        assert sb.paths_in(call) == [expected]


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
