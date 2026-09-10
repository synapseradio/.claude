#!/usr/bin/env python3.14
"""Render `references/$model/working-rules.md` from `CLAUDE.md` and the
always-on bodies under `rulesets/$model/`, and split that render back into
those sources in the other direction.

That render and those sources are two forms of one text, and this script
moves between them. With no argument it writes one render per model
directory, and `--model` scopes that to the model it names. With `--reverse`
it splits the default model's render back into `CLAUDE.md` and the bodies
under `rulesets/default/`, writing no other output. One run moves text one
way, and each direction reproduces the other's input byte for byte.

Both directions read marker-form sources: each rules file opens on
`<!-- rule: stem -->`, where the stem is the filename, and carries no second
marker, while `CLAUDE.md` is the preamble and so carries none at all. A
source in any other form stops the run before it writes.

A write, in either direction, refuses where a file it would write carries
changes git has not seen, naming each one. Commit those changes and run
again. No flag overrides that refusal. `--check` builds the same plan and
reports drift without writing, so it carries no refusal of its own: reading
what is on disk risks nothing a commit could lose.
"""

from __future__ import annotations

import argparse
import dataclasses
import re
from pathlib import Path

from projection import (
    DEFAULT_MODEL,
    DEFAULT_TARGETS,
    GeneratedFile,
    Plan,
    Targets,
    all_rules,
    apply_plan,
    model_names,
    ordered_rules,
    parse_document,
    refuse_uncommitted,
    restore_paths,
    rewrite_paths,
)

# The default this module is named for lives in the library, since `Targets`
# needs it and the library cannot import a job without a cycle. Carrying the
# name here, by importing it back under its own name, keeps one tuple rather
# than a second copy that could drift from the first.
from projection import WORKING_RULES_ORDER as WORKING_RULES_ORDER

TITLE = "# Working Rules"

# The stem charset is narrow on purpose: a marker has to name a filename and
# nothing else, so a line of prose reading `<!-- rule: this and that -->`
# stays content rather than opening a section nobody meant to open.
RULE_MARKER = re.compile(r"<!-- rule: ([a-z0-9]+(?:-[a-z0-9]+)*) -->")


def marker_line(stem: str) -> str:
    """The line that opens a rule body, naming the stem it carries."""

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
    """One model's render split at its rule markers.

    `preamble` is what sits between the title and the first marker, which is
    what `CLAUDE.md` holds. The title belongs to the render alone.
    """

    preamble: str
    rules: tuple[RuleSection, ...]


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


def _rule_form_fault(path: Path, body: str) -> str | None:
    """Whatever stops a rules file body from being one marked section."""

    markers, unclosed = _markers_outside_fences(body)
    if unclosed is not None:
        return f"{path} leaves a {unclosed} fence open"
    if not markers or markers[0][0] != 0:
        return f"{path} does not open on its rule marker"
    if markers[0][1] != path.stem:
        return f"{path} names itself {markers[0][1]!r}"
    if len(markers) > 1:
        return f"{path} carries a second rule marker, naming {markers[1][1]!r}"
    return None


def _preamble_fault(path: Path, body: str) -> str | None:
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


def build_working_rules(claude_md: Path, rules_dir: Path, order: tuple[str, ...]) -> str:
    """CLAUDE.md and the always-on rules as one document under its title.

    Raises ValueError naming every source that is not marker form, so a run
    against sources the reverse direction has not reached yet stops before
    `apply_plan` writes anything. Two sections of one render cannot carry one
    stem from here, since `ordered_rules` names each stem once and each body
    has to mark itself with its own filename.
    """

    preamble = parse_document(claude_md.read_text(encoding="utf-8")).body.strip("\n")
    fault = _preamble_fault(claude_md, preamble)
    faults = [] if fault is None else [fault]
    sections = [preamble]
    for rule in ordered_rules(rules_dir, order):
        body = parse_document(rule.read_text(encoding="utf-8")).body.strip("\n")
        fault = _rule_form_fault(rule, body)
        if fault is not None:
            faults.append(fault)
        sections.append(body)

    if faults:
        raise ValueError(
            "the render reads marker-form sources, and these are not: " + "; ".join(faults)
        )
    return rewrite_paths(f"{TITLE}\n\n" + "\n\n".join(sections) + "\n")


def _carries_frontmatter(path: Path) -> bool:
    return (
        path.is_file() and parse_document(path.read_text(encoding="utf-8")).frontmatter is not None
    )


def model_order(targets: Targets) -> tuple[str, ...]:
    """The order this model's render follows.

    The default model's directory holds every always-on body, so its render
    follows the whole order and a stem with no file there stops the run.
    Another model's directory holds the bodies that model overrides, so its
    render follows the part of the order it holds, and delivery resolves
    every other stem to the default model's file.
    """

    if targets.model == DEFAULT_MODEL:
        return targets.working_rules_order
    held = {rule.stem for rule in all_rules(targets.rules_dir)}
    return tuple(stem for stem in targets.working_rules_order if stem in held)


def build_one_model(targets: Targets, *, check: bool = False) -> Plan:
    """The render for the one model `targets` names, and no other."""

    content = build_working_rules(targets.claude_md, targets.rules_dir, model_order(targets))
    if not check:
        refuse_uncommitted(targets.claude_home, [targets.working_rules])
    return Plan(files=(GeneratedFile(targets.working_rules, content),), keys=(), dropped=())


def build_forward_plan(targets: Targets = DEFAULT_TARGETS, *, check: bool = False) -> Plan:
    """One render per model, each from that model's own bodies.

    A model reads its own rules, so the reference showing what it reads
    carries its name. `targets` names one model, and a run covers every
    model the rulesets root holds a directory for unless the caller scoped
    it to one.

    The refusal below guards the write, so `check=True` builds the same
    plan `apply_plan` reports drift from, and skips it: a run that only
    reads risks nothing a commit could lose.
    """

    files = []
    for model in model_names(targets.claude_home, targets.rulesets_dirname):
        scoped = targets.for_model(model)
        content = build_working_rules(scoped.claude_md, scoped.rules_dir, model_order(scoped))
        files.append(GeneratedFile(scoped.working_rules, content))

    if not check:
        refuse_uncommitted(targets.claude_home, [generated.path for generated in files])
    return Plan(files=tuple(files), keys=(), dropped=())


def build_reverse_plan(targets: Targets = DEFAULT_TARGETS, *, check: bool = False) -> Plan:
    """Every source file a run in the reverse direction would write.

    The render is the form the user edits, and this carries those edits back
    into `CLAUDE.md` and the rules files it was rendered from.

    Raises ValueError where the render's rules and `working_rules_order`
    disagree, so a rule added to the render lands its stem in the order in
    the same change, and where a rule resolves to a file carrying
    frontmatter, since that frontmatter is what scopes a rule to its paths.

    The refusal below guards the write, so `check=True` builds the same
    plan `apply_plan` reports drift from, and skips it.
    """

    reference = parse_reference(targets.working_rules.read_text(encoding="utf-8"))
    named = tuple(section.name for section in reference.rules)
    if named != targets.working_rules_order:
        raise ValueError(
            f"the render's rules disagree with the order: render {list(named)}, "
            f"order {list(targets.working_rules_order)}"
        )

    files = [GeneratedFile(targets.claude_md, restore_paths(reference.preamble) + "\n")]
    for section in reference.rules:
        path = targets.rules_dir / f"{section.name}.md"
        if _carries_frontmatter(path):
            raise ValueError(f"{path} carries frontmatter, which scopes it to its own paths")
        files.append(GeneratedFile(path, restore_paths(section.text) + "\n"))

    if not check:
        refuse_uncommitted(targets.claude_home, [generated.path for generated in files])
    return Plan(files=tuple(files), keys=(), dropped=())


def main(argv: list[str] | None = None, targets: Targets = DEFAULT_TARGETS) -> int:
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
        help="render this model's reference file alone, named for its rulesets directory",
    )
    args = parser.parse_args(argv)
    if args.reverse and args.model:
        parser.error(
            "--reverse runs on the default model's render, whose directory holds every "
            "always-on body. Which sections another model's render writes back is undecided."
        )
    if args.model:
        held = model_names(targets.claude_home, targets.rulesets_dirname)
        if args.model not in held:
            parser.error(f"{args.model!r} names no directory under the rulesets root: {held}")
        return apply_plan(
            build_one_model(targets.for_model(args.model), check=args.check), check=args.check
        )

    build = build_reverse_plan if args.reverse else build_forward_plan
    return apply_plan(build(targets, check=args.check), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
