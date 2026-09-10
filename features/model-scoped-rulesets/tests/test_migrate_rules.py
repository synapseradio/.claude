#!/usr/bin/env python3
"""Moving an auto-loading rules directory into the corpus, reversibly.

The harness loads every body under its own rules directory into every
context. That is the state this corpus replaces, so the bodies have to leave
that directory or each one arrives twice. A move that edited a body, or that
could not be undone, would make the change one nobody would risk.

Run with `python3.14 -m pytest features/model-scoped-rulesets/tests/test_migrate_rules.py`.
"""

import json
import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import resolve  # noqa: E402  (path must be set before this import)

ALWAYS_ON = "## alpha\n\nAlpha holds, in every context.\n"
PATH_SCOPED = '---\npaths:\n  - "**/*.sh"\n---\n\n## gated\n\nGated holds.\n'


@pytest.fixture
def source(tmp_path):
    """A rules directory holding one always-on body and one path-scoped body."""

    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "alpha.md").write_text(ALWAYS_ON, encoding="utf-8")
    (rules / "gated.md").write_text(PATH_SCOPED, encoding="utf-8")
    return rules


def migrate(source, root, *flags) -> int:
    return resolve.main(["migrate-rules", "--from", str(source), "--root", str(root), *flags])


class TestThePartition:
    def test_an_always_on_body_moves_into_the_default_tier(self, source, tmp_path, capsys):
        root = tmp_path / "rulesets"

        code = migrate(source, root)

        assert code == 0, capsys.readouterr().out
        assert (root / "default" / "alpha.md").is_file()
        assert not (source / "alpha.md").exists(), (
            "a body left in the auto-loading directory arrives in the context twice, once "
            "from the harness and once from delivery"
        )

    def test_a_path_scoped_body_stays_where_the_harness_reads_it(self, source, tmp_path):
        root = tmp_path / "rulesets"

        migrate(source, root)

        assert (source / "gated.md").read_text(encoding="utf-8") == PATH_SCOPED, (
            "the frontmatter is what scopes a rule to its paths, and the harness is what "
            "reads it there, so moving it would put the body in every context instead"
        )
        assert not (root / "default" / "gated.md").exists()

    def test_the_run_reports_one_line_per_file_and_a_count(self, source, tmp_path, capsys):
        root = tmp_path / "rulesets"

        migrate(source, root)

        printed = capsys.readouterr().out.strip().split("\n")
        assert f"move  {source / 'alpha.md'} -> {root / 'default' / 'alpha.md'}" in printed
        assert f"stay  {source / 'gated.md'}  (frontmatter)" in printed
        assert printed[-1] == "moved 1, stayed 1"

    def test_the_body_is_the_same_bytes_after_the_move(self, source, tmp_path):
        root = tmp_path / "rulesets"
        before = (source / "alpha.md").read_bytes()

        migrate(source, root)

        assert (root / "default" / "alpha.md").read_bytes() == before, (
            "a migration that rewrote a body would edit the user's rules while claiming "
            "only to move them"
        )

    def test_the_corpus_is_scaffolded_when_the_root_holds_no_manifest(self, source, tmp_path):
        root = tmp_path / "rulesets"

        migrate(source, root)

        assert (root / "manifest.yaml").is_file(), (
            "a body under a root with no manifest composes into nothing, so the move would "
            "take the rules out of play altogether"
        )


class TestADryRunChangesNothing:
    def test_it_prints_the_lines_the_real_run_would(self, source, tmp_path, capsys):
        root = tmp_path / "rulesets"
        migrate(source, root, "--dry-run")
        dry = capsys.readouterr().out

        migrate(source, root)

        assert capsys.readouterr().out == dry, (
            "the dry run is what a reader decides from, so a line it does not print is a "
            "move they did not agree to"
        )

    def test_it_moves_no_file(self, source, tmp_path):
        root = tmp_path / "rulesets"

        migrate(source, root, "--dry-run")

        assert (source / "alpha.md").read_text(encoding="utf-8") == ALWAYS_ON
        assert not (root / "default" / "alpha.md").exists()

    def test_it_creates_no_corpus(self, source, tmp_path):
        root = tmp_path / "rulesets"

        migrate(source, root, "--dry-run")

        assert not root.exists(), (
            "a reader asking what a run would do has not agreed to anything yet, and a "
            "corpus left behind is something they would have to remove by hand"
        )


class TestARefusalMovesNothing:
    def test_an_occupied_destination_stops_the_whole_run(self, source, tmp_path, capsys):
        root = tmp_path / "rulesets"
        resolve.main(["init", "--root", str(root)])
        (root / "default" / "alpha.md").write_text("Alpha, already in the corpus.\n", "utf-8")
        (source / "beta.md").write_text("## beta\n\nBeta holds.\n", encoding="utf-8")
        capsys.readouterr()

        code = migrate(source, root)

        assert code == 1
        assert str(root / "default" / "alpha.md") in capsys.readouterr().out
        assert (source / "alpha.md").is_file() and (source / "beta.md").is_file(), (
            "a partial migration leaves the reader to work out which half moved, so a run "
            "that cannot finish makes no move at all"
        )
        assert (root / "default" / "alpha.md").read_text(encoding="utf-8") == (
            "Alpha, already in the corpus.\n"
        )

    def test_a_source_directory_that_is_not_there_is_reported(self, tmp_path, capsys):
        code = migrate(tmp_path / "absent", tmp_path / "rulesets")

        assert code == 1
        assert str(tmp_path / "absent") in capsys.readouterr().out


class TestTheUndo:
    def test_it_puts_the_last_run_s_moves_back(self, source, tmp_path, capsys):
        root = tmp_path / "rulesets"
        migrate(source, root)
        capsys.readouterr()

        code = migrate(source, root, "--undo")

        assert code == 0
        assert (source / "alpha.md").read_text(encoding="utf-8") == ALWAYS_ON, (
            "the reason to run a migration is that it can be undone, and the body has to "
            "come back to where the harness reads it"
        )
        assert not (root / "default" / "alpha.md").exists()

    def test_it_refuses_where_the_moved_body_changed_since(self, source, tmp_path, capsys):
        root = tmp_path / "rulesets"
        migrate(source, root)
        moved = root / "default" / "alpha.md"
        moved.write_text(f"{ALWAYS_ON}\nAnd a line added since.\n", encoding="utf-8")
        capsys.readouterr()

        code = migrate(source, root, "--undo")

        assert code == 1
        assert str(moved) in capsys.readouterr().out
        assert moved.is_file(), (
            "an edit made where the body now sits is the user's current text, so moving it "
            "back would carry that edit somewhere they did not put it"
        )

    def test_an_occupied_destination_stops_the_whole_undo(self, source, tmp_path, capsys):
        root = tmp_path / "rulesets"
        migrate(source, root)
        new_content = "## alpha\n\nA new alpha, written after the migration.\n"
        (source / "alpha.md").write_text(new_content, encoding="utf-8")
        capsys.readouterr()

        code = migrate(source, root, "--undo")

        assert code == 1
        assert str(source / "alpha.md") in capsys.readouterr().out
        assert (source / "alpha.md").read_text(encoding="utf-8") == new_content, (
            "a file written into the vacated spot after the migration is the user's new "
            "text, and an undo that overwrote it with no check would destroy it with "
            "nothing left to recover it from"
        )
        assert (root / "default" / "alpha.md").is_file(), (
            "a refused undo has to leave the migrated body exactly where it was, the same "
            "way a refused forward migration leaves nothing moved"
        )

    def test_it_records_nothing_left_to_undo(self, source, tmp_path, capsys):
        root = tmp_path / "rulesets"
        migrate(source, root)
        migrate(source, root, "--undo")
        capsys.readouterr()

        code = migrate(source, root, "--undo")

        assert code == 1
        assert "no migration recorded" in capsys.readouterr().out, (
            "an undo that ran twice would try to move a file that is already back, and the "
            "second run has to say so rather than report a reversal it did not make"
        )

    def test_the_journal_records_each_move_as_one_object(self, source, tmp_path):
        root = tmp_path / "rulesets"
        migrate(source, root)

        lines = (root / resolve.JOURNAL).read_text(encoding="utf-8").strip().split("\n")
        records = [json.loads(line) for line in lines]

        assert len(records) == 1
        assert records[0]["src"] == str(source / "alpha.md")
        assert records[0]["dst"] == str(root / "default" / "alpha.md")
        assert records[0]["timestamp"], "an undo picks the last run, which needs a time on it"
