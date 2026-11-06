#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Prompts (permissionDecision: "ask") when a command runs git commit with
# --amend, wherever --amend stands among the arguments and whatever global
# options precede the subcommand, `git -C <path> commit --amend` included.
# The settings prompt carries no text, so the reason below tells the agent
# what to do instead.
#
# git counts when it stands at a command position, as the splitting in
# lib/command_words.sh defines it. The subcommand is the first word after
# git that is not a global option or an option's value. The value of a
# commit option such as -m is skipped, so a message that says --amend stays
# silent.
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

# Global git options whose next word is a value.
readonly GLOBAL_VALUE_OPTIONS=' -C -c --git-dir --work-tree --namespace --exec-path --super-prefix --config-env '

# git commit options whose next word is a value.
readonly COMMIT_VALUE_OPTIONS=' -m -F -C -c -t --message --file --author --date --template --reuse-message --reedit-message --fixup --squash --cleanup --trailer --pathspec-from-file '

readonly ASK_REASON='After a hook rejects a commit, fix the cause and commit anew rather than amending. An amend rewrites the previous commit, which can discard work that was already committed.'

#######################################
# Report whether a program line is git commit with --amend.
# Globals:
#   GLOBAL_VALUE_OPTIONS, COMMIT_VALUE_OPTIONS
# Arguments:
#   The program's name, then its arguments.
# Returns:
#   0 for git commit --amend, 1 otherwise.
#######################################
is_git_amend() {
  local program="$1" word skip=0 in_commit=0
  shift
  [[ "${program}" == git ]] || return 1

  for word in "$@"; do
    if ((skip)); then
      skip=0
      continue
    fi
    if ((in_commit)); then
      if [[ "${word}" == --amend ]]; then
        return 0
      fi
      if [[ "${COMMIT_VALUE_OPTIONS}" == *" ${word} "* ]]; then
        skip=1
      elif [[ "${word}" =~ ^-[A-Za-z]*[mFCct]$ ]]; then
        # A short-flag cluster ending in a value option, as in -am.
        skip=1
      fi
      continue
    fi
    if [[ "${word}" == -* ]]; then
      if [[ "${GLOBAL_VALUE_OPTIONS}" == *" ${word} "* ]]; then
        skip=1
      fi
      continue
    fi
    [[ "${word}" == commit ]] || return 1
    in_commit=1
  done
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
    if is_git_amend "${words[@]}"; then
      ask
    fi
  done < <(command_words::resolve "${command}")

  return 0
}

main "$@"
