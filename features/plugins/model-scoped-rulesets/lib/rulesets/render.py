#!/usr/bin/env python3.14
"""Render `renders/$tier/working-rules.md` from `CLAUDE.md` and the always-on
bodies under the corpus's `$tier/`, and split that render back into those
sources in the other direction.

That render and those sources are two forms of one text, and this module
moves between them. With no argument it writes one render per tier the
manifest names, and `--model` scopes that to the tier it names. With
`--reverse` it splits the default tier's render back into `CLAUDE.md` and the
bodies under the corpus's `default/`, writing no other output. One run moves
text one way, and each direction reproduces the other's input byte for byte.

A rule marker, `<!-- rule: stem -->`, is what bounds a section, and the stem
is the filename. A body may carry its own marker as its first line or carry
none, in which case this derives it; either way the render carries one per
section. A body naming a stem other than its own, carrying a second marker,
or carrying one below its first line stops the run, as does a `CLAUDE.md`
carrying any marker at all, since the preamble is what sits above the first
one. A reverse run writes each body back in the form that body already has,
so neither direction changes which of the two a file uses.

A write, in either direction, refuses where a file it would write carries
changes git has not seen, naming each one. Commit those changes and run
again. No flag overrides that refusal. `--check` builds the same plan and
reports drift without writing, so it carries no refusal of its own: reading
what is on disk risks nothing a commit could lose.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
from collections.abc import Sequence

from . import resolve
from .documents import (
    GeneratedFile,
    parse_document,
    refuse_uncommitted,
    restore_paths,
    rewrite_paths,
    summarize,
    unconditional_rules,
    write_or_check,
)

TITLE = "# Working Rules"

DEFAULT_TIER = "default"

# The stem charset is narrow on purpose: a marker has to name a filename and
# nothing else, so a line of prose reading `<!-- rule: this and that -->`
# stays content rather than opening a section nobody meant to open.
RULE_MARKER = re.compile(r"<!-- rule: ([a-z0-9]+(?:-[a-z0-9]+)*) -->")


def marker_line(stem: str) -> str:
    """The line that opens a rule body, naming the stem it carries.

    The delivered text and the render read this from one definition, so a
    reader telling one rule from the next sees the same line in both and
    `resolve.naming_line` calls through to here.
    """

    return f"<!-- rule: {stem} -->"


@dataclasses.dataclass(frozen=True)
class RuleSection:
    """One marked section of the render, named by the stem in its marker.

    `text` carries the marker, so the section is what its rules file holds
    and nothing has to be rebuilt on the way in either direction.
    """

    name: str
    text: str


@dataclasses.dataclass(frozen=True)
class Reference:
    """One tier's render split at its rule markers.

    `preamble` is what sits between the title and the first marker, which is
    what `CLAUDE.md` holds. The title belongs to the render alone.
    """

    preamble: str
    rules: tuple[RuleSection, ...]


@dataclasses.dataclass(frozen=True)
class RenderTargets:
    """The two roots a render run reads from and writes to.

    `config_root` holds `CLAUDE.md` and is the repository the refusal reads
    git status in. `corpus_root` holds one directory per tier, the manifest
    stating the order, and the renders, so the whole of one corpus moves as
    one directory and a render always sits beside the bodies it was built
    from. `order` overrides what the manifest states, which is what lets a
    caller render an order it holds in memory.
    """

    config_root: pathlib.Path
    corpus_root: pathlib.Path
    order: tuple[str, ...] | None = None
    tier: str = DEFAULT_TIER

    @property
    def claude_md(self) -> pathlib.Path:
        return self.config_root / "CLAUDE.md"

    @property
    def tier_dir(self) -> pathlib.Path:
        return self.corpus_root / self.tier

    @property
    def render_path(self) -> pathlib.Path:
        return self.corpus_root / "renders" / self.tier / "working-rules.md"

    def for_tier(self, tier: str) -> RenderTargets:
        """The same roots, reading and writing one other tier's files.

        The tier directory and the render both carry the tier's name, so they
        move together and neither can name a tier the other does not.
        """

        return dataclasses.replace(self, tier=tier)


def default_targets() -> RenderTargets:
    """The roots a run with no argument uses.

    Both are where a session's hooks read them from, so a run with no flags
    renders the corpus that is live. A run over a checkout names that
    checkout with `--root` and `--config-root`, since the `CLAUDE.md` a
    render carries is the one beside the bodies it renders.
    """

    return RenderTargets(
        config_root=resolve.config_root(),
        corpus_root=resolve.rulesets_root(),
    )


def _fence_after(line: str, fence: str | None) -> str | None:
    """The fence state a line leaves behind, given the state it met."""

    stripped = line.lstrip()
    if fence is None:
        return stripped[:3] if stripped.startswith(("```", "~~~")) else None
    return None if stripped.startswith(fence) else fence


def _markers_outside_fences(text: str) -> tuple[tuple[tuple[int, str], ...], str | None]:
    """Every rule marker outside a fence, and the fence left open at the end.

    A marker inside a fenced block is a template a model copies, so only a
    marker outside every fence bounds a section. `_fence_after` returns the
    token on an opening line and None on a closing line, so a fence line can
    never also read as a marker.

    The render splitter and the source validator both walk through here, so
    what counts as a marker is decided once and the two cannot disagree.
    Matching is `fullmatch` against a whole line, which is what makes column
    0 and own-line true of every marker either of them sees.
    """

    markers: list[tuple[int, str]] = []
    fence: str | None = None
    for index, line in enumerate(text.split("\n")):
        fence = _fence_after(line, fence)
        if fence is not None:
            continue
        found = RULE_MARKER.fullmatch(line)
        if found is not None:
            markers.append((index, found.group(1)))
    return tuple(markers), fence


def _repeated(stems: tuple[str, ...]) -> list[str]:
    return sorted({stem for stem in stems if stems.count(stem) > 1})


def parse_reference(text: str) -> Reference:
    """Split the render into its preamble and one section per rule.

    A section opens on its marker and closes at the next marker or at the end
    of the document, so every line after a marker belongs to the section
    above it.

    Raises ValueError where the document opens on something other than the
    title, where nothing precedes the first marker, where a fence never
    closes, or where two sections carry one stem, since each of those would
    move text into the wrong source file or drop it from one.
    """

    lines = text.split("\n")
    if lines[0] != TITLE:
        raise ValueError(f"the render must open on {TITLE!r}, not {lines[0]!r}")

    markers, unclosed = _markers_outside_fences(text)
    if unclosed is not None:
        raise ValueError(
            f"a {unclosed} fence never closes, so every rule marker below it reads as content"
        )

    repeated = _repeated(tuple(stem for _, stem in markers))
    if repeated:
        raise ValueError(f"the render marks these rules more than once: {repeated}")

    first = markers[0][0] if markers else len(lines)
    preamble = "\n".join(lines[1:first]).strip("\n")
    if not preamble:
        raise ValueError("the render carries no preamble between its title and its first rule")

    # One bound per marker plus the end of the document, so each section reads
    # from its own marker to the next bound. A document carrying no marker
    # yields no section and never indexes past the one bound it has.
    bounds = [start for start, _ in markers] + [len(lines)]
    sections = tuple(
        RuleSection(
            name=stem,
            text="\n".join(lines[bounds[position] : bounds[position + 1]]).strip("\n"),
        )
        for position, (_, stem) in enumerate(markers)
    )
    return Reference(preamble=preamble, rules=sections)


def _rule_form_fault(path: pathlib.Path, body: str) -> str | None:
    """Whatever stops a rules file body from being one marked section.

    A body carrying no marker is one section already, since the marker names
    the filename and `marked` derives it. A marker below the first line is
    the one placement that is neither form: the lines above it would join the
    section before this one.
    """

    markers, unclosed = _markers_outside_fences(body)
    if unclosed is not None:
        return f"{path} leaves a {unclosed} fence open"
    if not markers:
        return None
    if markers[0][0] != 0:
        return f"{path} carries a rule marker below its first line, naming {markers[0][1]!r}"
    if markers[0][1] != path.stem:
        return f"{path} names itself {markers[0][1]!r}"
    if len(markers) > 1:
        return f"{path} carries a second rule marker, naming {markers[1][1]!r}"
    return None


def marked(stem: str, body: str) -> str:
    """One body's text, opening on its own rule marker.

    A body already opening on that marker is returned unchanged, so the
    render carries what the file holds down to the byte. A body carrying
    none gets one, which is what makes the marker a form a corpus may use
    rather than one it must.
    """

    if body.split("\n", 1)[0] == marker_line(stem):
        return body
    return f"{marker_line(stem)}\n\n{body}"


def unmarked(section: str) -> str:
    """One section's text without its opening marker line.

    A reverse run writes a body back in the form that body already has, so a
    file that carries no marker keeps carrying none and the forward run that
    follows derives the same section again.
    """

    _, _, rest = section.partition("\n")
    return rest.lstrip("\n")


def _preamble_fault(path: pathlib.Path, body: str) -> str | None:
    """Whatever stops `CLAUDE.md` from being the render's preamble.

    The preamble is what sits above the first marker, so a marker anywhere
    inside it would open a section the reverse direction writes into a rules
    file, and `CLAUDE.md` would lose every line below that marker.
    """

    markers, unclosed = _markers_outside_fences(body)
    if unclosed is not None:
        return f"{path} leaves a {unclosed} fence open"
    if markers:
        return f"{path} carries a rule marker, naming {markers[0][1]!r}"
    return None


def build_working_rules(claude_md: pathlib.Path, body_paths: Sequence[pathlib.Path]) -> str:
    """CLAUDE.md and the given bodies as one document under its title.

    Takes the bodies already resolved and ordered, rather than a directory to
    read them from, because a tier's bodies do not all live in one directory:
    delivery composes a tier from its own files falling back to the default
    tier's, and the render is the view of what delivery reads.

    Raises ValueError naming every source no section can be built from, so a
    run against such a source stops before anything is written. Two sections
    of one render cannot carry one stem, since the caller names each stem
    once and no body may mark itself with another's name.
    """

    preamble = parse_document(claude_md.read_text(encoding="utf-8")).body.strip("\n")
    fault = _preamble_fault(claude_md, preamble)
    faults = [] if fault is None else [fault]
    sections = [preamble]
    for rule in body_paths:
        body = parse_document(rule.read_text(encoding="utf-8")).body.strip("\n")
        fault = _rule_form_fault(rule, body)
        if fault is not None:
            faults.append(fault)
        sections.append(marked(rule.stem, body))

    if faults:
        raise ValueError(
            "the render reads marker-form sources, and these are not: " + "; ".join(faults)
        )
    return rewrite_paths(f"{TITLE}\n\n" + "\n\n".join(sections) + "\n")


def _carries_frontmatter(path: pathlib.Path) -> bool:
    return (
        path.is_file() and parse_document(path.read_text(encoding="utf-8")).frontmatter is not None
    )


def tiers_to_render(corpus_root: pathlib.Path) -> tuple[str, ...]:
    """Every tier the manifest names whose directory the corpus holds.

    The manifest is what admits a tier, so a directory beside the tiers is
    never read as one and a tier the manifest names but no directory backs
    contributes no render.
    """

    return tuple(tier for tier in resolve.all_tiers(corpus_root) if (corpus_root / tier).is_dir())


def corpus_order(targets: RenderTargets) -> tuple[str, ...]:
    """The order the corpus states, or its default tier's stems sorted.

    The order is the sequence a reader meets the rules in, which belongs to
    whoever wrote them, so it is stated in the corpus and not here. A corpus
    stating none renders sorted, which is the order delivery composes in, so
    a fresh corpus renders without anyone writing a list first.
    """

    if targets.order is not None:
        return targets.order
    stated = resolve.load_order(targets.corpus_root)
    if stated is not None:
        return stated
    default_dir = targets.corpus_root / DEFAULT_TIER
    if not default_dir.is_dir():
        return ()
    return tuple(sorted(rule.stem for rule in unconditional_rules(default_dir)))


def tier_order(targets: RenderTargets) -> tuple[str, ...]:
    """The order this tier's render follows.

    Every tier follows the corpus order, less the stems it does not deliver:
    those its manifest entry leaves out, and those it composes but nothing
    resolves, which `compose` reports as a `no-body` finding rather than
    rendered empty. A stem the tier holds no body for still renders, from
    the default tier's file.
    """

    resolved = resolved_bodies(targets)
    return tuple(stem for stem in corpus_order(targets) if stem in resolved)


def resolved_bodies(targets: RenderTargets) -> dict[str, pathlib.Path]:
    """Each stem this tier delivers, mapped to the file it resolves to.

    `resolve.compose` decides that mapping wherever the corpus states a
    manifest, even one composing nothing for this tier. A corpus stating
    none still renders, so this function applies the same tier-then-default
    fallback itself.
    """

    composition = _composition(targets)
    if composition is not None:
        return dict(composition.body_paths)

    resolved: dict[str, pathlib.Path] = {}
    for stem in corpus_order(targets):
        own = targets.corpus_root / targets.tier / f"{stem}.md"
        fallback = targets.corpus_root / DEFAULT_TIER / f"{stem}.md"
        if own.is_file():
            resolved[stem] = own
        elif fallback.is_file():
            resolved[stem] = fallback
    return resolved


def expected_stems(targets: RenderTargets) -> tuple[str, ...]:
    """Each stem this tier must resolve to a body.

    Where the corpus states a manifest, this is the tier's composition,
    which already leaves out what the tier's entry excludes. Where it states
    none, this is every stem the order names, matching the fallback in
    `resolved_bodies`.
    """

    composition = _composition(targets)
    if composition is not None:
        return composition.stems
    return corpus_order(targets)


def _composition(targets: RenderTargets) -> resolve.Composition | None:
    """This tier's composition, or None where the corpus states no manifest.

    `compose` answers a missing or unparseable manifest with a `manifest`
    finding and no stems. A tier that excludes every stem also yields no
    stems, so the finding, not the empty result, tells the two apart.
    """

    composition = resolve.compose(targets.tier, targets.corpus_root)
    if any(finding.kind == "manifest" for finding in composition.findings):
        return None
    return composition


def _tier_body_paths(targets: RenderTargets) -> tuple[pathlib.Path, ...]:
    """Each body this tier delivers, in corpus order, wherever it lives.

    The render reads the resolution rather than a directory. That is what
    makes it the view of what the tier reads instead of a view of what its
    directory happens to hold.
    """

    order = corpus_order(targets)
    resolved = resolved_bodies(targets)

    # The guard `ordered_rules` gave when the render read one directory: a
    # body whose stem the order does not name renders nowhere, and silently,
    # so a rule added without a line in the order list would just not arrive.
    # Composition moved the read off a single directory, so the check now
    # covers both directories a tier resolves across.
    directories = {targets.tier_dir, targets.corpus_root / DEFAULT_TIER}
    held = {
        rule.stem for path in directories if path.is_dir() for rule in unconditional_rules(path)
    }
    unlisted = sorted(held - set(order))
    # A stem is absent where the tier composes it and nothing resolves it, so
    # the composition, not the order, decides which stems need a body.
    expected = set(expected_stems(targets))
    absent = [stem for stem in order if stem in expected and stem not in resolved]
    if unlisted or absent:
        raise ValueError(
            f"working rules order disagrees with {targets.tier_dir}: "
            f"unlisted {unlisted}, absent {absent}"
        )

    return tuple(resolved[stem] for stem in tier_order(targets))


def _tier_file(targets: RenderTargets) -> GeneratedFile:
    """The one generated file a tier's composed bodies render to."""

    content = build_working_rules(targets.claude_md, _tier_body_paths(targets))
    return GeneratedFile(targets.render_path, content)


def build_one_tier(targets: RenderTargets, *, check: bool = False) -> tuple[GeneratedFile, ...]:
    """The render for the one tier `targets` names, and no other."""

    files = (_tier_file(targets),)
    if not check:
        refuse_uncommitted(targets.config_root, [targets.render_path])
    return files


def build_forward_plan(targets: RenderTargets, *, check: bool = False) -> tuple[GeneratedFile, ...]:
    """One render per tier, each from that tier's own bodies.

    A model reads its own rules, so the render showing what it reads carries
    its tier's name. A run covers every tier the corpus holds a directory
    for unless the caller scoped it to one.

    The refusal below guards the write, so `check=True` builds the same
    files drift is reported from, and skips it: a run that only reads risks
    nothing a commit could lose.
    """

    files = tuple(
        _tier_file(targets.for_tier(tier)) for tier in tiers_to_render(targets.corpus_root)
    )

    if not check:
        refuse_uncommitted(targets.config_root, [generated.path for generated in files])
    return files


def build_reverse_plan(targets: RenderTargets, *, check: bool = False) -> tuple[GeneratedFile, ...]:
    """Every source file a run in the reverse direction would write.

    The render is the form the user edits, and this carries those edits back
    into `CLAUDE.md` and the rules files it was rendered from.

    Raises ValueError where the render's rules and the order disagree, so a
    rule added to the render lands its stem in the order in the same change,
    and where a rule resolves to a file carrying frontmatter, since that
    frontmatter is what scopes a rule to its paths.

    The refusal below guards the write, so `check=True` builds the same
    files drift is reported from, and skips it.
    """

    reference = parse_reference(targets.render_path.read_text(encoding="utf-8"))
    named = tuple(section.name for section in reference.rules)
    order = corpus_order(targets)
    if named != order:
        raise ValueError(
            f"the render's rules disagree with the order: render {list(named)}, order {list(order)}"
        )

    files = [GeneratedFile(targets.claude_md, restore_paths(reference.preamble) + "\n")]
    for section in reference.rules:
        path = targets.tier_dir / f"{section.name}.md"
        if _carries_frontmatter(path):
            raise ValueError(f"{path} carries frontmatter, which scopes it to its own paths")
        files.append(GeneratedFile(path, restore_paths(_as_held(path, section)) + "\n"))

    if not check:
        refuse_uncommitted(targets.config_root, [generated.path for generated in files])
    return tuple(files)


def _as_held(path: pathlib.Path, section: RuleSection) -> str:
    """One section's text in the form the file it writes to already holds."""

    if not path.is_file():
        return section.text
    held = parse_document(path.read_text(encoding="utf-8")).body.strip("\n")
    if held.split("\n", 1)[0] == marker_line(section.name):
        return section.text
    return unmarked(section.text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit nonzero when the render disagrees with its sources",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="split the render back into CLAUDE.md and the rules files, writing no other output",
    )
    parser.add_argument(
        "--model",
        help="render this tier's file alone, named for its directory under the corpus",
    )
    parser.add_argument("--root", default=None, help="an alternate rulesets root")
    parser.add_argument(
        "--config-root",
        default=None,
        help="the directory holding the CLAUDE.md to render, and the repository to check",
    )
    return parser


def main(argv: list[str] | None = None, targets: RenderTargets | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.reverse and args.model:
        parser.error(
            "--reverse runs on the default tier's render, whose directory holds every "
            "always-on body. Which sections another tier's render writes back is undecided."
        )
    targets = default_targets() if targets is None else targets
    if args.root:
        targets = dataclasses.replace(targets, corpus_root=pathlib.Path(args.root))
    if args.config_root:
        targets = dataclasses.replace(targets, config_root=pathlib.Path(args.config_root))

    if args.model:
        held = tiers_to_render(targets.corpus_root)
        if args.model not in held:
            parser.error(f"{args.model!r} names no tier directory under the corpus: {held}")
        files = build_one_tier(targets.for_tier(args.model), check=args.check)
    elif args.reverse:
        files = build_reverse_plan(targets, check=args.check)
    else:
        files = build_forward_plan(targets, check=args.check)

    stale = write_or_check(files, check=args.check)
    return summarize(stale, len(files), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
