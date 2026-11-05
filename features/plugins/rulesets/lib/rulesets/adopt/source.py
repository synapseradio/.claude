"""The source adopt and compare read: a tier corpus where it holds a manifest, else a rules folder."""

from __future__ import annotations

import pathlib

from rulesets.adopt.rules_folder import RulesFolder, read_rules_folder
from rulesets.adopt.tier_corpus import MANIFEST_FILE, SourceError, TierCorpus, read_tier_corpus

type Source = TierCorpus | RulesFolder


def read_source(path: pathlib.Path) -> Source:
    """Read `path` as a tier corpus or a rules folder. Raises SourceError for neither."""

    if not path.is_dir():
        raise SourceError(f"{path} is not a directory")
    if (path / MANIFEST_FILE).is_file():
        return read_tier_corpus(path)
    return read_rules_folder(path)
