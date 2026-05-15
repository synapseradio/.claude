"""HTTP client for the local `mlx_lm.server`.

One focused yes/no call per verdict, dispatched in parallel via a
`ThreadPoolExecutor`. The model answers free-form `yes` or `no` and a
strict-first-word parser at the boundary turns the response into a
bool. Any deviation is treated as a judge failure: `judge_many`
returns `None` for the whole batch and the dispatcher fails closed,
emitting `compose.FALLBACK_REPLAN_SLIM` via the binding's action
shape instead of a verdict-derived block reason.

The host and port the client probes are read from
`scripts/arbiter/arbiter-config.sh` at module import. That shell file
is the single source of truth for the running daemon — sourcing it
here keeps the hook in lockstep with whatever `arbiter-up.sh` last
spawned. If the file is unreadable, missing, or missing the expected
`ARBITER_HOST` / `ARBITER_PORT` declarations, the import raises a
`RuntimeError` so config drift surfaces immediately rather than being
masked by a stale literal.

Before the parallel chat-completions fan-out, `judge_many` runs one
fast `/health` probe. A non-200 (or connect error) on `/health` short-
circuits the batch with a single labeled failure reason
(`health-<reason>`) instead of four near-identical chat-completions
errors. That distinguishes "judge truly down" from "one chat call
flaked" in the log without changing the fail-closed contract the
dispatcher depends on.

mlx_lm.server returns HTTP 200 with `{"status": "ok"}` once it can
answer chat-completion requests. Weights are mapped lazily, so the
first `/v1/chat/completions` call pays the warm-up cost and
subsequent calls are fast.
"""

import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

# arbiter-config.sh sits two directories above this file:
#   scripts/arbiter/lib/client.py  →  scripts/arbiter/arbiter-config.sh
_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "arbiter-config.sh"

# `readonly NAME="value"` or `NAME="value"` — quotes optional, value
# must be a literal. `$` and `` ` `` are forbidden in the captured
# value so `${VAR:-default}`, `$(cmd)`, and `\`cmd\`` all leak through
# to the env/default fallback rather than being captured as a literal
# string.
_BASH_ASSIGN = re.compile(
    r"""^\s*(?:readonly\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?(?P<value>[^"\n#$`]+?)"?\s*(?:#.*)?$"""
)


def _parse_arbiter_config(path: pathlib.Path) -> dict[str, str]:
    """Pull simple `NAME="value"` declarations out of arbiter-config.sh.

    Returns a flat dict. Unparseable lines are skipped silently — the
    file is bash, not python, and the loader only needs a couple of
    string constants. Anything we cannot extract falls back to the
    defaults at module level.
    """
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        m = _BASH_ASSIGN.match(line)
        if not m:
            continue
        out[m.group("name")] = m.group("value").strip()
    return out


def _resolve_endpoint() -> tuple[str, int, str]:
    """Resolve `(host, port, model)` from arbiter-config.sh, with env override.

    Override order (same for all three):
      1. Matching env var (live, no restart).
      2. Value parsed out of `arbiter-config.sh`.

    Raises `RuntimeError` if host, port, or model is missing or if
    `ARBITER_PORT` does not parse as an integer.
    """
    cfg = _parse_arbiter_config(_CONFIG_PATH)
    host = os.environ.get("ARBITER_HOST") or cfg.get("ARBITER_HOST")
    raw_port = os.environ.get("ARBITER_PORT") or cfg.get("ARBITER_PORT")
    model = os.environ.get("ARBITER_MODEL") or cfg.get("ARBITER_MODEL")
    if not host:
        raise RuntimeError(f"ARBITER_HOST not set in env or {_CONFIG_PATH}")
    if not raw_port:
        raise RuntimeError(f"ARBITER_PORT not set in env or {_CONFIG_PATH}")
    if not model:
        raise RuntimeError(f"ARBITER_MODEL not set in env or {_CONFIG_PATH}")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise RuntimeError(f"ARBITER_PORT={raw_port!r} is not a valid integer") from exc
    return host, port, model


_HOST, _PORT, _MODEL = _resolve_endpoint()
JUDGE_BASE_URL = f"http://{_HOST}:{_PORT}"
JUDGE_HEALTH_URL = f"{JUDGE_BASE_URL}/health"
JUDGE_URL = f"{JUDGE_BASE_URL}/v1/chat/completions"
# mlx_lm.server validates the OpenAI `model` field against the loaded
# model id and 404s on a mismatch, so the real HuggingFace id must be
# sent on every request.
JUDGE_MODEL_FIELD = _MODEL

# Generous ceiling: tolerates the first call after the server starts,
# which warms the weights into memory. Steady-state warm calls finish
# well under one second.
JUDGE_TIMEOUT_SECONDS = 90
# The /health probe is a yes/no liveness check, not an inference call.
# 2 seconds covers loopback + any kernel-level scheduling jitter
# without making the hook feel sluggish when the daemon really is
# down.
JUDGE_HEALTH_TIMEOUT_SECONDS = 2
# Each focused yes/no call should decide quickly. Qwen3 emits an
# empty `<think>\n\n</think>\n\n` block (~8 tokens) before the answer
# even with /no_think. 24 tokens holds both halves with margin.
JUDGE_MAX_TOKENS = 24

LOG_PATH = pathlib.Path.home() / ".claude" / "arbiter" / "logs" / "arbiter.log"

# /no_think collapses Qwen3's reasoning block to an empty pair of
# <think></think> tags instead of a multi-hundred-token chain of
# thought. Combined with the strict-first-word parser below, this
# keeps the call sub-second.
_OUTPUT_INSTRUCTION = (
    "\n\nAnswer with exactly one word: `yes` or `no`. Nothing else, no punctuation.\n\n/no_think"
)

# Qwen3 emits `<think>...</think>` reasoning even when the prompt
# requests a single-word answer. The /no_think directive collapses
# the block to an empty tag pair, but the tags themselves still
# appear in the response. Strip them before parsing so the parser
# sees only the answer.
_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)

_ERROR = "ERROR"
_CLEAR = "CLEAR"


def _probe_health() -> str | None:
    """Return None when the judge is healthy, else a short reason label.

    Labels are stable strings the log reader can grep:
      - `health-connect`  — TCP refused / DNS / unreachable host
      - `health-timeout`  — server bound but did not answer in time
      - `health-status`   — non-2xx response from /health
      - `health-body`     — 2xx but body did not contain `"status":"ok"`
      - `health-error`    — anything else urllib raised
    """
    try:
        with urllib.request.urlopen(JUDGE_HEALTH_URL, timeout=JUDGE_HEALTH_TIMEOUT_SECONDS) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            if status is None or not (200 <= int(status) < 300):
                return "health-status"
            try:
                body = resp.read(256).decode("utf-8", errors="replace")
            except OSError:
                return "health-body"
    except urllib.error.HTTPError:
        return "health-status"
    except urllib.error.URLError as exc:
        # urllib wraps connect-refused, no-route, and DNS failures as
        # URLError. TimeoutError shows up as URLError(TimeoutError(...))
        # under recent CPython, so peel one layer to distinguish.
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError):
            return "health-timeout"
        return "health-connect"
    except TimeoutError:
        return "health-timeout"
    except OSError:
        return "health-error"
    if '"status"' not in body or '"ok"' not in body:
        return "health-body"
    return None


def log_call(event: str, duration_ms: int, verdicts: str) -> None:
    """Append one line per judge call so the user can `tail` real timings."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{ts}  event={event}  duration_ms={duration_ms}  verdicts={verdicts}\n")
    except OSError:
        pass


def _extract_yes(body) -> bool | None:
    """Pull the boolean from an OpenAI-compatible chat-completions response.

    The model is instructed to answer with exactly `yes` or `no`. The
    parser tolerates leading whitespace, code-fence backticks, and
    trailing punctuation, but treats prose like "the answer is yes"
    as None — we asked for one word and got a sentence, which is a
    judge failure. Any malformed response shape returns None so the
    caller treats it as fail-closed.
    """
    if not isinstance(body, dict):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return None

    cleaned = _THINK_BLOCK.sub("", content)
    tok = cleaned.strip().lower().lstrip("`'\"")
    words = tok.split() if tok else []
    if not words:
        return None
    head = words[0].rstrip("`.,!?;:'\"")
    if head.startswith("yes"):
        return True
    if head.startswith("no"):
        return False
    return None


def _post_chat(body_text: str, framing: str, verdict_prompt: str) -> bool | None:
    """One POST attempt. Returns the yes/no judgment or None on any failure."""
    system_prompt = framing + verdict_prompt + _OUTPUT_INSTRUCTION
    framed = (
        "Below, between BEGIN and END markers, is the body to judge.\n\n"
        "===== BEGIN BODY =====\n"
        f"{body_text}\n"
        "===== END BODY =====\n"
    )

    payload = json.dumps(
        {
            "model": JUDGE_MODEL_FIELD,
            "stream": False,
            "max_tokens": JUDGE_MAX_TOKENS,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": framed},
            ],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        JUDGE_URL,
        data=payload,
        method="POST",
        headers={"content-type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=JUDGE_TIMEOUT_SECONDS) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError:
        return None

    return _extract_yes(body)


def _judge_one(body_text: str, framing: str, verdict_prompt: str) -> bool | None:
    """One focused yes/no judge call. Returns True/False, or None on error.

    None signals an outage or malformed response — the caller treats
    that as a fail-closed signal across the whole judgment. Uses the
    OpenAI-compatible /v1/chat/completions endpoint that mlx_lm.server
    exposes.
    """
    return _post_chat(body_text, framing, verdict_prompt)


def judge_many(body_text: str, framing: str, verdict_specs: list, event: str):
    """Run one focused call per verdict in parallel.

    Returns:
      - [] when none fired
      - [verdict_key, ...] (snake_case keys) when one or more fired
      - None when any call failed (fail-closed signal)

    A `/health` probe runs first. If the daemon is unreachable or
    unhealthy, the function logs the specific reason
    (`ERROR:health-<label>`) and returns `None` without making any
    chat-completions calls.
    """
    if not verdict_specs:
        log_call(event, 0, _CLEAR)
        return []

    started = time.monotonic()

    health_reason = _probe_health()
    if health_reason is not None:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        log_call(event, elapsed_ms, f"{_ERROR}:{health_reason}")
        return None

    with ThreadPoolExecutor(max_workers=len(verdict_specs)) as pool:
        futures = {
            pool.submit(_judge_one, body_text, framing, spec.prompt): spec.key
            for spec in verdict_specs
        }
        results: dict[str, bool | None] = {}
        for fut in futures:
            key = futures[fut]
            try:
                results[key] = fut.result()
            except Exception:
                results[key] = None
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if any(v is None for v in results.values()):
        errored = [k for k, v in results.items() if v is None]
        log_call(event, elapsed_ms, f"{_ERROR}:{','.join(errored)}")
        return None

    fired_specs = [spec for spec in verdict_specs if results[spec.key]]
    if not fired_specs:
        log_call(event, elapsed_ms, _CLEAR)
        return []
    log_call(event, elapsed_ms, ",".join(spec.name for spec in fired_specs))
    return [spec.key for spec in fired_specs]
