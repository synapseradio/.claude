#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Reads the hook input JSON from stdin, extracts the proposed shell command,
# and refuses (permissionDecision: "deny") when that command would print an
# environment variable whose name matches a secret-shaped pattern such as
# *API_KEY*, *TOKEN*, *SECRET*, *PASSWORD*, *CREDENTIAL*, *PRIVATE_KEY*, etc.
#
# The decision reads the programs lib/command_words.sh resolves, so a word
# inside a quoted argument or a search pattern names no program:
#   - printenv, as a program;
#   - bare env and bare set, as a program with no arguments (a redirect
#     aside), behind any wrapper the resolver steps over;
#   - an output command (OUTPUT_CMD) followed in the same program by a word
#     that holds a reference to a secret-shaped variable. The output command
#     may sit behind another launcher, as in `docker run img echo ...`, so any
#     word of the program counts, a quoted word apart.
#
# The resolver skips here-document bodies, which a shell fed on stdin runs,
# so a command that opens a here-document is also read as raw text, line by
# line, as it was before the resolver.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (deny is communicated via stdout, not exit code).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"

readonly SECRET_WORD='(API_?KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE_?KEY|ACCESS_?KEY|AUTH_?TOKEN|SESSION_?TOKEN|BEARER)'

# Commands whose primary purpose is emitting their arguments to stdout/stderr.
# `jq` and `awk` are included because they are commonly used to interpolate
# variables into output.
readonly OUTPUT_CMD='(echo|printf|print|cat|tee|jq|awk|yes)'

# A dollar-reference, with or without braces, to a secret-shaped variable.
# Single quotes are intentional: the pattern matches the literal `$`.
# shellcheck disable=SC2016
readonly SECRET_REFERENCE='\$\{?[A-Za-z_]*'"${SECRET_WORD}"

# Appended to the words of a part that ends in env, to learn whether env
# stands alone behind its wrappers: the resolver then prints this word as the
# program, where it prints nothing for a bare env.
readonly BARE_SENTINEL='__warden_nothing_behind_env__'

#######################################
# Emit a deny decision and exit.
# Arguments:
#   $1 - human-readable reason shown in the permission prompt UI.
#######################################
deny() {
  local reason="$1"
  jq -nc --arg r "${reason}" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

#######################################
# Report whether a program's words hold an output command followed by a word
# that references a secret-shaped variable.
# Arguments:
#   The program's words.
# Returns:
#   0 when they do, 1 otherwise.
#######################################
prints_secret() {
  local seen=0 word
  for word in "$@"; do
    if ((seen)) && [[ "${word}" =~ ${SECRET_REFERENCE} ]]; then
      return 0
    fi
    if [[ "${word##*/}" =~ ^${OUTPUT_CMD}$ ]]; then
      seen=1
    fi
  done
  return 1
}

#######################################
# Deny when one program line dumps the environment or prints a secret.
# Arguments:
#   $1 - a program line from command_words::resolve.
#######################################
check_program() {
  local -a words
  IFS=' ' read -r -a words <<<"$1"
  ((${#words[@]} > 0)) || return 0

  if prints_secret "${words[@]}"; then
    deny "Refused: command would print an env var matching a secret pattern (API_KEY/TOKEN/SECRET/...). If this is intentional, run it yourself."
  fi

  # printenv: its sole purpose is showing env.
  if [[ "${words[0]}" == printenv ]]; then
    deny "Refused: printenv would print env vars to stdout. If this is intentional, run it yourself."
  fi

  # `set` with no args dumps every shell variable.
  if [[ "${words[0]}" == set ]] && { ((${#words[@]} == 1)) || [[ "${words[1]}" == '>'* ]]; }; then
    deny "Refused: bare 'set' would dump every shell variable. If this is intentional, run it yourself."
  fi
}

#######################################
# Deny when one part of the command is env with nothing behind it: `env`
# alone, behind wrappers, or ahead of a redirect. `env CMD ARGS` launches a
# subprocess and stays allowed.
# Arguments:
#   $1 - a part from command_words::split.
#######################################
check_bare_env() {
  local -a words head
  local word last behind
  IFS=' ' read -r -a words <<<"$1"
  head=()
  for word in ${words[@]+"${words[@]}"}; do
    [[ "${word}" == '>'* ]] && break
    head+=("${word}")
  done
  ((${#head[@]} > 0)) || return 0
  last="${head[${#head[@]} - 1]}"
  [[ "${last##*/}" == env ]] || return 0

  behind="$(command_words::emit_command "${head[@]}" "${BARE_SENTINEL}")"
  if [[ "${behind}" == "${BARE_SENTINEL}" ]]; then
    deny "Refused: bare 'env' would dump every env var to stdout. If this is intentional, run it yourself."
  fi
}

#######################################
# The checks as they ran on raw text, for the body of a here-document that
# the resolver skips. ripgrep is used because bash's =~ ERE engine lacks \b
# word boundaries.
# Arguments:
#   $1 - the command text.
#######################################
check_raw_text() {
  local cmd="$1" bare
  if rg -q \
    "\b${OUTPUT_CMD}\b[^|;&]*\\\$\{?[A-Za-z_]*${SECRET_WORD}[A-Za-z_0-9]*" \
    <<<"${cmd}"; then
    deny "Refused: command would print an env var matching a secret pattern (API_KEY/TOKEN/SECRET/...). If this is intentional, run it yourself."
  fi
  if rg -q '\bprintenv\b' <<<"${cmd}"; then
    deny "Refused: printenv would print env vars to stdout. If this is intentional, run it yourself."
  fi
  bare='(^|[;&|`(])[[:space:]]*([A-Za-z0-9_.-]+[[:space:]]+)?'
  if rg -q "${bare}env[[:space:]]*(\||;|&|>|\$)" <<<"${cmd}"; then
    deny "Refused: bare 'env' would dump every env var to stdout. If this is intentional, run it yourself."
  fi
  if rg -q "${bare}set[[:space:]]*(\||;|&|>|\$)" <<<"${cmd}"; then
    deny "Refused: bare 'set' would dump every shell variable. If this is intentional, run it yourself."
  fi
}

main() {
  local cmd line
  cmd="$(jq -r '.tool_input.command // ""')"

  if [[ -z "${cmd}" ]]; then
    exit 0
  fi

  while IFS= read -r line; do
    check_program "${line}"
  done < <(command_words::resolve "${cmd}")

  while IFS= read -r line; do
    check_bare_env "${line}"
  done < <(command_words::split "${cmd}")

  # A here-document opens with << and not <<<, the here-string.
  if [[ "${cmd}" =~ (^|[^\<])\<\<[^\<] ]]; then
    check_raw_text "${cmd}"
  fi

  exit 0
}

main "$@"
