#!/usr/bin/env python3.14
"""Regression checker for the SudoLang ontology under rules/ and agents/.

Reads every file under rules/ and agents/ as one set of SudoLang v2
interfaces, splits each into statements, and reports any statement that
reintroduces an inconsistency the ontology settled: a trigger block named
anything but AppliesWhen, a pointer that resolves to no node or stands
mid-sentence, a prose pointer (`under X`, `per X`, `X applies`) where
`via(X)` is the form, a prohibition in a spelling other than `require you
never` or `require no`, a match head carrying an annotation or no braces,
two sentences in one statement, a demand outside a constraint or fn, a
numbered block, a name of another file's node, a duplicated name, an agent
whose closing Constraints roll call disagrees with its declared
constraints, or a command without an alias.

Usage:
    python3.14 scripts/hooks/check-rules-ontology.py            # the repo's rules/ and agents/
    python3.14 scripts/hooks/check-rules-ontology.py --root DIR # another tree with the same layout
    python3.14 scripts/hooks/check-rules-ontology.py FILE...    # named files, cross-file rules
                                                                # still read the whole tree

Exit status 0 with no findings, 1 with findings printed one per line as
`path:line: RULE message`, 2 on a usage error. The rule names in the output
are stable identifiers a test can assert on.

Runs as a lefthook pre-commit job (see lefthook.yml) and by hand.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SIDES = ("rules", "agents")

BLOCK_OPEN = re.compile(r"\{\s*$")
LITERAL_OPEN = re.compile(r"\+=\s*\{\s*$")
CLOSER = re.compile(r"^[\]\}\)\,\s]+$")
RE_CONSTRAINT = re.compile(r"^constraint\s+([A-Za-z]\w*)\s*\{")
RE_FN = re.compile(r"^fn\s+([A-Za-z]\w*)\s*(\([^)]*\))?")
RE_NUMBERED = re.compile(r"^(\d+)\.([A-Z]\w*)\s*\{")
RE_PASCAL = re.compile(r"^([A-Z]\w*)\s*\{")
RE_LOWER = re.compile(r"^([a-z]\w*)\s*\{")
RE_COMMAND = re.compile(r"^/([a-z]\w*)(\s*\|\s*(\w+))?")
RE_GUARD = re.compile(r"^(warn\s*)?\(")
RE_VIA = re.compile(r"\bvia\(([^)]*)\)")
RE_RUN = re.compile(r"\brun\(([^)]*)\)")
RE_PASCAL_TOKEN = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+)\b")
RE_NUMBERED_REF = re.compile(r"\b\d+\.[A-Z]\w+")
RE_DOTTED_REF = re.compile(r"\b([A-Z]\w+)\.([a-z]\w*)\b")
RE_PROSE_POINTER = re.compile(
    r"\b(?:under|per)\s+([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+)\b"
    r"|\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+)\s+applies\b"
    r"|\blet\s+([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+)\s+decide\b"
)
RE_MATCH_HEAD = re.compile(r"\bmatch\s*\(")
RE_SENTENCE_JOIN = re.compile(r"(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)(?<!\betc)[a-z)`\"']\.\s+[a-z]")
RE_REQUIRE_OTHER_NEVER = re.compile(r"^require\s+(?!you never\b|no\b|none\b)[^,]*\bnever\b")
RE_NEGATED_IMPERATIVE = re.compile(r"^(?!require\b)[a-z]+\s+(no|none)\s+\w")
RE_APPLIES_BARE = re.compile(r"\bApplies\b(?!When)")

DEMANDS = {
    "guard",
    "require",
    "imperative",
    "match",
    "pipeline",
    "loop",
    "let",
    "skillInvoke",
    "stateAppend",
}
# An assignment names a value (`StreamEditors = [...]`, `manager = ...`) and
# stands at interface level as a definition, so it is no demand.
CONTAINERS_FOR_DEMANDS = {"constraint", "fn"}
DEFINITION_BLOCKS = {"optionsBlock", "stateBlock", "exampleBlock"}


@dataclass
class Statement:
    file: Path
    line: int
    text: str
    construct: str
    name: str
    container: list[tuple[str, str]]
    raw_lines: list[str]

    def inside(self, kind: str) -> bool:
        return any(k == kind for k, _ in self.container)

    @property
    def in_example(self) -> bool:
        return self.inside("exampleBlock")


@dataclass
class Document:
    path: Path
    side: str
    frontmatter: dict[str, str]
    statements: list[Statement]
    interface: str | None = None
    declared: dict[str, str] = field(default_factory=dict)  # name -> kind


@dataclass(frozen=True)
class Finding:
    rule: str
    file: Path
    line: int
    message: str


def classify(text: str, container_kind: str) -> tuple[str, str]:
    """Return (construct, name) for one statement's joined text."""
    t = text.strip()
    if t.startswith("AppliesWhen") and t.rstrip().endswith(("{", "}")):
        return "appliesWhen", ""
    if t.startswith("AppliesWhen {"):
        return "appliesWhen", ""
    m = RE_CONSTRAINT.match(t)
    if m:
        return "constraint", m.group(1)
    if re.match(r"^Constraints\s*\{", t):
        return "constraintsBlock", ""
    m = RE_FN.match(t)
    if m:
        return "fn", m.group(1)
    if re.match(r"^Options\s*\{", t):
        return "optionsBlock", ""
    if re.match(r"^State\s*\{", t):
        return "stateBlock", ""
    if re.match(r"^Example\s*\{", t):
        return "exampleBlock", ""
    m = RE_COMMAND.match(t)
    if m:
        return "command", m.group(1)
    if re.match(r"^test\s*\{", t):
        return "testBlock", ""
    m = RE_NUMBERED.match(t)
    if m:
        return "numberedBlock", m.group(2)
    if RE_GUARD.match(t) and "=>" in t:
        return "guard", ""
    if t.startswith("require"):
        return "require", ""
    if t.startswith("warn"):
        return "guard", ""
    if re.match(r"^(case\b|default\s*(=>|\{))", t):
        return "caseArm", ""
    if re.match(r"^[\w.{}, ]+\s*=\s*match\s*\(", t) or RE_MATCH_HEAD.match(t):
        return "match", ""
    if re.match(r"^(for each|while|loop)\b", t):
        return "loop", ""
    if re.match(r"^[\w.]+\s*\+=\s", t):
        return "stateAppend", ""
    if t.startswith("invoke skill:"):
        return "skillInvoke", ""
    if t.startswith("let "):
        return "let", ""
    m = RE_PASCAL.match(t)
    if m:
        return "pascalBlock", m.group(1)
    m = RE_LOWER.match(t)
    if m:
        return "lowerBlock", m.group(1)
    in_record = container_kind in {"optionsBlock", "stateBlock", "pascalBlock", "lowerBlock"}
    if in_record and (re.match(r"^[\w.]+\s*(:|=)\s", t) or re.match(r"^[\w.]+\s*$", t)):
        return "field", ""
    if re.match(r"^[\w.\[\]{}, ]{1,40}\s=\s(?!=)", t) and not t.startswith(
        ("use ", "set ", "make ")
    ):
        return "assignment", ""
    if re.match(r"^[A-Za-z]\w*\s*:\s", t) and len(t.split(":", 1)[0].split()) == 1:
        return "field", ""
    if "|>" in t and len(t.split("|>")[0].split()) <= 4:
        return "pipeline", ""
    if container_kind == "exampleBlock":
        return "exampleLine", ""
    if container_kind == "appliesWhen":
        return "trigger", ""
    return "imperative", ""


def parse_document(path: Path, side: str) -> Document:
    lines = path.read_text().splitlines()
    frontmatter: dict[str, str] = {}
    i = 0
    if lines and lines[0].strip() == "---":
        j = 1
        while j < len(lines) and lines[j].strip() != "---":
            m = re.match(r"^(\w+):\s*(.*)$", lines[j])
            if m:
                frontmatter[m.group(1)] = m.group(2)
            j += 1
        i = j + 1
    doc = Document(path=path, side=side, frontmatter=frontmatter, statements=[])
    stack: list[tuple[str, str, int]] = []  # kind, name, depthAtOpen
    cur_line = 0
    cur_indent = 0
    cur_lines: list[str] = []
    depth = 0

    def opens_block(line: str) -> bool:
        return (
            bool(BLOCK_OPEN.search(line))
            and line.count("{") > line.count("}")
            and not LITERAL_OPEN.search(line)
        )

    def flush(depth_before: int) -> None:
        nonlocal cur_lines
        if not cur_lines:
            return
        text = " ".join(s.strip() for s in cur_lines)
        container_kind = stack[-1][0] if stack else "<interface>"
        construct, name = classify(text, container_kind)
        if not stack and construct == "pascalBlock":
            construct = "interface"
            doc.interface = name
        st = Statement(
            file=path,
            line=cur_line,
            text=text,
            construct=construct,
            name=name,
            container=[(k, n) for k, n, _ in stack],
            raw_lines=list(cur_lines),
        )
        doc.statements.append(st)
        if opens_block(cur_lines[-1]):
            stack.append((construct, name, depth_before))
        cur_lines = []

    def pop_closed() -> None:
        while stack and depth <= stack[-1][2]:
            stack.pop()

    while i < len(lines):
        raw = lines[i]
        ln = i + 1
        i += 1
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        s = raw.strip()
        before = depth
        depth += raw.count("{") - raw.count("}")
        if s.startswith("}"):
            flush(before)
            pop_closed()
            continue
        if cur_lines and (indent > cur_indent or CLOSER.match(s) or s.startswith("| ")):
            cur_lines.append(raw)
            if opens_block(raw):
                flush(before)
            pop_closed()
            continue
        flush(before)
        cur_line, cur_indent, cur_lines = ln, indent, [raw]
        if opens_block(raw):
            flush(before)
        pop_closed()
    flush(depth)
    for st in doc.statements:
        if (
            st.construct in {"constraint", "fn", "pascalBlock", "lowerBlock", "numberedBlock"}
            and st.name
        ):
            doc.declared.setdefault(st.name, st.construct)
    return doc


# ----------------------------------------------------------------- rules


def rule_trigger(doc: Document) -> list[Finding]:
    """A1: the trigger construct is AppliesWhen, and rules open on it."""
    out = []
    for st in doc.statements:
        if st.in_example:
            continue
        if RE_APPLIES_BARE.search(st.text):
            out.append(
                Finding(
                    "TRIGGER",
                    doc.path,
                    st.line,
                    "names the trigger construct `Applies`; write `AppliesWhen`",
                )
            )
    if doc.side == "rules":
        body = [s for s in doc.statements if s.construct != "interface"]
        if not body or body[0].construct != "appliesWhen":
            line = body[0].line if body else 1
            out.append(
                Finding(
                    "TRIGGER",
                    doc.path,
                    line,
                    "a rules file opens its interface on `AppliesWhen { ... }`",
                )
            )
    return out


def strip_code_spans(text: str) -> str:
    return re.sub(r"`[^`]*`", "", text)


def _targets(expr: str) -> list[str]:
    return [t.strip() for t in expr.split(",") if t.strip()]


def rule_pointer(doc: Document) -> list[Finding]:
    """A2, A3, D4: every via()/run() names a constraint or fn declared in this file."""
    out = []
    for st in doc.statements:
        if st.in_example:
            continue
        text = strip_code_spans(st.text)  # `via(Name)` in backticks quotes the form
        for regex, kind in ((RE_VIA, "via"), (RE_RUN, "run")):
            for m in regex.finditer(text):
                for target in _targets(m.group(1)):
                    declared = doc.declared.get(target)
                    if declared not in CONTAINERS_FOR_DEMANDS:
                        out.append(
                            Finding(
                                "POINTER",
                                doc.path,
                                st.line,
                                f"{kind}({target}) names no constraint or fn declared in this file",
                            )
                        )
    return out


def rule_via_trailing(doc: Document) -> list[Finding]:
    """A4: via(...) closes the line it governs, and never stands as a line of its own."""
    out = []
    for st in doc.statements:
        if st.in_example or "via(" not in st.text:
            continue
        if re.fullmatch(r"(via\([^)]*\)\s*)+", st.text.strip()):
            # a via() line closing a fn or constraint body governs that body
            siblings = [s for s in doc.statements if s.container == st.container]
            closes_body = (
                st.container
                and st.container[-1][0] in CONTAINERS_FOR_DEMANDS
                and siblings[-1] is st
            )
            if not closes_body:
                out.append(
                    Finding(
                        "VIA_TRAILING",
                        doc.path,
                        st.line,
                        "via(...) alone on a line that closes no fn or constraint body; append it to the statement it governs",
                    )
                )
            continue
        for offset, raw in enumerate(st.raw_lines):
            line = strip_code_spans(raw).rstrip()
            if "via(" in line and not re.search(r"via\([^)]*\)(\s+via\([^)]*\))*$", line):
                out.append(
                    Finding(
                        "VIA_TRAILING",
                        doc.path,
                        st.line + offset,
                        "via(...) stands mid-line; move it to the end of the line",
                    )
                )
    return out


def rule_prose_pointer(doc: Document) -> list[Finding]:
    """A3: `under X`, `per X`, `X applies`, `let X decide` on a declared node; write via(X)."""
    out = []
    for st in doc.statements:
        if st.in_example:
            continue
        for m in RE_PROSE_POINTER.finditer(st.text):
            name = next(g for g in m.groups() if g)
            if name in doc.declared:
                out.append(
                    Finding(
                        "PROSE_POINTER",
                        doc.path,
                        st.line,
                        f"points at {name} in prose; write via({name})",
                    )
                )
    return out


def rule_prohibition(doc: Document) -> list[Finding]:
    """A5: a statement-level prohibition reads `require you never ...` or `require no ...`."""
    out = []
    for st in doc.statements:
        if st.in_example or st.construct not in {"require", "imperative", "let"}:
            continue
        t = st.text
        if RE_REQUIRE_OTHER_NEVER.match(t):
            out.append(
                Finding(
                    "PROHIBITION",
                    doc.path,
                    st.line,
                    "`require ... never` without a comma; write `require you never` or `require no`",
                )
            )
        elif RE_NEGATED_IMPERATIVE.match(t):
            out.append(
                Finding(
                    "PROHIBITION",
                    doc.path,
                    st.line,
                    "prohibition in the imperative (`verb no ...`); write `require you never` or `require no`",
                )
            )
    return out


def rule_match_head(doc: Document) -> list[Finding]:
    """A7: a match head is `match (subject) {` and nothing else."""
    out = []
    for st in doc.statements:
        if st.in_example:
            continue
        for m in RE_MATCH_HEAD.finditer(st.text):
            rest = st.text[m.end() - 1 :]
            depth = 0
            end = -1
            for idx, ch in enumerate(rest):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        end = idx
                        break
            after = rest[end + 1 :].strip() if end >= 0 else ""
            if not after.startswith("{"):
                out.append(
                    Finding(
                        "MATCH_HEAD",
                        doc.path,
                        st.line,
                        "match head carries text other than `{` after its subject",
                    )
                )
    return out


def rule_sentence_join(doc: Document) -> list[Finding]:
    """A9: one statement, one sentence."""
    out = []
    for st in doc.statements:
        if st.in_example or st.construct in {"interface", "command"}:
            continue
        if RE_SENTENCE_JOIN.search(st.text):
            out.append(
                Finding(
                    "SENTENCE_JOIN",
                    doc.path,
                    st.line,
                    "two sentences in one statement; give the second its own line",
                )
            )
    return out


def rule_demand_container(doc: Document) -> list[Finding]:
    """B1-B4: every demand sits under a constraint or fn; no numbered block; rules carry no Constraints {."""
    out = []
    for st in doc.statements:
        if st.in_example:
            continue
        if st.construct == "numberedBlock":
            out.append(
                Finding(
                    "DEMAND_CONTAINER",
                    doc.path,
                    st.line,
                    f"numbered block {st.name}; write `constraint {st.name} {{`",
                )
            )
            continue
        if st.construct == "constraintsBlock" and doc.side == "rules":
            out.append(
                Finding(
                    "DEMAND_CONTAINER",
                    doc.path,
                    st.line,
                    "anonymous `Constraints {` in a rules file; name it `constraint X {`",
                )
            )
            continue
        if st.construct not in DEMANDS:
            continue
        kinds = {k for k, _ in st.container}
        if kinds & CONTAINERS_FOR_DEMANDS or kinds & DEFINITION_BLOCKS or "numberedBlock" in kinds:
            continue
        if doc.side == "agents" and ("constraintsBlock" in kinds or st.construct == "imperative"):
            continue
        out.append(
            Finding(
                "DEMAND_CONTAINER",
                doc.path,
                st.line,
                f"{st.construct} outside any constraint or fn",
            )
        )
    return out


def rule_xref(doc: Document, index: dict[str, set[str]]) -> list[Finding]:
    """C1, C2, D3: no statement names a node of another file."""
    out = []
    own = set(doc.declared) | ({doc.interface} if doc.interface else set())
    for st in doc.statements:
        if st.in_example:
            continue
        seen: set[str] = set()
        for m in RE_NUMBERED_REF.finditer(st.text):
            if st.construct == "numberedBlock":
                break
            out.append(
                Finding(
                    "XREF",
                    doc.path,
                    st.line,
                    f"numbered reference `{m.group(0)}`; restate the clause",
                )
            )
        for m in RE_PASCAL_TOKEN.finditer(st.text):
            name = m.group(1)
            if name in own or name in seen or name not in index:
                continue
            seen.add(name)
            others = sorted(index[name] - {doc.path.name})
            if others:
                out.append(
                    Finding(
                        "XREF",
                        doc.path,
                        st.line,
                        f"names `{name}`, a node of {', '.join(others)}; restate the clause",
                    )
                )
        for m in RE_DOTTED_REF.finditer(st.text):
            head = m.group(1)
            if head not in own and head in index:
                out.append(
                    Finding(
                        "XREF",
                        doc.path,
                        st.line,
                        f"names `{m.group(0)}`, a node of another file; restate the clause",
                    )
                )
    return out


def rule_unique_name(docs: list[Document]) -> list[Finding]:
    """D1, D2: names are unique within a file, and interface names across the set."""
    out = []
    interface_owner: dict[str, Path] = {}
    for doc in docs:
        seen: dict[str, int] = {}
        for st in doc.statements:
            if (
                st.construct in {"constraint", "fn", "pascalBlock", "numberedBlock"}
                and st.name
                and not st.in_example
            ):
                if st.name in seen:
                    out.append(
                        Finding(
                            "UNIQUE_NAME",
                            doc.path,
                            st.line,
                            f"`{st.name}` already names a node at line {seen[st.name]}",
                        )
                    )
                else:
                    seen[st.name] = st.line
        if doc.interface:
            if doc.interface in interface_owner:
                out.append(
                    Finding(
                        "UNIQUE_NAME",
                        doc.path,
                        1,
                        f"interface `{doc.interface}` also opens {interface_owner[doc.interface].name}",
                    )
                )
            interface_owner[doc.interface] = doc.path
    for doc in docs:
        for name, kind in doc.declared.items():
            owner = interface_owner.get(name)
            if owner and owner != doc.path:
                line = next(s.line for s in doc.statements if s.name == name)
                out.append(
                    Finding(
                        "UNIQUE_NAME",
                        doc.path,
                        line,
                        f"{kind} `{name}` shares its name with the interface of {owner.name}",
                    )
                )
    return out


def rule_agent_rollcall(doc: Document) -> list[Finding]:
    """E2: an agent's closing Constraints block names exactly its declared constraints."""
    if doc.side != "agents":
        return []
    out = []
    for key in ("name", "description"):
        if not doc.frontmatter.get(key):
            out.append(Finding("AGENT_FRONTMATTER", doc.path, 1, f"frontmatter lacks `{key}`"))
    declared = {s.name for s in doc.statements if s.construct == "constraint" and not s.in_example}
    blocks = [s for s in doc.statements if s.construct == "constraintsBlock"]
    if len(blocks) != 1:
        return [
            *out,
            Finding(
                "AGENT_ROLLCALL",
                doc.path,
                blocks[0].line if blocks else 1,
                "an agent closes with one `Constraints { require ... hold on every turn }` block",
            ),
        ]
    block = blocks[0]
    roll = [
        s.text
        for s in doc.statements
        if ("constraintsBlock", "") in s.container and re.search(r"\bhold on every turn\b", s.text)
    ]
    if not roll:
        return [
            *out,
            Finding(
                "AGENT_ROLLCALL",
                doc.path,
                block.line,
                "the Constraints block carries no `require ... hold on every turn` roll call",
            ),
        ]
    listed = set(re.findall(r"\b[A-Z]\w+\b", " ".join(roll)))
    for name in sorted(declared - listed):
        out.append(
            Finding(
                "AGENT_ROLLCALL",
                doc.path,
                block.line,
                f"declared constraint `{name}` missing from the roll call",
            )
        )
    for name in sorted(listed - declared):
        out.append(
            Finding(
                "AGENT_ROLLCALL",
                doc.path,
                block.line,
                f"roll call names `{name}`, which no constraint declares",
            )
        )
    return out


def rule_command_alias(doc: Document) -> list[Finding]:
    """H1: every command carries an alias."""
    out = []
    for st in doc.statements:
        if st.construct == "command" and not st.in_example:
            m = RE_COMMAND.match(st.text)
            if m and not m.group(3):
                out.append(
                    Finding("COMMAND_ALIAS", doc.path, st.line, f"/{st.name} carries no alias")
                )
    return out


def rule_member_form(doc: Document) -> list[Finding]:
    """A8: a member of a record or catalog block takes `name`, `name: type`, `name = value`, or `name { text }`."""
    out = []
    for st in doc.statements:
        if st.in_example or st.construct != "imperative" or not st.container:
            continue
        kind, _ = st.container[-1]
        if kind != "pascalBlock":
            continue
        if len(st.container) > 1 and st.container[-2][0] in CONTAINERS_FOR_DEMANDS:
            continue
        siblings = [s for s in doc.statements if s.container == st.container and s is not st]
        if siblings and all(
            s.construct in {"field", "pascalBlock", "lowerBlock"} for s in siblings
        ):
            out.append(
                Finding(
                    "MEMBER_FORM",
                    doc.path,
                    st.line,
                    "member of a record block without a form; write `name: ...` or `name = ...`",
                )
            )
    return out


def check(docs: list[Document]) -> list[Finding]:
    index: dict[str, set[str]] = {}
    for doc in docs:
        for name in doc.declared:
            index.setdefault(name, set()).add(doc.path.name)
        if doc.interface:
            index.setdefault(doc.interface, set()).add(doc.path.name)
    findings: list[Finding] = []
    for doc in docs:
        for rule in (
            rule_trigger,
            rule_pointer,
            rule_via_trailing,
            rule_prose_pointer,
            rule_prohibition,
            rule_match_head,
            rule_sentence_join,
            rule_demand_container,
            rule_agent_rollcall,
            rule_command_alias,
            rule_member_form,
        ):
            findings.extend(rule(doc))
        findings.extend(rule_xref(doc, index))
    findings.extend(rule_unique_name(docs))
    return sorted(set(findings), key=lambda f: (str(f.file), f.line, f.rule))


def load(root: Path) -> list[Document]:
    docs = []
    for side in SIDES:
        for path in sorted((root / side).glob("*.md")):
            docs.append(parse_document(path, side))
    return docs


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("files", nargs="*", help="files to report on; the whole tree is still read")
    ap.add_argument("--root", type=Path, default=REPO, help="tree holding rules/ and agents/")
    args = ap.parse_args()
    root = args.root.resolve()
    if not (root / "rules").is_dir():
        print(f"no rules/ under {root}", file=sys.stderr)
        return 2
    docs = load(root)
    findings = check(docs)
    if args.files:
        wanted = {Path(f).resolve() for f in args.files}
        findings = [f for f in findings if f.file.resolve() in wanted]
    for f in findings:
        try:
            shown = f.file.relative_to(root)
        except ValueError:
            shown = f.file
        print(f"{shown}:{f.line}: {f.rule} {f.message}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
