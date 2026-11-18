#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Turn the CSV behind a chart into the facts for its text alternative and a Markdown data table.

text_alternative.py data.csv [--unit '%'] [--form 'line chart'] [--max-rows 30]

The first column holds the labels (dates or categories); every other column is one numeric series.
Prints, per series, the first, last, highest and lowest values with their labels and the net
change, then the data as a Markdown table. Writes nothing to disk.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Series:
    name: str
    labels: list[str]
    values: list[float]


def read_series(path: Path) -> tuple[str, list[Series]]:
    """Return the label column's header and one Series per numeric column, skipping blank cells."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for row in csv.reader(handle) if any(cell.strip() for cell in row)]
    if len(rows) < 2 or len(rows[0]) < 2:
        problem = f"{path} needs a header row, a label column and at least one numeric column"
        raise ValueError(problem)
    header, body = rows[0], rows[1:]
    series = []
    for column in range(1, len(header)):
        labels, values = [], []
        for number, row in enumerate(body, start=2):
            cell = row[column].strip() if column < len(row) else ""
            if not cell:
                continue
            try:
                values.append(float(cell.replace(",", "")))
            except ValueError:
                problem = (
                    f"{path}, row {number}, column {header[column]!r}: {cell!r} is not a number"
                )
                raise ValueError(problem) from None
            labels.append(row[0].strip())
        if values:
            series.append(Series(header[column].strip(), labels, values))
    return header[0].strip(), series


def number(value: float, unit: str) -> str:
    text = f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{text}{unit}" if unit in {"%", "°"} or not unit else f"{text} {unit}"


def facts(series: Series, unit: str) -> list[str]:
    """Return the sentences a long description needs about one series."""
    first, last = series.values[0], series.values[-1]
    high = max(range(len(series.values)), key=series.values.__getitem__)
    low = min(range(len(series.values)), key=series.values.__getitem__)
    change = last - first
    size = (
        f"{number(abs(change), '')} percentage points" if unit == "%" else number(abs(change), unit)
    )
    direction = "no change" if change == 0 else ("up " if change > 0 else "down ") + size
    relative = (
        f" ({abs(change) / abs(first):.0%} of the starting value)" if first and change else ""
    )
    return [
        f"starts at {number(first, unit)} ({series.labels[0]}) and ends at {number(last, unit)} "
        f"({series.labels[-1]}): {direction}{relative}",
        f"highest: {number(series.values[high], unit)} ({series.labels[high]})",
        f"lowest: {number(series.values[low], unit)} ({series.labels[low]})",
    ]


def table(path: Path, max_rows: int) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for row in csv.reader(handle) if any(cell.strip() for cell in row)]
    header, body = rows[0], rows[1:]
    lines = [
        "| " + " | ".join(cell.strip() for cell in header) + " |",
        "| " + " | ".join(["---"] + ["---:"] * (len(header) - 1)) + " |",
    ]
    lines += ["| " + " | ".join(cell.strip() for cell in row) + " |" for row in body[:max_rows]]
    if len(body) > max_rows:
        lines.append(f"\n{len(body) - max_rows} more rows are in the source data.")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "data", type=Path, help="CSV file: labels in the first column, one series per other column"
    )
    parser.add_argument(
        "--unit", default="", help="unit to print after each value, such as '%%' or 'ms'"
    )
    parser.add_argument("--form", default="chart", help="what the picture is, such as 'line chart'")
    parser.add_argument("--max-rows", type=int, default=30, help="rows of the table to print")
    arguments = parser.parse_args()

    try:
        label_header, all_series = read_series(arguments.data)
    except (OSError, ValueError) as problem:
        parser.error(str(problem))
    if not all_series:
        parser.error(f"{arguments.data} holds no numeric column")

    names = ", ".join(series.name for series in all_series)
    span = f"{all_series[0].labels[0]} to {all_series[0].labels[-1]}"
    print("## Short alternative\n")
    print(
        f"{arguments.form.capitalize()} of {names} by {label_header}, {span}: <state the message here>.\n"
    )
    print("## Facts for the long description\n")
    for series in all_series:
        print(f"- {series.name}")
        for fact in facts(series, arguments.unit):
            print(f"  - {fact}")
    print("\n## Data table\n")
    print("\n".join(table(arguments.data, arguments.max_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
