#!/usr/bin/env python3
"""UserPromptSubmit hook: fire `graphify-sync <name>` when a prompt names an
in-scope repo.

Reads JSON {prompt, ...} on stdin. Tokenizes the prompt text, intersects with
the cached name → location map at ~/.graphify/.repo-cache.json (rebuilt every
24h), filters names shorter than 4 chars and names in the stoplist at
~/.graphify/.repo-name-stoplist, and spawns a detached `graphify-sync` per
match. Never blocks. Never prints to stdout. All activity goes to
~/.cache/graphify-sync.log.

Cooldown: 1h per repo, tracked via the .last-sync touchfile under
~/.graphify/local/<rel-path>/.

Missing-but-in-scope repos are cloned on demand by `graphify-sync` itself.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

HOME = pathlib.Path.home()
GRAPHIFY_HOME = HOME / ".graphify"
LOCAL_BASE = GRAPHIFY_HOME / "local"
SYNC_SCRIPT = GRAPHIFY_HOME / "sync.sh"
OWNER_CACHE = GRAPHIFY_HOME / ".allowed-owners"
REPO_CACHE = GRAPHIFY_HOME / ".repo-cache.json"
STOPLIST_FILE = GRAPHIFY_HOME / ".repo-name-stoplist"
EXTRA_REPOS_FILE = GRAPHIFY_HOME / ".extra-repos"
LOG_FILE = HOME / ".cache" / "grip.log"
SCAN_ROOTS = [HOME / "projects", HOME / "projects" / "ai"]

CACHE_TTL_SECONDS = 24 * 60 * 60
COOLDOWN_SECONDS = 60 * 60
MIN_NAME_LENGTH = 4
GH_TIMEOUT_SECONDS = 15

DEFAULT_STOPLIST = [
    "play", "core", "panda", "dollas", "lingua", "design",
    "common", "shared", "main", "docs", "test", "tests",
    "build", "dist", "util", "utils", "skills",
]


def log(msg: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"[{ts}] [prompt-hook] {msg}\n")
    except OSError:
        pass


def load_stoplist() -> set[str]:
    if not STOPLIST_FILE.exists():
        try:
            STOPLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
            STOPLIST_FILE.write_text("\n".join(DEFAULT_STOPLIST) + "\n", encoding="utf-8")
        except OSError:
            return set(DEFAULT_STOPLIST)
    try:
        return {
            line.strip().lower()
            for line in STOPLIST_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
    except OSError:
        return set(DEFAULT_STOPLIST)


def load_allowed_owners() -> list[str]:
    if not OWNER_CACHE.exists():
        return ["amboss-mededu"]
    try:
        owners = [
            line.strip()
            for line in OWNER_CACHE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return owners or ["amboss-mededu"]
    except OSError:
        return ["amboss-mededu"]


REMOTE_PATTERNS = [
    re.compile(r"^[^@]+@[^:]+:([^/]+)/([^/]+?)(?:\.git)?$"),
    re.compile(r"^[a-z]+://(?:[^@/]+@)?[^/]+/([^/]+)/([^/]+?)(?:\.git)?$"),
]


def parse_origin(url: str) -> tuple[str, str] | None:
    url = url.strip()
    for pat in REMOTE_PATTERNS:
        m = pat.match(url)
        if m:
            return (m.group(1), m.group(2))
    return None


def _repo_owner_or_none(child: pathlib.Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(child), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    parsed = parse_origin(result.stdout)
    if not parsed:
        return None
    return parsed[0]


def read_extras() -> list[pathlib.Path]:
    if not EXTRA_REPOS_FILE.exists():
        return []
    try:
        lines = EXTRA_REPOS_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        p = pathlib.Path(s)
        if p.is_dir() and (p / ".git").exists():
            out.append(p)
    return out


def discover_local_repos(allowed: set[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    # Scan default roots — only in-scope repos make it in.
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or not (child / ".git").exists():
                continue
            owner = _repo_owner_or_none(child)
            if not owner or owner not in allowed:
                continue
            found[child.name] = {
                "local_path": str(child),
                "owner": owner,
            }
    # Extras override the ownership filter — user opted in.
    for child in read_extras():
        owner = _repo_owner_or_none(child) or "extras"
        found[child.name] = {
            "local_path": str(child),
            "owner": owner,
        }
    return found


def discover_remote_repos(allowed: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not _have_gh():
        return out
    for owner in allowed:
        try:
            result = subprocess.run(
                ["gh", "repo", "list", owner, "--limit", "1000", "--json", "name"],
                capture_output=True, text=True, timeout=GH_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode != 0:
            continue
        try:
            entries = json.loads(result.stdout)
        except ValueError:
            continue
        for entry in entries:
            name = entry.get("name", "")
            if name:
                out.setdefault(name, []).append(owner)
    return out


def _have_gh() -> bool:
    try:
        return subprocess.run(
            ["gh", "auth", "status"], capture_output=True, timeout=5
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def cache_is_fresh() -> bool:
    if not REPO_CACHE.exists():
        return False
    age = time.time() - REPO_CACHE.stat().st_mtime
    return age < CACHE_TTL_SECONDS


def rebuild_cache() -> dict:
    allowed = load_allowed_owners()
    local = discover_local_repos(set(allowed))
    remote = discover_remote_repos(allowed)
    names: dict[str, dict] = {}
    for name, info in local.items():
        names[name] = {
            "local_path": info["local_path"],
            "remote_owners": [],
        }
    for name, owners in remote.items():
        if name in names:
            names[name]["remote_owners"] = owners
        else:
            names[name] = {"local_path": None, "remote_owners": owners}
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allowed_owners": allowed,
        "names": names,
    }
    try:
        REPO_CACHE.parent.mkdir(parents=True, exist_ok=True)
        REPO_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass
    log(f"cache rebuilt: {len(names)} names, owners={allowed}")
    return payload


def load_cache() -> dict:
    if cache_is_fresh():
        try:
            return json.loads(REPO_CACHE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return rebuild_cache()


def find_matches(prompt: str, cache: dict, stoplist: set[str]) -> list[tuple[str, dict]]:
    text = prompt.lower()
    out: list[tuple[str, dict]] = []
    for name, info in cache.get("names", {}).items():
        nlow = name.lower()
        if len(nlow) < MIN_NAME_LENGTH:
            continue
        if nlow in stoplist:
            continue
        # word-boundary match against lowercased prompt
        if re.search(rf"(?<![\w-]){re.escape(nlow)}(?![\w-])", text):
            out.append((name, info))
    return out


def cooldown_ok(name: str, info: dict) -> bool:
    local_path = info.get("local_path")
    if not local_path:
        return True
    rel = pathlib.Path(local_path).relative_to(HOME)
    last = LOCAL_BASE / rel / ".last-sync"
    if not last.exists():
        return True
    age = time.time() - last.stat().st_mtime
    return age >= COOLDOWN_SECONDS


def spawn_sync(name: str) -> None:
    if not SYNC_SCRIPT.exists():
        log(f"sync script missing: {SYNC_SCRIPT}")
        return
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            subprocess.Popen(
                ["bash", str(SYNC_SCRIPT), name],
                stdout=fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        log(f"spawned graphify-sync {name}")
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"spawn failed for {name}: {exc}")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)

    prompt = payload.get("prompt", "") or ""
    if not prompt.strip():
        sys.exit(0)

    try:
        stoplist = load_stoplist()
        cache = load_cache()
        matches = find_matches(prompt, cache, stoplist)
        if not matches:
            sys.exit(0)
        for name, info in matches:
            if not cooldown_ok(name, info):
                log(f"cooldown skip: {name}")
                continue
            # Touch last-sync proactively so a flurry of prompts doesn't
            # spawn duplicate syncs while one is already running.
            local_path = info.get("local_path")
            if local_path:
                try:
                    rel = pathlib.Path(local_path).relative_to(HOME)
                    last = LOCAL_BASE / rel / ".last-sync"
                    last.parent.mkdir(parents=True, exist_ok=True)
                    last.touch()
                except OSError:
                    pass
            spawn_sync(name)
    except Exception as exc:  # never let the hook block the prompt
        log(f"hook error: {type(exc).__name__}: {exc}")

    sys.exit(0)


if __name__ == "__main__":
    main()
