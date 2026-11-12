#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Lets rm run only where git can restore everything it removes. Each path rm
# names must not exist, or must be tracked by git, identical to HEAD, with
# nothing staged, modified, untracked, or ignored at or beneath it. Anything
# else is refused with a pointer to `trash <path>`, which moves the path to
# the Trash, where it can be recovered. The judging lives in
# lib/git_restorable.sh.
#
# The guard refuses whenever it cannot tell what rm removes: a path outside
# any git repository, an operand holding a glob, a variable, a command
# substitution, a brace expansion, or a tilde, an rm run through xargs or
# find -exec, a command that changes directory (a cd, a pushd, env -C, sudo
# -D), a relative operand when the envelope names no cwd, and a git that
# fails or answers too late. Relative operands resolve against the
# envelope's cwd. The hook's own timeout lets a command through, so the
# guard sets a deadline of its own, WARDEN_RM_DEADLINE seconds, and refuses
# when it passes.
#
# rm counts when it stands at a command position: the start of the command,
# or of any part after &&, ||, ;, |, a newline, or a subshell or $( opener,
# behind sudo, command, xargs, env, or exec, and inside a `sh -c` string or
# a find -exec. The splitting lives in lib/command_words.sh. `git rm`,
# `npm rm`, `docker rm`, rmdir, trash, and the word rm inside a quoted
# string or as an argument stay allowed.
#
# The judging reads disk state before the command runs, so an rm that follows
# another step is refused outright: that step may have written what rm then
# removes. Steps that are themselves rm do not count, since rm creates nothing.
# A shell run with -c is no step of its own; the programs in its script are.
#
# Globals: WARDEN_RM_DEADLINE (seconds git gets, default 4).
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -euo pipefail

# A hook run from a linked worktree inherits these, and git would then judge
# every path in the repository that holds the hook and not in its own.
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_COMMON_DIR \
  GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_NAMESPACE \
  GIT_CEILING_DIRECTORIES

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"
# shellcheck source=lib/git_restorable.sh
source "${SCRIPT_DIR}/lib/git_restorable.sh"

readonly DENIAL_REASON='rm runs only on files committed and unchanged in git, where git can restore them. For anything else, delete with trash <path> instead: it moves the path to the Trash, where it can be recovered. Deleting still needs the confirmation the task calls for.'

# Words in the command text that make the operands of an rm unknowable.
readonly XARGS_PATTERN='(^|[^[:alnum:]_.-])xargs([^[:alnum:]_.-]|$)'
readonly FIND_EXEC_PATTERN='[[:space:]]-(exec|execdir|ok|okdir)([[:space:]]|$)'
readonly WRAPPER_PATTERN='(^|[^[:alnum:]_.-])(env|sudo)([[:space:]]|$)'
readonly CHDIR_OPTION_PATTERN='[[:space:]](-[A-Za-z]*[CD]|--chdir)([[:space:]=]|$)'

#######################################
# Emit a deny decision and exit.
# Globals:
#   DENIAL_REASON
# Arguments:
#   $1 - what the guard found, appended to the reason.
# Outputs:
#   The permission decision JSON on stdout.
#######################################
deny() {
  jq -nc --arg reason "${DENIAL_REASON} Held back: $1." '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

#######################################
# Say why an operand's path cannot be read from its text.
# Arguments:
#   $1 - the operand as the command resolver prints it.
# Outputs:
#   The reason on stdout when the operand cannot be read.
# Returns:
#   0 when the operand is a plain path, 1 otherwise.
#######################################
operand_problem() {
  case "$1" in
  '~'* | '='*)
    echo 'starts with a tilde or an equals sign the guard does not expand'
    return 1
    ;;
  *['*?[]{}$`<>()^!|;&']* | *\\*)
    echo 'holds a glob, a variable, a substitution, a redirect, or other syntax the guard does not expand'
    return 1
    ;;
  esac
  return 0
}

#######################################
# Print the operands of one rm line, one per line, with the placeholder of a
# quoted space turned back into a space. Options before the first operand
# and exact redirects of rm's output are skipped.
# Globals:
#   CW_SPACE
# Arguments:
#   $1 - the program line: rm, then its words.
# Outputs:
#   One operand per line on stdout; a newline inside an operand stays the
#   placeholder.
#######################################
rm_operands() {
  local -a words
  local index word options=1
  IFS=' ' read -r -a words <<<"$1"
  for ((index = 1; index < ${#words[@]}; index++)); do
    word="${words[index]}"
    case "${word}" in
    '2>/dev/null' | '>/dev/null' | '&>/dev/null' | '1>/dev/null' | '2>&1' | '>&2' | '1>&2')
      continue
      ;;
    esac
    if ((options)); then
      if [[ "${word}" == -- ]]; then
        options=0
        continue
      elif [[ "${word}" == -* && "${word}" != - ]]; then
        continue
      fi
      options=0
    fi
    printf '%s\n' "${word//${CW_SPACE}/ }"
  done
}

#######################################
# Judge every operand of each rm line, stopping at the first one git cannot
# restore.
# Globals:
#   CW_NEWLINE
# Arguments:
#   $1 - the envelope's cwd, possibly empty.
#   The rm lines.
# Outputs:
#   The operand and why it is held back, on stdout, for the first failure.
# Returns:
#   0 when every operand is restorable, 1 otherwise.
#######################################
judge_rm_lines() {
  local cwd="$1" line operand target why count
  shift
  for line in "$@"; do
    count=0
    while IFS= read -r operand; do
      count=$((count + 1))
      if ! why="$(operand_problem "${operand}")"; then
        echo "${operand} ${why}"
        return 1
      fi
      target="${operand//${CW_NEWLINE}/$'\n'}"
      if [[ "${target}" != /* ]]; then
        if [[ -z "${cwd}" ]]; then
          echo "${operand} is relative and the command names no working directory"
          return 1
        fi
        target="${cwd%/}/${target}"
      fi
      if ! why="$(git_restorable::why_not "${target}")"; then
        echo "${operand} ${why}"
        return 1
      fi
    done < <(rm_operands "${line}")
    if ((count == 0)); then
      echo "rm names no path, so what it removes comes from elsewhere"
      return 1
    fi
  done
  return 0
}

main() {
  local envelope command cwd line detail result_file worker watcher status=0
  local cd_seen=0 other_steps=0 after_step=0
  local -a rm_lines=()

  envelope="$(cat)"
  command="$(jq -r '.tool_input.command // ""' <<<"${envelope}")"
  cwd="$(jq -r '.cwd // ""' <<<"${envelope}")"

  if [[ -z "${command}" ]]; then
    return 0
  fi

  # The resolver lists programs in the order they run, so a program with any
  # non-rm program listed ahead of it follows another step.
  while IFS= read -r line; do
    case "${line}" in
    rm | rm\ *)
      rm_lines+=("${line}")
      if ((other_steps > 0)); then
        after_step=1
      fi
      continue
      ;;
    cd | cd\ * | pushd | pushd\ * | popd | popd\ * | builtin\ *) cd_seen=1 ;;
    esac
    if ! command_words::hands_script_to_shell "${line}"; then
      other_steps=$((other_steps + 1))
    fi
  done < <(command_words::resolve "${command}")

  if ((${#rm_lines[@]} == 0)); then
    return 0
  fi

  if ((cd_seen)); then
    deny 'the command changes directory, so the guard cannot resolve what rm names'
  fi
  if [[ "${command}" =~ ${WRAPPER_PATTERN} && "${command}" =~ ${CHDIR_OPTION_PATTERN} ]]; then
    deny 'the command runs rm behind a wrapper that can change directory'
  fi
  if [[ "${command}" =~ ${XARGS_PATTERN} ]]; then
    deny 'rm runs behind xargs, which supplies operands the guard cannot see'
  fi
  if [[ "${command}" =~ ${FIND_EXEC_PATTERN} ]]; then
    deny 'rm runs behind find -exec, which supplies operands and directories the guard cannot see'
  fi

  if ((after_step)); then
    deny 'rm follows another step in the command, and that step may have written what rm removes. If the output is known to be throwaway, send it to /dev/null in place of writing a file and deleting it'
  fi

  result_file="$(mktemp "${TMPDIR:-/tmp}/deny-rm.XXXXXX")" ||
    deny 'the guard could not create a scratch file to judge with'
  judge_rm_lines "${cwd}" "${rm_lines[@]}" >"${result_file}" 2>/dev/null </dev/null &
  worker=$!
  (
    sleep "${WARDEN_RM_DEADLINE:-4}"
    kill "${worker}"
  ) >/dev/null 2>&1 </dev/null &
  watcher=$!
  wait "${worker}" 2>/dev/null || status=$?
  kill "${watcher}" >/dev/null 2>&1 || true
  # Reaping the killed watcher here keeps bash 3.2's job notice off stderr.
  wait "${watcher}" 2>/dev/null || true
  detail="$(<"${result_file}")"
  command rm -f "${result_file}"

  if ((status != 0)); then
    deny "${detail:-git did not answer before the deadline}"
  fi
  return 0
}

main "$@"
