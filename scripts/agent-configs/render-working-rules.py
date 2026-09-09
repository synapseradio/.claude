#!/usr/bin/env python3.14
"""Render `references/working-rules.md` from `CLAUDE.md` and the always-on
rules, and split that render back into those sources in the other direction.

That render and those sources are two forms of one text, and this script
moves between them. With no argument it writes the render from the sources.
With `--reverse` it splits the render back into `CLAUDE.md` and the rules
files, writing no other output. One run moves text one way, and each
direction reproduces the other's input byte for byte.

Both directions read tag-form sources: `CLAUDE.md` opens on `<hello`, and
each rules file carries one `<rule name="stem">` element whose name is the
filename. A source in any other form stops the run before it writes.

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

RULE_OPEN = re.compile(r'<rule name="([^"]+)">')
RULE_CLOSE = "</rule>"


@dataclasses.dataclass(frozen=True)
class RuleSection:
    """One `<rule>` element of the render, named by its `name` attribute.

    `text` carries the wrapper tags, so the section is what its rules file
    holds and nothing has to be rebuilt on the way in either direction.
    """

    name: str
    text: str


@dataclasses.dataclass(frozen=True)
class Reference:
    """`references/working-rules.md` split at its tag boundaries.

    `preamble` is what sits between the title and the first rule, which is
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


def parse_reference(text: str) -> Reference:
    """Split the render into its preamble and one section per rule.

    A `<rule>` tag inside a fenced block is a template a model copies, so
    only a tag outside every fence bounds a section.

    Raises ValueError where the document opens on something other than the
    title, where a rule never closes, where nothing precedes the first rule,
    or where a line sits outside every rule, since each of those would move
    text into a source file or drop it from one.
    """

    lines = text.split("\n")
    if lines[0] != TITLE:
        raise ValueError(f"the render must open on {TITLE!r}, not {lines[0]!r}")

    preamble: list[str] = []
    sections: list[RuleSection] = []
    body: list[str] = []
    open_name: str | None = None
    fence: str | None = None

    for line in lines[1:]:
        fence = _fence_after(line, fence)
        opening = RULE_OPEN.fullmatch(line) if fence is None else None
        if opening is not None:
            if open_name is not None:
                raise ValueError(f"rule {open_name!r} never closes before {opening.group(1)!r}")
            open_name = opening.group(1)
            body = [line]
            continue
        if open_name is None:
            if sections and line.strip():
                raise ValueError(f"this line sits outside every rule: {line!r}")
            preamble.append(line)
            continue
        body.append(line)
        if fence is None and line == RULE_CLOSE:
            sections.append(RuleSection(name=open_name, text="\n".join(body)))
            open_name = None

    if open_name is not None:
        raise ValueError(f"rule {open_name!r} never closes")

    joined = "\n".join(preamble).strip("\n")
    if not joined:
        raise ValueError("the render carries no preamble between its title and its first rule")
    return Reference(preamble=joined, rules=tuple(sections))


PREAMBLE_OPEN = "<hello"


def _rule_form_fault(path: Path, body: str) -> str | None:
    """Whatever stops a rules file body from being one `<rule>` element."""

    lines = body.split("\n")
    opening = RULE_OPEN.fullmatch(lines[0])
    if opening is None or lines[-1] != RULE_CLOSE:
        return f"{path} carries no <rule> element"
    if opening.group(1) != path.stem:
        return f"{path} names itself {opening.group(1)!r}"
    return None


def build_working_rules(claude_md: Path, rules_dir: Path, order: tuple[str, ...]) -> str:
    """CLAUDE.md and the always-on rules as one document under its title.

    Raises ValueError naming every source that is not tag form, so a run
    against sources the reverse direction has not reached yet stops before
    `apply_plan` writes anything.
    """

    preamble = parse_document(claude_md.read_text(encoding="utf-8")).body.strip("\n")
    faults = (
        []
        if preamble.startswith(PREAMBLE_OPEN)
        else [f"{claude_md} does not open on {PREAMBLE_OPEN!r}"]
    )
    sections = [preamble]
    for rule in ordered_rules(rules_dir, order):
        body = parse_document(rule.read_text(encoding="utf-8")).body.strip("\n")
        fault = _rule_form_fault(rule, body)
        if fault is not None:
            faults.append(fault)
        sections.append(body)

    if faults:
        raise ValueError(
            "the render reads tag-form sources, and these are not: " + "; ".join(faults)
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
