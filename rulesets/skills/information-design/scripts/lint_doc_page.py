#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Report where a Markdown page resists scanning: its headings, opening, paragraphs, lists, tables, links and images.

lint_doc_page.py page.md [more.md ...] [--strict] [--json]

Prints one finding per line as path:line, severity, code, message. Exits 1 when a finding is an
error, or a warning under --strict, and 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

OPENING_WORDS_MAX = 60
PARAGRAPH_WORDS_MAX = 120
SECTION_PROSE_WORDS_MAX = 350
HEADING_WORDS_MAX = 10
HEADING_DEPTH_MAX = 4
FLAT_LIST_ITEMS_MAX = 9
LIST_DEPTH_MAX = 2
STEP_WORDS_MAX = 45
TABLE_COLUMNS_MAX = 7
BOLD_SPANS_MAX = 3

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```+|~~~+)\s*(\S*)")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]*)\)")
BOLD = re.compile(r"(\*\*|__)(?=\S).+?(?<=\S)\1")
WORD = re.compile(r"[\w'\u2019-]+")
VAGUE_LINK_TEXT = {
    "here",
    "click here",
    "this",
    "this page",
    "link",
    "this link",
    "read more",
    "more",
    "see here",
}

Severity = Literal["error", "warning"]
Report = Callable[[int, Severity, str, str], None]


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    severity: Severity
    code: str
    message: str


@dataclass(frozen=True)
class Block:
    """A run of consecutive lines of one kind, with the 1-based number of its first line."""

    kind: Literal["heading", "paragraph", "list", "table", "code", "other"]
    line: int
    lines: list[str]


def count_words(text: str) -> int:
    return len(WORD.findall(text))


def blocks(lines: list[str]) -> Iterator[Block]:
    """Split a Markdown document into blocks, skipping YAML frontmatter and blank lines."""
    index = 0
    if lines and lines[0].strip() == "---":
        closing = next(
            (offset for offset, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
            None,
        )
        index = closing + 1 if closing is not None else 0
    while index < len(lines):
        line = lines[index]
        start = index
        fence = FENCE.match(line)
        if not line.strip():
            index += 1
        elif fence:
            marker = fence.group(1)
            index += 1
            while index < len(lines) and not lines[index].strip().startswith(marker):
                index += 1
            index += 1
            yield Block("code", start + 1, lines[start:index])
        elif HEADING.match(line):
            index += 1
            yield Block("heading", start + 1, [line])
        elif LIST_ITEM.match(line):
            while index < len(lines) and (
                LIST_ITEM.match(lines[index]) or lines[index].startswith((" ", "\t"))
            ):
                index += 1
            yield Block("list", start + 1, lines[start:index])
        elif TABLE_ROW.match(line):
            while index < len(lines) and TABLE_ROW.match(lines[index]):
                index += 1
            yield Block("table", start + 1, lines[start:index])
        elif line.lstrip().startswith((">", "<", "---", "***")):
            index += 1
            yield Block("other", start + 1, [line])
        else:
            while index < len(lines) and lines[index].strip() and not _starts_block(lines[index]):
                index += 1
            index = max(index, start + 1)
            yield Block("paragraph", start + 1, lines[start:index])


def _starts_block(line: str) -> bool:
    return bool(
        HEADING.match(line) or FENCE.match(line) or LIST_ITEM.match(line) or TABLE_ROW.match(line)
    )


def lint(path: str, text: str) -> list[Finding]:
    """Return the scannability findings for one Markdown document."""
    findings: list[Finding] = []

    def report(line: int, severity: Severity, code: str, message: str) -> None:
        findings.append(Finding(path, line, severity, code, message))

    document = list(blocks(text.splitlines()))
    headings = [
        (block.line, *_heading(block.lines[0])) for block in document if block.kind == "heading"
    ]

    titles = [line for line, level, _ in headings if level == 1]
    if not titles:
        report(
            1, "error", "title-missing", "the page has no level-1 heading naming what it is about"
        )
    for line in titles[1:]:
        report(line, "error", "title-repeated", "a second level-1 heading; a page has one title")

    previous_level = 0
    for line, level, title in headings:
        if previous_level and level > previous_level + 1:
            report(
                line,
                "error",
                "heading-skip",
                f"heading jumps from level {previous_level} to level {level}",
            )
        if level > HEADING_DEPTH_MAX:
            report(
                line,
                "warning",
                "heading-deep",
                f"level-{level} heading; split the page or flatten the outline",
            )
        if count_words(title) > HEADING_WORDS_MAX:
            report(line, "warning", "heading-long", f"heading runs past {HEADING_WORDS_MAX} words")
        if title.endswith((".", ":", ";", ",")):
            report(
                line,
                "warning",
                "heading-punctuation",
                "heading ends in punctuation; write it as a label",
            )
        previous_level = level
    for title, count in Counter(title.casefold() for _, _, title in headings).items():
        if count > 1:
            line = next(line for line, _, text_ in headings if text_.casefold() == title)
            report(
                line,
                "error",
                "heading-duplicate",
                f"{count} headings share this text; a reader cannot tell them apart",
            )

    _lint_opening(document, report)

    prose_words = 0
    section_line = 1
    for block in document:
        body = "\n".join(block.lines)
        if block.kind == "heading":
            prose_words, section_line = 0, block.line
        elif block.kind in {"list", "table", "code"}:
            prose_words = 0
        if block.kind == "paragraph":
            words = count_words(body)
            prose_words += words
            if words > PARAGRAPH_WORDS_MAX:
                report(
                    block.line,
                    "warning",
                    "paragraph-long",
                    f"paragraph of {words} words; split it at its ideas",
                )
            if prose_words > SECTION_PROSE_WORDS_MAX:
                report(
                    section_line,
                    "warning",
                    "section-wall",
                    f"more than {SECTION_PROSE_WORDS_MAX} words of unbroken prose; add a subheading, list or table",
                )
                prose_words = 0
            if len(BOLD.findall(body)) > BOLD_SPANS_MAX:
                report(
                    block.line,
                    "warning",
                    "emphasis-heavy",
                    "more than three bold spans; emphasis on everything marks nothing",
                )
        elif block.kind == "list":
            _lint_list(block, report)
        elif block.kind == "table":
            columns = block.lines[0].strip().strip("|").count("|") + 1
            if columns > TABLE_COLUMNS_MAX:
                report(
                    block.line,
                    "warning",
                    "table-wide",
                    f"table of {columns} columns; drop or split columns",
                )
        elif block.kind == "code" and not _fence_language(block.lines[0]):
            report(block.line, "warning", "code-language", "code fence names no language")
        if block.kind != "code":
            for offset, line in enumerate(block.lines):
                for alt in IMAGE.findall(line):
                    if not alt.strip():
                        report(
                            block.line + offset,
                            "error",
                            "image-alt",
                            "image has no text alternative",
                        )
                for label, target in LINK.findall(line):
                    plain = label.strip().casefold()
                    if plain in VAGUE_LINK_TEXT or plain == target.strip().casefold():
                        report(
                            block.line + offset,
                            "warning",
                            "link-text",
                            f"link text {label!r} does not name its target",
                        )
    return sorted(findings, key=lambda finding: finding.line)


def _heading(line: str) -> tuple[int, str]:
    match = HEADING.match(line)
    if match is None:
        problem = f"not a heading: {line!r}"
        raise ValueError(problem)
    return len(match.group(1)), match.group(2).strip()


def _fence_language(line: str) -> str:
    match = FENCE.match(line)
    return match.group(2) if match else ""


def _lint_opening(document: list[Block], report: Report) -> None:
    title_index = next(
        (
            index
            for index, block in enumerate(document)
            if block.kind == "heading" and _heading(block.lines[0])[0] == 1
        ),
        None,
    )
    if title_index is None:
        return
    following = document[title_index + 1] if title_index + 1 < len(document) else None
    if following is None or following.kind != "paragraph":
        report(
            document[title_index].line,
            "warning",
            "opening-missing",
            "no paragraph follows the title; open with what the page gives the reader",
        )
    elif count_words("\n".join(following.lines)) > OPENING_WORDS_MAX:
        report(
            following.line,
            "warning",
            "opening-long",
            f"opening paragraph runs past {OPENING_WORDS_MAX} words",
        )


def _lint_list(block: Block, report: Report) -> None:
    indents: list[int] = []
    siblings: Counter[tuple[int, ...]] = Counter()
    for offset, line in enumerate(block.lines):
        item = LIST_ITEM.match(line)
        if not item:
            continue
        indent = len(item.group(1).expandtabs(4))
        while indents and indents[-1] > indent:
            indents.pop()
        if not indents or indents[-1] < indent:
            indents.append(indent)
        siblings[tuple(indents)] += 1
        if len(indents) == LIST_DEPTH_MAX + 1 and siblings[tuple(indents)] == 1:
            report(
                block.line + offset,
                "warning",
                "list-deep",
                "list nests three levels; flatten it or split the page",
            )
        if item.group(2)[0].isdigit() and count_words(item.group(3)) > STEP_WORDS_MAX:
            report(
                block.line + offset,
                "warning",
                "step-long",
                "numbered step runs long; give each action its own step",
            )
    if siblings and max(siblings.values()) > FLAT_LIST_ITEMS_MAX:
        report(
            block.line,
            "warning",
            "list-long",
            f"more than {FLAT_LIST_ITEMS_MAX} items at one level; group them under labels or use a table",
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("pages", nargs="+", type=Path, help="Markdown files to check")
    parser.add_argument(
        "--strict", action="store_true", help="exit 1 on warnings as well as errors"
    )
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    arguments = parser.parse_args()

    findings: list[Finding] = []
    for page in arguments.pages:
        findings += lint(str(page), page.read_text(encoding="utf-8"))

    if arguments.json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2))
    else:
        for finding in findings:
            print(
                f"{finding.path}:{finding.line}: {finding.severity} [{finding.code}] {finding.message}"
            )
        errors = sum(finding.severity == "error" for finding in findings)
        print(
            f"{errors} error(s), {len(findings) - errors} warning(s) in {len(arguments.pages)} page(s)"
        )
    failing = {"error", "warning"} if arguments.strict else {"error"}
    return 1 if any(finding.severity in failing for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
