"""An edited render split back into the pool files its sections came from."""

from __future__ import annotations

import dataclasses
import pathlib

from rulesets.render.context_render import SECTION_SEPARATOR
from rulesets.source.marker import Marker, marker, read_marker
from rulesets.source.pool import Pool, PoolFile, read_pool


@dataclasses.dataclass(frozen=True)
class SplitReport:
    """The pool files the split rewrote."""

    written: tuple[pathlib.Path, ...]


@dataclasses.dataclass(frozen=True)
class MalformedRender:
    """Why the split refused a rendered file; it wrote nothing."""

    reason: str


@dataclasses.dataclass(frozen=True)
class _Section:
    marker: Marker
    body: str


def _sections(text: str) -> list[_Section] | MalformedRender:
    """The marked sections of a render, each body without the separator before the next marker."""

    starts: list[tuple[Marker, int, int]] = []
    offset = 0
    for line in text.split("\n"):
        found = read_marker(line)
        if found is not None:
            starts.append((found, offset, min(offset + len(line) + 1, len(text))))
        offset += len(line) + 1
    if not starts:
        return [] if not text else MalformedRender("the file holds no marker")
    if starts[0][1] > 0:
        return MalformedRender("the file holds text before its first marker")
    sections = []
    for (found, _, body_start), following in zip(starts, [*starts[1:], None], strict=True):
        if following is None:
            body = text[body_start:]
        else:
            body = text[body_start : following[1]].removesuffix(SECTION_SEPARATOR)
        sections.append(_Section(found, body))
    return sections


def _source(pool: Pool, section: Marker) -> PoolFile | None:
    rule = pool.rules.get(section.rule)
    if rule is None:
        return None
    file = rule.default if section.variant is None else rule.variants.get(section.variant)
    return file if file is not None and file.problem is None else None


def split(rendered: pathlib.Path, root: pathlib.Path) -> SplitReport | MalformedRender:
    """Write each section of `rendered` to the pool file its marker names, where the text differs.

    A malformed file writes nothing. A marker names a file; a file name is never parsed.
    """

    parsed = _sections(rendered.read_bytes().decode("utf-8"))
    if isinstance(parsed, MalformedRender):
        return parsed
    pool = read_pool(root)
    seen: set[Marker] = set()
    targets: list[tuple[PoolFile, str]] = []
    for section in parsed:
        line = marker(section.marker.rule, section.marker.variant)
        if section.marker in seen:
            return MalformedRender(f"the marker `{line}` appears twice")
        seen.add(section.marker)
        source = _source(pool, section.marker)
        if source is None:
            return MalformedRender(f"the marker `{line}` names a file the pool does not hold")
        targets.append((source, section.body))
    written = []
    for source, body in targets:
        if source.text != body:
            source.path.write_bytes(body.encode("utf-8"))
            written.append(source.path)
    return SplitReport(tuple(written))
