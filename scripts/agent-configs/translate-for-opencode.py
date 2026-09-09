#!/usr/bin/env python3.14
"""Project agent definitions onto opencode's own format.

`AGENTS.md` carries the `CLAUDE.md` preamble alone: opencode reads the
always-on rules through the `instructions` key a separate job owns inside
its hand-written `opencode.json`, so repeating them here would load them
twice. Each Claude Code agent under `agents/*.md` gets its own translation
under opencode's `agents/` directory.

`--check` compares without writing and exits nonzero where any output
differs from what a write would produce, naming each differing path.
`--agent` scopes a run to one agent's translation, leaving `AGENTS.md` as it
stands, since the preamble derives from no single agent.

Every generated file is owned end to end: this job rewrites it whole and
never merges into hand-written content.
"""

from __future__ import annotations

import argparse
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
    agent_source,
    apply_plan,
    parse_document,
    read_agent,
    rewrite_paths,
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


def build_preamble(claude_md: Path) -> str:
    """`CLAUDE.md` alone, with its paths resolved."""

    return rewrite_paths(
        parse_document(claude_md.read_text(encoding="utf-8")).body.strip("\n") + "\n"
    )


def translate_for_opencode(agent: AgentDefinition) -> Translation:
    frontmatter: dict = {"description": agent.description, "mode": "subagent"}
    if agent.model is not None:
        frontmatter["model"] = OPENCODE_MODEL_IDS[agent.model]
    tools, dropped = _map_tools(agent.tools, OPENCODE_TOOL_NAMES)
    if tools is not None:
        frontmatter["tools"] = dict.fromkeys(tools, True)
    return Translation(content=_render(frontmatter, agent.body), dropped=dropped)


def build_plan(targets: Targets = DEFAULT_TARGETS) -> Plan:
    files = [
        GeneratedFile(targets.opencode_home / "AGENTS.md", build_preamble(targets.claude_md)),
    ]
    dropped: list[tuple[str, str, str]] = []

    for source in sorted(targets.agents_dir.glob("*.md")):
        agent = read_agent(source)
        translated = translate_for_opencode(agent)
        files.append(
            GeneratedFile(
                targets.opencode_home / "agents" / f"{source.stem}.md", translated.content
            )
        )
        dropped += [("opencode", source.stem, tool) for tool in translated.dropped]

    return Plan(files=tuple(files), keys=(), dropped=tuple(dropped))


def build_one_agent(name: str, targets: Targets = DEFAULT_TARGETS) -> Plan:
    """The translation of the one agent `name` reaches, and no other output.

    The preamble derives from `CLAUDE.md` and from no single agent, so a run
    scoped to one leaves it as it stands.
    """

    source = agent_source(targets.agents_dir, name)
    translated = translate_for_opencode(read_agent(source))
    return Plan(
        files=(
            GeneratedFile(
                targets.opencode_home / "agents" / f"{source.stem}.md", translated.content
            ),
        ),
        keys=(),
        dropped=tuple(("opencode", source.stem, tool) for tool in translated.dropped),
    )


def main(argv: list[str] | None = None, targets: Targets = DEFAULT_TARGETS) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit nonzero when any generated file is out of date",
    )
    parser.add_argument(
        "--agent",
        help="translate this agent alone, named for its source file's stem",
    )
    args = parser.parse_args(argv)
    if args.agent:
        try:
            plan = build_one_agent(args.agent, targets)
        except ValueError as unreached:
            parser.error(str(unreached))
        return apply_plan(plan, check=args.check)
    return apply_plan(build_plan(targets), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
