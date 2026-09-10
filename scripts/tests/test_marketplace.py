#!/usr/bin/env python3
"""Every feature packaged as a plugin is one this marketplace can install.

A plugin reaches a session only once the marketplace lists it and the listing
resolves to a directory holding a manifest. A feature directory with no entry
installs for nobody, and an entry naming a directory that is not there fails
at install with the marketplace file looking correct.

Run with `python3.14 -m pytest scripts/tests/test_marketplace.py`.
"""

import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
FEATURES = REPO_ROOT / "features"


def listing() -> dict:
    return json.loads(MARKETPLACE.read_text(encoding="utf-8"))


def entries() -> list[dict]:
    return listing()["plugins"]


def packaged() -> list[pathlib.Path]:
    """Every feature directory carrying a plugin manifest."""

    return sorted(
        child
        for child in FEATURES.iterdir()
        if (child / ".claude-plugin" / "plugin.json").is_file()
    )


class TestTheListingReachesEveryPackagedFeature:
    def test_at_least_one_feature_is_packaged(self):
        assert packaged(), "a test over the listing proves nothing with nothing packaged"

    def test_every_packaged_feature_has_an_entry(self):
        named = {entry["name"] for entry in entries()}
        unlisted = [
            path.name
            for path in packaged()
            if json.loads((path / ".claude-plugin" / "plugin.json").read_text())["name"]
            not in named
        ]

        assert unlisted == [], (
            f"a feature the marketplace does not list installs for nobody: {unlisted}"
        )

    def test_every_entry_resolves_to_a_manifest_naming_the_same_plugin(self):
        for entry in entries():
            source = (REPO_ROOT / entry["source"]).resolve()
            manifest = source / ".claude-plugin" / "plugin.json"

            assert manifest.is_file(), (
                f"{entry['name']} names {source}, which holds no plugin manifest, so the "
                "install fails with this file looking correct"
            )
            assert json.loads(manifest.read_text(encoding="utf-8"))["name"] == entry["name"], (
                "the harness keys a plugin's data and its enablement on the manifest's name, "
                "so a listing naming it differently enables something else"
            )

    def test_every_entry_states_the_version_its_manifest_states(self):
        """A listing and a manifest that disagree send a reader to the wrong changelog."""

        for entry in entries():
            manifest = json.loads(
                (
                    (REPO_ROOT / entry["source"]).resolve() / ".claude-plugin" / "plugin.json"
                ).read_text(encoding="utf-8")
            )

            assert entry.get("version") == manifest.get("version"), (
                f"{entry['name']} is listed at {entry.get('version')!r} and ships "
                f"{manifest.get('version')!r}, so a reader picks a version from whichever "
                "file they opened"
            )

    def test_every_source_is_relative_to_this_repository(self):
        for entry in entries():
            source = entry["source"]

            assert isinstance(source, str) and source.startswith("./"), (
                f"{entry['name']} names {source!r}, and a path outside this checkout resolves "
                "on one machine and nowhere else"
            )
