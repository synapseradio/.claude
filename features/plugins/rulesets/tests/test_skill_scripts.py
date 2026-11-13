"""The rulesets skill's scripts answer a rule author as their `main` functions answer, called in-process.

A rule author runs each script through `hooks/with-python.sh`, which `test_launcher.py` covers; the
cases here call the script's `main` with the arguments the author gives it.
"""

import importlib.util
import os
import pathlib
import subprocess
from collections.abc import Callable
from unittest import mock

from delivery_world import PLUGIN_ROOT, World, call_main, run_cli, scratch_environment

SCRIPTS = PLUGIN_ROOT / "skills" / "rulesets" / "scripts"


def script_main(name: str) -> Callable[[list[str]], int]:
    """The `main` of one skill script, loaded from its file once."""
    spec = importlib.util.spec_from_file_location(
        f"skill_{name.removesuffix('.py')}", SCRIPTS / name
    )
    assert spec is not None and spec.loader is not None, f"{name} loads as a module"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


MAINS = {
    name: script_main(name) for name in ("gate.py", "impact.py", "scaffold.py", "session_report.py")
}

CONFIG = """\
models: opus haiku
flags: strict
defaults: voice brevity
"""

STRICT_BLOCK = """\
flag strict:
  include: voice@terse
"""


def run(world: World, script: str, *arguments: object) -> subprocess.CompletedProcess[str]:
    """One skill script's `main`, under the world's configuration directory.

    The scripts find the configuration directory in `os.environ`, so the call sets the world's
    there and restores the process's own when it returns.
    """
    with mock.patch.dict(os.environ, scratch_environment(world.config.parent)):
        return call_main(MAINS[script], [str(argument) for argument in arguments])


def render(world: World, root: pathlib.Path) -> None:
    done = run_cli(["render", "--root", str(root)], scratch_environment(world.config.parent))
    assert done.returncode == 0, done.stderr


def pool(world: World) -> None:
    world.rule("voice")
    world.rule("voice@terse", "terse text of voice\n")
    world.rule("brevity")
    world.write_config(CONFIG)


def files_under(root: pathlib.Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class TestGate:
    def test_gate_stops_at_check_when_a_variant_lacks_its_default_form(self, tmp_path) -> None:
        world = World(tmp_path)
        world.rule("voice@terse", "terse text of voice\n")
        world.write_config("defaults: all.*\n")

        done = run(world, "gate.py", "--root", world.rulesets)

        assert done.returncode == 1, done.stdout + done.stderr
        assert "gate: stopped at check" in done.stdout
        assert "voice" in done.stdout
        assert "render --check" not in done.stdout

    def test_gate_passes_a_clean_directory(self, tmp_path) -> None:
        world = World(tmp_path)
        pool(world)
        render(world, world.rulesets)

        done = run(world, "gate.py", "--root", world.rulesets)

        assert done.returncode == 0, done.stdout + done.stderr

    def test_gate_names_render_check_when_the_render_is_stale(self, tmp_path) -> None:
        world = World(tmp_path)
        pool(world)
        render(world, world.rulesets)
        world.rule("brevity", "edited text of brevity\n")

        done = run(world, "gate.py", "--root", world.rulesets)

        assert done.returncode == 1, done.stdout + done.stderr
        assert "gate: stopped at render --check" in done.stdout


class TestImpact:
    def snapshot(self, world: World, out: pathlib.Path) -> None:
        done = run(world, "impact.py", "snapshot", "--root", world.rulesets, "--out", out)
        assert done.returncode == 0, done.stdout + done.stderr

    def test_a_new_block_shows_only_in_the_contexts_it_reaches(self, tmp_path) -> None:
        world = World(tmp_path)
        pool(world)
        self.snapshot(world, tmp_path / "before")
        world.write_config(CONFIG + STRICT_BLOCK)
        self.snapshot(world, tmp_path / "after")

        done = run(world, "impact.py", "diff", tmp_path / "before", tmp_path / "after")

        assert done.returncode == 0, done.stdout + done.stderr
        headers = [line for line in done.stdout.splitlines() if not line.startswith(" ")]
        assert headers, "the diff names the contexts the block reaches"
        assert all("flag=strict" in header for header in headers), headers
        assert "voice" in done.stdout
        assert "brevity" not in done.stdout

    def test_an_edit_that_changes_nothing_leaves_the_diff_empty(self, tmp_path) -> None:
        world = World(tmp_path)
        pool(world)
        self.snapshot(world, tmp_path / "before")
        world.write_config("# reordered, same meaning\n" + CONFIG)
        self.snapshot(world, tmp_path / "after")

        done = run(world, "impact.py", "diff", tmp_path / "before", tmp_path / "after")

        assert done.returncode == 0, done.stdout + done.stderr
        assert done.stdout == ""


class TestSessionReport:
    def test_a_session_that_matches_the_pool_shows_empty_check_sections(self, tmp_path) -> None:
        world = World(tmp_path)
        pool(world)
        world.start_session()

        done = run(world, "session_report.py", "show", "--session", "s1")

        assert done.returncode == 0, done.stdout + done.stderr
        sections = done.stdout.split("\n\n")
        assert sections[0].splitlines()[0] == "deliveries"
        assert len(sections[0].splitlines()) == 2, "one delivery line under the heading"
        assert sections[1].strip() == "delivery-check"
        assert sections[2].strip() == "load-check"

    def test_comparing_sessions_with_and_without_a_flag_names_the_rule_it_varies(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        pool(world)
        world.write_config(CONFIG + STRICT_BLOCK)
        world.environment["RULESETS_FLAGS"] = "strict"
        world.start_session(session_id="with-strict")
        del world.environment["RULESETS_FLAGS"]
        world.start_session(session_id="plain")

        done = run(world, "session_report.py", "compare", "with-strict", "plain")

        assert done.returncode == 0, done.stdout + done.stderr
        assert "flags with-strict: strict" in done.stdout
        assert "flags plain: -" in done.stdout
        assert "  voice  with-strict: terse  plain: default" in done.stdout
        assert "brevity" not in done.stdout


class TestScaffold:
    def test_a_scaffolded_directory_passes_the_gate(self, tmp_path) -> None:
        world = World(tmp_path)
        fresh = tmp_path / "fresh"

        made = run(world, "scaffold.py", "--root", fresh)
        gated = run(world, "gate.py", "--root", fresh)

        assert made.returncode == 0, made.stdout + made.stderr
        assert (fresh / "rules" / "example.md").is_file()
        assert gated.returncode == 0, gated.stdout + gated.stderr

    def test_a_scaffolded_directory_holds_a_config_yaml_check_clears_and_no_manifest(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        fresh = tmp_path / "fresh"

        made = run(world, "scaffold.py", "--root", fresh)
        checked = run_cli(["check", "--root", str(fresh)], scratch_environment(world.config.parent))

        assert made.returncode == 0, made.stdout + made.stderr
        assert (fresh / "config.yaml").is_file()
        assert not (fresh / "manifest.yaml").exists()
        assert checked.returncode == 0, checked.stdout + checked.stderr
        assert ": error " not in checked.stdout

    def test_scaffolding_fills_the_empty_directory_a_first_session_left(self, tmp_path) -> None:
        world = World(tmp_path)
        world.write_config("models:\nflags:\ndefaults:\n")

        made = run(world, "scaffold.py", "--root", world.rulesets)

        assert made.returncode == 0, made.stdout + made.stderr
        assert (world.rulesets / "rules" / "example.md").is_file()

    def test_scaffolding_refuses_a_directory_that_holds_a_file_and_leaves_it_unchanged(
        self, tmp_path
    ) -> None:
        world = World(tmp_path)
        taken = tmp_path / "taken"
        taken.mkdir()
        (taken / "notes.txt").write_text("mine\n", encoding="utf-8")
        before = files_under(taken)

        made = run(world, "scaffold.py", "--root", taken)

        assert made.returncode == 2, made.stdout + made.stderr
        assert f"scaffold.py: {taken} holds files" in made.stderr
        assert files_under(taken) == before
