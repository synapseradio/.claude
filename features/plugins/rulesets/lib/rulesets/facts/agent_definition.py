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
    Scopes follow https://code.claude.com/docs/en/sub-agents.md#choose-the-subagent-scope;
    which files register follows
    https://code.claude.com/docs/en/sub-agents.md#subagent-files-claude-code-skips.
    """

    if ":" in agent_type:
        plugin, *subfolders, name = agent_type.split(":")
        for install in _plugin_install_paths(plugin, config_dir):
            directory = install.joinpath("agents", *subfolders)
            definition = _named_definition(list(directory.glob("*.md")), name, in_plugin=True)
            if definition is not None:
                return definition
        return None
    directories = [*(_project_agent_dirs(cwd) if cwd else []), config_dir / "agents"]
    for directory in directories:
        definition = _named_definition(list(directory.rglob("*.md")), agent_type, in_plugin=False)
        if definition is not None:
            return definition
    return None


_MAX_NAME_LENGTH = 256


def _frontmatter(path: pathlib.Path) -> Frontmatter | None:
    """The frontmatter of a file, `{}` where it has none, None where it cannot be read or parsed."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    split = split_frontmatter(text)
    if split is None:
        return {}
    block, _ = split
    try:
        front = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    return front if isinstance(front, dict) else {}


def _registered_name(
    path: pathlib.Path, front: Frontmatter | None, *, in_plugin: bool
) -> str | None:
    """The name a file registers under, or None where the harness skips the file.

    A project, user, or managed file registers under its `name` alone, and only when the name
    is valid and a `description` accompanies it. A plugin file registers under its `name`, or
    under its filename where it has none or its frontmatter does not parse.
    """

    if in_plugin:
        name = (front or {}).get("name")
        return name if isinstance(name, str) and name else path.stem
    if front is None:
        return None
    name = front.get("name")
    if not isinstance(name, str) or not name:
        return None
    if name.startswith("-") or ":" in name or len(name) > _MAX_NAME_LENGTH:
        return None
    description = front.get("description")
    if not isinstance(description, str) or not description.strip():
        return None
    return name


def _named_definition(
    paths: list[pathlib.Path], name: str, *, in_plugin: bool
) -> Definition | None:
    """The first definition the harness registers as `name`."""

    for path in sorted(paths):
        front = _frontmatter(path)
        if _registered_name(path, front, in_plugin=in_plugin) == name:
            return Definition(path, front or {})
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
