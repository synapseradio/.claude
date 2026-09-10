"""The delivery shim never fails the session, and never fails it quietly.

Nothing in the corpus auto-loads, so a shim that raised would leave a
session with no user rules, and a shim that swallowed the error would leave
it with none and no word of it. These tests run the shim as the harness
does, as a subprocess reading a payload on stdin, against a temporary corpus
and state directory so no live rule or record is touched. The failure tests
load the shim as a module and inject the resolver, so no global is patched.
"""

import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import typing

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = PLUGIN_ROOT / "hooks" / "deliver.py"

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import resolve  # noqa: E402  (path must be set before this import)

FAILURE_PHRASE = "running without its user rules"


def load_shim():
    """The shim as a module, so `main` can be handed streams and a resolver."""

    spec = importlib.util.spec_from_file_location("deliver_shim", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_in_process(module, payload, corpus, state, deliver=None):
    """`main` with injected streams; answers (exit code, stdout, stderr)."""

    stdout, stderr = io.StringIO(), io.StringIO()
    argv = ["--root", str(corpus), "--state", str(state)]
    kwargs = {} if deliver is None else {"deliver": deliver}
    code = module.main(
        argv, stdin=io.StringIO(json.dumps(payload)), stdout=stdout, stderr=stderr, **kwargs
    )
    return code, stdout.getvalue(), stderr.getvalue()


def build_corpus(tmp_path):
    """A corpus holding a manifest, a models file, and two default bodies."""

    root = tmp_path / "corpus"
    resolve.scaffold(root)
    for stem in ("alpha", "beta"):
        (root / "default" / f"{stem}.md").write_text(f"Body {stem}.\n", encoding="utf-8")
    return root


def run(payload, corpus, state):
    """The shim as the harness runs it, told which corpus and state to use."""

    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK), "--root", str(corpus), "--state", str(state)],
        input=stdin,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )


class TestDeliveryShim:
    def test_a_session_start_delivers_the_tier_and_exits_zero(self, tmp_path):
        corpus = build_corpus(tmp_path)
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }

        result = run(payload, corpus, state)

        assert result.returncode == 0
        emitted = json.loads(result.stdout)
        text = emitted["hookSpecificOutput"]["additionalContext"]
        assert "tier haiku" in text

    def test_malformed_stdin_exits_zero_with_no_output(self, tmp_path):
        corpus = build_corpus(tmp_path)

        result = run("not json at all", corpus, tmp_path / "state")

        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_a_non_object_payload_exits_zero_with_no_output(self, tmp_path):
        corpus = build_corpus(tmp_path)

        result = run("[1, 2, 3]", corpus, tmp_path / "state")

        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_a_corpus_holding_no_manifest_still_exits_zero(self, tmp_path):
        # The root is there, so nothing is scaffolded over it, and it holds
        # no manifest; the resolver answers a header naming that, and the
        # session starts.
        empty = tmp_path / "empty"
        empty.mkdir()
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }

        result = run(payload, empty, tmp_path / "state")

        assert result.returncode == 0
        assert "0 stems" in result.stdout and "no manifest at" in result.stdout, (
            "a corpus with no manifest composes nothing, and the header has to name that "
            "rather than the shim printing a context that looks like a ruleset"
        )


class TestAFailedDeliveryIsAnnounced:
    """A delivery that raises still answers the harness, and says it failed.

    The announcement travels the channel a delivery travels, `stdout` as one
    JSON object under `hookSpecificOutput.additionalContext`, addressed to
    the event the payload named, so the harness carries it into the same
    context the rules would have reached.
    """

    PAYLOAD: typing.ClassVar[dict] = {
        "hook_event_name": "SubagentStart",
        "session_id": "s1",
        "agent_id": "a1",
    }

    def test_a_delivery_that_raises_a_defect_announces_it_in_context_and_exits_zero(self, tmp_path):
        module = load_shim()

        def boom(payload, root=None, state=None):
            raise RuntimeError("synthetic defect")

        code, out, _ = run_in_process(module, self.PAYLOAD, tmp_path / "c", tmp_path / "s", boom)

        assert code == 0, "a delivery hook that exits non-zero blocks nothing and helps nobody"
        emitted = json.loads(out)["hookSpecificOutput"]
        assert emitted["hookEventName"] == "SubagentStart"
        assert FAILURE_PHRASE in emitted["additionalContext"]
        assert "RuntimeError: synthetic defect" in emitted["additionalContext"]

    def test_a_defect_puts_its_traceback_on_stderr(self, tmp_path):
        module = load_shim()

        def boom(payload, root=None, state=None):
            raise RuntimeError("synthetic defect")

        _, _, err = run_in_process(module, self.PAYLOAD, tmp_path / "c", tmp_path / "s", boom)

        assert "Traceback" in err and "synthetic defect" in err

    def test_an_unreadable_body_is_announced_without_a_traceback(self, tmp_path):
        module = load_shim()

        def unreadable(payload, root=None, state=None):
            raise PermissionError(13, "Permission denied", str(root))

        code, out, err = run_in_process(
            module, self.PAYLOAD, tmp_path / "c", tmp_path / "s", unreadable
        )

        assert code == 0
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert FAILURE_PHRASE in context and "PermissionError" in context
        assert "Traceback" not in err, (
            "a file the process cannot read is the corpus owner's to repair, and a "
            "traceback would point them at the plugin instead"
        )

    def test_the_announcement_takes_the_shape_a_delivery_takes(self, tmp_path):
        module = load_shim()
        corpus = build_corpus(tmp_path)
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }

        def boom(payload, root=None, state=None):
            raise RuntimeError("synthetic defect")

        _, delivered, _ = run_in_process(module, payload, corpus, tmp_path / "s1")
        _, announced, _ = run_in_process(module, payload, corpus, tmp_path / "s2", boom)

        def shape(text):
            return {k: sorted(v) for k, v in json.loads(text).items()}

        assert (
            shape(announced)
            == shape(delivered)
            == {"hookSpecificOutput": ["additionalContext", "hookEventName"]}
        )
        assert json.loads(announced)["hookSpecificOutput"]["additionalContext"].startswith(
            "<!-- ruleset: delivery failed, from deliver.py, 0 stems -->"
        )

    def test_a_delivery_that_succeeds_carries_no_announcement(self, tmp_path):
        corpus = build_corpus(tmp_path)
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }

        result = run(payload, corpus, tmp_path / "state")

        assert FAILURE_PHRASE not in result.stdout
        assert result.stderr == ""

    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads a mode-000 file")
    def test_a_body_the_process_cannot_read_is_announced_through_the_real_resolver(self, tmp_path):
        corpus = build_corpus(tmp_path)
        body = corpus / "default" / "alpha.md"
        body.chmod(0o000)
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }

        try:
            result = run(payload, corpus, tmp_path / "state")
        finally:
            body.chmod(0o644)

        assert result.returncode == 0
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        assert FAILURE_PHRASE in context and "alpha.md" in context
