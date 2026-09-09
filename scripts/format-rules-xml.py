#!/usr/bin/env python3
"""Indent the tag structure of the rules files and `CLAUDE.md`.

Every rules file carries one `<rule>` element whose groups nest, and this
script renders that nesting with two spaces per level. Text sits one level
inside its own tags, so a group's prose reads as the body of the group. Text
keeps its wording and keeps its indentation relative to the sibling lines of
its own element, so a nested list item stays nested and a fenced template
keeps the internal layout a model copies.

`paths:` frontmatter passes through byte for byte, since its globs are read by
the harness rather than by any reader of the prose. A path-scoped rules file
is otherwise formatted like every other one, and no output of this script
depends on which rules the render carries.

With no path argument it formats every body under a `rulesets/` tier, every
path-scoped rule under `rules/`, and `CLAUDE.md`, resolved from this script's
own location, so a run inside a worktree formats that worktree. With
`--check` it writes nothing and exits nonzero where any file would change,
which is what the pre-push hook gates on.

Run the tests with `python3.14 -m pytest scripts/tests/test_format_rules_xml.py`.
"""

import argparse
import dataclasses
import re
import sys
from pathlib import Path

INDENT = "  "

TAG_OPEN = re.compile(r"\A<([a-z_][\w-]*)((?:\s[^<>]*)?)>\Z")
TAG_CLOSE = re.compile(r"\A</([a-z_][\w-]*)>\Z")
TAG_INLINE = re.compile(r"\A<([a-z_][\w-]*)((?:\s[^<>]*)?)>(.+)</\1>\Z")
FENCE = re.compile(r"\A(```|~~~)")


@dataclasses.dataclass
class Element:
    """One tag pair and whatever sits between its tags."""

    name: str
    attrs: str
    children: list


@dataclasses.dataclass
class Lines:
    """A run of text, or a fenced block, held raw."""

    raw: list[str]


@dataclasses.dataclass
class Blank:
    """One empty line, which no indentation reaches."""


def split_frontmatter(lines: list[str]) -> tuple[list[str], list[str]]:
    """The frontmatter lines including both delimiters, then the body."""

    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return lines[: index + 1], lines[index + 1 :]
    return [], lines


def is_structural(line: str) -> bool:
    stripped = line.strip()
    return bool(
        not stripped
        or FENCE.match(stripped)
        or TAG_OPEN.match(stripped)
        or TAG_CLOSE.match(stripped)
        or TAG_INLINE.match(stripped)
    )


def parse(lines: list[str], path: Path) -> list:
    """The body as a tree of elements, text runs, fenced blocks, and blanks.

    Raises ValueError naming the line where a fence never closes, where a
    closing tag names a different element than the open one, where a closing
    tag arrives with nothing open, or where an element never closes, since
    each of those would move text out of the element that holds it.
    """

    top: list = []
    stack = [top]
    open_tags: list[tuple[str, int]] = []
    index, count = 0, len(lines)

    while index < count:
        raw = lines[index].rstrip()
        stripped = raw.strip()

        if not stripped:
            stack[-1].append(Blank())
            index += 1
            continue

        fence = FENCE.match(stripped)
        if fence:
            token = fence.group(1)
            block, cursor, closed = [raw], index + 1, False
            while cursor < count:
                block.append(lines[cursor].rstrip())
                if lines[cursor].strip().startswith(token):
                    closed, cursor = True, cursor + 1
                    break
                cursor += 1
            if not closed:
                raise ValueError(f"{path}:{index + 1}: fence never closes")
            stack[-1].append(Lines(block))
            index = cursor
            continue

        inline = TAG_INLINE.match(stripped)
        if inline:
            body = Lines([inline.group(3).strip()])
            stack[-1].append(Element(inline.group(1), inline.group(2), [body]))
            index += 1
            continue

        opening = TAG_OPEN.match(stripped)
        if opening:
            element = Element(opening.group(1), opening.group(2), [])
            stack[-1].append(element)
            stack.append(element.children)
            open_tags.append((opening.group(1), index + 1))
            index += 1
            continue

        closing = TAG_CLOSE.match(stripped)
        if closing:
            if not open_tags:
                raise ValueError(f"{path}:{index + 1}: </{closing.group(1)}> closes nothing")
            name, line_number = open_tags.pop()
            if name != closing.group(1):
                raise ValueError(
                    f"{path}:{index + 1}: </{closing.group(1)}> closes <{name}> "
                    f"opened at line {line_number}"
                )
            stack.pop()
            index += 1
            continue

        run: list[str] = []
        while index < count and not is_structural(lines[index]):
            run.append(lines[index].rstrip())
            index += 1
        stack[-1].append(Lines(run))

    if open_tags:
        name, line_number = open_tags[-1]
        raise ValueError(f"{path}: <{name}> opened at line {line_number} never closes")
    return top


def leading(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def render(nodes: list, depth: int, out: list[str]) -> None:
    """Append each node at this depth, text keeping its relative indentation.

    The base is the narrowest indentation among the text of these siblings, so
    a line indented past it stays indented past it by the same amount, and a
    second run over the output reproduces the output.
    """

    widths = [
        leading(line)
        for node in nodes
        if isinstance(node, Lines)
        for line in node.raw
        if line.strip()
    ]
    base = min(widths) if widths else 0

    for node in nodes:
        if isinstance(node, Blank):
            out.append("")
        elif isinstance(node, Lines):
            for line in node.raw:
                if not line.strip():
                    out.append("")
                else:
                    relative = " " * max(0, leading(line) - base)
                    out.append(f"{INDENT * depth}{relative}{line.strip()}")
        else:
            out.append(f"{INDENT * depth}<{node.name}{node.attrs}>")
            render(node.children, depth + 1, out)
            out.append(f"{INDENT * depth}</{node.name}>")


def format_text(text: str, path: Path) -> str:
    """The file's text with its tag structure indented."""

    lines = text.split("\n")
    frontmatter, body = split_frontmatter(lines)
    while body and not body[-1].strip():
        body.pop()
    while body and not body[0].strip():
        body.pop(0)

    out: list[str] = []
    render(parse(body, path), 0, out)
    prefix = "\n".join(frontmatter) + "\n\n" if frontmatter else ""
    return prefix + "\n".join(out) + "\n"


RULES_DIRNAME = "rules"
RULESETS_DIRNAME = "rulesets"


def default_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    return [
        *sorted((root / RULESETS_DIRNAME).glob("*/*.md")),
        *sorted((root / RULES_DIRNAME).glob("*.md")),
        root / "CLAUDE.md",
    ]


def owns(path: Path) -> bool:
    """Whether this script formats the given path.

    A hook hands over every staged markdown file, and the tag form belongs to
    the always-on bodies under a `rulesets/` tier, the path-scoped rules under
    `rules/`, and `CLAUDE.md`. Every other path passes through untouched, a
    markdown file sitting directly in `rulesets/` included, since that one
    carries prose.
    """

    if path.suffix != ".md":
        return False
    if path.name == "CLAUDE.md" or path.parent.name == RULES_DIRNAME:
        return True
    return path.parent.parent.name == RULESETS_DIRNAME


def main() -> int:
    parser = argparse.ArgumentParser(description="Indent the tag structure of the rules files.")
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit nonzero where any file would change",
    )
    args = parser.parse_args()
    paths = [path for path in args.paths if owns(path)] if args.paths else default_paths()

    changed: list[Path] = []
    faults: list[str] = []
    for path in paths:
        original = path.read_text(encoding="utf-8")
        try:
            formatted = format_text(original, path)
        except ValueError as error:
            faults.append(str(error))
            continue
        if formatted != original:
            changed.append(path)
            if not args.check:
                path.write_text(formatted, encoding="utf-8")

    for fault in faults:
        print(f"error: {fault}", file=sys.stderr)
    verb = "would reindent" if args.check else "reindented"
    print(f"{verb}: {len(changed)} of {len(paths)} files")
    for path in changed:
        print(f"  {path}")
    return 1 if faults or (args.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
