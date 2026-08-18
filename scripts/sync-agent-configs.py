#!/usr/bin/env python3.14
"""Project Claude Code's canonical configuration onto pi and opencode.

`~/.claude` holds the source of truth: `CLAUDE.md`, the rules under
`rules/`, and the agent definitions under `agents/`. pi and opencode read
their own formats from their own directories. This script generates those,
so the three agents carry the same behavioral configuration.

Run it to write, or with `--check` to compare without writing. `--check`
exits nonzero when any generated file differs from what a write would
produce, which is what the pre-push hook gates on.

Every generated file is owned end to end: the script rewrites it whole and
never merges into hand-written content. One exception carries its own rule:
opencode's `instructions` array lists rule files rather than holding their
text, so it lives inside the hand-written `opencode.json`. The script owns
that one key and leaves every other key in the file as it found it.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
from pathlib import Path

import yaml

HOME = Path.home()
CLAUDE_HOME = HOME / ".claude"


@dataclasses.dataclass(frozen=True)
class Document:
    """A markdown file split at its YAML frontmatter.

    `frontmatter` is None when the file opens on something other than a
    `---` line, which distinguishes a file carrying no frontmatter from one
    carrying an empty mapping.
    """

    frontmatter: dict | None
    body: str


FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def parse_document(text: str) -> Document:
    match = FRONTMATTER.match(text)
    if match is None:
        return Document(frontmatter=None, body=text)
    return Document(
        frontmatter=yaml.safe_load(match.group(1)) or {},
        body=text[match.end() :].lstrip("\n"),
    )


MARKDOWN_LINK = re.compile(r"(?<=\]\()([^)\s]+)(?=\))")
SCHEME = re.compile(r"\A[a-zA-Z][a-zA-Z0-9+.-]*:")


def _absolute_link_target(target: str) -> str:
    if target.startswith(("#", "/", "~")) or SCHEME.match(target):
        return target
    return os.path.normpath(CLAUDE_HOME / target)


def rewrite_paths(text: str) -> str:
    """Resolve the path references that only work from inside `~/.claude`.

    Generated files sit in directories where `~` goes unexpanded and where a
    link relative to `~/.claude` points at nothing. Both forms resolve to
    absolute paths; every other byte survives.
    """

    text = MARKDOWN_LINK.sub(lambda m: _absolute_link_target(m.group(1)), text)
    return text.replace("~/", f"{HOME}/")


def all_rules(rules_dir: Path) -> list[Path]:
    """Every rule file, sorted by filename."""

    return sorted(rules_dir.glob("*.md"))


def unconditional_rules(rules_dir: Path) -> list[Path]:
    """The rule files that load every session, carrying no frontmatter.

    A rule carrying `paths:` frontmatter stays out. Claude Code loads one
    only once a matching file enters play, and each adapter reproduces that
    condition from the same frontmatter, so listing it here would put the
    text in every prompt and a second copy in a matching one.
    """

    return [
        rule
        for rule in all_rules(rules_dir)
        if parse_document(rule.read_text(encoding="utf-8")).frontmatter is None
    ]


def build_preamble(claude_md: Path) -> str:
    """`CLAUDE.md` alone, with its paths resolved."""

    return rewrite_paths(
        parse_document(claude_md.read_text(encoding="utf-8")).body.strip("\n") + "\n"
    )


def build_agents_markdown(claude_md: Path, rules_dir: Path) -> str:
    """Assemble the always-loaded configuration into one AGENTS.md body.

    pi reads one context file per directory and offers no second mechanism
    for carrying rules as separate files, so its copy holds the preamble and
    every rule concatenated, frontmatter stripped.
    """

    sections = [parse_document(claude_md.read_text(encoding="utf-8")).body]
    sections += [
        parse_document(rule.read_text(encoding="utf-8")).body
        for rule in unconditional_rules(rules_dir)
    ]
    return rewrite_paths("\n\n".join(section.strip("\n") for section in sections) + "\n")


def rule_instructions(rules_dir: Path) -> list[str]:
    """The `instructions` entries opencode reads the session-wide rules from.

    Each names its canonical path under `~/.claude/rules/`, so an edit to a
    rule reaches opencode with no run of this script.
    """

    return [_home_relative(rule) for rule in unconditional_rules(rules_dir)]


def _home_relative(path: Path) -> str:
    """`~/`-prefixed where the path sits under the home directory, absolute otherwise."""

    return f"~/{path.relative_to(HOME)}" if path.is_relative_to(HOME) else str(path)


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


OPENCODE_MODEL_IDS = {
    "haiku": "anthropic/claude-haiku-4-5",
    "sonnet": "anthropic/claude-sonnet-4-6",
    "opus": "anthropic/claude-opus-4-7",
}

OPENCODE_TOOL_NAMES = {
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "Bash": "bash",
    "Grep": "grep",
    "Glob": "glob",
    "Agent": "task",
}

PI_TOOL_NAMES = {
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "Bash": "bash",
    "Grep": "grep",
    "Glob": "find",
}


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


def translate_for_opencode(agent: AgentDefinition) -> Translation:
    frontmatter: dict = {"description": agent.description, "mode": "subagent"}
    if agent.model is not None:
        frontmatter["model"] = OPENCODE_MODEL_IDS[agent.model]
    tools, dropped = _map_tools(agent.tools, OPENCODE_TOOL_NAMES)
    if tools is not None:
        frontmatter["tools"] = dict.fromkeys(tools, True)
    return Translation(content=_render(frontmatter, agent.body), dropped=dropped)


def translate_for_pi(agent: AgentDefinition) -> Translation:
    frontmatter: dict = {"description": agent.description}
    if agent.model is not None:
        frontmatter["model"] = agent.model
    tools, dropped = _map_tools(agent.tools, PI_TOOL_NAMES)
    if tools is not None:
        frontmatter["tools"] = ", ".join(tools)
    frontmatter["inheritSkills"] = True
    return Translation(content=_render(frontmatter, agent.body), dropped=dropped)


def _install_path(records: list[dict]) -> str | None:
    """Pick the one install a user-level enable turns on.

    A plugin installed against several projects can carry several versions
    at once. Putting all of them on a skills path loads each skill twice
    under two versions, so the user-scoped record wins where one exists.
    """

    for record in records:
        if record.get("scope") == "user":
            return record.get("installPath")
    return records[0].get("installPath") if records else None


def resolve_skill_paths(installed_plugins: Path, settings: Path) -> list[str]:
    plugins = json.loads(installed_plugins.read_text(encoding="utf-8")).get("plugins", {})
    enabled = json.loads(settings.read_text(encoding="utf-8")).get("enabledPlugins", {})

    resolved = set()
    for key, is_enabled in enabled.items():
        if not is_enabled:
            continue
        install_path = _install_path(plugins.get(key, []))
        if install_path is None:
            continue
        skills = Path(install_path) / "skills"
        if skills.is_dir():
            resolved.add(str(skills))
    return sorted(resolved)


@dataclasses.dataclass(frozen=True)
class Targets:
    """The three roots this script reads from and writes to."""

    claude_home: Path
    pi_home: Path
    opencode_home: Path

    @property
    def claude_md(self) -> Path:
        return self.claude_home / "CLAUDE.md"

    @property
    def rules_dir(self) -> Path:
        return self.claude_home / "rules"

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
    claude_home=CLAUDE_HOME,
    pi_home=HOME / ".pi" / "agent",
    opencode_home=HOME / ".config" / "opencode",
)


@dataclasses.dataclass(frozen=True)
class GeneratedFile:
    path: Path
    content: str


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


def build_plan(targets: Targets = DEFAULT_TARGETS) -> Plan:
    files = [
        GeneratedFile(
            targets.pi_home / "AGENTS.md",
            build_agents_markdown(targets.claude_md, targets.rules_dir),
        ),
        GeneratedFile(targets.opencode_home / "AGENTS.md", build_preamble(targets.claude_md)),
    ]
    keys = [
        GeneratedKey(
            targets.opencode_config,
            "instructions",
            rule_instructions(targets.rules_dir),
            after="$schema",
        )
    ]
    dropped: list[tuple[str, str, str]] = []

    for source in sorted(targets.agents_dir.glob("*.md")):
        agent = read_agent(source)
        for label, home, translate in (
            ("opencode", targets.opencode_home, translate_for_opencode),
            ("pi", targets.pi_home, translate_for_pi),
        ):
            translated = translate(agent)
            files.append(GeneratedFile(home / "agents" / f"{source.stem}.md", translated.content))
            dropped += [(label, source.stem, tool) for tool in translated.dropped]

    skill_paths = resolve_skill_paths(targets.installed_plugins, targets.settings)
    files.append(
        GeneratedFile(
            targets.skill_paths_file,
            json.dumps({"paths": skill_paths}, indent=2) + "\n",
        )
    )
    return Plan(files=tuple(files), keys=tuple(keys), dropped=tuple(dropped))


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


def _current(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def apply_plan(plan: Plan, *, check: bool) -> int:
    stale = 0
    for generated in plan.files:
        current = _current(generated.path)
        if current == generated.content:
            continue
        stale += 1
        if check:
            state = "missing" if current is None else "stale"
            print(f"{state}: {generated.path}")
            continue
        generated.path.parent.mkdir(parents=True, exist_ok=True)
        generated.path.write_text(generated.content, encoding="utf-8")
        if current is None:
            print(f"created: {generated.path} ({len(generated.content.encode())} bytes)")
        else:
            print(
                f"updated: {generated.path} "
                f"({len(current.encode())} -> {len(generated.content.encode())} bytes)"
            )

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

    total = len(plan.files) + len(plan.keys)
    if check:
        print(f"{stale} of {total} generated outputs out of date")
        return 1 if stale else 0
    print(f"{stale} of {total} generated outputs written")
    return 0


def main(argv: list[str] | None = None, targets: Targets = DEFAULT_TARGETS) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit nonzero when any generated file is out of date",
    )
    args = parser.parse_args(argv)
    return apply_plan(build_plan(targets), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
