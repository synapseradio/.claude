"""Whether a rule file's frontmatter scopes it to paths."""

from __future__ import annotations

import pathlib

import yaml

from rulesets.documents import split_frontmatter


def is_path_scoped(path: pathlib.Path) -> bool:
    """Whether the file's frontmatter carries a `paths` key, which scopes it to matching paths."""

    split = split_frontmatter(path.read_bytes().decode("utf-8", errors="replace"))
    if split is None:
        return False
    try:
        front = yaml.safe_load(split[0])
    except yaml.YAMLError:
        return False
    return isinstance(front, dict) and "paths" in front
