"""HTTP client for the local `llama-server`.

One focused yes/no call per verdict, dispatched in parallel via a
`ThreadPoolExecutor`. Schema-forced JSON output keeps the response
shape `{"yes": <bool>}` deterministic. Any deviation is treated as a
judge failure: `judge_many` returns `None` for the whole batch and
the dispatcher fails closed, emitting `compose.FALLBACK_REPLAN_SLIM`
via the binding's action shape instead of a verdict-derived block
reason.

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

`/health` distinguishes two kinds of unavailability. llama.cpp returns
HTTP 503 with `{"error":{"message":"Loading model",...}}` while the
weights are still loading, and HTTP 200 with `{"status":"ok"}` once
the server can answer chat-completion requests. The probe surfaces the
loading state as the `JUDGE_COLD` sentinel so the dispatcher can no-op
silently during the cold-load window — a fail-closed message during
startup would flood the user the moment they kicked off a session and
trains them to disable the safety net.

A single chat-completion call that comes back HTTP 400 with
"exceeds the available context size" gets one retry whose body is
tail-trimmed to the last `_BODY_TAIL_LINES` lines. The slot context
in llama-server is roughly `--ctx-size / --parallel`, so a long plan
or essay-length turn-ending message can overflow without anything
being wrong with the daemon. The retry preserves a judgment for the
closing of the message, which is where the verdicts Arbiter cares
about (open questions, uncommitted alternatives, out-of-scope
dismissals) tend to live.
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

YES_NO_SCHEMA = {
    "type": "object",
    "properties": {"yes": {"type": "boolean"}},
    "required": ["yes"],
}

# Sentinel returned by `judge_many` when the daemon is up but the model
# is still loading. The dispatcher treats this as a no-op rather than a
# fail-closed signal, so cold start does not produce block messages.
JUDGE_COLD = object()

# Tail size for the oversize retry. 100 lines of typical prose fits
# inside the per-slot context window for the daemon's default
# configuration. Rare cases where 100 lines still overflows fall
# through to the standard fail-closed path.
_BODY_TAIL_LINES = 100

# arbiter-config.sh sits two directories above this file:
#   scripts/arbiter/lib/client.py  →  scripts/arbiter/arbiter-config.sh
_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "arbiter-config.sh"

# `readonly NAME="value"` or `NAME="value"` — quotes optional, value
# must be a literal (no command substitution, no $-expansion). Anything
# fancier means the operator stepped outside what this loader handles
# and the fallback kicks in.
_BASH_ASSIGN = re.compile(
    r"""^\s*(?:readonly\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?(?P<value>[^"\n#]+?)"?\s*(?:#.*)?$"""
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


def _resolve_endpoint() -> tuple[str, int]:
    """Resolve `(host, port)` from arbiter-config.sh, with env override.

    Override order:
      1. `ARBITER_HOST` / `ARBITER_PORT` env vars (live, no restart).
      2. Values parsed out of `arbiter-config.sh` (canonical source of
         truth — what `arbiter-up.sh` consumes).

    Raises `RuntimeError` if neither source yields a value, or if
    `ARBITER_PORT` does not parse as an integer.
    """
    cfg = _parse_arbiter_config(_CONFIG_PATH)
    host = os.environ.get("ARBITER_HOST") or cfg.get("ARBITER_HOST")
    raw_port = os.environ.get("ARBITER_PORT") or cfg.get("ARBITER_PORT")
    if not host:
        raise RuntimeError(f"ARBITER_HOST not set in env or {_CONFIG_PATH}")
    if not raw_port:
        raise RuntimeError(f"ARBITER_PORT not set in env or {_CONFIG_PATH}")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise RuntimeError(f"ARBITER_PORT={raw_port!r} is not a valid integer") from exc
    return host, port


_HOST, _PORT = _resolve_endpoint()
JUDGE_BASE_URL = f"http://{_HOST}:{_PORT}"
JUDGE_HEALTH_URL = f"{JUDGE_BASE_URL}/health"
JUDGE_URL = f"{JUDGE_BASE_URL}/v1/chat/completions"

# llama-server doesn't dispatch by model name when only one model is
# loaded, but the OpenAI schema requires the field. The actual model
# is whatever scripts/arbiter/arbiter-up.sh pinned at startup.
JUDGE_MODEL_FIELD = "judge"
# Generous ceiling: tolerates cold weights load on first call after
# the server starts. Steady-state warm calls finish well under one
# second.
JUDGE_TIMEOUT_SECONDS = 90
# The /health probe is a yes/no liveness check, not an inference call.
# llama-server's /health endpoint returns instantly when the server is
# accepting requests; 2 seconds covers loopback + any kernel-level
# scheduling jitter without making the hook feel sluggish when the
# daemon really is down.
JUDGE_HEALTH_TIMEOUT_SECONDS = 2
# Each focused yes/no call should decide quickly. Schema-forced
# output keeps decode short; 32 tokens covers `{"yes": false}` plus
# whitespace with margin.
JUDGE_MAX_TOKENS = 32

LOG_PATH = pathlib.Path.home() / ".claude" / "logs" / "arbiter.log"

_OUTPUT_INSTRUCTION = '\n\nOutput exactly `{"yes": true}` or `{"yes": false}`. JSON only, no prose.'

_ERROR = "ERROR"
_CLEAR = "CLEAR"


def _probe_health() -> str | None:
    """Return None when the judge is healthy, else a short reason label.

    Labels are stable strings the log reader can grep:
      - `cold`            — HTTP 503 with `Loading model` body. The daemon
                            is up but the model has not finished loading.
                            The caller turns this into `JUDGE_COLD`.
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
    except urllib.error.HTTPError as exc:
        # llama.cpp returns 503 with `{"error":{"message":"Loading model",...}}`
        # while the weights are still loading. Treat as cold rather than
        # outage so the dispatcher can stay silent during the cold-load
        # window. Any other HTTPError is a real outage.
        try:
            err_body = exc.read(256).decode("utf-8", errors="replace")
        except OSError:
            err_body = ""
        if exc.code == 503 and "Loading model" in err_body:
            return "cold"
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


def _tail_lines(text: str, n: int = _BODY_TAIL_LINES) -> str:
    """Return the last `n` lines of `text`, or `text` unchanged when shorter."""
    lines = text.splitlines()
    if len(lines) <= n:
        return text
    return "\n".join(lines[-n:])


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

    Schema-forced output is `{"yes": <bool>}` inside
    `choices[0].message.content`. Any deviation returns None so the
    caller treats the response as a judge failure and falls back
    closed.
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
    try:
        parsed = json.loads(content)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    yes = parsed.get("yes")
    if not isinstance(yes, bool):
        return None
    return yes


def _post_chat(body_text: str, framing: str, verdict_prompt: str) -> tuple[bool | None, str | None]:
    """One POST attempt. Returns (yes/no, reason_label).

    `reason_label` is `None` on success or generic failure, and
    `"oversize"` when llama-server returned HTTP 400 with the
    "exceeds the available context size" body. The caller uses that
    label to decide whether retrying with a tail-trimmed body is
    worthwhile.
    """
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
            # llama.cpp extension to /v1/chat/completions. Disables the
            # slot's prefix KV-cache reuse so each judgment recomputes
            # the full forward pass from scratch. The cache is a pure
            # speed optimization, but reuse can introduce floating-point
            # nondeterminism between batched and non-batched paths, which
            # in turn can flip a borderline yes/no. The cost of disabling
            # is one prefill of the framing+verdict prompt per call —
            # acceptable on a local GPU 4B.
            "cache_prompt": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "yes_no", "schema": YES_NO_SCHEMA},
            },
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
    except urllib.error.HTTPError as exc:
        try:
            err_body = exc.read(512).decode("utf-8", errors="replace")
        except OSError:
            err_body = ""
        if exc.code == 400 and "exceeds the available context" in err_body:
            return None, "oversize"
        return None, None
    except urllib.error.URLError, TimeoutError, OSError, ValueError:
        return None, None

    return _extract_yes(body), None


def _judge_one(body_text: str, framing: str, verdict_prompt: str) -> bool | None:
    """One focused yes/no judge call. Returns True/False, or None on error.

    None signals an outage or malformed response — the caller treats
    that as a fail-closed signal across the whole judgment. Uses the
    OpenAI-compatible /v1/chat/completions endpoint that llama-server
    exposes; schema is enforced via `response_format.json_schema`.

    On HTTP 400 "exceeds the available context size", the call retries
    once with the body tailed to the last `_BODY_TAIL_LINES` lines.
    Truncation only happens on retry — the first attempt always sees
    the full body so short messages are judged in full.
    """
    result, reason = _post_chat(body_text, framing, verdict_prompt)
    if reason == "oversize":
        result, _ = _post_chat(_tail_lines(body_text), framing, verdict_prompt)
    return result


def judge_many(body_text: str, framing: str, verdict_specs: list, event: str):
    """Run one focused call per verdict in parallel.

    Returns:
      - [] when none fired
      - [verdict_key, ...] (snake_case keys) when one or more fired
      - JUDGE_COLD when the daemon is up but the model is still
        loading (HTTP 503 + "Loading model" body on /health). The
        caller should treat this as a no-op rather than fail-closed.
      - None when any call failed (fail-closed signal)

    A `/health` probe runs first. If the daemon is unreachable or
    unhealthy, the function logs the specific reason
    (`ERROR:health-<label>`) and returns `None` without making any
    chat-completions calls. The cold-load case is logged as
    `SKIP:cold` instead, since it is not an error.
    """
    if not verdict_specs:
        log_call(event, 0, _CLEAR)
        return []

    started = time.monotonic()

    health_reason = _probe_health()
    if health_reason == "cold":
        elapsed_ms = int((time.monotonic() - started) * 1000)
        log_call(event, elapsed_ms, "SKIP:cold")
        return JUDGE_COLD
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
