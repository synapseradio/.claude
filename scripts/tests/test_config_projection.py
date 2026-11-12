#!/usr/bin/env python3
"""Tests for the config-projection jobs under `scripts/agent-configs/`.

Run with `uv run --frozen pytest -p no:cacheprovider scripts/tests/test_config_projection.py`.

Every test builds its own tree under a tmp_path and passes a Targets naming it, so no test reads
or writes this checkout's configuration or the real pi and opencode directories.
"""

import dataclasses
import importlib.util
import json
import pathlib
import sys
import types

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT / "scripts" / "agent-configs"))
import projection  # noqa: E402  (path must be set before this import)


def _load(name: str, filename: str) -> types.ModuleType:
    path = REPO_ROOT / "scripts" / "agent-configs" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pi = _load("config_projection_pi", "translate-for-pi.py")
opencode = _load("config_projection_opencode", "translate-for-opencode.py")
key_owner = _load("config_projection_key", "own-opencode-key.py")

PREAMBLE = "# Preamble\n\nPlay."
AGENT_SOURCE = (
    "---\n"
    "name: scout\n"
    "description: scouts the codebase.\n"
    "model: haiku\n"
    "tools: Read, Glob, Agent\n"
    "---\n\n"
    "Scout body.\n"
)
UNTOUCHED_CONFIG = json.dumps({"instructions": ["untouched"]}, indent=2) + "\n"


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _rule(stem: str, body: str) -> str:
    return f"<!-- rule: {stem} -->\n\n## {stem}\n\n{body}\n"


def _tree(
    tmp_path: pathlib.Path, rules: dict[str, str], *, agent: str = AGENT_SOURCE
) -> projection.Targets:
    """A checkout-shaped tree whose pool holds `rules`, keyed by file name."""
    claude_home = tmp_path / "claude"
    _write(claude_home / "CLAUDE.md", f"{PREAMBLE}\n")
    for name, text in rules.items():
        _write(claude_home / "rulesets" / "rules" / name, text)
    _write(claude_home / "agents" / "scout.md", agent)
    _write(claude_home / "plugins" / "installed_plugins.json", json.dumps({"plugins": {}}))
    _write(claude_home / "settings.json", json.dumps({"enabledPlugins": {}}))
    return projection.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi",
        opencode_home=tmp_path / "opencode",
        rulesets_dir=claude_home / "rulesets",
    )


def _run_every_job(targets: projection.Targets) -> None:
    for job in (pi, opencode, key_owner):
        assert job.main([], targets=targets) == 0


def _snapshot(*roots: pathlib.Path) -> dict[pathlib.Path, bytes]:
    return {
        path: path.read_bytes()
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _instructions(targets: projection.Targets) -> list[str]:
    return json.loads(targets.opencode_config.read_text(encoding="utf-8"))["instructions"]


class TestEachProjectionJobRunsIndependently:
    def test_the_pi_translation_alone_writes_pi_outputs_and_leaves_opencode_alone(
        self, tmp_path
    ) -> None:
        targets = _tree(tmp_path, {"core-rules.md": _rule("core-rules", "Core holds.")})
        opencode_agents = _write(targets.opencode_home / "AGENTS.md", "opencode context\n")
        _write(targets.opencode_config, UNTOUCHED_CONFIG)

        assert pi.main([], targets=targets) == 0

        assert (targets.pi_home / "AGENTS.md").is_file(), "pi's context file must be written"
        assert (targets.pi_home / "agents" / "scout.md").is_file(), (
            "pi's agent file must be written"
        )
        assert opencode_agents.read_text(encoding="utf-8") == "opencode context\n", (
            "pi alone must leave opencode's outputs untouched"
        )
        assert not (targets.opencode_home / "agents").exists(), (
            "pi alone must write no opencode agent file"
        )
        assert targets.opencode_config.read_text(encoding="utf-8") == UNTOUCHED_CONFIG, (
            "pi alone must leave the opencode key untouched"
        )

    def test_a_failing_opencode_translation_leaves_pi_outputs_and_the_key_alone(
        self, tmp_path
    ) -> None:
        broken_agent = AGENT_SOURCE.replace("model: haiku", "model: an-unmapped-model")
        targets = _tree(
            tmp_path, {"core-rules.md": _rule("core-rules", "Core holds.")}, agent=broken_agent
        )
        assert pi.main([], targets=targets) == 0
        assert key_owner.main([], targets=targets) == 0
        pi_before = _snapshot(targets.pi_home)
        key_before = targets.opencode_config.read_text(encoding="utf-8")

        with pytest.raises(KeyError):
            opencode.main([], targets=targets)

        assert _snapshot(targets.pi_home) == pi_before, (
            "the opencode job's failure must leave pi's outputs untouched"
        )
        assert targets.opencode_config.read_text(encoding="utf-8") == key_before, (
            "the opencode job's failure must leave the opencode key untouched"
        )


class TestThePoolIsTheOneRulesSourceEveryJobReads:
    def test_a_new_pool_rule_reaches_the_pi_context_and_the_opencode_key(self, tmp_path) -> None:
        targets = _tree(tmp_path, {"core-rules.md": _rule("core-rules", "Core holds.")})
        sorting = _write(
            targets.rulesets_dir / "rules" / "sorting.md", _rule("sorting", "Sorting holds.")
        )

        assert pi.main([], targets=targets) == 0
        assert key_owner.main([], targets=targets) == 0

        assert "Sorting holds." in (targets.pi_home / "AGENTS.md").read_text(encoding="utf-8"), (
            "pi's context file must hold the default-form text of the added rule"
        )
        assert str(sorting) in _instructions(targets), (
            "the opencode key must list the file that holds the default form of the added rule"
        )

    def test_moving_the_source_directory_changes_no_job_output(self, tmp_path) -> None:
        rules = {"alpha.md": _rule("alpha", "Alpha holds.")}
        before = _tree(tmp_path / "before", rules)
        after = _tree(tmp_path / "after", rules)
        moved = dataclasses.replace(
            before,
            pi_home=after.pi_home,
            opencode_home=after.opencode_home,
            rulesets_dir=after.rulesets_dir,
        )
        _run_every_job(before)
        _run_every_job(moved)

        assert (after.pi_home / "AGENTS.md").read_bytes() == (
            before.pi_home / "AGENTS.md"
        ).read_bytes(), "pi's context file must not change when the pool moves"
        assert (after.opencode_home / "agents" / "scout.md").read_bytes() == (
            before.opencode_home / "agents" / "scout.md"
        ).read_bytes(), "opencode's agent file must not change when the pool moves"
        assert [pathlib.Path(entry).name for entry in _instructions(after)] == [
            pathlib.Path(entry).name for entry in _instructions(before)
        ], "the opencode key must list the same rule files when the pool moves"

    def test_a_rule_file_outside_the_pool_is_read_by_no_job(self, tmp_path) -> None:
        targets = _tree(tmp_path, {"alpha.md": _rule("alpha", "Alpha holds.")})
        stray = targets.rulesets_dir / "stray.md"
        stray.write_bytes(b"\xff\xfe a file no job can decode, so a job that read it would fail")

        _run_every_job(targets)

        assert "stray" not in (targets.pi_home / "AGENTS.md").read_text(encoding="utf-8"), (
            "pi's context file must omit the file outside the pool"
        )
        assert str(stray) not in _instructions(targets), (
            "the opencode key must not list the file outside the pool"
        )

    def test_a_variant_file_in_the_pool_is_read_by_no_job(self, tmp_path) -> None:
        targets = _tree(
            tmp_path,
            {
                "writing-prose.md": _rule("writing-prose", "Default prose holds."),
                "writing-prose@haiku.md": _rule("writing-prose", "Haiku prose holds."),
            },
        )

        _run_every_job(targets)

        outputs = _snapshot(targets.pi_home, targets.opencode_home)
        assert not any(b"Haiku prose holds." in text for text in outputs.values()), (
            "no output may hold the text of the variant"
        )
        assert "Default prose holds." in (targets.pi_home / "AGENTS.md").read_text(
            encoding="utf-8"
        ), "pi's context file must hold the default form"
        assert [pathlib.Path(entry).name for entry in _instructions(targets)] == [
            "writing-prose.md"
        ], "the opencode key must list the default form alone"


class TestACheckModeReportsDrift:
    def test_every_job_checks_clean_and_writes_nothing_when_outputs_match(self, tmp_path) -> None:
        targets = _tree(tmp_path, {"alpha.md": _rule("alpha", "Alpha holds.")})
        _run_every_job(targets)
        before = _snapshot(tmp_path)

        for job in (pi, opencode, key_owner):
            assert job.main(["--check"], targets=targets) == 0, (
                "a check of outputs that match what the job writes must exit zero"
            )

        assert _snapshot(tmp_path) == before, "a check mode must write no file"

    def test_the_pi_check_names_its_output_after_a_pool_rule_changes(
        self, tmp_path, capsys
    ) -> None:
        targets = _tree(tmp_path, {"alpha.md": _rule("alpha", "Alpha holds.")})
        assert pi.main([], targets=targets) == 0
        _write(targets.rulesets_dir / "rules" / "alpha.md", _rule("alpha", "Alpha, edited."))
        before = _snapshot(tmp_path)
        capsys.readouterr()

        status = pi.main(["--check"], targets=targets)

        assert status != 0, "a pool rule changed since the pi job ran, so its check must fail"
        assert str(targets.pi_home / "AGENTS.md") in capsys.readouterr().out, (
            "the check must name pi's context file"
        )
        assert _snapshot(tmp_path) == before, "the check must change nothing on disk"
