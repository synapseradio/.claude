#!/usr/bin/env bats
#
# Tests for deny-bulk-home-search.sh, the PreToolUse guard that refuses a
# file search rooted at the filesystem root or a whole home directory.
#
# HOME is pinned to a fixed path so every case reads the same whatever
# machine runs it. The guard reads paths as text and opens nothing.

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard deny-bulk-home-search
  isolate_home
  export HOME=/Users/tester
}

# Run the guard against a command proposed from a given working directory.
run_bash_in() {
  run_bash_hook_in "$1" "$2"
}

# Run the guard against a Grep or Glob call from a given working directory.
# Grep's pattern is a regex over file contents, so only Glob is given one.
run_tool_in() {
  local tool="$1" cwd="$2" path="$3" pattern="$4"
  if [[ "${tool}" == Grep ]]; then
    judge decide_grep "${path}" "${cwd}"
  else
    judge decide_glob "${pattern}" "${path}" "${cwd}"
  fi
}

@test "find from the filesystem root is denied" {
  assert_denies "find / -path '*/hindsight_api/config.py'"
}

@test "find from a tilde home is denied" {
  assert_denies 'find ~ -name config.py'
}

@test "find from \$HOME is denied" {
  # shellcheck disable=SC2016
  assert_denies 'find "$HOME" -name config.py'
}

@test "find from an absolute home path is denied" {
  assert_denies 'find /Users/tester -maxdepth 3 -name x'
}

@test "find from the directory of homes is denied" {
  assert_denies 'find /Users -name x'
}

@test "a second command in a chain is checked" {
  assert_denies 'ls -d ~/.hindsight; find / -name config.py 2>/dev/null'
}

@test "ls -d over a glob at the top of home is denied" {
  assert_denies 'ls -d ~/*/'
}

@test "a recursive ls of home is denied" {
  assert_denies 'ls -R ~'
}

@test "a recursive grep of home is denied" {
  assert_denies 'grep -rl token ~'
}

@test "rg over home is denied" {
  assert_denies 'rg -g "*.py" STRICT ~/'
}

@test "fd over the filesystem root is denied" {
  assert_denies 'fd config.py /'
}

@test "du over home is denied" {
  assert_denies 'du -sh ~'
}

@test "locate is denied" {
  assert_denies 'locate config.py'
}

@test "mdfind without -onlyin is denied" {
  assert_denies 'mdfind -name config.py'
}

@test "find . run from home is denied" {
  run_bash_in /Users/tester 'find . -name x'
  assert_decision deny 'find . from home'
}

@test "rg with no root run from home is denied" {
  run_bash_in /Users/tester 'rg STRICT'
  assert_decision deny 'rg from home'
}

@test "find .. run from one level below home is denied" {
  run_bash_in /Users/tester/projects 'find .. -name x'
  assert_decision deny 'find .. below home'
}

@test "the Grep tool over home is denied" {
  run_tool_in Grep /Users/tester/projects /Users/tester 'STRICT'
  assert_decision deny 'Grep over home'
}

@test "the Grep tool with no path run from home is denied" {
  run_tool_in Grep /Users/tester '' 'STRICT'
  assert_decision deny 'Grep from home'
}

@test "the Glob tool with an absolute recursive pattern over home is denied" {
  run_tool_in Glob /Users/tester/projects '' '/Users/tester/**/config.py'
  assert_decision deny 'Glob over home'
}

@test "the Glob tool with a recursive pattern run from home is denied" {
  run_tool_in Glob /Users/tester '' '**/config.py'
  assert_decision deny 'Glob from home'
}

@test "a denial names what it matched" {
  run_bash_hook 'find / -name x'
  [[ "$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")" == *'find /'* ]]
}

@test "find scoped to a directory inside home stays silent" {
  assert_silent 'find ~/.hindsight/coding-agents -name "*.js"'
}

@test "a glob below a named directory in home stays silent" {
  assert_silent 'ls -d ~/.hindsight/*/'
}

@test "a plain listing of home stays silent" {
  assert_silent 'ls ~'
}

@test "a non-recursive grep of a file in home stays silent" {
  assert_silent 'grep -n STRICT ~/.hindsight/profiles/coding-agent.env'
}

@test "a recursive grep of a project directory stays silent" {
  assert_silent 'grep -rn sleepy src/'
}

@test "rg with no root run from a project stays silent" {
  run_bash_in /Users/tester/projects/app 'rg STRICT'
  assert_no_decision 'rg in a project'
}

@test "mdfind scoped with -onlyin stays silent" {
  assert_silent 'mdfind -onlyin ~/projects -name config.py'
}

@test "a search command named inside a quoted argument stays silent" {
  assert_silent 'echo "find / -name x" > notes.txt'
}

@test "the Grep tool in a project stays silent" {
  run_tool_in Grep /Users/tester/projects/app '' 'STRICT'
  assert_no_decision 'Grep in a project'
}

@test "the Glob tool with a recursive pattern in a project stays silent" {
  run_tool_in Glob /Users/tester/projects/app '' '**/*.ts'
  assert_no_decision 'Glob in a project'
}

@test "an empty command stays silent" {
  assert_silent ''
}

@test "an envelope proposing a search of home prints a PreToolUse denial" {
  assert_main_prints deny 'find with no root, run in /Users/tester' \
    '{"tool_name":"Bash","cwd":"/Users/tester","tool_input":{"command":"find -name x"}}'
  assert_main_prints deny 'Grep in /Users/tester' \
    '{"tool_name":"Grep","cwd":"/Users/tester/app","tool_input":{"pattern":"x","path":".."}}'
  assert_main_prints deny 'Glob **/x.py in /Users/tester' \
    '{"tool_name":"Glob","cwd":"/Users/tester","tool_input":{"pattern":"**/x.py"}}'
}
