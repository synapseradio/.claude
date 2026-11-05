"""The tools fact: the tools an agent definition grants, read from its frontmatter alone."""

from rulesets.facts.agent_definition import Frontmatter
from rulesets.facts.context import ABSENT, Absent, AllToolsBut, ListedTools


def tools_fact(front: Frontmatter | None) -> ListedTools | AllToolsBut | Absent:
    """The tools a definition's frontmatter grants, or ABSENT where no definition was found.

    A `tools` list names the tools held; without one the definition inherits every tool.
    Each `disallowedTools` entry removes its whole tool, a specifier such as `Bash(git push *)`
    included (https://code.claude.com/docs/en/sub-agents.md#supported-frontmatter-fields).
    """

    if front is None:
        return ABSENT
    listed = _tool_names(front.get("tools"))
    removed = _tool_names(front.get("disallowedTools"))
    if not listed:
        return AllToolsBut(removed)
    return ListedTools(listed - removed)


def _tool_names(field: object) -> frozenset[str]:
    """The tool names of a comma-separated string or a list, each entry cut at its specifier."""

    match field:
        case str():
            entries = _split_entries(field)
        case list():
            entries = [
                entry for item in field if isinstance(item, str) for entry in _split_entries(item)
            ]
        case _:
            return frozenset()
    names = (entry.split("(", 1)[0].strip() for entry in entries)
    return frozenset(name for name in names if name)


def _split_entries(text: str) -> list[str]:
    """The comma-separated entries of `text`, keeping a comma inside parentheses in its entry."""

    entries: list[str] = []
    depth = 0
    start = 0
    for at, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif char == "," and depth == 0:
            entries.append(text[start:at])
            start = at + 1
    entries.append(text[start:])
    return entries
