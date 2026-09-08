#!/usr/bin/env python3.14
"""Project Claude Code's canonical configuration onto pi and opencode.

A checkout carries `CLAUDE.md`, the rules under `rules/`, and the agent
definitions under `agents/`. This script reads the checkout it sits in,
resolved from its own path, so a hook running inside a worktree syncs that
worktree. pi and opencode read their own formats from their own directories,
and this script writes those, so the three agents run on the same behavioral
configuration and on whichever checkout last ran it.

`references/working-rules.md` renders `CLAUDE.md` and the always-on rules as
one document, in the order `WORKING_RULES_ORDER` names. That render and
those sources are two forms of one text, and this script moves between them
in either direction. With no argument it writes the render from the sources.
With `--reverse` it splits the render back into `CLAUDE.md` and the rules
files, writing no other output. One run moves text one way, and each
direction reproduces the other's input byte for byte.

Both directions read tag-form sources: `CLAUDE.md` opens on `<hello`, and
each rules file carries one `<rule name="stem">` element whose name is the
filename. A source in any other form stops the run before it writes.

Each direction writes its target side whole, so it refuses where a file it
would write carries changes git has not seen, naming each one. Commit those
changes and run again. No flag overrides the refusal.

`--check` compares without writing and exits nonzero where any output
differs from what a write would produce, which is what the pre-push hook
gates on. It composes with `--reverse`.

Every generated file is owned end to end: the script rewrites it whole and
never merges into hand-written content. One exception carries its own rule:
opencode's `instructions` array lists rule files rather than holding their
text, so it lives inside the hand-written `opencode.json`. The script owns
that one key and leaves every other key in the file as it found it.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "agent-configs"))

from projection import (
    DEFAULT_TARGETS,
    AgentDefinition,
    GeneratedFile,
    GeneratedKey,
    Plan,
    Targets,
    Translation,
    _map_tools,
    _render,
    apply_plan,
    home_relative,
    parse_document,
    read_agent,
    refuse_uncommitted,
    rewrite_paths,
    unconditional_rules,
)

# `restore_paths` moved with the reverse-direction render into
# render-working-rules.py; nothing in this shim's own remaining code calls
# it, but test_sync_agent_configs.py still reads it from here, so the import
# re-exports it under its own name rather than let a lint pass drop it.
from projection import restore_paths as restore_paths

# render-working-rules.py is a job, invoked by path and never imported, per
# the convention every job under agent-configs/ follows. This shim still
# promises `build_working_rules`, `build_reverse_plan`, `RuleSection`,
# `TITLE`, and `parse_reference` to whatever already reads them from here, so
# it loads the job by path exactly as a test loads this module, rather than
# keeping a second copy of what that job now owns.
_RENDER_PATH = Path(__file__).resolve().parent / "agent-configs" / "render-working-rules.py"
_render_spec = importlib.util.spec_from_file_location("render_working_rules", _RENDER_PATH)
assert _render_spec is not None and _render_spec.loader is not None
render_working_rules = importlib.util.module_from_spec(_render_spec)
sys.modules["render_working_rules"] = render_working_rules
_render_spec.loader.exec_module(render_working_rules)

RuleSection = render_working_rules.RuleSection
TITLE = render_working_rules.TITLE
build_working_rules = render_working_rules.build_working_rules
parse_reference = render_working_rules.parse_reference

# The job's own `build_reverse_plan` takes a `check` keyword the job's own
# `--check` uses to skip the uncommitted-changes guard on a read-only run.
# Every call written against this shim omits it, so `check` stays False and
# the guard still runs on every call here, matching what those calls expect.
build_reverse_plan = render_working_rules.build_reverse_plan


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

    return [home_relative(rule) for rule in unconditional_rules(rules_dir)]


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


def build_plan(targets: Targets = DEFAULT_TARGETS) -> Plan:
    refuse_uncommitted(targets.claude_home, [targets.working_rules])
    files = [
        GeneratedFile(
            targets.pi_home / "AGENTS.md",
            build_agents_markdown(targets.claude_md, targets.rules_dir),
        ),
        GeneratedFile(targets.opencode_home / "AGENTS.md", build_preamble(targets.claude_md)),
        GeneratedFile(
            targets.working_rules,
            build_working_rules(targets.claude_md, targets.rules_dir, targets.working_rules_order),
        ),
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


def main(argv: list[str] | None = None, targets: Targets = DEFAULT_TARGETS) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit nonzero when any generated file is out of date",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="split the render back into CLAUDE.md and the rules files, writing no other output",
    )
    args = parser.parse_args(argv)
    build = build_reverse_plan if args.reverse else build_plan
    return apply_plan(build(targets), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
