#!/usr/bin/env python3
"""Tests for the load audit under `scripts/hooks/rulesets-audit.py`.

Run with `python3.14 -m pytest scripts/hooks/test_rulesets_audit.py`.

Every test points the audit at a temporary state directory through
`RULESETS_STATE_DIR`, so no test reads or writes a real session's log.
"""

import json
import pathlib
import subprocess
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rulesets import audit, resolve

HOOK = pathlib.Path(__file__).resolve().parent / "rulesets-audit.py"


def run_hook(payload, state):
    """The hook as the harness runs it, with its own state directory."""

    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"RULESETS_STATE_DIR": str(state), "PATH": "/usr/bin:/bin"},
    )


@pytest.fixture
def state(tmp_path):
    return tmp_path / "state"


class TestRecordPartitioning:
    def test_writes_a_session_own_records_to_the_session_file(self, state):
        audit.append_record({"kind": "load"}, session_id="abc", state=state)

        assert (audit.session_dir("abc", state) / "session.jsonl").is_file()

    def test_writes_a_delegate_records_to_a_file_keyed_by_the_delegate(self, state):
        audit.append_record({"kind": "load"}, session_id="abc", agent_id="agent1", state=state)

        assert (audit.session_dir("abc", state) / "agent1.jsonl").is_file()

    def test_keeps_two_delegates_under_one_session_in_separate_files(self, state):
        audit.append_record({"n": 1}, session_id="abc", agent_id="agent1", state=state)
        audit.append_record({"n": 2}, session_id="abc", agent_id="agent2", state=state)
        audit.append_record({"n": 3}, session_id="abc", state=state)

        directory = audit.session_dir("abc", state)
        files = sorted(path.name for path in directory.glob("*.jsonl"))
        assert files == ["agent1.jsonl", "agent2.jsonl", "session.jsonl"]
        for path in directory.glob("*.jsonl"):
            assert len(path.read_text(encoding="utf-8").splitlines()) == 1

    def test_reads_a_session_records_together_with_its_delegates(self, state):
        audit.append_record({"n": 1}, session_id="abc", agent_id="agent1", state=state)
        audit.append_record({"n": 2}, session_id="abc", state=state)

        assert sorted(r["n"] for r in audit.read_records("abc", state)) == [1, 2]

    def test_reads_no_other_session_records(self, state):
        audit.append_record({"n": 1}, session_id="abc", state=state)
        audit.append_record({"n": 2}, session_id="other", state=state)

        assert [r["n"] for r in audit.read_records("abc", state)] == [1]

    def test_sanitizes_a_session_identifier_before_it_becomes_a_filename(self, state):
        audit.append_record({"n": 1}, session_id="../escape/../x", state=state)

        assert audit.read_records("../escape/../x", state) == [{"n": 1}]
        assert (state / "audit").is_dir()
        assert not (state / "escape").exists()


class TestLoadRecords:
    def test_carries_the_path_the_reason_and_the_session(self, state):
        payload = {
            "file_path": "/Users/x/.claude/rules/core-rules.md",
            "load_reason": "session_start",
            "session_id": "abc",
        }

        run_hook(payload, state)

        records = audit.read_records("abc", state)
        assert records == [
            {
                "kind": "load",
                "file_path": "/Users/x/.claude/rules/core-rules.md",
                "load_reason": "session_start",
                "session_id": "abc",
            }
        ]

    def test_carries_the_trigger_path_on_a_glob_match(self, state):
        payload = {
            "file_path": "/Users/x/.claude/rules/testing.md",
            "load_reason": "path_glob_match",
            "session_id": "abc",
            "trigger_file_path": "/repo/scripts/tests/test_thing.py",
        }

        run_hook(payload, state)

        record = audit.read_records("abc", state)[0]
        assert record["trigger_file_path"] == "/repo/scripts/tests/test_thing.py"

    def test_carries_the_parent_path_on_an_include(self, state):
        payload = {
            "file_path": "/repo/nested/CLAUDE.md",
            "load_reason": "include",
            "session_id": "abc",
            "parent_file_path": "/repo/CLAUDE.md",
        }

        run_hook(payload, state)

        assert audit.read_records("abc", state)[0]["parent_file_path"] == "/repo/CLAUDE.md"

    def test_omits_an_optional_field_the_payload_does_not_supply(self, state):
        run_hook({"file_path": "/a.md", "load_reason": "session_start", "session_id": "abc"}, state)

        assert "trigger_file_path" not in audit.read_records("abc", state)[0]

    def test_keeps_two_delegates_records_apart_under_one_session(self, state):
        base = {"file_path": "/a.md", "load_reason": "session_start", "session_id": "abc"}
        run_hook(base | {"agent_id": "agent1"}, state)
        run_hook(base | {"agent_id": "agent2"}, state)
        run_hook(base, state)

        directory = audit.session_dir("abc", state)
        assert sorted(p.name for p in directory.glob("*.jsonl")) == [
            "agent1.jsonl",
            "agent2.jsonl",
            "session.jsonl",
        ]
        assert len(audit.read_records("abc", state)) == 3


class TestFailureLeavesTheSessionAlone:
    def test_exits_zero_and_prints_nothing_when_the_state_is_unwritable(self, state):
        state.mkdir(parents=True)
        state.chmod(0o500)
        try:
            result = run_hook(
                {"file_path": "/a.md", "load_reason": "session_start", "session_id": "abc"},
                state,
            )
        finally:
            state.chmod(0o700)

        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""

    def test_answers_false_when_the_write_cannot_land(self, state):
        state.mkdir(parents=True)
        state.chmod(0o500)
        try:
            landed = audit.append_record({"n": 1}, session_id="abc", state=state)
        finally:
            state.chmod(0o700)

        assert landed is False

    def test_exits_zero_on_a_payload_that_does_not_parse(self, state):
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input="{not json",
            capture_output=True,
            text=True,
            env={"RULESETS_STATE_DIR": str(state), "PATH": "/usr/bin:/bin"},
        )

        assert result.returncode == 0
        assert result.stdout == ""


class TestPartialLines:
    def test_skips_a_truncated_final_line_and_yields_the_rest(self, state):
        audit.append_record({"n": 1}, session_id="abc", state=state)
        path = audit.record_path("abc", state=state)
        with path.open("a", encoding="utf-8") as handle:
            handle.write('{"n": 2, "trunc')

        assert audit.read_records("abc", state) == [{"n": 1}]

    def test_yields_records_after_a_partial_line_in_the_middle(self, state):
        path = audit.record_path("abc", state=state)
        path.parent.mkdir(parents=True)
        path.write_text('{"n": 1}\n{"n": 2, "trunc\n{"n": 3}\n', encoding="utf-8")

        assert [r["n"] for r in audit.read_records("abc", state)] == [1, 3]

    def test_yields_nothing_for_a_session_with_no_records(self, state):
        assert audit.read_records("absent", state) == []


@pytest.fixture
def manifest_root(tmp_path):
    """A rulesets root whose manifest names `core-rules` and `writing-code`."""

    for tier in resolve.TIERS:
        (tmp_path / tier).mkdir()
    for stem in ("core-rules", "writing-code"):
        (tmp_path / "default" / f"{stem}.md").write_text("Body.\n", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(
        yaml.safe_dump({"tiers": {tier: {"include": "*"} for tier in resolve.TIERS}}),
        encoding="utf-8",
    )
    return tmp_path


def load_check(session, root, state):
    return resolve.main(
        ["load-check", "--session", session, "--root", str(root), "--state", str(state)]
    )


class TestLoadCheck:
    def test_exits_zero_when_only_claude_md_loaded(self, manifest_root, state, capsys):
        for path in ("/repo/CLAUDE.md", "/Users/x/.claude/CLAUDE.md", "/repo/nested/CLAUDE.md"):
            audit.append_record(
                {"kind": "load", "file_path": path, "load_reason": "session_start"},
                session_id="abc",
                state=state,
            )

        code = load_check("abc", manifest_root, state)

        assert code == 0
        assert capsys.readouterr().out == ""

    def test_exits_nonzero_naming_a_manifest_stem_that_auto_loaded(
        self, manifest_root, state, capsys
    ):
        audit.append_record(
            {
                "kind": "load",
                "file_path": "/Users/x/.claude/rules/core-rules.md",
                "load_reason": "session_start",
            },
            session_id="abc",
            state=state,
        )

        code = load_check("abc", manifest_root, state)

        assert code == 1
        assert "core-rules.md" in capsys.readouterr().out

    def test_exits_zero_for_a_path_scoped_rule_on_a_glob_match(self, manifest_root, state):
        audit.append_record(
            {
                "kind": "load",
                "file_path": "/Users/x/.claude/rules/testing.md",
                "load_reason": "path_glob_match",
                "trigger_file_path": "/repo/test_thing.py",
            },
            session_id="abc",
            state=state,
        )

        assert load_check("abc", manifest_root, state) == 0

    def test_exits_nonzero_for_a_manifest_stem_pulled_in_by_an_include(
        self, manifest_root, state, capsys
    ):
        audit.append_record(
            {
                "kind": "load",
                "file_path": "/Users/x/.claude/rules/writing-code.md",
                "load_reason": "include",
                "parent_file_path": "/repo/CLAUDE.md",
            },
            session_id="abc",
            state=state,
        )

        code = load_check("abc", manifest_root, state)

        assert code == 1
        assert "writing-code.md" in capsys.readouterr().out

    def test_exits_nonzero_for_a_manifest_stem_on_a_glob_match(self, manifest_root, state):
        audit.append_record(
            {
                "kind": "load",
                "file_path": "/Users/x/.claude/rules/core-rules.md",
                "load_reason": "path_glob_match",
            },
            session_id="abc",
            state=state,
        )

        assert load_check("abc", manifest_root, state) == 1

    def test_ignores_a_delivery_record(self, manifest_root, state):
        audit.append_record(
            {"kind": "delivery", "tier": "haiku", "stems": ["core-rules"]},
            session_id="abc",
            state=state,
        )

        assert load_check("abc", manifest_root, state) == 0
