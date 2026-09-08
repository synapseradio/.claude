#!/usr/bin/env python3.14
"""Project agent definitions and installed skills onto pi's own format.

pi reads one context file per directory and offers no second mechanism for
carrying rules as separate files, so `AGENTS.md` holds the `CLAUDE.md`
preamble and every always-on rule concatenated. Each Claude Code agent under
`agents/*.md` gets its own translation under pi's `agents/` directory. The
skill-paths file lists the directories an enabled plugin installs skills
into, which pi reads as a second source alongside its own.

`--check` compares without writing and exits nonzero where any output
differs from what a write would produce, naming each differing path.

Every generated file is owned end to end: this job rewrites it whole and
never merges into hand-written content.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from projection import (
    DEFAULT_TARGETS,
    AgentDefinition,
    GeneratedFile,
    Plan,
    Targets,
    Translation,
    _map_tools,
    _render,
    apply_plan,
    parse_document,
    read_agent,
    rewrite_paths,
    unconditional_rules,
)

PI_TOOL_NAMES = {
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "Bash": "bash",
    "Grep": "grep",
    "Glob": "find",
}


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


def build_plan(targets: Targets = DEFAULT_TARGETS) -> Plan:
    files = [
        GeneratedFile(
            targets.pi_home / "AGENTS.md",
            build_agents_markdown(targets.claude_md, targets.rules_dir),
        ),
    ]
    dropped: list[tuple[str, str, str]] = []

    for source in sorted(targets.agents_dir.glob("*.md")):
        agent = read_agent(source)
        translated = translate_for_pi(agent)
        files.append(
            GeneratedFile(targets.pi_home / "agents" / f"{source.stem}.md", translated.content)
        )
        dropped += [("pi", source.stem, tool) for tool in translated.dropped]

    skill_paths = resolve_skill_paths(targets.installed_plugins, targets.settings)
    files.append(
        GeneratedFile(
            targets.skill_paths_file,
            json.dumps({"paths": skill_paths}, indent=2) + "\n",
        )
    )
    return Plan(files=tuple(files), keys=(), dropped=tuple(dropped))


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
