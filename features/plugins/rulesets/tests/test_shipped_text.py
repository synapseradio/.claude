#!/usr/bin/env python3
"""The plugin's shipped text describes only config.yaml, and the release carries version 4.0.0.

The text serves the person who installs the plugin and writes a config from its skill, docs,
readme, and install guide: an example in the old layout would teach a form check rejects. The
version serves the installer, who sees a new major version for a release that reads only
config.yaml.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_shipped_text.py`.
"""

import json
import pathlib

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PLUGIN_ROOT.parents[2]
SKILL = PLUGIN_ROOT / "skills" / "rulesets"

SHIPPED = sorted(
    [
        *SKILL.rglob("*.md"),
        *(SKILL / "scripts").glob("*.py"),
        *(PLUGIN_ROOT / "docs").glob("*.md"),
        PLUGIN_ROOT / "README.md",
        PLUGIN_ROOT / "INSTALL.md",
    ]
)


class TestTheShippedTextHoldsNoOldFileNameOrNotation:
    @pytest.mark.parametrize("old", ["manifest.yaml", "when:", ":*"])
    def test_no_shipped_file_holds_the_old_form(self, old):
        holding = [
            str(path.relative_to(PLUGIN_ROOT))
            for path in SHIPPED
            if old in path.read_text(encoding="utf-8")
        ]

        assert SHIPPED
        assert holding == []

    def test_the_skill_and_docs_name_config_yaml(self):
        for path in (SKILL / "SKILL.md", PLUGIN_ROOT / "README.md", PLUGIN_ROOT / "INSTALL.md"):
            assert "config.yaml" in path.read_text(encoding="utf-8"), path.name


class TestBothVersionFieldsRead400:
    def test_the_plugin_file_and_the_marketplace_entry_read_4_0_0(self):
        plugin = json.loads(
            (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (REPOSITORY_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        (entry,) = [p for p in marketplace["plugins"] if p["name"] == "rulesets"]

        assert (plugin["version"], entry["version"]) == ("4.0.0", "4.0.0")
