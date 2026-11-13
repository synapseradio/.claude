#!/usr/bin/env python3
"""What `scripts/verify/cli.py lint` runs, under the real job manifest.

Each case copies `scripts/verify/jobs.toml` into a scratch tree laid out like
this repository (see `verify_fixtures.REAL_TREE`), so it checks the manifest's
lint jobs and the runner together: which check-only command each in-scope file
reaches, with which arguments. Every program is a stub, `bash` included, so
the rulesets check is observed as the argv bash receives.
"""

import pathlib
import subprocess

import pytest
from verify_fixtures import RealManifestSandbox, find_line

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
    result = sb.run("lint", *args)
    assert result.returncode == expect, (
        f"lint {' '.join(args)} exited {result.returncode}, wanted {expect}: {result.stderr}"
    )
    return result


def progs(sb) -> set[str]:
    return {call["prog"] for call in sb.calls()}


class TestFileTakingJobsGetOnlyTheirInScopeFiles:
    def test_a_python_file_reaches_ruff_check(self, sb) -> None:
        result = lint(sb, "app/main.py")

        assert progs(sb) == {"uv"}, [call["args"] for call in sb.calls()]
        call = sb.calls("uv")[0]
        assert call["args"][:4] == ["run", "--frozen", "ruff", "check"], call["args"]
        assert "--fix" not in call["args"], "lint never writes"
        assert sb.paths_in(call) == ["app/main.py"]
        find_line(result.stdout.splitlines(), r"PASS \S+ \(.*\)")

    def test_markdown_and_yaml_reach_markdownlint_and_yamllint(self, sb) -> None:
        lint(sb, "docs/guide.md", "conf/a.yaml")

        markdown = sb.calls("markdownlint-cli2")[0]
        assert "--fix" not in markdown["args"], "lint never writes"
        assert sb.paths_in(markdown) == ["docs/guide.md"]
        yaml = sb.call_for("uv", "yamllint")
        assert yaml["args"][:4] == ["run", "--frozen", "yamllint", "--strict"], yaml["args"]
        assert sb.paths_in(yaml) == ["conf/a.yaml"]

    def test_typescript_and_json_reach_biome_check_without_write(self, sb) -> None:
        lint(sb, "web/app.ts", "data/x.json")

        args = sb.calls("biome")[0]["args"]
        assert args[0] == "check", args
        assert "--no-errors-on-unmatched" in args and "--files-ignore-unknown=true" in args, args
        assert "--write" not in args, "lint never writes"
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
