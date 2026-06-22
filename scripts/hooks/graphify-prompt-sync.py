#!/usr/bin/env python3
"""UserPromptSubmit hook: fire `lodestar sync <name>` when a prompt names an
in-scope repo.

Reads JSON {prompt, ...} on stdin. Tokenizes the prompt text, intersects with
the cached name -> location map at ~/.graphify/.repo-cache.json (rebuilt every
24h), filters names shorter than the configured minimum and names in the
stoplist, and spawns a detached `lodestar sync` per match. Never blocks. Never
prints to stdout. All activity goes to ~/.cache/grip.log.

Scope is resolved from one YAML config, shared with the lodestar bash CLI, at
${LODESTAR_CONFIG_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/lodestar/config.yaml}.
The config supplies owners, scan roots, the explicit repo registry, the output
base, and the hook's stoplist and minimum name length. A missing, unparseable,
or PyYAML-less config degrades to built-in defaults that reproduce lodestar's
historical hardcoded scope. The hook always exits 0 and never raises into the
prompt.

The gh-authenticated user is always implicitly in scope, added on top of the
configured owners.

Cooldown: 1h per repo, tracked via the .last-sync touchfile under the per-repo
output base.

Missing-but-in-scope repos are cloned on demand by `lodestar sync` itself.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime

HOME = pathlib.Path.home()
GRAPHIFY_HOME = HOME / ".graphify"
REPO_CACHE = GRAPHIFY_HOME / ".repo-cache.json"
LOG_FILE = HOME / ".cache" / "grip.log"

CACHE_TTL_SECONDS = 24 * 60 * 60
COOLDOWN_SECONDS = 60 * 60
GH_TIMEOUT_SECONDS = 15

DEFAULT_OWNERS = ["amboss-mededu"]
DEFAULT_SCAN_ROOTS = ["~/projects", "~/projects/ai"]
DEFAULT_OUTPUT_BASE = "~/.graphify/local"
DEFAULT_MIN_NAME_LENGTH = 4

DEFAULT_STOPLIST = [
    "play",
    "core",
    "panda",
    "dollas",
    "lingua",
    "design",
    "common",
    "shared",
    "main",
    "docs",
    "test",
    "tests",
    "build",
    "dist",
    "util",
    "utils",
    "skills",
]


def log(msg: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"[{ts}] [prompt-hook] {msg}\n")
    except OSError:
        pass


def _expand_path(value: str) -> str:
    """Expand a leading ~ and $HOME/${HOME} to the home directory."""
    return os.path.expanduser(os.path.expandvars(value))


def config_path() -> pathlib.Path:
    explicit = os.environ.get("LODESTAR_CONFIG_FILE")
    if explicit:
        return pathlib.Path(explicit)
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(HOME / ".config")
    return pathlib.Path(xdg) / "lodestar" / "config.yaml"


def load_config() -> dict | None:
    """Load the shared lodestar YAML config.

    Returns the parsed mapping, or None when the config is missing,
    unparseable, not a mapping, or PyYAML is unavailable. Callers treat None as
    "apply built-in defaults", so the hook degrades to historical scope without
    ever raising into the prompt.
    """
    path = config_path()
    if not path.exists():
        return None
    try:
        import yaml
    except ImportError:
        log("PyYAML unavailable; degrading to built-in scope defaults")
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        log(f"config unreadable ({path}): {type(exc).__name__}: {exc}; using defaults")
        return None
    if not isinstance(data, dict):
        log(f"config is not a mapping ({path}); using defaults")
        return None
    return data


def gh_authenticated_user() -> str | None:
    """Return the gh-authenticated user's login, or None when unavailable."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except OSError, subprocess.SubprocessError:
        return None
    if result.returncode != 0:
        return None
    login = result.stdout.strip()
    return login or None


def resolve_owners(cfg: dict | None) -> list[str]:
    """Configured owners plus the always-implicit gh-authenticated user."""
    owners = list(DEFAULT_OWNERS)
    if cfg is not None:
        configured = cfg.get("owners")
        if isinstance(configured, list) and configured:
            owners = [str(o).strip() for o in configured if str(o).strip()]
    gh_user = gh_authenticated_user()
    if gh_user and gh_user not in owners:
        owners.append(gh_user)
    return owners


def resolve_scan_roots(cfg: dict | None) -> list[str]:
    roots = DEFAULT_SCAN_ROOTS
    if cfg is not None:
        configured = cfg.get("scan_roots")
        if isinstance(configured, list) and configured:
            roots = [str(r) for r in configured if str(r).strip()]
    return [_expand_path(r) for r in roots]


def resolve_output_base(cfg: dict | None) -> str:
    base = DEFAULT_OUTPUT_BASE
    if cfg is not None:
        paths = cfg.get("paths")
        if isinstance(paths, dict):
            configured = paths.get("output_base")
            if isinstance(configured, str) and configured.strip():
                base = configured
    return _expand_path(base)


def resolve_stoplist(cfg: dict | None) -> set[str]:
    if cfg is not None:
        hook = cfg.get("hook")
        if isinstance(hook, dict):
            configured = hook.get("stoplist")
            if isinstance(configured, list) and configured:
                return {str(s).strip().lower() for s in configured if str(s).strip()}
    return set(DEFAULT_STOPLIST)


def resolve_min_name_len(cfg: dict | None) -> int:
    if cfg is not None:
        hook = cfg.get("hook")
        if isinstance(hook, dict):
            configured = hook.get("min_name_len")
            if isinstance(configured, int) and configured > 0:
                return configured
    return DEFAULT_MIN_NAME_LENGTH


def resolve_repos(cfg: dict | None) -> list[dict]:
    """Enabled entries from the explicit repo registry.

    Each returned item is a dict with at least a `name`. Entries marked
    `disabled: true` are excluded from auto-detection (they stay in the config
    on disk; this only affects what the hook will match).
    """
    if cfg is None:
        return []
    registry = cfg.get("repos")
    if not isinstance(registry, list):
        return []
    out: list[dict] = []
    for entry in registry:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name or not str(name).strip():
            continue
        if entry.get("disabled") is True:
            continue
        item = dict(entry)
        item["name"] = str(name).strip()
        if isinstance(item.get("path"), str):
            item["path"] = _expand_path(item["path"])
        out.append(item)
    return out


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
            capture_output=True,
            text=True,
            timeout=5,
        )
    except OSError, subprocess.SubprocessError:
        return None
    if result.returncode != 0:
        return None
    parsed = parse_origin(result.stdout)
    if not parsed:
        return None
    return parsed[0]


def discover_local_repos(
    allowed: set[str], scan_roots: list[str], repos: list[dict]
) -> dict[str, dict]:
    found: dict[str, dict] = {}
    # Scan discovery roots — only in-scope repos (by git origin owner) make it in.
    for root_str in scan_roots:
        root = pathlib.Path(root_str)
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
    # Explicit registry entries (enabled only) — opted in regardless of scan roots.
    for entry in repos:
        path = entry.get("path")
        if not path:
            continue
        p = pathlib.Path(path)
        if not (p.is_dir() and (p / ".git").exists()):
            continue
        owner = entry.get("owner") or _repo_owner_or_none(p) or "registry"
        found[entry["name"]] = {
            "local_path": str(p),
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
                capture_output=True,
                text=True,
                timeout=GH_TIMEOUT_SECONDS,
            )
        except OSError, subprocess.SubprocessError:
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
        return (
            subprocess.run(["gh", "auth", "status"], capture_output=True, timeout=5).returncode == 0
        )
    except OSError, subprocess.SubprocessError:
        return False


def cache_is_fresh() -> bool:
    if not REPO_CACHE.exists():
        return False
    age = time.time() - REPO_CACHE.stat().st_mtime
    return age < CACHE_TTL_SECONDS


def rebuild_cache(cfg: dict | None) -> dict:
    allowed = resolve_owners(cfg)
    scan_roots = resolve_scan_roots(cfg)
    repos = resolve_repos(cfg)
    local = discover_local_repos(set(allowed), scan_roots, repos)
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
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
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


def load_cache(cfg: dict | None) -> dict:
    if cache_is_fresh():
        try:
            return json.loads(REPO_CACHE.read_text(encoding="utf-8"))
        except OSError, ValueError:
            pass
    return rebuild_cache(cfg)


def find_matches(
    prompt: str, cache: dict, stoplist: set[str], min_name_len: int
) -> list[tuple[str, dict]]:
    text = prompt.lower()
    out: list[tuple[str, dict]] = []
    for name, info in cache.get("names", {}).items():
        nlow = name.lower()
        if len(nlow) < min_name_len:
            continue
        if nlow in stoplist:
            continue
        # word-boundary match against lowercased prompt
        if re.search(rf"(?<![\w-]){re.escape(nlow)}(?![\w-])", text):
            out.append((name, info))
    return out


def cooldown_ok(name: str, info: dict, output_base: str) -> bool:
    local_path = info.get("local_path")
    if not local_path:
        return True
    try:
        rel = pathlib.Path(local_path).relative_to(HOME)
    except ValueError:
        rel = pathlib.Path(pathlib.Path(local_path).name)
    last = pathlib.Path(output_base) / rel / ".last-sync"
    if not last.exists():
        return True
    age = time.time() - last.stat().st_mtime
    return age >= COOLDOWN_SECONDS


def spawn_sync(name: str) -> None:
    lodestar = shutil.which("lodestar")
    if not lodestar:
        log(f"lodestar not on PATH; skipping sync for {name}")
        return
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            subprocess.Popen(
                [lodestar, "sync", name],
                stdout=fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        log(f"spawned lodestar sync {name}")
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
        cfg = load_config()
        stoplist = resolve_stoplist(cfg)
        min_name_len = resolve_min_name_len(cfg)
        output_base = resolve_output_base(cfg)
        cache = load_cache(cfg)
        matches = find_matches(prompt, cache, stoplist, min_name_len)
        if not matches:
            sys.exit(0)
        for name, info in matches:
            if not cooldown_ok(name, info, output_base):
                log(f"cooldown skip: {name}")
                continue
            # Touch last-sync proactively so a flurry of prompts doesn't
            # spawn duplicate syncs while one is already running.
            local_path = info.get("local_path")
            if local_path:
                try:
                    try:
                        rel = pathlib.Path(local_path).relative_to(HOME)
                    except ValueError:
                        rel = pathlib.Path(pathlib.Path(local_path).name)
                    last = pathlib.Path(output_base) / rel / ".last-sync"
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
