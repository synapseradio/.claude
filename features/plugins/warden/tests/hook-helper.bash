# Shared helpers for the warden hook tests.
#
# Every guard reads one PreToolUse envelope on stdin and answers on stdout: a
# permission decision object when it objects, and nothing at all when it does
# not. Its decision functions take the tool input as arguments and leave the
# decision in GUARD_DECISION and GUARD_REASON (hooks/lib/decision.sh); its
# main reads the envelope, calls one of them, and prints the result.
#
# Each test file sources its guard in setup through load_guard. The run_*
# helpers below call the guard's decision functions in the test's own shell,
# so a case starts no bash, jq, or cat of its own. run_hook_envelope runs the
# guard's main as a function with the envelope on stdin, the path the harness
# takes short of starting bash. The assertions check the exit status too, so
# a guard that crashed and a guard that allowed never look alike.
#
# shellcheck shell=bash

# Set by the run_* helpers, read by the assertions below. HOOK_OUTPUT holds
# the decision as the guard's JSON, for cases that read it with jq.
HOOK_OUTPUT=''
HOOK_STATUS=0
HOOK_DECISION=''
HOOK_REASON=''

# Point the banned-reads file at this test's own temporary directory. No
# case can then reach a file the machine already has, whatever the person
# running the tests keeps in their own Claude directory.
export WARDEN_BANNED_READS="${BATS_TEST_TMPDIR}/banned-reads.conf"

#######################################
# Point HOME and the XDG directories at this test's own directory, so a case
# reads and writes nothing in the home directory of whoever runs the tests.
# Globals:
#   HOME, XDG_CONFIG_HOME, XDG_DATA_HOME, XDG_CACHE_HOME, XDG_STATE_HOME
#######################################
isolate_home() {
  export HOME="${BATS_TEST_TMPDIR}/home"
  export XDG_CONFIG_HOME="${HOME}/.config"
  export XDG_DATA_HOME="${HOME}/.local/share"
  export XDG_CACHE_HOME="${HOME}/.cache"
  export XDG_STATE_HOME="${HOME}/.local/state"
  mkdir -p "${HOME}"
}

#######################################
# Give git a configuration of this test's own: a global file in HOME holding a
# committer identity, no system file, and none of the variables that locate a
# repository. A hook run from a linked worktree inherits those variables, and a
# scratch repository that kept them would write into the repository that holds
# the tests. Call isolate_home first.
# Globals:
#   HOME, GIT_CONFIG_GLOBAL, GIT_CONFIG_NOSYSTEM
#######################################
isolate_git_config() {
  export GIT_CONFIG_GLOBAL="${HOME}/.gitconfig"
  export GIT_CONFIG_NOSYSTEM=1
  printf '[user]\n\tname = Test\n\temail = test@example.com\n' \
    >"${GIT_CONFIG_GLOBAL}"
  unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_COMMON_DIR \
    GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_NAMESPACE \
    GIT_CEILING_DIRECTORIES
}

#######################################
# Source the guard under test into this shell, and fail where sourcing
# changed the shell's options: the guard's strict mode belongs to the process
# it runs as, and in force here it would end or alter the test. Sourcing that
# turned nounset or pipefail on has them turned off again before the failure,
# since bats itself stops reporting under either.
# Arguments:
#   $1 - the guard's file name in hooks/, without .sh.
#######################################
load_guard() {
  local flags="$-" pipefail=0 now_flags now_pipefail=0
  if shopt -qo pipefail; then
    pipefail=1
  fi
  # shellcheck source=/dev/null
  source "${BATS_TEST_DIRNAME}/../hooks/$1.sh"
  now_flags="$-"
  if shopt -qo pipefail; then
    now_pipefail=1
  fi
  [[ "${now_flags}" != "${flags}" ]] || ((now_pipefail != pipefail)) ||
    return 0

  [[ "${flags}" == *u* ]] || set +u
  ((pipefail)) || set +o pipefail
  echo "sourcing $1.sh changed the shell options: flags ${flags} to" \
    "${now_flags}, pipefail ${pipefail} to ${now_pipefail}" >&2
  return 1
}

#######################################
# Set JSON_TEXT to a JSON string literal holding a text.
# Globals:
#   JSON_TEXT
# Arguments:
#   $1 - the text.
#######################################
json_quote() {
  local text="$1" code octal char escaped
  local backslash=$'\\' quote='"'
  text="${text//${backslash}/${backslash}${backslash}}"
  text="${text//${quote}/${backslash}${quote}}"
  text="${text//$'\n'/${backslash}n}"
  text="${text//$'\t'/${backslash}t}"
  text="${text//$'\r'/${backslash}r}"
  if [[ "${text}" == *[[:cntrl:]]* ]]; then
    for ((code = 1; code < 32; code++)); do
      printf -v octal '%03o' "${code}"
      # shellcheck disable=SC2059
      printf -v char "\\${octal}"
      printf -v escaped '%su%04x' "${backslash}" "${code}"
      text="${text//"${char}"/${escaped}}"
    done
  fi
  JSON_TEXT="${quote}${text}${quote}"
}

#######################################
# Call one of the guard's decision functions under the options the guard runs
# with, then record what it decided. bats traces every command of a function
# it calls; the trace stays off for the call, which would otherwise cost more
# than the decision itself. A guard that judges with git leaves a timer
# process behind, and bats waits for every process holding its descriptor 3,
# so the call runs with that descriptor closed.
# https://bats-core.readthedocs.io/en/stable/writing-tests.html#file-descriptor-3-read-this-if-bats-hangs
# Globals:
#   GUARD_DECISION, GUARD_REASON, HOOK_OUTPUT, HOOK_STATUS, HOOK_DECISION,
#   HOOK_REASON, JSON_TEXT
# Arguments:
#   The decision function, then its arguments.
#######################################
judge() {
  local flags="$-" pipefail=0
  if shopt -qo pipefail; then
    pipefail=1
  fi
  set +T -u -o pipefail
  "$@" 3>&-
  [[ "${flags}" == *u* ]] || set +u
  ((pipefail)) || set +o pipefail
  [[ "${flags}" != *T* ]] || set -T

  HOOK_STATUS=0
  HOOK_DECISION="${GUARD_DECISION}"
  HOOK_REASON="${GUARD_REASON}"
  HOOK_OUTPUT=''
  if [[ -n "${HOOK_DECISION}" ]]; then
    json_quote "${HOOK_REASON}"
    HOOK_OUTPUT="{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"${HOOK_DECISION}\",\"permissionDecisionReason\":${JSON_TEXT}}}"
  fi
}

#######################################
# Feed one envelope to the guard's main, in a subshell under the guard's own
# options and with descriptor 3 closed as in judge, and read back what it
# printed.
# Globals:
#   HOOK_OUTPUT, HOOK_STATUS, HOOK_DECISION, HOOK_REASON
# Arguments:
#   $1 - the PreToolUse envelope JSON.
#######################################
run_hook_envelope() {
  local envelope="$1" fields
  HOOK_STATUS=0
  HOOK_OUTPUT="$(
    set -euo pipefail
    main <<<"${envelope}" 3>&-
  )" || HOOK_STATUS=$?
  HOOK_DECISION=''
  HOOK_REASON=''
  [[ -n "${HOOK_OUTPUT}" ]] || return 0
  fields="$(jq -r '.hookSpecificOutput.permissionDecision // "",
    .hookSpecificOutput.permissionDecisionReason // ""' <<<"${HOOK_OUTPUT}")"
  HOOK_DECISION="${fields%%$'\n'*}"
  HOOK_REASON="${fields#*$'\n'}"
}

#######################################
# Run the guard against a command the Bash tool proposes.
# Arguments:
#   $1 - the shell command.
#######################################
run_bash_hook() {
  judge decide_bash "$1"
}

#######################################
# Run the guard against a command the Bash tool proposes from a directory.
# Arguments:
#   $1 - the session's working directory.
#   $2 - the shell command.
#######################################
run_bash_hook_in() {
  judge decide_bash "$2" "$1"
}

#######################################
# Assert the guard denies a Bash command run from a directory.
# Arguments:
#   $1 - the session's working directory.
#   $2 - the shell command.
#######################################
assert_denies_in() {
  run_bash_hook_in "$1" "$2"
  assert_decision 'deny' "$2"
}

#######################################
# Assert the guard stays silent about a Bash command run from a directory.
# Arguments:
#   $1 - the session's working directory.
#   $2 - the shell command.
#######################################
assert_silent_in() {
  run_bash_hook_in "$1" "$2"
  assert_no_decision "$2"
}

#######################################
# Run the guard against a path the Read tool proposes to open.
# Arguments:
#   $1 - the file path.
#######################################
run_read_hook() {
  judge decide_read "$1"
}

#######################################
# Set JSON_FIELD to the value of one string field of a flat JSON object, or
# to empty where the object holds no such string.
# Globals:
#   JSON_FIELD
# Arguments:
#   $1 - the JSON object, holding no escaped character.
#   $2 - the field's name.
#######################################
json_field() {
  local pattern="\"$2\"[[:space:]]*:[[:space:]]*\"([^\"]*)\""
  JSON_FIELD=''
  if [[ "$1" =~ ${pattern} ]]; then
    JSON_FIELD="${BASH_REMATCH[1]}"
  fi
}

#######################################
# Run the guard against the input the Agent tool proposes, from a project
# directory under this test's own.
# Globals:
#   BATS_TEST_TMPDIR, JSON_FIELD
# Arguments:
#   $1 - the tool_input object as flat JSON, holding no escaped character.
#######################################
run_agent_hook() {
  local tool_input="$1" type
  [[ "${tool_input}" != *\\* ]] || {
    echo "run_agent_hook reads flat JSON with no escapes: ${tool_input}" >&2
    return 1
  }
  json_field "${tool_input}" subagent_type
  type="${JSON_FIELD}"
  json_field "${tool_input}" model
  judge decide_agent "${type}" "${JSON_FIELD}" "${BATS_TEST_TMPDIR}/project"
}

#######################################
# Assert the guard denies an Agent spawn.
# Arguments:
#   $1 - the tool_input object as JSON.
#######################################
assert_denies_agent() {
  run_agent_hook "$1"
  assert_decision 'deny' "$1"
}

#######################################
# Assert the guard stays silent about an Agent spawn.
# Arguments:
#   $1 - the tool_input object as JSON.
#######################################
assert_silent_agent() {
  run_agent_hook "$1"
  assert_no_decision "$1"
}

#######################################
# Assert the guard exited 0, whatever it decided.
# Globals:
#   HOOK_STATUS, HOOK_OUTPUT
#######################################
assert_exited_clean() {
  ((HOOK_STATUS == 0)) || {
    echo "guard exited ${HOOK_STATUS}, wanted 0; output: ${HOOK_OUTPUT}" >&2
    return 1
  }
}

#######################################
# Assert the last run carried a given permission decision.
# Globals:
#   HOOK_DECISION, HOOK_REASON
# Arguments:
#   $1 - the expected permissionDecision value.
#   $2 - the subject, quoted back on failure.
#######################################
assert_decision() {
  local want="$1" subject="$2"
  assert_exited_clean || return 1
  [[ -n "${HOOK_DECISION}" ]] || {
    echo "expected a ${want}, got silence for: ${subject}" >&2
    return 1
  }
  [[ "${HOOK_DECISION}" == "${want}" ]] || {
    echo "expected ${want}, got '${HOOK_DECISION}' for: ${subject}" >&2
    return 1
  }
  [[ -n "${HOOK_REASON}" ]] || {
    echo "decision carried no reason for the user to read: ${subject}" >&2
    return 1
  }
}

#######################################
# Assert the guard's main, fed one envelope, printed a PreToolUse decision
# whose reason holds a given text.
# Globals:
#   HOOK_OUTPUT
# Arguments:
#   $1 - the expected permissionDecision value.
#   $2 - text the reason must hold.
#   $3 - the PreToolUse envelope JSON.
#######################################
assert_main_prints() {
  local want="$1" text="$2" event
  run_hook_envelope "$3"
  assert_decision "${want}" "$3" || return 1
  event="$(jq -r '.hookSpecificOutput.hookEventName // ""' <<<"${HOOK_OUTPUT}")"
  [[ "${event}" == 'PreToolUse' ]] || {
    echo "expected hookEventName PreToolUse, got '${event}'" >&2
    return 1
  }
  assert_reason_contains "${text}"
}

#######################################
# Assert the last decision's reason contains a string.
# Globals:
#   HOOK_REASON
# Arguments:
#   $1 - the text the reason must hold.
#######################################
assert_reason_contains() {
  [[ "${HOOK_REASON}" == *"$1"* ]] || {
    echo "reason lacks '$1': ${HOOK_REASON}" >&2
    return 1
  }
}

#######################################
# Assert the guard said nothing about the last run.
# Globals:
#   HOOK_OUTPUT
# Arguments:
#   $1 - the subject, quoted back on failure.
#######################################
assert_no_decision() {
  local subject="$1"
  assert_exited_clean || return 1
  [[ -z "${HOOK_OUTPUT}" ]] || {
    echo "expected silence for: ${subject}; got: ${HOOK_OUTPUT}" >&2
    return 1
  }
}

#######################################
# Assert the guard denies a Bash command.
# Arguments:
#   $1 - the shell command.
#######################################
assert_denies() {
  run_bash_hook "$1"
  assert_decision 'deny' "$1"
}

#######################################
# Assert the guard asks about a Bash command.
# Arguments:
#   $1 - the shell command.
#######################################
assert_asks() {
  run_bash_hook "$1"
  assert_decision 'ask' "$1"
}

#######################################
# Assert the guard stays silent about a Bash command.
# Arguments:
#   $1 - the shell command.
#######################################
assert_silent() {
  run_bash_hook "$1"
  assert_no_decision "$1"
}

#######################################
# Assert the guard denies a Read target.
# Arguments:
#   $1 - the file path.
#######################################
assert_denies_read() {
  run_read_hook "$1"
  assert_decision 'deny' "$1"
}

#######################################
# Assert the guard stays silent about a Read target.
# Arguments:
#   $1 - the file path.
#######################################
assert_silent_read() {
  run_read_hook "$1"
  assert_no_decision "$1"
}
