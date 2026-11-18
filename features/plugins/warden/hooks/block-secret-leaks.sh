#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Reads the hook input JSON from stdin, extracts the proposed shell command,
# and refuses (permissionDecision: "deny") when that command would print an
# environment variable whose name matches a secret-shaped pattern such as
# *API_KEY*, *TOKEN*, *SECRET*, *PASSWORD*, *CREDENTIAL*, *PRIVATE_KEY*, etc.
#
# The decision reads the programs lib/command_words.sh resolves. Each program
# line is judged by its words, wherever they stand in it, so that a launcher
# the resolver does not unwrap, as in `timeout 5 printenv`, `docker exec c
# printenv`, or `ssh host env`, hides nothing. One word is left out: the
# pattern operand of grep and rg, which names what to search for and runs
# nothing (lib/search_operands.sh). The judgments:
#   - the word printenv;
#   - env as the last word, a redirect aside; bare env behind a wrapper the
#     resolver does step over is read from the parts of the command instead,
#     since the resolver prints nothing for it;
#   - bare set, as the program with no arguments, a redirect aside;
#   - an output command (OUTPUT_CMD) followed by a word that holds a
#     reference to a secret-shaped variable, looking inside a quoted word
#     too, as in `ssh host 'echo ...'`.
#
# The resolver skips here-document bodies, which a shell fed on stdin runs,
# so a command that opens a here-document is also read as raw text, line by
# line, as it was before the resolver.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (deny is communicated via stdout, not exit code).
# Sourced: defines decide_bash and main, and runs neither.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -euo pipefail
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"
# shellcheck source=lib/search_operands.sh
source "${SCRIPT_DIR}/lib/search_operands.sh"
# shellcheck source=lib/decision.sh
source "${SCRIPT_DIR}/lib/decision.sh"
# shellcheck source=lib/secret_advice.sh
source "${SCRIPT_DIR}/lib/secret_advice.sh"

# What a refusal tells the agent to run instead of printing the environment.
# The message never repeats a name or value from the command: a refusal only
# has the pattern to go on.
readonly ADVICE_NAME_ONE="Name the one variable you need: echo \"\$NAME\" for one that is not a secret, or [ -n \"\${NAME:-}\" ] && echo set to check a secret one."

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

# The four refusals, each said once for the program checks and the raw-text
# checks alike.

#######################################
# Deny a command that would print a secret-shaped variable.
# Globals:
#   GUARD_DECISION, GUARD_REASON
#######################################
deny_print_secret() {
  decision::reach deny "Refused: command would print an env var matching a secret pattern (API_KEY/TOKEN/SECRET/...). $(secret_advice::test_set) If this is intentional, run it yourself."
}

#######################################
# Deny a command that runs printenv.
# Globals:
#   GUARD_DECISION, GUARD_REASON
#######################################
deny_printenv() {
  decision::reach deny "Refused: printenv would print env vars to stdout. ${ADVICE_NAME_ONE} If this is intentional, run it yourself."
}

#######################################
# Deny a command that runs env with nothing behind it.
# Globals:
#   GUARD_DECISION, GUARD_REASON
#######################################
deny_bare_env() {
  decision::reach deny "Refused: bare 'env' would dump every env var to stdout. ${ADVICE_NAME_ONE} env CMD ARGS, which launches a command, stays allowed. If this is intentional, run it yourself."
}

#######################################
# Deny a command that runs set with no arguments.
# Globals:
#   GUARD_DECISION, GUARD_REASON
#######################################
deny_bare_set() {
  decision::reach deny "Refused: bare 'set' would dump every shell variable. ${ADVICE_NAME_ONE} If this is intentional, run it yourself."
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
  local seen=0 argument word
  local -a parts
  for argument in "$@"; do
    # A quoted word comes with its spaces as placeholders.
    IFS=' ' read -r -a parts <<<"${argument//${CW_SPACE}/ }"
    for word in ${parts[@]+"${parts[@]}"}; do
      if ((seen)) && [[ "${word}" =~ ${SECRET_REFERENCE} ]]; then
        return 0
      fi
      if [[ "${word##*/}" =~ ^${OUTPUT_CMD}$ ]]; then
        seen=1
      fi
    done
  done
  return 1
}

#######################################
# Deny when one program line dumps the environment or prints a secret.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - a program line from command_words::resolve.
#######################################
check_program() {
  local -a words
  local word last=''
  IFS=' ' read -r -a words <<<"$(search_line_without_pattern "$1")"
  ((${#words[@]} > 0)) || return 0

  if prints_secret "${words[@]}"; then
    deny_print_secret
    return 0
  fi

  # printenv: its sole purpose is showing env.
  for word in "${words[@]}"; do
    if [[ "${word}" == printenv ]]; then
      deny_printenv
      return 0
    fi
  done

  # env ending the program dumps the environment, whatever launches it.
  for word in "${words[@]}"; do
    [[ "${word}" == '>'* ]] && break
    last="${word}"
  done
  if [[ "${last}" == env ]]; then
    deny_bare_env
    return 0
  fi

  # `set` with no args dumps every shell variable.
  if [[ "${words[0]}" == set ]] && { ((${#words[@]} == 1)) || [[ "${words[1]}" == '>'* ]]; }; then
    deny_bare_set
  fi
}

#######################################
# Deny when one part of the command is env with nothing behind it: `env`
# alone, behind wrappers, or ahead of a redirect. `env CMD ARGS` launches a
# subprocess and stays allowed.
# Globals:
#   GUARD_DECISION, GUARD_REASON
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
    deny_bare_env
  fi
}

#######################################
# The checks as they ran on raw text, for the body of a here-document that
# the resolver skips. ripgrep is used because bash's =~ ERE engine lacks \b
# word boundaries.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the command text.
#######################################
check_raw_text() {
  local cmd="$1" bare
  if rg -q \
    "\b${OUTPUT_CMD}\b[^|;&]*\\\$\{?[A-Za-z_]*${SECRET_WORD}[A-Za-z_0-9]*" \
    <<<"${cmd}"; then
    deny_print_secret
    return 0
  fi
  if rg -q '\bprintenv\b' <<<"${cmd}"; then
    deny_printenv
    return 0
  fi
  bare='(^|[;&|`(])[[:space:]]*([A-Za-z0-9_.-]+[[:space:]]+)?'
  if rg -q "${bare}env[[:space:]]*(\||;|&|>|\$)" <<<"${cmd}"; then
    deny_bare_env
    return 0
  fi
  if rg -q "${bare}set[[:space:]]*(\||;|&|>|\$)" <<<"${cmd}"; then
    deny_bare_set
  fi
}

#######################################
# Decide on a command the Bash tool proposes, stopping at the first check
# that denies.
# Globals:
#   GUARD_DECISION, GUARD_REASON
# Arguments:
#   $1 - the command.
#######################################
decide_bash() {
  local cmd="$1" line
  local -a parts=()
  decision::clear

  if [[ -z "${cmd}" ]]; then
    return 0
  fi

  # The command is split once; the programs and the bare-env check both read
  # its parts.
  while IFS= read -r line; do
    parts+=("${line}")
  done < <(command_words::split "${cmd}")

  while IFS= read -r line; do
    check_program "${line}"
    ! decision::reached || return 0
  done < <(command_words::resolve_parts ${parts[@]+"${parts[@]}"})

  for line in ${parts[@]+"${parts[@]}"}; do
    check_bare_env "${line}"
    ! decision::reached || return 0
  done

  if command_words::opens_heredoc "${cmd}"; then
    check_raw_text "${cmd}"
  fi
}

main() {
  decision::main_bash
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
