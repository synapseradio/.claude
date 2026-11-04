"""Research ingestion into the session's Hindsight bank, shared by the research hooks.

The bank is the one the hindsight-coding-agents plugin resolves for a working directory,
read from its status script. Research documents go in under the bank's `research` retain
strategy, which this module adds to a bank that lacks it.
"""

import json
import os
import subprocess
import urllib.request
from pathlib import Path

API_URL = os.environ.get("HINDSIGHT_API_URL", "http://127.0.0.1:9077")
STATUS_SCRIPT = Path.home() / ".hindsight" / "coding-agents" / "dist" / "status.js"
STRATEGY_NAME = "research"
STRATEGY = {
    "retain_mission": (
        "You are ingesting a research note: claims checked against sources, each "
        "with its citation. Extract each claim together with the URL or path that "
        "backs it and the kind of source it is (code, spec, maintainer docs, "
        "measurement, practitioner account). Extract each recommendation or "
        "conclusion with its reasoning and the problem it answers. Skip narration "
        "of how the research was carried out. Never record a line number or a "
        "count; cite the source that holds it."
    ),
    "retain_chunk_size": 12000,
    "retain_extraction_mode": "concise",
}


def request(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        API_URL + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def resolve_bank(cwd):
    result = subprocess.run(
        ["node", str(STATUS_SCRIPT), "--repo", cwd],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    return json.loads(result.stdout)["bank"]


def ensure_strategy(bank):
    config = request("GET", f"/v1/default/banks/{bank}/config")
    strategies = (config.get("config") or config).get("retain_strategies") or {}
    if STRATEGY_NAME in strategies:
        return
    strategies[STRATEGY_NAME] = STRATEGY
    request(
        "PATCH", f"/v1/default/banks/{bank}/config", {"updates": {"retain_strategies": strategies}}
    )


def retain_report(cwd, repo, document_id, content, metadata):
    """Queue a research report as one document in the bank resolved for cwd; returns the bank."""
    bank = resolve_bank(cwd)
    ensure_strategy(bank)
    tags = ["source:research", f"agent:{metadata['agent_type']}"]
    if repo:
        tags.append(f"project:{repo}")
    item = {
        "content": content,
        "document_id": document_id,
        "context": f"research report from {metadata['agent_type']}",
        "metadata": metadata,
        "tags": tags,
        "strategy": STRATEGY_NAME,
    }
    request("POST", f"/v1/default/banks/{bank}/memories", {"items": [item], "async": True})
    return bank
