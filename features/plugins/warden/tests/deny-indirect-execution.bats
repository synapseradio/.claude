#!/usr/bin/env bats
#
# Tests for deny-indirect-execution.sh, the PreToolUse Bash hook that
# refuses a command running text that does not stand as a command of its
# own: command substitution, backticks, process substitution, and a
# subshell.
#
# The deny cases cover each form, the forms inside double quotes and inside
# an unquoted here-document, where the shell still runs them, and an
# exempted query that carries anything beyond the query itself. The silent
# cases cover the same characters where nothing runs: single quotes,
# backslash escapes, quoted here-documents, comments, arithmetic, arrays,
# patterns, and the read-only queries the exemption list names.
#
# Single quotes are intentional throughout: the guard has to receive the
# literal text, never its expansion (SC2016). setup sets HOOK and the
# helpers read it, which shellcheck cannot see (SC2034).
# shellcheck disable=SC2016,SC2034

setup() {
  export HOME="${BATS_TEST_TMPDIR}/home"
  export XDG_CONFIG_HOME="${HOME}/.config"
  export XDG_DATA_HOME="${HOME}/.local/share"
  export XDG_CACHE_HOME="${HOME}/.cache"
  mkdir -p "${HOME}"
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-indirect-execution.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
}

@test "command substitution is denied" {
  assert_denies 'echo $(rm tracked)'
}

@test "command substitution inside double quotes is denied" {
  assert_denies 'echo "today is $(date)"'
}

@test "backticks are denied" {
  assert_denies 'echo `date`'
}

@test "backticks inside double quotes are denied" {
  assert_denies 'echo "now `date`"'
}

@test "input process substitution is denied" {
  assert_denies 'diff <(jq . a.json) a.json'
}

@test "output process substitution is denied" {
  assert_denies 'ls | tee >(wc -l)'
}

@test "zsh =( ) process substitution is denied" {
  assert_denies 'cat =(ls)'
}

@test "a subshell at the start is denied" {
  assert_denies '(cd sub && make)'
}

@test "a subshell after ; is denied" {
  assert_denies 'ls; (rm x)'
}

@test "a subshell after && is denied" {
  assert_denies 'true && (rm x)'
}

@test "a subshell after a pipe is denied" {
  assert_denies 'ls | (cat)'
}

@test "a subshell after a newline is denied" {
  assert_denies $'ls\n(rm x)'
}

@test "command substitution in an unquoted here-document is denied" {
  assert_denies $'cat <<EOF\n$(rm x)\nEOF'
}

@test "a commit message built from a substituted here-document is denied" {
  assert_denies $'git commit -m "$(cat <<\'EOF\'\nfix: x\nEOF\n)"'
}

@test "an exempted query followed by another step is denied" {
  assert_denies 'echo $(git rev-parse HEAD; rm x)'
}

@test "an exempted query holding a nested substitution is denied" {
  assert_denies 'echo $(pwd $(rm x))'
}

@test "an exempted query with a redirect is denied" {
  assert_denies 'echo $(git rev-parse HEAD > out)'
}

@test "a query outside the exemption list is denied" {
  assert_denies 'echo $(git branch -D topic)'
}

@test "a denial says how to run the step instead" {
  run_bash_hook 'echo $(date)'
  local reason
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'its own command'* ]]
  [[ "${reason}" == *'script file in the scratchpad'* ]]
  [[ "${reason}" == *'git commit -F'* ]]
}

@test "git rev-parse in a substitution stays silent" {
  assert_silent 'git -C "$(git rev-parse --show-toplevel)" status'
}

@test "git branch --show-current in a substitution stays silent" {
  assert_silent 'echo "$(git branch --show-current)"'
}

@test "wt stack base in a substitution stays silent" {
  assert_silent 'git rebase $(wt stack base)'
}

@test "pwd in a substitution stays silent" {
  assert_silent 'ls "$(pwd)/src"'
}

@test "substitution text in single quotes stays silent" {
  assert_silent "echo '\$(rm x)'"
}

@test "an escaped dollar stays silent" {
  assert_silent 'echo \$(rm x)'
}

@test "an escaped backtick stays silent" {
  assert_silent 'echo \`date\`'
}

@test "substitution text in an ANSI-C string stays silent" {
  assert_silent "printf \$'a\\\\n\$(rm x)'"
}

@test "substitution text in a comment stays silent" {
  assert_silent $'ls # $(rm x)\npwd'
}

@test "substitution text in a quoted here-document stays silent" {
  assert_silent $'cat <<\'EOF\'\n$(rm x)\n`date`\nEOF'
}

@test "a commit message mentioning a substitution stays silent" {
  assert_silent "git commit -m 'docs: explain \$(x)'"
}

@test "arithmetic expansion stays silent" {
  assert_silent 'echo $((1 + 2))'
}

@test "an arithmetic command stays silent" {
  assert_silent '(( count > 2 )) && echo many'
}

@test "an array assignment stays silent" {
  assert_silent 'args=(a b c)'
}

@test "a zsh glob qualifier stays silent" {
  assert_silent 'ls *(.)'
}

@test "parentheses in a quoted pattern stay silent" {
  assert_silent "grep -E 'a(b|c)' file"
}

@test "parentheses in a jq program stay silent" {
  assert_silent "jq '.items | map(select(.ok))' f.json"
}

@test "parentheses inside double quotes stay silent" {
  assert_silent 'echo "a (b) c"'
}

@test "a regex group in a conditional stays silent" {
  assert_silent '[[ $x =~ ^(a|b)$ ]] && echo y'
}

@test "a here-string stays silent" {
  assert_silent 'jq . <<<"{}"'
}

@test "an input redirect stays silent" {
  assert_silent 'bash -s < script.sh'
}

@test "a parameter expansion stays silent" {
  assert_silent 'ls "${HOME}/x"'
}

@test "an empty command stays silent" {
  assert_silent ''
}
