"""The rulesets directory read whole: its pool and its manifest."""

from __future__ import annotations

import dataclasses
import pathlib

from rulesets.source.manifest import Manifest, ManifestParseError, read_manifest
from rulesets.source.pool import Pool, read_pool


@dataclasses.dataclass(frozen=True)
class Present:
    manifest: Manifest


@dataclasses.dataclass(frozen=True)
class Missing:
    """No manifest file stands in the directory."""


@dataclasses.dataclass(frozen=True)
class Unparsable:
    error: ManifestParseError


type ManifestState = Present | Missing | Unparsable


@dataclasses.dataclass(frozen=True)
class RulesetsDirectory:
    root: pathlib.Path
    pool: Pool
    manifest: ManifestState


def read_directory(root: pathlib.Path) -> RulesetsDirectory:
    """Read the pool and the manifest. A manifest that does not parse is a state, not a raise."""

    manifest: ManifestState
    if not (root / "manifest.yaml").is_file():
        manifest = Missing()
    else:
        try:
            manifest = Present(read_manifest(root))
        except ManifestParseError as failure:
            manifest = Unparsable(failure)
    return RulesetsDirectory(root, read_pool(root), manifest)
