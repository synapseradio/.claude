"""The render tree's contents: each file name with the text render writes to it."""

from __future__ import annotations

from collections.abc import Mapping

from rulesets.compose.base_context import base_composition
from rulesets.render.context_render import render_context
from rulesets.source.directory import RulesetsDirectory


def render_tree(directory: RulesetsDirectory) -> Mapping[str, str]:
    """The renders of the tree by file name, with no block applied in any of them."""

    return {"defaults.md": render_context(base_composition(directory), directory.pool)}
