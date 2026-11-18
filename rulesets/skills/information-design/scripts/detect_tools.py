#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""List the optional tools this machine has, what each adds, and what to do without it.

detect_tools.py [--json]

Installs nothing and reads nothing but PATH and three application folders. For a missing tool it
prints the route that needs no install, and the install command to show a person when asking
whether to install.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Tool:
    name: str
    commands: tuple[str, ...]
    adds: str
    without: str
    install: dict[str, str]
    changes: str
    docs: str
    app_paths: tuple[str, ...] = ()


TOOLS = (
    Tool(
        name="Graphviz",
        commands=("dot",),
        adds="lays out a node-and-arrow diagram automatically and writes it as SVG",
        without="write Mermaid source in a fenced block, or an indented list or table of the connections",
        install={
            "Darwin": "brew install graphviz",
            "Linux": "sudo apt install graphviz   (Debian, Ubuntu)  |  sudo dnf install graphviz   (Fedora)",
            "Windows": "winget install graphviz",
        },
        changes="adds the Graphviz command-line programs through the system package manager",
        docs="https://graphviz.org/download/",
    ),
    Tool(
        name="Mermaid CLI",
        commands=("mmdc",),
        adds="renders Mermaid diagram source to an SVG or PNG file a reader can open anywhere",
        without="leave the Mermaid source in a fenced block for hosts that render it, and add a text description",
        install={
            "Darwin": "npm install -g @mermaid-js/mermaid-cli",
            "Linux": "npm install -g @mermaid-js/mermaid-cli",
            "Windows": "npm install -g @mermaid-js/mermaid-cli",
        },
        changes="needs Node.js; installs a global npm package, which downloads a headless browser",
        docs="https://github.com/mermaid-js/mermaid-cli",
    ),
    Tool(
        name="Pandoc",
        commands=("pandoc",),
        adds="converts a Markdown page to HTML, DOCX or slides for a reader who cannot open Markdown",
        without="deliver the Markdown, or write the page as one self-contained HTML file",
        install={
            "Darwin": "brew install pandoc",
            "Linux": "see https://pandoc.org/installing.html for your distribution",
            "Windows": "winget install --source winget --exact --id JohnMacFarlane.Pandoc",
        },
        changes="adds the pandoc program through the system package manager",
        docs="https://pandoc.org/installing.html",
    ),
    Tool(
        name="Chromium-family browser",
        commands=(
            "chromium",
            "chromium-browser",
            "google-chrome",
            "google-chrome-stable",
            "msedge",
        ),
        app_paths=(
            "/Applications/Google Chrome.app",
            "/Applications/Chromium.app",
            "/Applications/Microsoft Edge.app",
        ),
        adds="renders an HTML page to a PNG or PDF in headless mode, so the result can be looked at",
        without="hand over the HTML file and say that its rendered layout has not been looked at",
        install={},
        changes="",
        docs="",
    ),
    Tool(
        name="Node.js",
        commands=("node",),
        adds="runs JavaScript chart and diagram tooling",
        without="write SVG or self-contained HTML by hand; the browser runs the page's own inline script",
        install={},
        changes="",
        docs="https://nodejs.org/",
    ),
)


def locate(tool: Tool) -> str | None:
    """Return where the tool is installed, or None when it is absent."""
    for command in tool.commands:
        found = shutil.which(command)
        if found:
            return found
    for app in tool.app_paths:
        if Path(app).exists():
            return app
    return None


def survey(system: str) -> list[dict[str, object]]:
    """Return one record per optional tool for the given platform name."""
    records = []
    for tool in TOOLS:
        path = locate(tool)
        record: dict[str, object] = {
            "name": tool.name,
            "present": path is not None,
            "path": path,
            "adds": tool.adds,
        }
        if path is None:
            record["without"] = tool.without
            record["install"] = tool.install.get(system, "")
            record["changes"] = tool.changes
            record["docs"] = tool.docs
        records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json", action="store_true", help="print the survey as JSON")
    arguments = parser.parse_args()

    records = survey(platform.system())
    if arguments.json:
        print(json.dumps(records, indent=2))
        return 0
    for record in records:
        if record["present"]:
            print(f"present  {record['name']}: {record['path']}")
            continue
        print(f"missing  {record['name']}")
        print(f"           adds:     {record['adds']}")
        print(f"           without:  {record['without']}")
        if record["install"]:
            print(f"           install:  {record['install']}")
            print(f"           changes:  {record['changes']}")
        elif record["docs"]:
            print(f"           install:  see {record['docs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
