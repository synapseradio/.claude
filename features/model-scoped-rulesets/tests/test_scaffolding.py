#!/usr/bin/env python3
"""A fresh corpus is legal, empty, and delivers no content.

This plugin ships mechanism and no rules, so the corpus a first run meets is
one nobody has written yet. That corpus has to pass `check`, and delivery
against it has to say plainly that it carried nothing rather than hand a
session a context that reads like a ruleset.

Run with `python3.14 -m pytest features/model-scoped-rulesets/tests/test_scaffolding.py`.
"""

import pathlib
import sys

import yaml

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import resolve  # noqa: E402  (path must be set before this import)

SESSION = {"hook_event_name": "SessionStart", "session_id": "s1", "model": "a-model-with-no-tier"}


def delivered(payload, root, state) -> str:
    output = resolve.deliver_payload(payload, root=root, state=state, env={})
    return output["hookSpecificOutput"]["additionalContext"]


class TestTheScaffoldIsALegalCorpus:
    def test_init_writes_a_manifest_a_models_file_and_every_tier(self, tmp_path, capsys):
        root = tmp_path / "rulesets"

        code = resolve.main(["init", "--root", str(root)])

        assert code == 0, capsys.readouterr().out
        assert yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))["tiers"], (
            "a manifest naming no tier composes nothing, so the corpus it opens would "
            "deliver a header for every model"
        )
        assert (root / "models.yaml").is_file()
        for tier in resolve.TIERS:
            assert (root / tier / ".gitkeep").is_file(), (
                f"the {tier} tier's directory is what a body gets dropped into, and an empty "
                "directory does not survive a commit without a file in it"
            )

    def test_check_exits_zero_against_a_scaffold(self, tmp_path, capsys):
        root = tmp_path / "rulesets"
        resolve.main(["init", "--root", str(root)])
        capsys.readouterr()

        code = resolve.main(["check", "--root", str(root)])

        assert code == 0, (
            "a corpus nobody has written to yet is a legal corpus, and a check that failed "
            f"on one would report an error at every install: {capsys.readouterr().out}"
        )

    def test_init_refuses_a_root_that_already_holds_a_manifest(self, tmp_path, capsys):
        root = tmp_path / "rulesets"
        resolve.main(["init", "--root", str(root)])
        (root / "default" / "alpha.md").write_text("Alpha holds.\n", encoding="utf-8")
        capsys.readouterr()

        code = resolve.main(["init", "--root", str(root)])

        assert code == 1
        assert str(root / "manifest.yaml") in capsys.readouterr().out
        assert (root / "default" / "alpha.md").read_text(encoding="utf-8") == "Alpha holds.\n", (
            "the corpus is the user's, so a second init writing over it would replace what "
            "they had written with an empty tier"
        )


class TestDeliveryAgainstAScaffoldCarriesNoContent:
    def test_the_delivered_text_is_the_header_and_nothing_else(self, tmp_path):
        root = tmp_path / "rulesets"
        resolve.main(["init", "--root", str(root)])

        text = delivered(SESSION, root, tmp_path / "state")

        content = [
            line
            for line in text.strip().split("\n")
            if line.strip() and not line.startswith("<!--")
        ]
        assert content == [], (
            "an empty corpus has no rules to deliver, so any line beyond the comment header "
            f"is text this plugin put in a session nobody wrote: {content}"
        )
        assert "0 stems" in text, (
            "the count is where a reader sees that the corpus is empty rather than that "
            "delivery failed"
        )

    def test_an_absent_root_is_scaffolded_and_the_header_says_so(self, tmp_path):
        root = tmp_path / "rulesets"

        text = delivered(SESSION, root, tmp_path / "state")

        assert (root / "manifest.yaml").is_file(), (
            "the first hook run after an install meets no corpus, and leaving none behind "
            "would leave its owner nothing to drop a body into"
        )
        assert f"scaffolded an empty corpus at {root}" in text, (
            "a session that receives no rules and no explanation reads as a session whose "
            "rules failed to load"
        )

    def test_a_second_run_scaffolds_nothing_and_says_nothing(self, tmp_path):
        root = tmp_path / "rulesets"
        delivered(SESSION, root, tmp_path / "state")
        (root / "default" / "alpha.md").write_text("Alpha holds.\n", encoding="utf-8")

        text = delivered(SESSION, root, tmp_path / "state")

        assert (root / "default" / "alpha.md").is_file(), (
            "the corpus a session reads is the user's, so a later run reaching it would "
            "replace every body they had written"
        )
        assert "Alpha holds." in text
        assert "scaffolded an empty corpus" not in text, (
            "the note on a run that created nothing would read as a corpus just replaced"
        )


class TestAScaffoldThatCannotBeWrittenIsReported:
    def test_the_header_names_the_reason_and_the_hook_still_answers(self, tmp_path):
        blocked = tmp_path / "blocked"
        blocked.mkdir()
        blocked.chmod(0o500)
        try:
            text = delivered(SESSION, blocked / "rulesets", tmp_path / "state")
        finally:
            blocked.chmod(0o700)

        assert "could not be scaffolded" in text, (
            "a corpus that cannot be created is why the session has no rules, and the "
            "header is the only place its reader sees that"
        )


class TestTheChecksScaffoldNothing:
    def test_check_reports_the_missing_manifest_and_creates_nothing(self, tmp_path, capsys):
        root = tmp_path / "rulesets"

        code = resolve.main(["check", "--root", str(root)])

        assert code == 1
        assert f"no manifest at {root / 'manifest.yaml'}" in capsys.readouterr().out
        assert not root.exists(), (
            "a check that scaffolded would create a corpus from a command that only reads, "
            "and the next check would pass against a corpus nobody asked for"
        )

    def test_inspect_reports_the_missing_manifest_and_creates_nothing(self, tmp_path):
        root = tmp_path / "rulesets"

        code = resolve.main(["inspect", "--tier", "default", "--root", str(root)])

        assert code == 1
        assert not root.exists()
