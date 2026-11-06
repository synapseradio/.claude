#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Prompts (permissionDecision: "ask") when a command is a fetch-and-run
# command: one that resolves a package from a registry and executes code
# from it in the same step. The settings prompt carries no text, so the
# reason below tells the agent what to state before the command runs.
#
# Matched forms:
#   npx, pnpx, bx, uvx
#   npm exec, npm x, npm create, npm init <name>
#   pnpm dlx, pnpm create, yarn dlx, yarn create, bun create
#   uv tool run, pipx run
#   docker run, podman run (also docker container run)
# bunx and bun x stay silent, as does npm init without an initializer name.
#
# A program counts when it stands at a command position, as the splitting in
# lib/command_words.sh defines it, so the name inside a quoted argument
# does not prompt. A subcommand is the first word after the program that is
# not an option; an option's value is skipped for the options listed below.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when asking; nothing when staying silent.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"

# Options, across the package managers and container runtimes handled below,
# whose next word is a value rather than a subcommand.
readonly VALUE_OPTIONS=' -w --workspace --prefix -C --cwd --dir --filter -F --registry --scope --userconfig --cache -H --host -c --context --config --log-level '

readonly ASK_REASON='This command resolves a package from a registry and runs code from it in the same step. Before it runs, state in the message: the package, the version the command pins, what it executes, and which installed tool falls short of the step. The command must pin a version: name@1.2.3 for a package, a tag or digest for an image. A command that pins none runs whatever the registry serves at that moment.'

# The words after the program that are not options, set by collect_positionals.
POSITIONALS=()

#######################################
# Collect the non-option words among a program's arguments.
# Globals:
#   VALUE_OPTIONS, POSITIONALS
# Arguments:
#   The program's arguments.
#######################################
collect_positionals() {
  local word skip=0
  POSITIONALS=()
  for word in "$@"; do
    if ((skip)); then
      skip=0
      continue
    fi
    if [[ "${word}" == -* ]]; then
      if [[ "${VALUE_OPTIONS}" == *" ${word} "* ]]; then
        skip=1
      fi
      continue
    fi
    POSITIONALS+=("${word}")
  done
}

#######################################
# Report whether a program line is a fetch-and-run command.
# Globals:
#   POSITIONALS
# Arguments:
#   The program's name, then its arguments.
# Returns:
#   0 for a fetch-and-run command, 1 otherwise.
#######################################
is_fetch_and_run() {
  local program="$1" first second
  shift

  case "${program}" in
  npx | pnpx | bx | uvx) return 0 ;;
  esac

  collect_positionals "$@"
  first="${POSITIONALS[0]:-}"
  second="${POSITIONALS[1]:-}"

  case "${program}" in
  npm)
    case "${first}" in
    exec | x | create) return 0 ;;
    init) [[ -n "${second}" ]] && return 0 ;;
    esac
    ;;
  pnpm | yarn)
    [[ "${first}" == dlx || "${first}" == create ]] && return 0
    ;;
  bun)
    [[ "${first}" == create ]] && return 0
    ;;
  uv)
    [[ "${first}" == tool && "${second}" == run ]] && return 0
    ;;
  pipx)
    [[ "${first}" == run ]] && return 0
    ;;
  docker | podman)
    [[ "${first}" == run ]] && return 0
    [[ "${first}" == container && "${second}" == run ]] && return 0
    ;;
  esac
  return 1
}

#######################################
# Emit an ask decision and exit.
# Outputs:
#   The permission decision JSON on stdout.
#######################################
ask() {
  jq -nc --arg r "${ASK_REASON}" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"ask",permissionDecisionReason:$r}}'
  exit 0
}

main() {
  local command line
  local -a words
  command="$(jq -r '.tool_input.command // ""')"

  if [[ -z "${command}" ]]; then
    return 0
  fi

  while IFS= read -r line; do
    IFS=' ' read -r -a words <<<"${line}"
    if is_fetch_and_run "${words[@]}"; then
      ask
    fi
  done < <(command_words::resolve "${command}")

  return 0
}

main "$@"
