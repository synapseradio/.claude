#!/usr/bin/env -S uv run --frozen
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
    @pytest.mark.parametrize(
        ("path", "program", "needle", "fix_flag"),
        [
            ("app/main.py", "uv", "ruff", "--fix"),
            ("docs/guide.md", "uv", "rumdl", "--fix"),
            ("web/app.ts", "biome", None, "--write"),
            ("data/x.json", "biome", None, "--write"),
            ("conf/b.toml", "taplo", None, None),
            ("bin/run.sh", "uv", "shellcheck_fix.py", None),
        ],
        ids=["python", "markdown", "typescript", "json", "toml", "shell"],
    )
    def test_each_file_type_reaches_its_linter_and_that_linter_alone(
        self, sb, path, program, needle, fix_flag
    ) -> None:
        result = lint(sb, path)

        call = sb.call_for(program, needle) if needle else sb.calls(program)[0]
        assert sb.paths_in(call) == [path], "the linter gets the file it was handed"
        if fix_flag:
            assert fix_flag in call["args"], "the linter applies its safe fixes"
        assert len(sb.calls()) == 1, "no other program runs for this file"
        find_line(result.stdout.splitlines(), r"PASS \S+ \(.*\)")

    def test_yaml_reaches_no_lint_job(self, sb) -> None:
        result = lint(sb, "conf/a.yaml")

        assert "no lint job covers the given files" in result.stdout + result.stderr
        assert sb.calls() == [], "yamlfmt lays YAML out; no linter checks it"

    def test_typescript_outside_the_context_gauge_project_runs_no_tsc(self, sb) -> None:
        lint(sb, "web/app.ts")

        assert sb.calls("tsc") == [], "web/app.ts is outside the context-gauge project"

    def test_no_scope_lints_every_tracked_file_and_no_untracked_one(self, sb) -> None:
        sb.write("scratch.py", "UNTRACKED = 1\n")

        lint(sb)

        ruff = sb.call_for("uv", "ruff")
        assert set(sb.paths_in(ruff)) == sb.tracked(".py"), (
            "every tracked python file, the root-level one included"
        )
        markdown = sb.call_for("uv", "rumdl")
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
        assert sb.paths_in(sb.call_for("uv", "shellcheck_fix.py")) == [
            "features/plugins/warden/hooks/h.sh"
        ]

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


def test_lang_sh_selects_only_the_shellcheck_fixer(sb) -> None:
    lint(sb, "--lang", "sh")

    assert progs(sb) == {"uv"}, [(c["prog"], c["args"]) for c in sb.calls()]
    assert set(sb.paths_in(sb.call_for("uv", "shellcheck_fix.py"))) == sb.tracked(".sh")


FIXED_LINE = r"PASS ruff \(lint, fixed 2 files, [\d.]+s\)"


def ruff_rewrites(sb, *paths: str, stdout: str = "", exit_code: int = 0) -> None:
    sb.respond("uv", "ruff", stdout, exit_code, rewrite=list(paths))


class TestFixingJobs:
    def test_only_ruff_biome_and_rumdl_carry_a_fix_flag(self, sb) -> None:
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
            assert bool(carried) == (name in {"ruff", "biome", "rumdl"}), call["args"]
            assert not carried & {"--unsafe", "--unsafe-fixes"}, call["args"]

    def test_a_fixed_file_is_listed_and_the_job_passes(self, sb) -> None:
        ruff_rewrites(sb, "app/main.py", "top.py")

        result = lint(sb, "app/main.py", "top.py")

        lines = result.stdout.splitlines()
        index, _ = find_line(lines, FIXED_LINE)
        assert indented_block(lines, index) == ["app/main.py", "top.py"], lines
        assert lines[-1].startswith("verify: 1 passed, 0 failed"), lines[-1]

    def test_only_the_handed_files_a_fixer_changed_are_reported_per_job(self, sb) -> None:
        ruff_rewrites(sb, "app/main.py", "top.py")

        report = sb.run_json("lint", "app/main.py", "conf/b.toml")

        fixed = {suite["name"]: suite["fixed"] for suite in report["suites"]}
        assert fixed == {"ruff": ["app/main.py"], "taplo": []}, (
            "top.py was not handed to the fixer, so it is not this run's fix to report"
        )

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
        assert "rumdl check --fix" in result.stdout, result.stdout
        assert "biome check --write" in result.stdout, result.stdout


class TestLintVerdicts:
    def test_a_failing_check_prints_fail_and_exits_one(self, sb) -> None:
        sb.respond("uv", "shellcheck_fix.py", "In bin/run.sh line 2:\nSC2086\n", exit_code=1)

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
            ("taplo", "conf/b.toml", "just tools"),
            ("biome", "web/app.ts", "just setup"),
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
