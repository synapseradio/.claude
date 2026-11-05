"""Find the frontmatter of the agent definition an agent type names."""

import json
import pathlib
from dataclasses import dataclass

import yaml

from rulesets.documents import split_frontmatter

Frontmatter = dict[str, object]


@dataclass(frozen=True)
class Definition:
    """An agent definition file and the frontmatter it carries."""

    path: pathlib.Path
    front: Frontmatter


def definition_front(
    agent_type: str, cwd: str | None, config_dir: pathlib.Path
) -> Frontmatter | None:
    """The frontmatter of the definition `agent_type` names, or None where none is found."""

    definition = find_definition(agent_type, cwd, config_dir)
    return definition.front if definition else None


def find_definition(
    agent_type: str, cwd: str | None, config_dir: pathlib.Path
) -> Definition | None:
    """The definition `agent_type` names, or None where none is found.

    A plugin-scoped type, `plugin:name` or `plugin:subfolder:name`, reads that plugin's
    `agents/` directory. Any other type takes the first definition found in the project
    directories from `cwd` up to the repository root, then in `config_dir/agents`.
    Scopes follow https://code.claude.com/docs/en/sub-agents.md#choose-the-subagent-scope.
    """

    if ":" in agent_type:
        plugin, *subfolders, name = agent_type.split(":")
        for install in _plugin_install_paths(plugin, config_dir):
            directory = install.joinpath("agents", *subfolders)
            definition = _named_definition(list(directory.glob("*.md")), name)
            if definition is not None:
                return definition
        return None
    directories = [*(_project_agent_dirs(cwd) if cwd else []), config_dir / "agents"]
    for directory in directories:
        definition = _named_definition(list(directory.rglob("*.md")), agent_type)
        if definition is not None:
            return definition
    return None


def _frontmatter(path: pathlib.Path) -> Frontmatter:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    split = split_frontmatter(text)
    if split is None:
        return {}
    block, _ = split
    try:
        front = yaml.safe_load(block)
    except yaml.YAMLError:
        return {}
    return front if isinstance(front, dict) else {}


def _named_definition(paths: list[pathlib.Path], name: str) -> Definition | None:
    """The first definition registered as `name`.

    A definition registers under its `name` field, or under its filename where it has none.
    """

    for path in sorted(paths):
        front = _frontmatter(path)
        if (front.get("name") or path.stem) == name:
            return Definition(path, front)
    return None


def _project_agent_dirs(cwd: str) -> list[pathlib.Path]:
    """Each `.claude/agents/` from `cwd` up to the directory holding `.git`, closest first.

    Outside a repository only `cwd` itself is a project directory.
    """

    start = pathlib.Path(cwd).resolve()
    dirs = []
    for directory in (start, *start.parents):
        dirs.append(directory / ".claude" / "agents")
        if (directory / ".git").exists():
            return dirs
    return dirs[:1]


def _plugin_install_paths(plugin: str, config_dir: pathlib.Path) -> list[pathlib.Path]:
    """Every install path `installed_plugins.json` records for one plugin name."""

    index = config_dir / "plugins" / "installed_plugins.json"
    try:
        installed = json.loads(index.read_text(encoding="utf-8")).get("plugins", {})
    except (OSError, json.JSONDecodeError, AttributeError):
        return []
    paths = []
    for key, entries in installed.items():
        if key.split("@", 1)[0] != plugin or not isinstance(entries, list):
            continue
        paths += [
            pathlib.Path(entry["installPath"])
            for entry in entries
            if isinstance(entry, dict) and entry.get("installPath")
        ]
    return paths
