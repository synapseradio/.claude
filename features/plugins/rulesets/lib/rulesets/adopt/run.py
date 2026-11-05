"""Adopt end to end: a source mapped to a rulesets directory in an empty output directory, then compared."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Collection

from rulesets.adopt.agent_exclusions import exclusion_blocks, read_definitions
from rulesets.adopt.manifest_text import manifest_text
from rulesets.adopt.mapping import map_source
from rulesets.adopt.skipped import Skipped
from rulesets.adopt.source import read_source
from rulesets.adopt.tier_corpus import SourceError, TierCorpus
from rulesets.compare.run import CompareReport, compare
from rulesets.locations import Locations
from rulesets.render.tree import render_tree
from rulesets.render.tree_writer import write_tree
from rulesets.source.directory import read_directory
from rulesets.source.manifest import MANIFEST_FILE
from rulesets.source.pool import RENDER_DIRECTORY

_POOL_FOLDER = "rules"


@dataclasses.dataclass(frozen=True)
class Refused:
    """Adopt wrote nothing."""

    reason: str


@dataclasses.dataclass(frozen=True)
class Adopted:
    skipped: tuple[Skipped, ...]
    comparison: CompareReport


def _refusal(source: pathlib.Path, out: pathlib.Path) -> str | None:
    """Why `out` cannot take the output: it is the source, lies inside it, or already holds files."""

    resolved_source, resolved_out = source.resolve(), out.resolve()
    if resolved_out == resolved_source or resolved_out.is_relative_to(resolved_source):
        return f"the output directory {out} is the source or lies inside it"
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        return f"the output directory {out} already holds files"
    return None


def adopt(
    source: pathlib.Path, out: pathlib.Path, expect: Collection[str], locations: Locations
) -> Adopted | Refused:
    """Write the pool, the manifest, and the render tree into `out`, then compare every context.

    The source and the agent definitions are read and never written.
    """

    if (reason := _refusal(source, out)) is not None:
        return Refused(reason)
    try:
        read = read_source(source)
    except SourceError as failure:
        return Refused(str(failure))

    adopted = map_source(read)
    blocks = adopted.blocks
    if isinstance(read, TierCorpus):
        definitions = read_definitions(locations.config / "agents")
        blocks += exclusion_blocks(definitions, adopted.rule_names())

    (out / _POOL_FOLDER).mkdir(parents=True)
    for name, path in adopted.pool.items():
        (out / _POOL_FOLDER / name).write_bytes(path.read_bytes())
    (out / MANIFEST_FILE).write_text(manifest_text(adopted.models, blocks), encoding="utf-8")
    write_tree(out / RENDER_DIRECTORY, render_tree(read_directory(out)))

    return Adopted(adopted.skipped, compare(source, out, expect, locations))
