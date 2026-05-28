# shellcheck shell=bash
# shellcheck disable=SC2034
# Every constant declared here is consumed after sourcing — the
# disable silences SC2034 ("appears unused") when shellcheck checks
# this file standalone, with no caller in view.
#
# Single source of truth for the Arbiter judge daemon. Sourced by
# arbiter-up.sh and (indirectly via env reads) by callers that want
# to stay aligned with the running server.
#
# The daemon is mlx_lm.server (Apple Silicon native, dynamic KV
# allocation) serving Qwen3-4B 4-bit MLX weights. Free-form yes/no
# output, parsed at the boundary.

# Model. HuggingFace identifier — mlx_lm.server resolves it through
# the local HF cache (or downloads on first run).
readonly ARBITER_MODEL="mlx-community/Qwen3-4B-4bit"

# Launcher binary. Ships with the `mlx-lm` PyPI package. Default
# path matches `pip install --user mlx-lm` on macOS with the system
# python3.
readonly ARBITER_BIN="${HOME}/Library/Python/3.9/bin/mlx_lm.server"

# Network. 127.0.0.1 only — the judge is private to this machine.
readonly ARBITER_HOST="127.0.0.1"
readonly ARBITER_PORT="11436"

# Filesystem. The daemon writes its own stdout/stderr to
# arbiter-server.log; the per-call hook records (structured one-line
# entries written by lib/client.py) live in arbiter.log. Keeping the
# two streams separate prevents interleaved writes when the daemon
# is busy.
readonly ARBITER_LOG_FILE="${HOME}/.claude/arbiter/logs/arbiter-server.log"
readonly ARBITER_PID_FILE="${HOME}/.claude/arbiter/state/arbiter.pid"

# On-off switch. When this sentinel file exists, arbiter-up.sh skips
# spawning the daemon and arbiter-hook.py exits silently before
# dispatching. The Python side reads the same path via os.environ
# fallback to a hardcoded default — keep these in sync if you move
# the state directory.
readonly ARBITER_DISABLED_FILE="${HOME}/.claude/arbiter/state/disabled"
