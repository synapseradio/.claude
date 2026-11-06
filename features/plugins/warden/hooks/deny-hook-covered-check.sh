#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Refuses (permissionDecision: "deny") a command that runs, by hand, a check
# the current repository's git hooks already run on commit or push. The hook
# runs the check on every commit anyway, so a manual run only spends a turn.
#
# The repository is the one holding the envelope's cwd, moved by each `cd`
# the command makes before the program in question. `git -C` is not followed:
# git never stands for a check, and `git -C` does not move the commands that
# come after it.
#
# What the hooks run is read from the pre-commit and pre-push hooks of:
#   lefthook.yml, lefthook.yaml, .lefthook.yml, .lefthook.yaml and their
#     -local variants: every `run:` value under a pre-commit or pre-push key;
#   .pre-commit-config.yaml: every `entry:` value, which names a command only
#     for local hooks, so a hook taken from a remote repository is not read;
#   .husky/pre-commit and .husky/pre-push;
#   the pre-commit and pre-push files in the git hooks directory, that is
#     `git rev-parse --git-path hooks`, which follows core.hooksPath, when
#     they are executable.
# The YAML is read line by line with awk, with no YAML tool, so the guard
# behaves the same on a machine with or without yq. Inline values, quoted
# values, and block scalars (`run: |`) are read; flow-style, anchored, and
# multi-line plain scalars are not. lefthook `scripts:` and `extends:` are
# not read either. Shell files go through lib/command_words.sh.
#
# Each command a hook runs becomes a signature (see command_signature), and
# a command is refused when its signature equals one of them. Anything the
# guard cannot read or resolve is a silent allow.
#
# Globals: none exported.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -uo pipefail
# Fail open: any crash below still ends in a silent exit 0.
trap 'exit 0' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# shellcheck source=lib/command_words.sh
source "${SCRIPT_DIR}/lib/command_words.sh"

readonly UNIT=$'\037'
readonly DEADLINE_SECONDS=2
readonly MAX_YAML_BYTES=65536
readonly MAX_SCRIPT_BYTES=4096
readonly MAX_RECORD_CHARS=2048
readonly STARTED="${SECONDS}"

# Programs that are no check: a signature naming one would refuse ordinary
# work. The hook runners are here too, so a shim that calls lefthook does
# not make `lefthook run` a refused command.
readonly GENERIC_PROGRAMS=' git echo cat printf grep egrep fgrep rg sed awk find ls cd test [ [[ exit return true false : set export unset source . eval read wait trap bash sh zsh dash ksh node deno ruby perl php env xargs command exec time nohup nice sudo mkdir rmdir cp mv rm trash touch ln chmod jq yq curl wget tee head tail sort uniq wc diff cmp date sleep tr cut basename dirname pwd which type declare local shift if then else fi do done for while case esac lefthook call_lefthook husky pre-commit '

# Programs that name a check only with a subcommand after them.
readonly NEEDS_SUBCOMMAND=' make just task cargo go docker uv pip pip3 gradle mvn dotnet kubectl terraform gh helm brew '

# Programs whose job is running tests. A test run stays allowed.
readonly TEST_PROGRAMS=' jest vitest bats pytest mocha rstest playwright cypress rspec phpunit ava tap karma '

# Flags that change how a tool runs without changing which check it is.
readonly IGNORED_FLAGS=' --fix --write -w --staged --quiet -q --cache --color --no-color --verbose -v --silent --no-error-on-unmatched-pattern '

# Package-manager words that are never a script name.
readonly PM_BUILTINS=' install i add a remove rm uninstall update upgrade up link unlink init create exec x dlx pm patch publish pack audit outdated why ls list info cache config help version login logout whoami run test start stop restart '

readonly DENIAL_REASON_HEAD="The repository's git hooks run this check on commit or push. Commit, and let the hook run it."

# The signature of the program under inspection, set by command_signature:
# SIG_HEAD names the program or package script, SIG_SUB its subcommand (empty
# when the signature covers every run of the program), SIG_FLAGS the flags a
# matching run must carry, and SIG_WORDS and SIG_SECOND the words and the
# second word of the run itself.
SIG_HEAD=''
SIG_SUB=''
SIG_FLAGS=''
SIG_WORDS=''
SIG_SECOND=''

# The signatures the current repository's hooks produce, one per line, each
# "head<US>sub<US>flags<US>source<US>command". LOADED_DIR is the directory they
# were read for, LOADED_OK whether any were found.
HOOK_SIGS=''
LOADED_DIR=''
LOADED_OK=1

#######################################
# Succeed when a name appears in a space-padded list.
# Arguments:
#   $1 - the padded list.
#   $2 - the name.
#######################################
in_list() {
  [[ "$1" == *" $2 "* ]]
}

#######################################
# Succeed when a script name or subcommand is a test run.
# Arguments:
#   $1 - the name.
#######################################
is_test_name() {
  case "$1" in
  test | tests | test:* | test-* | *:test | *:tests | *-test | *-tests | pretest | posttest) return 0 ;;
  *) return 1 ;;
  esac
}

#######################################
# Drop the flags of a runner from the front of WORDS, then its separator.
# Globals:
#   WORDS
#######################################
skip_runner_flags() {
  while ((${#WORDS[@]} > 0)) && [[ "${WORDS[0]}" == -* ]]; do
    if [[ "${WORDS[0]}" == -- ]]; then
      WORDS=(${WORDS[@]+"${WORDS[@]:1}"})
      return 0
    fi
    if in_list ' -p --package -c --call --registry ' "${WORDS[0]}"; then
      WORDS=(${WORDS[@]+"${WORDS[@]:2}"})
    else
      WORDS=(${WORDS[@]+"${WORDS[@]:1}"})
    fi
  done
}

#######################################
# Drop one package runner from the front of WORDS: npx and bunx, bun x,
# pnpm dlx, npm exec, uv run, poetry run, python -m, and their kin.
# Globals:
#   WORDS
# Returns:
#   0 when a runner was dropped, 1 otherwise.
#######################################
strip_runner() {
  local name="${WORDS[0]##*/}" sub="${WORDS[1]-}"
  case "${name}" in
  bunx | npx | pnpx)
    WORDS=(${WORDS[@]+"${WORDS[@]:1}"})
    ;;
  bun | pnpm | npm | yarn)
    case "${sub}" in
    x | dlx | exec) WORDS=(${WORDS[@]+"${WORDS[@]:2}"}) ;;
    *) return 1 ;;
    esac
    ;;
  uv)
    if [[ "${sub}" == run ]]; then
      WORDS=(${WORDS[@]+"${WORDS[@]:2}"})
    elif [[ "${sub}" == tool && "${WORDS[2]-}" == run ]]; then
      WORDS=(${WORDS[@]+"${WORDS[@]:3}"})
    else
      return 1
    fi
    ;;
  uvx | pipx) WORDS=(${WORDS[@]+"${WORDS[@]:1}"}) ;;
  poetry | pdm | pipenv | hatch)
    [[ "${sub}" == run ]] || return 1
    WORDS=(${WORDS[@]+"${WORDS[@]:2}"})
    ;;
  python | python3 | python3.*)
    [[ "${sub}" == -m ]] || return 1
    WORDS=(${WORDS[@]+"${WORDS[@]:2}"})
    ;;
  *) return 1 ;;
  esac
  skip_runner_flags
  return 0
}

#######################################
# Set SIG_HEAD for a package-manager command that runs a package script.
# Arguments:
#   $1 - the package manager's name.
#   The rest of its words.
# Returns:
#   0 with SIG_HEAD set, 1 when the command runs no script or runs a test.
#######################################
script_signature() {
  local manager="$1" scope='' has_run=0 script='' word
  shift
  while (($# > 0)); do
    word="$1"
    shift
    case "${word}" in
    --) break ;;
    --filter | -F | --cwd | --workspace | --prefix | --dir | -C)
      scope+="${scope:+,}${word}=${1-}"
      (($# > 0)) && shift
      ;;
    --filter=* | --cwd=* | --workspace=* | --prefix=* | --dir=*)
      scope+="${scope:+,}${word}"
      ;;
    -*) ;;
    run | run-script | rum | urn)
      if ((has_run == 0)); then
        has_run=1
      else
        script="${word}"
        break
      fi
      ;;
    *)
      script="${word}"
      break
      ;;
    esac
  done

  [[ -n "${script}" ]] || return 1
  if ((has_run == 0)); then
    # npm runs only its own commands without `run`; bun runs the others
    # as scripts and keeps a few more for itself.
    [[ "${manager}" != npm ]] || return 1
    in_list "${PM_BUILTINS}" "${script}" && return 1
    if [[ "${manager}" == bun ]]; then
      in_list ' build dev repl completions ' "${script}" && return 1
    fi
  fi
  is_test_name "${script}" && return 1
  SIG_HEAD="pm:${manager}:${scope}:${script}"
  return 0
}

#######################################
# Work out the signature of one program: what a hook and a manual run must
# share for the run to count as the hook's check.
#   - a package script: package manager, scope flags, and script name, so
#     `bun run build` and `bun run build:check` differ;
#   - a tool with a subcommand: the program and that subcommand, so
#     `biome check` matches `biome check --staged`;
#   - a tool without one: the program and its leading flags, minus the
#     flags that only change how it runs, so `tsc --noEmit` needs --noEmit.
#     Every run of that program with those flags matches, a file argument
#     included, since a bare word after a program may be a subcommand.
# A package runner in front (bunx, npx, uv run, python -m) is dropped first.
# A generic program, a test run, and a program name holding a shell
# expansion have no signature.
# Globals:
#   SIG_HEAD, SIG_SUB, SIG_FLAGS, SIG_WORDS, SIG_SECOND
# Arguments:
#   The program's name, then its arguments.
# Returns:
#   0 with the signature set, 1 when the program has none.
#######################################
command_signature() {
  local -a WORDS
  local name sub flags='' index
  SIG_HEAD=''
  SIG_SUB=''
  SIG_FLAGS=''
  SIG_WORDS=''
  SIG_SECOND=''
  WORDS=("$@")

  while ((${#WORDS[@]} > 0)) && strip_runner; do :; done
  ((${#WORDS[@]} > 0)) || return 1
  SIG_WORDS=" ${WORDS[*]} "
  SIG_SECOND="${WORDS[1]-}"
  name="${WORDS[0]##*/}"

  [[ "${name}" =~ ^[A-Za-z0-9._@-][A-Za-z0-9._@+-]*$ ]] || return 1

  case "${name}" in
  bun | npm | pnpm | yarn)
    script_signature "${name}" ${WORDS[@]+"${WORDS[@]:1}"}
    return
    ;;
  python | python3 | python3.*) return 1 ;;
  esac
  in_list "${GENERIC_PROGRAMS}" "${name}" && return 1
  in_list "${TEST_PROGRAMS}" "${name}" && return 1

  sub="${WORDS[1]-}"
  if [[ "${sub}" =~ ^[a-z][a-z0-9-]*$ ]]; then
    is_test_name "${sub}" && return 1
    SIG_HEAD="tool:${name}"
    SIG_SUB="${sub}"
    return 0
  fi
  in_list "${NEEDS_SUBCOMMAND}" "${name}" && return 1

  for ((index = 1; index < ${#WORDS[@]}; index++)); do
    [[ "${WORDS[index]}" == -* ]] || break
    in_list "${IGNORED_FLAGS}" "${WORDS[index]}" && continue
    flags+="${flags:+ }${WORDS[index]}"
  done
  SIG_HEAD="tool:${name}"
  SIG_FLAGS="${flags}"
  return 0
}

#######################################
# Record the signature of every program a piece of command text runs.
# Globals:
#   HOOK_SIGS, STARTED, DEADLINE_SECONDS
# Arguments:
#   $1 - the command text.
#   $2 - the file it came from, for the refusal message.
#######################################
add_commands() {
  local text="${1:0:MAX_RECORD_CHARS}" source="$2" line display programs
  local -a words
  # The scanner is the slow part, so no scan starts once time has run out.
  ((SECONDS - STARTED < DEADLINE_SECONDS)) || return 0
  # A command substitution, not a process substitution: bash 3.2 keeps the
  # descriptor of each <( ) open for the life of the shell, and a hook file
  # with a few hundred commands would run the shell out of descriptors.
  programs="$(command_words::resolve "${text}")" || return 0
  while IFS= read -r line; do
    ((SECONDS - STARTED < DEADLINE_SECONDS)) || return 0
    [[ -n "${line}" ]] || continue
    IFS=' ' read -r -a words <<<"${line}"
    command_signature ${words[@]+"${words[@]}"} || continue
    display="${line//${CW_SPACE}/ }"
    display="${display//${CW_NEWLINE}/ }"
    HOOK_SIGS+="${SIG_HEAD}${UNIT}${SIG_SUB}${UNIT}${SIG_FLAGS}${UNIT}${source}${UNIT}${display}"$'\n'
  done <<<"${programs}"
}

#######################################
# Print each command a lefthook file runs in its pre-commit and pre-push
# hooks, one per line, with the newlines of a block scalar as \005.
# Arguments:
#   $1 - the file.
# Outputs:
#   One command per line on stdout.
#######################################
lefthook_runs() {
  head -c "${MAX_YAML_BYTES}" "$1" | awk '
    function indent_of(s) { match(s, /^ */); return RLENGTH }
    function unquote(v,   sq) {
      sq = "\047"
      sub(/^[[:space:]]+/, "", v)
      if (substr(v, 1, 1) == "\"") { v = substr(v, 2); sub(/".*$/, "", v); return v }
      if (substr(v, 1, 1) == sq) { v = substr(v, 2); sub(sq ".*$", "", v); return v }
      sub(/[[:space:]]+#.*$/, "", v)
      sub(/[[:space:]]+$/, "", v)
      return v
    }
    function emit() { if (block != "") print block; block = ""; in_block = 0 }
    {
      line = $0
      if (in_block) {
        if (line ~ /^[[:space:]]*$/) next
        if (indent_of(line) > key_indent) {
          t = line
          sub(/^[[:space:]]+/, "", t)
          block = block (block == "" ? "" : "\005") t
          next
        }
        emit()
      }
      if (line ~ /^[[:space:]]*#/ || line ~ /^[[:space:]]*$/) next
      if (indent_of(line) == 0 && line ~ /^[A-Za-z0-9_.-]+:/) {
        top = line
        sub(/:.*$/, "", top)
      }
      if (top != "pre-commit" && top != "pre-push") next
      if (line ~ /^[[:space:]]*(-[[:space:]]+)?run:/) {
        key_indent = index(line, "run:") - 1
        v = line
        sub(/^[[:space:]]*(-[[:space:]]+)?run:[[:space:]]*/, "", v)
        if (v ~ /^[|>][-+0-9]*[[:space:]]*(#.*)?$/) { in_block = 1; block = "" }
        else if (v != "") print unquote(v)
      }
    }
    END { emit() }
  '
}

#######################################
# Print each entry a pre-commit configuration runs, one per line. A hook
# restricted to the manual stage is left out.
# Arguments:
#   $1 - the file.
# Outputs:
#   One entry per line on stdout.
#######################################
precommit_entries() {
  head -c "${MAX_YAML_BYTES}" "$1" | awk '
    function unquote(v,   sq) {
      sq = "\047"
      sub(/^[[:space:]]+/, "", v)
      if (substr(v, 1, 1) == "\"") { v = substr(v, 2); sub(/".*$/, "", v); return v }
      if (substr(v, 1, 1) == sq) { v = substr(v, 2); sub(sq ".*$", "", v); return v }
      sub(/[[:space:]]+#.*$/, "", v)
      sub(/[[:space:]]+$/, "", v)
      return v
    }
    function flush() {
      if (entry != "" && !(stages ~ /manual/ && stages !~ /commit|push/)) print entry
      entry = ""; stages = ""
    }
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*-[[:space:]]+id:/ { flush() }
    /^[[:space:]]*(-[[:space:]]+)?stages:/ { stages = $0 }
    /^[[:space:]]*(-[[:space:]]+)?entry:/ {
      v = $0
      sub(/^[^:]*:[[:space:]]*/, "", v)
      if (v !~ /^[|>]/) entry = unquote(v)
    }
    END { flush() }
  '
}

#######################################
# Record the commands a file of YAML names, read by one of the parsers above.
# Arguments:
#   $1 - the parser function.
#   $2 - the file.
#   $3 - the name to show in a refusal.
#######################################
collect_yaml() {
  local parser="$1" file="$2" label="$3" record
  [[ -f "${file}" ]] || return 0
  while IFS= read -r record; do
    add_commands "${record//$'\005'/$'\n'}" "${label}"
  done < <("${parser}" "${file}")
}

#######################################
# Record the commands a hook script runs.
# Arguments:
#   $1 - the file.
#   $2 - the name to show in a refusal.
#   $3 - 1 when the file must be executable to count.
#######################################
collect_script() {
  local file="$1" label="$2" need_exec="$3" text
  [[ -f "${file}" ]] || return 0
  if [[ "${need_exec}" == 1 && ! -x "${file}" ]]; then
    return 0
  fi
  text="$(head -c "${MAX_SCRIPT_BYTES}" "${file}")" || return 0
  add_commands "${text}" "${label}"
}

#######################################
# Read the commands the repository holding a directory runs in its hooks.
# Globals:
#   HOOK_SIGS, LOADED_DIR, LOADED_OK
# Arguments:
#   $1 - the directory.
# Returns:
#   0 when the repository's hooks run at least one signed command.
#######################################
load_hook_signatures() {
  local dir="$1" root hooks_dir name hook

  if [[ "${dir}" == "${LOADED_DIR}" ]]; then
    return "${LOADED_OK}"
  fi
  LOADED_DIR="${dir}"
  LOADED_OK=1
  HOOK_SIGS=''

  root="$(git -C "${dir}" rev-parse --show-toplevel 2>/dev/null)" || return 1
  hooks_dir="$(git -C "${dir}" rev-parse --path-format=absolute --git-path hooks 2>/dev/null)" || hooks_dir=''

  for name in lefthook.yml lefthook.yaml .lefthook.yml .lefthook.yaml \
    lefthook-local.yml lefthook-local.yaml .lefthook-local.yml .lefthook-local.yaml; do
    collect_yaml lefthook_runs "${root}/${name}" "${name}"
  done
  collect_yaml precommit_entries "${root}/.pre-commit-config.yaml" '.pre-commit-config.yaml'
  for hook in pre-commit pre-push; do
    collect_script "${root}/.husky/${hook}" ".husky/${hook}" 0
    if [[ -n "${hooks_dir}" ]]; then
      collect_script "${hooks_dir}/${hook}" "the git ${hook} hook" 1
    fi
  done

  if [[ -n "${HOOK_SIGS}" ]]; then
    LOADED_OK=0
  fi
  return "${LOADED_OK}"
}

#######################################
# Find the hook command whose signature a program shares.
# Globals:
#   HOOK_SIGS
# Arguments:
#   $1 - the program's SIG_HEAD.
#   $2 - its SIG_SECOND.
#   $3 - its SIG_WORDS.
# Outputs:
#   "source<US>command" of the first match on stdout.
# Returns:
#   0 on a match, 1 otherwise.
#######################################
find_covering_hook() {
  local want_head="$1" second="$2" padded_words="$3"
  local entry head sub rest flags flag
  local -a required
  while IFS= read -r entry; do
    [[ -n "${entry}" ]] || continue
    head="${entry%%"${UNIT}"*}"
    [[ "${head}" == "${want_head}" ]] || continue
    rest="${entry#*"${UNIT}"}"
    sub="${rest%%"${UNIT}"*}"
    rest="${rest#*"${UNIT}"}"
    [[ -z "${sub}" || "${sub}" == "${second}" ]] || continue
    flags="${rest%%"${UNIT}"*}"
    rest="${rest#*"${UNIT}"}"
    required=()
    IFS=' ' read -r -a required <<<"${flags}"
    for flag in ${required[@]+"${required[@]}"}; do
      [[ "${padded_words}" == *" ${flag} "* ]] || continue 2
    done
    printf '%s\n' "${rest}"
    return 0
  done <<<"${HOOK_SIGS}"
  return 1
}

#######################################
# Emit a deny decision naming the hook command that covers the check.
# Arguments:
#   $1 - "source<US>command" of the covering hook.
# Outputs:
#   The permission decision JSON on stdout.
#######################################
deny() {
  local covering="$1" source command reason
  source="${covering%%"${UNIT}"*}"
  command="${covering#*"${UNIT}"}"
  reason="${DENIAL_REASON_HEAD} (${source} runs: ${command:0:120})"
  jq -nc --arg reason "${reason}" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
}

#######################################
# Print the directory a cd moves to, or nothing when it stays put.
# Arguments:
#   $1 - the directory the cd runs in.
#   The cd's arguments.
#######################################
cd_target() {
  local dir="$1" target
  shift
  while (($# > 0)) && [[ "$1" == -L || "$1" == -P || "$1" == -- ]]; do
    shift
  done
  if (($# == 0)); then
    target="${HOME}"
  else
    target="${1//${CW_SPACE}/ }"
  fi
  [[ "${target}" != - ]] || return 0
  if [[ "${target}" == \~ || "${target}" == \~/* ]]; then
    target="${HOME}${target#\~}"
  fi
  [[ "${target}" == /* ]] || target="${dir}/${target}"
  [[ -d "${target}" ]] || return 0
  printf '%s\n' "${target}"
}

main() {
  local input command cwd dir line moved covering head second padded
  local -a words

  input="$(cat)"
  command="$(jq -r '.tool_input.command // ""' <<<"${input}")" || return 0
  cwd="$(jq -r '.cwd // ""' <<<"${input}")" || return 0
  [[ -n "${command}" ]] || return 0
  [[ -n "${cwd}" ]] || cwd="${PWD}"
  [[ -d "${cwd}" ]] || return 0
  dir="${cwd}"

  while IFS= read -r line; do
    IFS=' ' read -r -a words <<<"${line}"
    if [[ "${words[0]}" == cd ]]; then
      moved="$(cd_target "${dir}" ${words[@]+"${words[@]:1}"})"
      [[ -z "${moved}" ]] || dir="${moved}"
      continue
    fi
    command_signature ${words[@]+"${words[@]}"} || continue
    # Reading the hooks reuses the signature globals, so keep this command's.
    head="${SIG_HEAD}"
    second="${SIG_SECOND}"
    padded="${SIG_WORDS}"
    load_hook_signatures "${dir}" || continue
    if covering="$(find_covering_hook "${head}" "${second}" "${padded}")"; then
      deny "${covering}"
      return 0
    fi
  done < <(command_words::resolve "${command}")

  return 0
}

main "$@"
