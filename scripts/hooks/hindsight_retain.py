"""Shared pieces for the hooks that retain session content into Hindsight banks.

The server and bank naming follow the coding-agent integration: the API URL comes
from ~/.hindsight/coding-agent.json, and a repo's name is the basename of its main
worktree, the key coding-agent::<repo> banks use.
"""

import json
import subprocess
import urllib.request
from pathlib import Path

CONFIG = Path.home() / ".hindsight" / "coding-agent.json"
DEFAULT_API = "http://localhost:8888"


def api_url():
    try:
        return json.loads(CONFIG.read_text()).get("apiUrl") or DEFAULT_API
    except OSError, ValueError:
        return DEFAULT_API


def repo_name(cwd):
    """Basename of the main worktree holding cwd, or None outside a git repository."""
    try:
        common = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        ).stdout.strip()
    except OSError, subprocess.SubprocessError:
        return None
    return Path(common).parent.name or None


def retain(bank, content, document_id, tags, context):
    """Queue one document for async extraction; the server answers before extracting."""
    body = json.dumps(
        {
            "items": [
                {
                    "content": content,
                    "context": context,
                    "document_id": document_id,
                    "tags": tags,
                }
            ],
            "async": True,
        }
    ).encode()
    req = urllib.request.Request(
        f"{api_url()}/v1/default/banks/{bank}/memories",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        resp.read()
