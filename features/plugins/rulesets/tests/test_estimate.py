r"""The `estimate` command prints each context's size and estimated tokens, and the change since a snapshot.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_estimate.py`.

The fixture pool holds rules `alpha` and `beta`. One context's composed text is
`<!-- rule: alpha -->\nalpha beta gamma\n` (38 characters), a line break, then
`<!-- rule: beta -->\ndelta\n` (26 characters): 65 characters and 12 words. At 3.5 characters
per token and a multiplier of 1.30, that is 65 / 3.5 * 1.30 = 24.14 tokens, which rounds to 24.
"""

import pathlib
import re
import subprocess
import sys

import pytest
from rulesets.cli import main
from rulesets.estimate import figures
from rulesets.source.directory import Present, read_directory

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
IMPACT = PLUGIN_ROOT / "skills" / "rulesets" / "scripts" / "impact.py"

KNOWN_MODELS = ("opus", "sonnet", "haiku", "fable")

SESSION_OPUS = "kind=session model=opus agent=- flag=- tools=-"
SESSION_HAIKU = "kind=session model=haiku agent=- flag=- tools=-"
SESSION_UNNAMED = "kind=session model=- agent=- flag=- tools=-"
SESSION_STRANGER = "kind=session model=stranger agent=- flag=- tools=-"


def pool(root: pathlib.Path, models: str, beta: str = "delta\n") -> pathlib.Path:
    (root / "rules").mkdir(parents=True)
    (root / "rules" / "alpha.md").write_text("alpha beta gamma\n", encoding="utf-8")
    (root / "rules" / "beta.md").write_text(beta, encoding="utf-8")
    (root / "config.yaml").write_text(f"models: {models}\ndefaults: alpha beta\n", encoding="utf-8")
    return root


def estimate(capsys, *arguments: object) -> tuple[int, dict[str, list[str]]]:
    """The exit status and each printed row's columns, keyed by its context name."""
    status = main(["estimate", *map(str, arguments)])
    lines = capsys.readouterr().out.splitlines()
    rows = {
        columns[0]: columns[1:]
        for columns in (re.split(r"\s{2,}", line.strip()) for line in lines[1:])
        if columns[0]
    }
    return status, rows


def snapshot(root: pathlib.Path, out: pathlib.Path) -> None:
    done = subprocess.run(
        [sys.executable, str(IMPACT), "snapshot", "--root", str(root), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr


class TestTheCount:
    def test_each_context_prints_its_model_characters_words_and_tokens(
        self, tmp_path, capsys
    ) -> None:
        root = pool(tmp_path / "rulesets", "opus haiku")

        status, rows = estimate(capsys, "--root", root)

        assert status == 0
        assert rows[SESSION_OPUS][:4] == ["opus", "65", "12", "24"]
        assert len(rows) == 6

    def test_a_context_with_no_model_prints_a_dash_for_its_model(self, tmp_path, capsys) -> None:
        root = pool(tmp_path / "rulesets", "opus")

        _, rows = estimate(capsys, "--root", root)

        assert rows[SESSION_UNNAMED][:4] == ["-", "65", "12", "24"]


class TestThePerModelFigure:
    def test_a_models_own_figure_sets_its_tokens(self, tmp_path, capsys, monkeypatch) -> None:
        root = pool(tmp_path / "rulesets", "opus haiku")
        monkeypatch.setitem(
            figures.FIGURES,
            "haiku",
            figures.Figure(5.0, "https://example.test/a", 1.0, "https://example.test/b"),
        )

        _, rows = estimate(capsys, "--root", root)

        assert rows[SESSION_HAIKU][3] == "13"
        assert rows[SESSION_OPUS][3] == "24"

    def test_a_model_the_table_lacks_takes_the_default_and_the_row_says_so(
        self, tmp_path, capsys
    ) -> None:
        root = pool(tmp_path / "rulesets", "opus stranger")

        _, rows = estimate(capsys, "--root", root)

        assert rows[SESSION_STRANGER][3] == "24"
        assert rows[SESSION_STRANGER][-1] == "default"
        assert rows[SESSION_OPUS][-1] == "table"


class TestTheDeltaAgainstABaseline:
    def test_an_edit_shows_as_the_change_in_tokens(self, tmp_path, capsys) -> None:
        before = pool(tmp_path / "before-root", "opus")
        snapshot(before, tmp_path / "snapshot")
        (before / "rules" / "beta.md").write_text("delta epsilon\n", encoding="utf-8")

        status, rows = estimate(capsys, "--root", before, "--baseline", tmp_path / "snapshot")

        assert status == 0
        assert rows[SESSION_OPUS][:7] == ["opus", "73", "13", "27", "24", "+3", "table"]

    def test_an_unchanged_pool_shows_a_delta_of_zero_everywhere(self, tmp_path, capsys) -> None:
        root = pool(tmp_path / "rulesets", "opus haiku")
        snapshot(root, tmp_path / "snapshot")

        status, rows = estimate(capsys, "--root", root, "--baseline", tmp_path / "snapshot")

        assert status == 0
        assert {columns[5] for columns in rows.values()} == {"0"}

    def test_a_directory_that_is_no_snapshot_is_a_usage_error(self, tmp_path, capsys) -> None:
        root = pool(tmp_path / "rulesets", "opus")

        status = main(["estimate", "--root", str(root), "--baseline", str(tmp_path)])

        assert status == 2
        assert "no snapshot" in capsys.readouterr().err


class TestTheFigureTable:
    def test_every_declared_model_the_table_knows_has_a_figure_and_sources(self, tmp_path) -> None:
        root = pool(tmp_path / "rulesets", " ".join(KNOWN_MODELS))
        directory = read_directory(root)
        assert isinstance(directory.config, Present)

        for name in directory.config.config.models:
            if name not in KNOWN_MODELS:
                continue
            assert name in figures.FIGURES, f"no figure for the declared model {name}"
            figure = figures.FIGURES[name]
            assert figure.chars_per_token > 0
            assert figure.multiplier > 0
            assert figure.chars_source.startswith("https://")
            assert figure.multiplier_source.startswith("https://")

    def test_the_default_figure_has_sources(self) -> None:
        assert figures.DEFAULT.chars_source.startswith("https://")
        assert figures.DEFAULT.multiplier_source.startswith("https://")


@pytest.mark.parametrize("name", KNOWN_MODELS)
def test_a_known_model_is_not_marked_defaulted(name) -> None:
    _, defaulted = figures.figure_for(name)

    assert not defaulted
