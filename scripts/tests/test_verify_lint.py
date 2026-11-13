#!/usr/bin/env python3
"""What `scripts/verify/cli.py lint` runs, under the real job manifest.

Each case copies `scripts/verify/jobs.toml` into a scratch tree laid out like
this repository (see `verify_fixtures.REAL_TREE`), so it checks the manifest's
lint jobs and the runner together: which command each in-scope file reaches,
with which arguments, and what the runner reports of the files a fixer changed. Every program is a stub, `bash` included, so
the rulesets check is observed as the argv bash receives.
"""

import pathlib
import subprocess

import pytest
from verify_fixtures import RealManifestSandbox, find_line, indented_block

RULESETS_CHECK = [
    "features/plugins/rulesets/hooks/with-python.sh",
    "features/plugins/rulesets/lib/rulesets/cli.py",
    "check",
    "--root",
    "rulesets",
]
PLUGIN_DIRS = {
    "features/plugins/warden",
    "features/plugins/planning",
    "features/plugins/rulesets",
    "features/mods/context-gauge",
}


@pytest.fixture
def sb(tmp_path) -> RealManifestSandbox:
    return RealManifestSandbox(tmp_path)


def normalized(sb, call: dict) -> list[str]:
    """A call's argv with every path inside the scratch tree written relative to its root, the root as `.`."""
    base = pathlib.Path(call["cwd"])
    out = []
    for arg in call["args"]:
        path = pathlib.Path(arg)
        resolved = (path if path.is_absolute() else base / path).resolve()
        if not arg.startswith("-") and resolved.exists() and resolved.is_relative_to(sb.repo):
            out.append(resolved.relative_to(sb.repo).as_posix() or ".")
        else:
            out.append(arg)
    return out


def lint(sb, *args: str, expect: int = 0) -> subprocess.CompletedProcess:
    return sb.run_expecting("lint", *args, expect=expect)


def progs(sb) -> set[str]:
    return {call["prog"] for call in sb.calls()}


class TestFileTakingJobsGetOnlyTheirInScopeFiles:
    def test_a_python_file_reaches_ruff_check_with_the_safe_fixer(self, sb) -> None:
        result = lint(sb, "app/main.py")

        assert progs(sb) == {"uv"}, [call["args"] for call in sb.calls()]
        call = sb.calls("uv")[0]
        assert call["args"][:5] == ["run", "--frozen", "ruff", "check", "--fix"], call["args"]
        assert "--unsafe-fixes" not in call["args"], "only safe fixes apply"
        assert sb.paths_in(call) == ["app/main.py"]
        find_line(result.stdout.splitlines(), r"PASS \S+ \(.*\)")

    def test_markdown_and_yaml_reach_markdownlint_and_yamllint(self, sb) -> None:
        lint(sb, "docs/guide.md", "conf/a.yaml")

        markdown = sb.calls("markdownlint-cli2")[0]
        assert "--fix" in markdown["args"], markdown["args"]
        assert sb.paths_in(markdown) == ["docs/guide.md"]
        yaml = sb.call_for("uv", "yamllint")
        assert yaml["args"][:4] == ["run", "--frozen", "yamllint", "--strict"], yaml["args"]
        assert sb.paths_in(yaml) == ["conf/a.yaml"]

    def test_typescript_and_json_reach_biome_check_with_safe_writes(self, sb) -> None:
        lint(sb, "web/app.ts", "data/x.json")

        args = sb.calls("biome")[0]["args"]
        assert args[0] == "check", args
        assert "--no-errors-on-unmatched" in args and "--files-ignore-unknown=true" in args, args
        assert "--write" in args, args
        assert "--unsafe" not in args, "only safe fixes apply"
        assert set(sb.paths_in(sb.calls("biome")[0])) == {"web/app.ts", "data/x.json"}
        assert sb.calls("tsc") == [], "web/app.ts is outside the context-gauge project"

    def test_toml_reaches_taplo_check(self, sb) -> None:
        lint(sb, "conf/b.toml")

        call = sb.calls("taplo")[0]
        assert call["args"][0] == "check", call["args"]
        assert sb.paths_in(call) == ["conf/b.toml"]

    def test_shell_reaches_shellcheck(self, sb) -> None:
        lint(sb, "bin/run.sh")

        assert sb.paths_in(sb.calls("shellcheck")[0]) == ["bin/run.sh"]

    def test_no_scope_lints_every_tracked_file_and_no_untracked_one(self, sb) -> None:
        sb.write("scratch.py", "UNTRACKED = 1\n")

        lint(sb)

        ruff = sb.call_for("uv", "ruff")
        assert set(sb.paths_in(ruff)) == sb.tracked(".py"), (
            "every tracked python file, the root-level one included"
        )
        markdown = sb.calls("markdownlint-cli2")[0]
        assert set(sb.paths_in(markdown)) == sb.tracked(".md")
        validated = {normalized(sb, call)[-1] for call in sb.calls("claude")}
        assert validated == PLUGIN_DIRS | {"."}, "every plugin dir plus the marketplace"
        assert len(sb.calls("tsc")) == 1
        assert [normalized(sb, call) for call in sb.calls("bash")] == [RULESETS_CHECK]


class TestProjectJobsRunWhenTheirScopeIsTouched:
    def test_a_context_gauge_ts_file_runs_tsc_over_the_whole_project(self, sb) -> None:
        lint(sb, "features/mods/context-gauge/src/gauge.ts")

        calls = sb.calls("tsc")
        assert len(calls) == 1
        assert normalized(sb, calls[0]) == ["-p", "features/mods/context-gauge"], calls[0]["args"]

    def test_a_context_gauge_json_file_runs_no_tsc(self, sb) -> None:
        lint(sb, "features/mods/context-gauge/.claude-plugin/plugin.json")

        assert sb.calls("tsc") == [], "tsc runs only when a ts or tsx file is in scope"

    def test_a_file_in_a_plugin_validates_that_plugin_alone(self, sb) -> None:
        lint(sb, "features/plugins/warden/hooks/h.sh")

        validations = [normalized(sb, call) for call in sb.calls("claude")]
        assert validations == [["plugin", "validate", "features/plugins/warden"]], validations
        assert sb.paths_in(sb.calls("shellcheck")[0]) == ["features/plugins/warden/hooks/h.sh"]

    def test_the_marketplace_file_validates_the_repository_root(self, sb) -> None:
        lint(sb, ".claude-plugin/marketplace.json")

        validations = [normalized(sb, call) for call in sb.calls("claude")]
        assert validations == [["plugin", "validate", "."]], validations

    def test_a_rulesets_pool_file_runs_the_rulesets_check(self, sb) -> None:
        lint(sb, "rulesets/config.yaml")

        assert [normalized(sb, call) for call in sb.calls("bash")] == [RULESETS_CHECK]

    def test_a_rulesets_plugin_file_runs_the_rulesets_check(self, sb) -> None:
        lint(sb, "features/plugins/rulesets/lib/rulesets/cli.py")

        assert [normalized(sb, call) for call in sb.calls("bash")] == [RULESETS_CHECK]
        validations = [normalized(sb, call) for call in sb.calls("claude")]
        assert validations == [["plugin", "validate", "features/plugins/rulesets"]], validations


def test_lang_sh_selects_only_shellcheck(sb) -> None:
    lint(sb, "--lang", "sh")

    assert progs(sb) == {"shellcheck"}, [(c["prog"], c["args"]) for c in sb.calls()]
    assert set(sb.paths_in(sb.calls("shellcheck")[0])) == sb.tracked(".sh")


FIXED_LINE = r"PASS ruff \(lint, fixed 2 files, [\d.]+s\)"


def ruff_rewrites(sb, *paths: str, stdout: str = "", exit_code: int = 0) -> None:
    sb.respond("uv", "ruff", stdout, exit_code, rewrite=list(paths))


class TestFixingJobs:
    def test_only_ruff_biome_and_markdownlint_carry_a_fixer(self, sb) -> None:
        lint(
            sb,
            "app/main.py",
            "docs/guide.md",
            "web/app.ts",
            "conf/a.yaml",
            "conf/b.toml",
            "bin/run.sh",
        )

        fixing = {"--fix", "--write", "--unsafe", "--unsafe-fixes"}
        for call in sb.calls():
            carried = fixing & set(call["args"])
            name = call["prog"] if call["prog"] != "uv" else call["args"][2]
            assert bool(carried) == (name in {"ruff", "biome", "markdownlint-cli2"}), call["args"]
            assert not carried & {"--unsafe", "--unsafe-fixes"}, call["args"]

    def test_a_fixed_file_is_listed_and_the_job_passes(self, sb) -> None:
        ruff_rewrites(sb, "app/main.py", "top.py")

        result = lint(sb, "app/main.py", "top.py")

        lines = result.stdout.splitlines()
        index, _ = find_line(lines, FIXED_LINE)
        assert indented_block(lines, index) == ["app/main.py", "top.py"], lines
        assert lines[-1].startswith("verify: 1 passed, 0 failed"), lines[-1]

    def test_a_fixer_that_changes_nothing_reports_nothing_fixed(self, sb) -> None:
        result = lint(sb, "app/main.py")

        assert "fixed" not in result.stdout, result.stdout

    def test_a_file_outside_the_handed_files_is_not_reported(self, sb) -> None:
        ruff_rewrites(sb, "app/main.py", "top.py")

        report = sb.run_json("lint", "app/main.py")

        assert report["suites"][0]["fixed"] == ["app/main.py"], report["suites"][0]

    def test_json_carries_the_fixed_list_of_every_job(self, sb) -> None:
        ruff_rewrites(sb, "app/main.py", "top.py")

        report = sb.run_json("lint", "app/main.py", "top.py", "conf/b.toml")

        fixed = {suite["name"]: suite["fixed"] for suite in report["suites"]}
        assert fixed == {"ruff": ["app/main.py", "top.py"], "taplo": []}, fixed

    def test_no_more_than_twenty_fixed_paths_print(self, sb) -> None:
        for number in range(25):
            sb.write(f"many/m{number:02}.py", "X = 1\n")
        paths = [f"many/m{number:02}.py" for number in range(25)]
        ruff_rewrites(sb, *paths)

        result = lint(sb, *paths)

        lines = result.stdout.splitlines()
        index, _ = find_line(lines, r"PASS ruff \(lint, fixed 25 files, [\d.]+s\)")
        assert indented_block(lines, index) == paths[:20], lines

    def test_findings_left_after_fixing_fail_the_job_and_still_list_the_fixed_files(
        self, sb
    ) -> None:
        ruff_rewrites(sb, "app/main.py", stdout="app/main.py:1:1: F821\n", exit_code=1)

        result = lint(sb, "app/main.py", "top.py", expect=1)

        lines = result.stdout.splitlines()
        index, _ = find_line(lines, r"FAIL ruff \(lint, fixed 1 file, [\d.]+s\) log=\S+")
        assert indented_block(lines, index) == ["app/main.py", "app/main.py:1:1: F821"], lines

    def test_under_prepush_a_fixed_file_fails_the_job_and_says_to_commit_it(self, sb) -> None:
        sb.git("checkout", "-q", "-b", "feature")
        sb.add_origin()
        sb.git("push", "-q", "origin", "main")
        sb.write("app/main.py", "MAIN = 2\n")
        sb.write("top.py", "TOP = 2\n")
        sb.commit("change python")
        ruff_rewrites(sb, "app/main.py", "top.py")

        result = lint(sb, "--prepush", expect=1)

        lines = result.stdout.splitlines()
        index, _ = find_line(lines, r"FAIL ruff \(lint, fixed 2 files, [\d.]+s\) log=\S+")
        block = indented_block(lines, index)
        assert block[:2] == ["app/main.py", "top.py"], block
        message = " ".join(block[2:])
        assert "pushed commits lack these fixes" in message and "commit" in message, block

    def test_under_prepush_a_job_that_fixed_nothing_still_passes(self, sb) -> None:
        sb.git("checkout", "-q", "-b", "feature")
        sb.add_origin()
        sb.git("push", "-q", "origin", "main")
        sb.write("app/main.py", "MAIN = 2\n")
        sb.commit("change python")

        result = lint(sb, "--prepush")

        find_line(result.stdout.splitlines(), r"PASS ruff \(lint, [\d.]+s\)")

    def test_list_shows_the_fixing_commands(self, sb) -> None:
        result = lint(sb, "app/main.py", "docs/guide.md", "web/app.ts", "--list")

        assert sb.calls() == [], "--list starts no runner"
        assert "ruff check --fix" in result.stdout, result.stdout
        assert "markdownlint-cli2 --fix" in result.stdout, result.stdout
        assert "biome check --write" in result.stdout, result.stdout


class TestLintVerdicts:
    def test_a_failing_check_prints_fail_and_exits_one(self, sb) -> None:
        sb.respond("shellcheck", "run.sh", "In bin/run.sh line 2:\nSC2086\n", exit_code=1)

        result = lint(sb, "bin/run.sh", expect=1)

        lines = result.stdout.splitlines()
        find_line(lines, r"FAIL \S+ \(.*\) log=\S+")
        assert lines[-1].startswith("verify: 0 passed, 1 failed"), lines[-1]

    def test_paths_no_lint_job_covers_exit_zero_and_say_so(self, sb) -> None:
        result = lint(sb, "Brewfile", "justfile")

        assert "no lint job covers the given files" in result.stdout + result.stderr
        assert sb.calls() == [], "a commit staging only such files has nothing to lint"

    def test_a_file_filter_matching_no_file_exits_five(self, sb) -> None:
        lint(sb, "--file", "zzz-no-such-file", expect=5)

    def test_a_language_filter_selecting_no_job_exits_five(self, sb) -> None:
        lint(sb, "--lang", "bats", "app/main.py", expect=5)

    @pytest.mark.parametrize(
        ("prog", "scope", "recipe"),
        [
            ("shellcheck", "bin/run.sh", "just tools"),
            ("taplo", "conf/b.toml", "just tools"),
            ("biome", "web/app.ts", "just setup"),
            ("markdownlint-cli2", "docs/guide.md", "just setup"),
            ("tsc", "features/mods/context-gauge/src/gauge.ts", "just setup"),
        ],
    )
    def test_a_missing_program_exits_three_naming_the_recipe_that_provides_it(
        self, sb, prog, scope, recipe
    ) -> None:
        sb.remove_stub(prog)

        result = lint(sb, scope, expect=3)

        output = result.stdout + result.stderr
        assert prog in output, "the message names the missing program"
        assert recipe in output, (
            f"PATH programs come from just tools, node_modules/.bin from just setup: {output}"
        )
