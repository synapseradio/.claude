# shellcheck shell=bash
# shellcheck disable=SC2034
# Every constant declared here is consumed after sourcing — the
# disable silences SC2034 ("appears unused") when shellcheck checks
# this file standalone, with no caller in view.
#
# Single source of truth for the Arbiter llama-server. Sourced by
# arbiter-up.sh and (indirectly via env reads) by callers that want
# to stay aligned with the running server.
#
# Updating values here only takes effect on the next arbiter-up.sh
# run. A running server keeps the values it was started with — by
# design, so parallel Claude Code sessions never restart each other's
# daemon.

# Model blob. Currently points at Ollama's local cache to avoid a
# duplicate download. Both qwen3:4b and phi4-mini blobs sit here as
# immutable sha256-named files.
readonly ARBITER_MODEL_PATH="${HOME}/.ollama/models/blobs/sha256-3e4cb14174460404e7a233e531675303b2fbf7749c02f91864fe311ab6344e4f"
readonly ARBITER_MODEL_LABEL="qwen3:4b"

# Network. 127.0.0.1 only — the judge is private to this machine.
readonly ARBITER_HOST="127.0.0.1"
readonly ARBITER_PORT="11436"

# Inference. ctx=8192 split across 5 parallel slots gives ~1638
# tokens per slot, rounded by llama.cpp to 2048. Each focused
# yes/no judge call sends 300-1500 tokens (framing + verdict prompt
# + body wrapped between BEGIN/END markers), so 2048 leaves real
# headroom for long turn-ending messages.
readonly ARBITER_CTX="8192"
readonly ARBITER_PARALLEL="5"

# Reasoning is off because Qwen3 burns 200-400 tokens of <think>
# before answering — incompatible with sub-second latency targets.
# Schema-forced output via response_format keeps the answer
# deterministic without needing reasoning.
ARBITER_EXTRA_FLAGS=(
  --jinja
  --reasoning off
  --reasoning-budget 0
)
readonly ARBITER_EXTRA_FLAGS

# Filesystem. The daemon writes its own stdout/stderr to
# arbiter-server.log; the per-call hook records (structured one-line
# entries written by lib/client.py) live in arbiter.log. Keeping the
# two streams separate prevents interleaved writes when the daemon
# is busy.
readonly ARBITER_LOG_FILE="${HOME}/.claude/logs/arbiter-server.log"
readonly ARBITER_PID_FILE="${HOME}/.claude/state/arbiter.pid"
