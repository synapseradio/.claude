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

@test "a search rooted at the disk root, the homes folder, or a home directory is denied" {
  local -a forms=(
    "find / -path '*/hindsight_api/config.py'"
    'find ~ -name config.py'
    "find \"\$HOME\" -name config.py"
    'find /Users/tester -maxdepth 3 -name x'
    'find /Users -name x'
    'ls -d ~/.hindsight; find / -name config.py 2>/dev/null'
    'ls -d ~/*/'
    'ls -R ~'
    'grep -rl token ~'
    'rg -g "*.py" STRICT ~/'
    'fd config.py /'
    'du -sh ~'
    'locate config.py'
    'mdfind -name config.py'
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
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

@test "a search scoped below home, a plain listing, and search commands named as text stay silent" {
  local -a forms=(
    'find ~/.hindsight/coding-agents -name "*.js"'
    'ls -d ~/.hindsight/*/'
    'ls ~'
    'grep -n STRICT ~/.hindsight/profiles/coding-agent.env'
    'grep -rn sleepy src/'
    'mdfind -onlyin ~/projects -name config.py'
    'echo "find / -name x" > notes.txt'
    ''
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "rg with no root run from a project stays silent" {
  run_bash_in /Users/tester/projects/app 'rg STRICT'
  assert_no_decision 'rg in a project'
}

@test "the Grep tool in a project stays silent" {
  run_tool_in Grep /Users/tester/projects/app '' 'STRICT'
  assert_no_decision 'Grep in a project'
}

@test "the Glob tool with a recursive pattern in a project stays silent" {
  run_tool_in Glob /Users/tester/projects/app '' '**/*.ts'
  assert_no_decision 'Glob in a project'
}

@test "an envelope proposing a search of home prints a PreToolUse denial" {
  assert_main_prints deny \
    '{"tool_name":"Bash","cwd":"/Users/tester","tool_input":{"command":"find -name x"}}'
  assert_main_prints deny \
    '{"tool_name":"Grep","cwd":"/Users/tester/app","tool_input":{"pattern":"x","path":".."}}'
  assert_main_prints deny \
    '{"tool_name":"Glob","cwd":"/Users/tester","tool_input":{"pattern":"**/x.py"}}'
}
