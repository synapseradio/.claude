#!/bin/bash
#
# Library for the warden hooks that judge a Bash command by what git says
# about the disk before the command runs. Source it after
# lib/command_words.sh; it defines functions and constants only. Uses only
# what /bin/bash 3.2 on macOS offers.
#
# Each hook supplies its own program match, its judge function, its deadline
# variable, its scratch-file prefix, and its denial wording. The library holds
# what both hooks share: the clean git environment, the envelope read, the
# scan for steps around the matched programs, and the deadline runner.
#
# Globals: GG_CWD, GG_COMMAND, GG_CD_SEEN, GG_AFTER_STEP, GG_DETAIL.

# The globals are this library's results; the hooks that source it read them.
# shellcheck disable=SC2034

# Words in the command text that change which repository or directory git
# reads. env and sudo can change directory.
readonly GG_WRAPPER_PATTERN='(^|[^[:alnum:]_.-])(env|sudo)([[:space:]]|$)'
readonly GG_CHDIR_OPTION_PATTERN='[[:space:]](-[A-Za-z]*[CD]|--chdir)([[:space:]=]|$)'

# What git_guard::read_envelope reports.
GG_CWD=''
GG_COMMAND=''

# What git_guard::scan_programs reports.
GG_CD_SEEN=0
GG_AFTER_STEP=0

# What git_guard::run_with_deadline reports.
GG_DETAIL=''

#######################################
# Drop the variables that locate a repository. A hook run from a linked
# worktree inherits them, and git would then judge the repository that holds
# the hook and not the one the command names.
#######################################
git_guard::unset_repository_env() {
  unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_COMMON_DIR \
    GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_NAMESPACE \
    GIT_CEILING_DIRECTORIES
}

#######################################
# Read the PreToolUse envelope from stdin with one jq call.
# Globals:
#   GG_CWD, GG_COMMAND
# Outputs:
#   Nothing; GG_CWD holds the envelope's cwd, empty when it names none, and
#   GG_COMMAND the Bash command, newlines inside it kept.
#######################################
git_guard::read_envelope() {
  local fields
  # The cwd is the first line and the command the rest, so an empty cwd and a
  # multi-line command both survive.
  fields="$(jq -r '(.cwd // ""), (.tool_input.command // "")')"
  GG_CWD="${fields%%$'\n'*}"
  if [[ "${fields}" == *$'\n'* ]]; then
    GG_COMMAND="${fields#*$'\n'}"
  else
    GG_COMMAND=''
  fi
}

#######################################
# Say whether the command text holds a wrapper that can change directory
# together with an option that does.
# Arguments:
#   $1 - the command text.
# Returns:
#   0 when it does, 1 otherwise.
#######################################
git_guard::wrapper_may_chdir() {
  [[ "$1" =~ ${GG_WRAPPER_PATTERN} && "$1" =~ ${GG_CHDIR_OPTION_PATTERN} ]]
}

#######################################
# Walk the programs a command would run, in the order they run, and learn
# whether it changes directory and whether a program the hook matches follows
# another step. A shell run with -c is no step of its own; the programs in its
# script are.
# Globals:
#   GG_CD_SEEN, GG_AFTER_STEP
# Arguments:
#   $1 - the hook's match function. It takes a program line, returns 0 when
#        the line is a program the hook judges, and records the line itself.
#   $2 - 1 when a matched program is a step that a later match follows, 0
#        when it is not.
#   $3 - the command text.
#######################################
git_guard::scan_programs() {
  local match_fn="$1" matches_are_steps="$2" line
  local step_seen=0
  GG_CD_SEEN=0
  GG_AFTER_STEP=0

  while IFS= read -r line; do
    if "${match_fn}" "${line}"; then
      if ((step_seen)); then
        GG_AFTER_STEP=1
      fi
      if ((matches_are_steps)); then
        step_seen=1
      fi
      continue
    fi
    case "${line}" in
    cd | cd\ * | pushd | pushd\ * | popd | popd\ * | builtin\ *) GG_CD_SEEN=1 ;;
    esac
    if ! command_words::hands_script_to_shell "${line}"; then
      step_seen=1
    fi
  done < <(command_words::resolve "$3")
}

#######################################
# Run a function with a deadline. The function's stdout goes to a scratch
# file, read back as GG_DETAIL; its stderr and stdin are closed.
# Globals:
#   GG_DETAIL
# Arguments:
#   $1 - seconds the function gets.
#   $2 - prefix of the scratch file's name.
#   $3 - the function.
#   The rest - the function's arguments.
# Returns:
#   0 when the function succeeded in time, 1 when it failed or ran out of
#   time, 2 when the scratch file could not be created.
#######################################
git_guard::run_with_deadline() {
  local seconds="$1" prefix="$2" judge="$3" result_file worker watcher status=0
  shift 3
  GG_DETAIL=''

  result_file="$(mktemp "${TMPDIR:-/tmp}/${prefix}.XXXXXX")" || return 2
  "${judge}" "$@" >"${result_file}" 2>/dev/null </dev/null &
  worker=$!
  (
    sleep "${seconds}"
    kill "${worker}"
  ) >/dev/null 2>&1 </dev/null &
  watcher=$!
  wait "${worker}" 2>/dev/null || status=$?
  kill "${watcher}" >/dev/null 2>&1 || true
  # Reaping the killed watcher here keeps bash 3.2's job notice off stderr.
  wait "${watcher}" 2>/dev/null || true
  GG_DETAIL="$(<"${result_file}")"
  command rm -f "${result_file}"

  ((status == 0)) || return 1
}
