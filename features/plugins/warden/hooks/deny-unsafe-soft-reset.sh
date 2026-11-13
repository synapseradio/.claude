#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Lets git reset --soft run only where it uncommits nothing but local work.
# A soft reset moves the branch back and keeps the changes staged, so it
# squashes a branch's own commits, and it also rewrites history when the
# commits it drops are published or the branch is shared. Each denial names
# the condition that failed and points at `wt -C <worktree> step squash
# <target>`, the squash that leaves published history alone.
#
# A soft reset passes only when all of these hold:
#   - it names exactly one revision, no pathspec, no option beyond --quiet,
#     and no second mode flag (--hard, --mixed, --merge, --keep);
#   - the repository has no rebase, merge, cherry-pick, or revert in progress;
#   - HEAD is on a branch, and the branch is not the default branch, which is
#     the one origin/HEAD names, or main and master where origin/HEAD is unset;
#   - the revision resolves to a commit that is an ancestor of HEAD;
#   - no commit between the revision and HEAD is reachable from a
#     remote-tracking ref.
#
# The guard denies whenever it cannot tell what the command would do: a
# revision or -C path holding a glob, a variable, a command substitution, or a
# reflog brace; a git global option other than -C and a GIT_ variable set for
# the command, which can point git at another repository; a command that
# changes directory (a cd, a pushd, env -C, sudo -D); a relative path when the
# envelope names no cwd; a git that fails or answers too late. The hook's own
# timeout lets a command through, so the guard sets a deadline of its own,
# WARDEN_SOFT_RESET_DEADLINE seconds, and denies when it passes.
#
# The judging reads repository state before the command runs, so a soft reset
# that follows another step is denied: that step may have pushed, switched
# branches, or committed. A reset that comes first runs, and steps after it
# are no concern of this guard. A shell run with -c is no step of its own; the
# programs in its script are.
#
# git counts when it stands at a command position, as the splitting in
# lib/command_words.sh defines it. Resets that carry no --soft, or its
# abbreviation, are left to the settings' own rules.
#
# Globals: WARDEN_SOFT_RESET_DEADLINE (seconds git gets, default 4).
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"
# shellcheck source=lib/git_guard.sh
source "${SCRIPT_DIR}/lib/git_guard.sh"

# Git would otherwise judge the repository that holds the hook and not the
# one the command names.
git_guard::unset_repository_env

readonly DENIAL_ADVICE='To squash a branch, use wt -C <worktree> step squash <target>: it rewrites only the branch'\''s own commits and leaves published history alone.'

# Words in the command text that name another repository for git to read; a
# GIT_ variable can do it.
readonly GIT_VARIABLE_PATTERN='(^|[^[:alnum:]_])GIT_[A-Z_]+='

# Global git options whose next word is a value.
readonly GLOBAL_VALUE_OPTIONS=' -c --git-dir --work-tree --namespace --exec-path --super-prefix --config-env '

# What parse_reset_line reports about the line it read.
PR_CHDIRS=()
PR_REV=''
PR_PROBLEM=''

# What collect_reset_line took from each soft reset line, one entry per line.
# The -C paths of all lines run together in RESET_CHDIRS, each line's share
# counted in RESET_CHDIR_COUNTS.
RESET_REVS=()
RESET_PROBLEMS=()
RESET_CHDIR_COUNTS=()
RESET_CHDIRS=()

#######################################
# Emit a deny decision and exit.
# Globals:
#   DENIAL_ADVICE
# Arguments:
#   $1 - what the guard found, appended to the reason.
# Outputs:
#   The permission decision JSON on stdout.
#######################################
deny() {
  jq -nc --arg reason "Soft reset held back: $1. ${DENIAL_ADVICE}" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

#######################################
# Say whether a word is a prefix of a long option, long enough that git's
# option parser takes it as that option.
# Arguments:
#   $1 - the word.
#   $2 - the full option.
# Returns:
#   0 when the word abbreviates the option, 1 otherwise.
#######################################
is_option_abbreviation() {
  [[ ${#1} -ge 3 && "$2" == "$1"* ]]
}

#######################################
# Say why a word's text cannot be read as it stands.
# Arguments:
#   $1 - the word as the command resolver prints it.
# Outputs:
#   The reason on stdout when the word cannot be read.
# Returns:
#   0 when the word is plain text, 1 otherwise.
#######################################
text_problem() {
  case "$1" in
  '')
    echo 'is empty'
    return 1
    ;;
  '~'* | '='*)
    echo 'starts with a tilde or an equals sign the guard does not expand'
    return 1
    ;;
  *['*?[]{}$`<>()!|;&']* | *\\* | *"${CW_NEWLINE}"*)
    echo 'holds a glob, a variable, a substitution, a reflog brace, or other syntax the guard does not expand'
    return 1
    ;;
  esac
  return 0
}

#######################################
# Read one program line and report whether it is git reset with --soft.
# Fills the globals with what the line names. A global option other than -C
# and a flag the guard does not accept become the first problem.
# Globals:
#   GLOBAL_VALUE_OPTIONS, PR_CHDIRS, PR_REV, PR_PROBLEM
# Arguments:
#   $1 - the program line.
# Returns:
#   0 for git reset with --soft, 1 otherwise.
#######################################
parse_reset_line() {
  local -a words
  local count index word arg subcommand='' odd_global='' soft=0 other_mode=''
  local operands=0 after_dashes=0
  PR_CHDIRS=()
  PR_REV=''
  PR_PROBLEM=''

  IFS=' ' read -r -a words <<<"$1"
  [[ "${words[0]-}" == git ]] || return 1
  count=${#words[@]}

  index=1
  while ((index < count)); do
    word="${words[index]}"
    case "${word}" in
    -C)
      PR_CHDIRS+=("${words[index + 1]-}")
      index=$((index + 2))
      ;;
    --no-pager | --paginate | -p | -P | --no-optional-locks)
      index=$((index + 1))
      ;;
    -*)
      odd_global="${odd_global:-${word}}"
      if [[ "${GLOBAL_VALUE_OPTIONS}" == *" ${word} "* ]]; then
        index=$((index + 2))
      else
        index=$((index + 1))
      fi
      ;;
    *)
      subcommand="${word}"
      break
      ;;
    esac
  done
  [[ "${subcommand}" == reset ]] || return 1

  for ((index = index + 1; index < count; index++)); do
    arg="${words[index]}"
    if ((after_dashes)); then
      continue
    fi
    case "${arg}" in
    --)
      after_dashes=1
      PR_PROBLEM="${PR_PROBLEM:-the reset names a pathspec, and only a revision may follow --soft}"
      ;;
    -q) ;;
    --*)
      if is_option_abbreviation "${arg}" --soft; then
        soft=1
      elif is_option_abbreviation "${arg}" --hard ||
        is_option_abbreviation "${arg}" --mixed ||
        is_option_abbreviation "${arg}" --merge ||
        is_option_abbreviation "${arg}" --keep; then
        other_mode="${other_mode:-${arg}}"
      elif ! is_option_abbreviation "${arg}" --quiet; then
        PR_PROBLEM="${PR_PROBLEM:-the reset carries the option ${arg}, which the guard does not accept}"
      fi
      ;;
    -*)
      PR_PROBLEM="${PR_PROBLEM:-the reset carries the option ${arg}, which the guard does not accept}"
      ;;
    *)
      operands=$((operands + 1))
      PR_REV="${PR_REV:-${arg}}"
      ;;
    esac
  done
  ((soft)) || return 1

  if [[ -n "${other_mode}" ]]; then
    PR_PROBLEM="${PR_PROBLEM:-it sits beside a second mode flag (${other_mode})}"
  fi
  if [[ -n "${odd_global}" ]]; then
    PR_PROBLEM="${PR_PROBLEM:-git runs with the global option ${odd_global}, which can change the repository or the configuration it reads}"
  fi
  if ((operands != 1)); then
    PR_PROBLEM="${PR_PROBLEM:-it must name exactly one revision operand, and it names ${operands}}"
  fi
  return 0
}

#######################################
# Judge each soft reset, stopping at the first condition that fails. Reads
# the fields collect_reset_line took from each line.
# Globals:
#   RESET_REVS, RESET_PROBLEMS, RESET_CHDIR_COUNTS, RESET_CHDIRS, CW_SPACE
# Arguments:
#   $1 - the envelope's cwd, possibly empty.
# Outputs:
#   The failed condition on stdout for the first failure.
# Returns:
#   0 when every reset passes every condition, 1 otherwise.
#######################################
judge_reset_lines() {
  local cwd="$1" dir rev chdir why branch default ref paths path sha
  local total unpushed index offset=0 end

  for ((index = 0; index < ${#RESET_REVS[@]}; index++)); do
    if [[ -n "${RESET_PROBLEMS[index]}" ]]; then
      echo "${RESET_PROBLEMS[index]}"
      return 1
    fi

    rev="${RESET_REVS[index]}"
    if ! why="$(text_problem "${rev}")" || [[ "${rev}" == *"${CW_SPACE}"* ]]; then
      echo "the revision ${rev} ${why:-holds a space}"
      return 1
    fi

    dir="${cwd}"
    end=$((offset + RESET_CHDIR_COUNTS[index]))
    for (( ; offset < end; offset++)); do
      chdir="${RESET_CHDIRS[offset]}"
      if ! why="$(text_problem "${chdir}")"; then
        echo "the -C path ${chdir} ${why}"
        return 1
      fi
      chdir="${chdir//${CW_SPACE}/ }"
      if [[ "${chdir}" == /* ]]; then
        dir="${chdir}"
      elif [[ -z "${dir}" ]]; then
        echo "the -C path ${chdir} is relative and the command names no working directory"
        return 1
      else
        dir="${dir%/}/${chdir}"
      fi
    done
    if [[ -z "${dir}" ]]; then
      echo 'the command names no working directory, so the guard cannot tell which repository it resets'
      return 1
    fi
    # One git call locates every marker of an operation in progress, and fails
    # outside a repository.
    if [[ ! -d "${dir}" ]] || ! paths="$(git -C "${dir}" rev-parse \
      --git-path rebase-merge --git-path rebase-apply --git-path sequencer \
      --git-path MERGE_HEAD --git-path CHERRY_PICK_HEAD --git-path REVERT_HEAD \
      2>/dev/null)"; then
      echo "git finds no repository at ${dir}"
      return 1
    fi
    while IFS= read -r path; do
      [[ "${path}" == /* ]] || path="${dir%/}/${path}"
      if [[ -e "${path}" ]]; then
        echo "a rebase, merge, cherry-pick, or revert is in progress (${path##*/} exists)"
        return 1
      fi
    done <<<"${paths}"

    if ! branch="$(git -C "${dir}" symbolic-ref -q --short HEAD 2>/dev/null)"; then
      echo 'HEAD is detached, so the reset would leave no branch pointing at the dropped commits'
      return 1
    fi
    if ref="$(git -C "${dir}" symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null)"; then
      default="${ref#origin/}"
      if [[ "${branch}" == "${default}" ]]; then
        echo "HEAD is on ${branch}, the default branch"
        return 1
      fi
    elif [[ "${branch}" == main || "${branch}" == master ]]; then
      echo "HEAD is on ${branch}, a default branch"
      return 1
    fi

    if ! sha="$(git -C "${dir}" rev-parse --verify --quiet "${rev}^{commit}" 2>/dev/null)"; then
      echo "${rev} does not resolve to a commit"
      return 1
    fi
    if ! git -C "${dir}" merge-base --is-ancestor "${sha}" HEAD 2>/dev/null; then
      echo "${rev} is not an ancestor of HEAD"
      return 1
    fi

    if ! total="$(git -C "${dir}" rev-list --count "${sha}..HEAD" 2>/dev/null)" ||
      ! unpushed="$(git -C "${dir}" rev-list --count "${sha}..HEAD" --not --remotes 2>/dev/null)"; then
      echo 'git could not count the commits the reset drops'
      return 1
    fi
    if ((total != unpushed)); then
      echo "$((total - unpushed)) of the ${total} commits between ${rev} and HEAD are reachable from a remote-tracking ref, so the reset would rewrite pushed history"
      return 1
    fi
  done
  return 0
}

#######################################
# Record what a program line names when it is git reset with --soft.
# Globals:
#   RESET_REVS, RESET_PROBLEMS, RESET_CHDIR_COUNTS, RESET_CHDIRS, PR_CHDIRS,
#   PR_REV, PR_PROBLEM
# Arguments:
#   $1 - the program line.
# Returns:
#   0 when the line is a soft reset, 1 otherwise.
#######################################
collect_reset_line() {
  if ! parse_reset_line "$1"; then
    return 1
  fi
  RESET_REVS+=("${PR_REV}")
  RESET_PROBLEMS+=("${PR_PROBLEM}")
  RESET_CHDIR_COUNTS+=("${#PR_CHDIRS[@]}")
  if ((${#PR_CHDIRS[@]} > 0)); then
    RESET_CHDIRS+=("${PR_CHDIRS[@]}")
  fi
}

main() {
  local command cwd status=0

  git_guard::read_envelope
  command="${GG_COMMAND}"
  cwd="${GG_CWD}"

  if [[ -z "${command}" ]]; then
    return 0
  fi

  # The resolver lists programs in the order they run, so a reset with any
  # other program listed ahead of it follows another step, an earlier reset
  # included.
  git_guard::scan_programs collect_reset_line 1 "${command}"

  if ((${#RESET_REVS[@]} == 0)); then
    return 0
  fi

  if ((GG_CD_SEEN)); then
    deny 'the command changes directory, so the guard cannot resolve which repository the reset runs in'
  fi
  if git_guard::wrapper_may_chdir "${command}"; then
    deny 'the command runs git behind a wrapper that can change directory'
  fi
  if [[ "${command}" =~ ${GIT_VARIABLE_PATTERN} ]]; then
    deny 'the command sets a GIT_ variable, which can point git at another repository'
  fi
  if ((GG_AFTER_STEP)); then
    deny 'the soft reset follows another step in the command, and that step may have pushed, switched branches, or committed. Run the soft reset as the first step of its own command'
  fi

  git_guard::run_with_deadline "${WARDEN_SOFT_RESET_DEADLINE:-4}" deny-unsafe-soft-reset \
    judge_reset_lines "${cwd}" || status=$?
  case "${status}" in
  0) ;;
  2) deny 'the guard could not create a scratch file to judge with' ;;
  *) deny "${GG_DETAIL:-git did not answer before the deadline}" ;;
  esac
  return 0
}

main "$@"
