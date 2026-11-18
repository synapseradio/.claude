#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check a chart spec, written from templates/chart-spec.json, before the chart is drawn.

check_chart_spec.py spec.json [--json]

Reports each decision the spec leaves open or gets wrong: the message, the scale, the series, the
colour, the uncertainty, and the text alternative. Exits 1 when a finding is an error, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

LENGTH_FORMS = {
    "bar",
    "column",
    "stacked-bar",
    "grouped-bar",
    "area",
    "stacked-area",
    "histogram",
    "diverging-bar",
}
POSITION_FORMS = {"line", "dot", "scatter", "slope", "dumbbell", "strip", "small-multiples"}
ANGLE_FORMS = {"pie", "donut"}
OTHER_FORMS = {"table", "heatmap", "map", "flow", "treemap", "box", "number"}
POSITION_CHANNELS = {"x", "y", "length", "position"}
SECOND_CUES = {"label", "shape", "pattern", "position"}
COLOUR_JOBS = {"none", "highlight", "identity", "magnitude", "polarity"}
PIE_PARTS_MAX = 3
COLOURED_SERIES_MAX = 4
SHORT_ALTERNATIVE_CHARACTERS_MAX = 160


@dataclass(frozen=True)
class Finding:
    severity: Literal["error", "warning"]
    field: str
    message: str


def check(spec: dict[str, Any]) -> list[Finding]:
    """Return the findings for one chart spec."""
    findings: list[Finding] = []

    def error(field: str, message: str) -> None:
        findings.append(Finding("error", field, message))

    def warning(field: str, message: str) -> None:
        findings.append(Finding("warning", field, message))

    def section(name: str) -> dict[str, Any]:
        value = spec.get(name)
        return value if isinstance(value, dict) else {}

    def filled(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("<")

    for field, purpose in (
        ("question", "the question the reader brings"),
        ("takeaway", "the one thing the reader should leave with"),
        ("title", "a title"),
    ):
        if not filled(spec.get(field)):
            error(field, f"state {purpose}")

    form = spec.get("form")
    known = LENGTH_FORMS | POSITION_FORMS | ANGLE_FORMS | OTHER_FORMS
    if form not in known:
        error("form", f"choose one of: {', '.join(sorted(known))}")

    data = section("data")
    if not filled(data.get("source")):
        error("data.source", "name where the data comes from")
    if not filled(data.get("period")):
        warning("data.period", "state the period or date the data covers")

    encodings = [item for item in spec.get("encodings", []) if isinstance(item, dict)]
    if not encodings and form not in {"table", "number"}:
        error("encodings", "list which field maps to which channel")
    measures = [item for item in encodings if item.get("type") == "quantitative"]
    if measures and not any(item.get("channel") in POSITION_CHANNELS for item in measures):
        warning(
            "encodings",
            "no measure sits on position or length; put the measure the message is about there",
        )
    for item in measures:
        if not filled(item.get("unit")):
            warning(f"encodings.{item.get('field', '?')}", "give the measure's unit")

    scale = section("value_scale")
    baseline = scale.get("baseline")
    if scale.get("count", 1) != 1:
        error(
            "value_scale.count",
            "two value scales on one chart; use two panels on a shared time axis, or index both",
        )
    if form in LENGTH_FORMS and baseline != 0:
        error(
            "value_scale.baseline",
            "bars and areas encode value as length, so the scale starts at zero",
        )
    if (
        form in POSITION_FORMS
        and baseline not in (0, None)
        and not filled(scale.get("reason_not_zero"))
    ):
        error(
            "value_scale.reason_not_zero",
            "the scale starts off zero; say why, and show the tick labels",
        )
    if spec.get("effects"):
        error("effects", "remove 3D, shadows and gradients; they distort or add nothing")

    series = section("series")
    count = series.get("count", 1)
    highlighted = series.get("highlight") or []
    if form in ANGLE_FORMS and count > PIE_PARTS_MAX:
        error("form", f"a pie with more than {PIE_PARTS_MAX} slices; use sorted bars")
    if form in {"line", "slope"} and count > COLOURED_SERIES_MAX and not highlighted:
        warning(
            "series.highlight",
            "many lines and none highlighted; colour the ones the message is about, grey the rest",
        )
    if 1 < count <= COLOURED_SERIES_MAX and series.get("labels") == "legend":
        warning("series.labels", "few enough series to label directly on the marks")
    if count > 1 and series.get("labels") not in {"direct", "legend"}:
        error("series.labels", "say how series are named: direct or legend")

    colour = section("colour")
    job = colour.get("job", "none")
    if job not in COLOUR_JOBS:
        error("colour.job", f"choose one of: {', '.join(sorted(COLOUR_JOBS))}")
    if job == "identity":
        if colour.get("second_cue") not in SECOND_CUES:
            error(
                "colour.second_cue",
                f"colour alone carries identity; add one of: {', '.join(sorted(SECOND_CUES))}",
            )
        if len(colour.get("palette") or []) < min(count, COLOURED_SERIES_MAX):
            warning(
                "colour.palette",
                "fewer colours than series; list the palette, then run check_palette.py on it",
            )
    if job != "none" and not colour.get("palette_checked"):
        warning(
            "colour.palette_checked",
            "run check_palette.py on the palette and background, then set this to true",
        )

    uncertainty = section("uncertainty")
    if data.get("estimated") and not uncertainty.get("shown"):
        error(
            "uncertainty.shown",
            "the data is estimated, sampled or forecast; show or state its uncertainty",
        )
    if uncertainty.get("shown"):
        for field, purpose in (("as", "how it is drawn"), ("meaning", "what the range covers")):
            if not filled(uncertainty.get(field)):
                error(f"uncertainty.{field}", f"state {purpose}")

    alternative = section("text_alternative")
    short = alternative.get("short")
    if not filled(short):
        error(
            "text_alternative.short",
            "write a short alternative that names the chart type and its message",
        )
    elif len(short) > SHORT_ALTERNATIVE_CHARACTERS_MAX:
        warning(
            "text_alternative.short",
            "keep the short alternative to a sentence; move detail to the long description",
        )
    if form not in {"table", "number"} and not (
        filled(alternative.get("long")) or alternative.get("data_table")
    ):
        error("text_alternative", "give the data another route: a long description or a data table")

    if spec.get("medium") == "interactive":
        interaction = section("interaction")
        if not interaction.get("message_visible_without_interaction"):
            error(
                "interaction.message_visible_without_interaction",
                "the takeaway must show before any interaction",
            )
        if not interaction.get("keyboard_operable"):
            error("interaction.keyboard_operable", "every control must work from the keyboard")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("spec", type=Path, help="chart spec as JSON")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    arguments = parser.parse_args()

    try:
        spec = json.loads(arguments.spec.read_text(encoding="utf-8"))
    except json.JSONDecodeError as problem:
        parser.error(f"{arguments.spec} is not valid JSON: {problem}")
    if not isinstance(spec, dict):
        parser.error(f"{arguments.spec} must hold a JSON object")

    findings = check(spec)
    if arguments.json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2))
    else:
        for finding in findings:
            print(f"{finding.severity:7} {finding.field}: {finding.message}")
        errors = sum(finding.severity == "error" for finding in findings)
        print(f"{errors} error(s), {len(findings) - errors} warning(s)")
    return 1 if any(finding.severity == "error" for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
