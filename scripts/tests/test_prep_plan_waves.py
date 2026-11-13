#!/usr/bin/env python3
"""Tests for the prep-plan skill's `scripts/plan-waves.py`.

Run with `uv run --frozen pytest scripts/tests/test_prep_plan_waves.py`.

The script reads one file and prints a report. Every test writes that file
under tmp_path and runs the script with HOME pointed at an empty directory
beside it, so no test reads or writes the real home.
"""

import ast
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "features/plugins/prep/skills/prep-plan/scripts/plan-waves.py"


def waves(tmp_path, text) -> subprocess.CompletedProcess:
    home = tmp_path / "home"
    home.mkdir()
    readiness = tmp_path / "readiness.md"
    readiness.write_text(text)
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(readiness)],
        env={"HOME": str(home), "PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )
    assert list(home.iterdir()) == []
    return result


def test_units_that_wait_on_nothing_share_the_first_wave(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- intent: add themes\n"
        "- unit: palette | the colour tables | owns: src/palette.ts | waits: none\n"
        "- unit: setting | the theme setting | owns: src/settings.ts | waits: none\n"
        "- unit: wiring | draw with the chosen palette | owns: src/app.tsx | waits: palette, setting\n",
    )

    assert result.returncode == 0, result.stdout
    assert "wave 1: palette, setting\n" in result.stdout
    assert "wave 2: wiring\n" in result.stdout
    assert "widest wave: 2 units; longest chain: 2 waves\n" in result.stdout
    assert "problems" not in result.stdout


def test_a_strict_chain_is_reported_as_one_unit_per_wave(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- unit: a | owns: src/one.ts | waits: none\n"
        "- unit: b | owns: src/two.ts | waits: a\n"
        "- unit: c | owns: src/three.ts | waits: b\n",
    )

    assert result.returncode == 0
    assert "widest wave: 1 unit; longest chain: 3 waves\n" in result.stdout
    assert "every unit runs alone" in result.stdout


def test_a_path_rewritten_by_a_chain_of_units_is_named_as_a_hotspot(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- unit: a | owns: src/app.tsx, src/one.ts | waits: none\n"
        "- unit: b | owns: src/app.tsx | waits: a\n"
        "- unit: c | owns: src/app.tsx | waits: b\n",
    )

    assert result.returncode == 0
    assert "hotspots\n" in result.stdout
    assert "src/app.tsx: a, b, c\n" in result.stdout
    assert "src/one.ts" not in result.stdout.split("hotspots\n")[1]


def test_two_unordered_units_owning_one_path_whole_is_a_problem(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- unit: a | owns: src/app.tsx | waits: none\n- unit: b | owns: src/app.tsx | waits: none\n",
    )

    assert result.returncode == 1
    assert "problems\n" in result.stdout
    assert "a and b both own src/app.tsx and neither waits on the other" in result.stdout


def test_two_unordered_units_owning_different_regions_of_one_path_pass(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- unit: a | owns: src/app.tsx#legend | waits: none\n"
        "- unit: b | owns: src/app.tsx#bar | waits: none\n",
    )

    assert result.returncode == 0, result.stdout
    assert "problems" not in result.stdout


def test_an_unordered_unit_owning_a_whole_path_collides_with_a_region_of_it(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- unit: a | owns: src/app.tsx#legend | waits: none\n"
        "- unit: b | owns: src/app.tsx | waits: none\n",
    )

    assert result.returncode == 1
    assert "a and b both own src/app.tsx and neither waits on the other" in result.stdout


def test_a_wait_on_an_unnamed_unit_is_a_problem(tmp_path) -> None:
    result = waves(tmp_path, "- unit: a | owns: x | waits: ghost\n")

    assert result.returncode == 1
    assert "a waits on ghost, which no unit line names" in result.stdout


def test_a_cycle_is_a_problem(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- unit: a | owns: x | waits: b\n- unit: b | owns: y | waits: a\n",
    )

    assert result.returncode == 1
    assert "a and b wait on each other in a cycle" in result.stdout


def test_a_repeated_unit_name_is_a_problem(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- unit: a | owns: x | waits: none\n- unit: a | owns: y | waits: none\n",
    )

    assert result.returncode == 1
    assert "two unit lines are named a" in result.stdout


def test_a_unit_consuming_a_fixed_contract_starts_beside_its_provider(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- contract: Palette | fixed | the palette module's exported type and lookup\n"
        "- unit: palette | owns: src/palette.ts | provides: Palette | waits: none\n"
        "- unit: legend | owns: src/legend.ts | consumes: Palette | waits: none\n",
    )

    assert result.returncode == 0, result.stdout
    assert "wave 1: legend, palette\n" in result.stdout
    assert "open contracts" not in result.stdout


def test_a_unit_consuming_an_open_contract_waits_on_its_provider(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- contract: Palette | open | shape still unknown\n"
        "- unit: palette | owns: src/palette.ts | provides: Palette | waits: none\n"
        "- unit: legend | owns: src/legend.ts | consumes: Palette | waits: none\n"
        "- unit: bar | owns: src/bar.ts | consumes: Palette | waits: none\n",
    )

    assert result.returncode == 0, result.stdout
    assert "wave 1: palette\n" in result.stdout
    assert "wave 2: bar, legend\n" in result.stdout
    assert "open contracts\n" in result.stdout
    assert (
        "  Palette: stating it in the plan moves bar, legend to an earlier wave\n" in result.stdout
    )


def test_a_wait_may_name_the_code_it_needs_in_parentheses(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- unit: palette | owns: src/palette.ts | waits: none\n"
        "- unit: wiring | owns: src/app.tsx | waits: palette (its tests call the real lookup)\n",
    )

    assert result.returncode == 0, result.stdout
    assert "wave 2: wiring\n" in result.stdout


def test_consuming_a_contract_no_line_names_is_a_problem(tmp_path) -> None:
    result = waves(tmp_path, "- unit: legend | owns: src/legend.ts | consumes: Palette\n")

    assert result.returncode == 1
    assert "legend consumes Palette, which no contract line names" in result.stdout


def test_a_contract_that_is_neither_fixed_nor_open_is_a_problem(tmp_path) -> None:
    result = waves(
        tmp_path,
        "- contract: Palette | maybe\n- unit: legend | owns: src/legend.ts | consumes: Palette\n",
    )

    assert result.returncode == 1
    assert "contract Palette is marked maybe, neither fixed nor open" in result.stdout


def test_a_file_with_no_unit_line_is_a_usage_error(tmp_path) -> None:
    result = waves(tmp_path, "- intent: nothing yet\n")

    assert result.returncode == 2
    assert "no line starting '- unit:'" in result.stderr


def test_the_script_parses_under_python_3_9() -> None:
    ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT), feature_version=(3, 9))
