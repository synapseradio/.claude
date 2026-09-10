"""Shared ground for the jobs that project this checkout onto other formats.

Each job under this directory reads its sources through this module and
writes through its plan machinery, so a change to one job reaches no other
job's output. The jobs import this by name, since a script run by path puts
its own directory first on `sys.path`.

Reading a markdown document, resolving the paths it cites, and writing a
generated file all live in the model-scoped-rulesets plugin, whose mechanism
these jobs share. This module imports those inward and re-exports them under
their own names, so a job importing `parse_document` from here still gets
the one definition. The rule bodies themselves belong to this checkout: the
corpus is named once, as `Targets.corpus_root`, and every job reads the
always-on bodies through `Targets.rules_dir`.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import yaml

HOME = Path.home()

# The checkout this directory sits in, so a run reads and writes the tree it
# was invoked from and a hook inside a worktree syncs that worktree.
SCRIPT_ROOT = Path(__file__).resolve().parents[2]

PLUGIN_ROOT = SCRIPT_ROOT / "features" / "model-scoped-rulesets"

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.documents import (  # noqa: E402  (path must be set before this import)
    CLAUDE_HOME_VAR,
    HOME_VAR,
    Document,
    GeneratedFile,
    all_rules,
    home_relative,
    ordered_rules,
    parse_document,
    refuse_uncommitted,
    restore_paths,
    rewrite_paths,
    summarize,
    uncommitted,
    unconditional_rules,
    write_or_check,
)

# Re-exported for the jobs that import these by name from this module.
__all__ = [
    "CLAUDE_HOME_VAR",
    "HOME_VAR",
    "AgentDefinition",
    "Document",
    "GeneratedFile",
    "GeneratedKey",
    "Plan",
    "Targets",
    "Translation",
    "agent_source",
    "all_rules",
    "apply_plan",
    "home_relative",
    "ordered_rules",
    "parse_document",
    "read_agent",
    "refuse_uncommitted",
    "restore_paths",
    "rewrite_paths",
    "uncommitted",
    "unconditional_rules",
    "write_or_check",
]


def agent_source(agents_dir: Path, name: str) -> Path:
    """The source file for one agent, or a ValueError naming what is there.

    A translation job scoped to one agent takes a name from the command line,
    and the source is what the name has to reach. The error carries the names
    that do resolve, so a misspelling is fixed from the message.
    """

    source = agents_dir / f"{name}.md"
    if not source.is_file():
        held = tuple(sorted(child.stem for child in agents_dir.glob("*.md")))
        raise ValueError(f"{name!r} names no agent source under {agents_dir}: {held}")
    return source


@dataclasses.dataclass(frozen=True)
class AgentDefinition:
    """One Claude Code agent definition, read from `agents/<name>.md`.

    `model` is None where the source names none, which means the agent
    inherits its caller's model. `tools` is None where the source names
    none, which grants every tool rather than no tool.
    """

    name: str
    description: str
    model: str | None
    tools: tuple[str, ...] | None
    body: str


@dataclasses.dataclass(frozen=True)
class Translation:
    """A generated agent file, with the source tool names it could not carry."""

    content: str
    dropped: tuple[str, ...]


def read_agent(path: Path) -> AgentDefinition:
    document = parse_document(path.read_text(encoding="utf-8"))
    frontmatter = document.frontmatter or {}
    tools = frontmatter.get("tools")
    return AgentDefinition(
        name=frontmatter["name"],
        description=frontmatter["description"],
        model=frontmatter.get("model"),
        tools=None if tools is None else tuple(t.strip() for t in tools.split(",") if t.strip()),
        body=document.body,
    )


def _map_tools(
    tools: tuple[str, ...] | None, names: dict[str, str]
) -> tuple[list[str] | None, tuple[str, ...]]:
    if tools is None:
        return None, ()
    mapped = [names[tool] for tool in tools if tool in names]
    dropped = tuple(tool for tool in tools if tool not in names)
    return mapped, dropped


def _render(frontmatter: dict, body: str) -> str:
    rendered = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10**9,
    )
    return f"---\n{rendered}---\n\n{body}"


@dataclasses.dataclass(frozen=True)
class Targets:
    """The roots this script reads from and writes to.

    `corpus_root` is the one place the rule bodies are named. It holds one
    directory per tier and sits in this checkout, which owns them, beside
    the manifest that composes them; a job reads the always-on bodies
    through `rules_dir`, so moving the corpus is a change to this field's
    default alone.
    """

    claude_home: Path
    pi_home: Path
    opencode_home: Path
    corpus_root: Path = SCRIPT_ROOT / "rulesets"

    @property
    def claude_md(self) -> Path:
        return self.claude_home / "CLAUDE.md"

    @property
    def rules_dir(self) -> Path:
        return self.corpus_root / "default"

    @property
    def agents_dir(self) -> Path:
        return self.claude_home / "agents"

    @property
    def installed_plugins(self) -> Path:
        return self.claude_home / "plugins" / "installed_plugins.json"

    @property
    def settings(self) -> Path:
        return self.claude_home / "settings.json"

    @property
    def skill_paths_file(self) -> Path:
        return self.claude_home / "scratchpad" / "main" / "generated-skill-paths.json"

    @property
    def opencode_config(self) -> Path:
        return self.opencode_home / "opencode.json"


DEFAULT_TARGETS = Targets(
    claude_home=SCRIPT_ROOT,
    pi_home=HOME / ".pi" / "agent",
    opencode_home=HOME / ".config" / "opencode",
)


@dataclasses.dataclass(frozen=True)
class GeneratedKey:
    """One top-level key this script owns inside a hand-written JSON file.

    `after` names the key the new one follows when the file carries none
    yet, so a first write lands where a reader expects it rather than at the
    end. Every other key, and the file's key order, survives the write.
    """

    path: Path
    key: str
    value: object
    after: str


@dataclasses.dataclass(frozen=True)
class Plan:
    """Every file a run would write, and every tool grant that could not cross.

    `dropped` holds (target, agent, tool) for each source tool name the
    target has no equivalent for, so a run reports where an agent's reach
    narrowed rather than narrowing it silently.
    """

    files: tuple[GeneratedFile, ...]
    keys: tuple[GeneratedKey, ...]
    dropped: tuple[tuple[str, str, str], ...]


def _reorder(data: dict, key: str, value: object, after: str) -> dict:
    """`data` with `key` set to `value`, placed after `after` when new."""

    if key in data:
        return {name: (value if name == key else held) for name, held in data.items()}
    reordered: dict = {}
    for name, held in data.items():
        reordered[name] = held
        if name == after:
            reordered[key] = value
    if key not in reordered:
        reordered[key] = value
    return reordered


def apply_plan(plan: Plan, *, check: bool) -> int:
    stale = write_or_check(plan.files, check=check)

    for owned in plan.keys:
        # A config file absent altogether gets created holding this key
        # alone, so a fresh machine needs no hand-written stub first.
        data = json.loads(owned.path.read_text(encoding="utf-8")) if owned.path.is_file() else {}
        if data.get(owned.key) == owned.value:
            continue
        stale += 1
        if check:
            state = "missing" if owned.key not in data else "stale"
            print(f"{state}: {owned.key} in {owned.path}")
            continue
        rewritten = _reorder(data, owned.key, owned.value, owned.after)
        owned.path.parent.mkdir(parents=True, exist_ok=True)
        owned.path.write_text(json.dumps(rewritten, indent=2) + "\n", encoding="utf-8")
        print(f"updated: {owned.key} in {owned.path}")

    for label, agent, tool in plan.dropped:
        print(f"dropped: {tool} from {agent} for {label}, which carries no equivalent")

    return summarize(stale, len(plan.files) + len(plan.keys), check=check)
