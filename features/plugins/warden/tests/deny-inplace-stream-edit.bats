#!/usr/bin/env bats
#
# Tests for deny-inplace-stream-edit.sh, the PreToolUse Bash guard that
# denies an in-place stream edit.
#
# The denial cases cover the flag spellings that rewrite a file: a short-flag
# cluster carrying i, the long --in-place, and gawk's `-i inplace`. The silent
# cases cover read-only stream editing, which stays allowed, and a mention of
# the flag inside a quoted argument, which edits nothing.

setup_file() {
  export BATS_TEST_TIMEOUT=10
}

setup() {
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
  load_guard deny-inplace-stream-edit
  isolate_home
}

@test "an in-place sed or awk edit is denied in each spelling and at each command position" {
  local -a forms=(
    "sed -i 's/old/new/' notes.md"
    "sed -i '' 's/old/new/' notes.md"
    "sed -i.bak 's/old/new/' notes.md"
    "sed -Ei 's/old/new/' notes.md"
    "sed --in-place 's/old/new/' notes.md"
    "gsed -i 's/old/new/' notes.md"
    "awk -i inplace '{print}' notes.md"
    "git ls-files && sed -i 's/old/new/' notes.md"
    "cd /tmp; sed -i 's/old/new/' notes.md"
    "(sed -i 's/old/new/' notes.md)"
    "sudo sed -i s/a/b/ /etc/hosts"
    "echo sed -i s/a/b/ notes.md"
  )
  local form
  for form in "${forms[@]}"; do
    assert_denies "${form}"
  done
}

@test "read-only sed and awk, and the flag named as text, stay silent" {
  local -a forms=(
    "sed 's/old/new/' notes.md"
    "grep -n TODO notes.md | sed -n '1,5p'"
    "awk '{print \$1}' notes.md"
    'echo "sed -i is banned here"'
    'rg --files-with-matches TODO'
    "parsed -i 's/old/new/' notes.md"
    'echo "/usr/local/bin/notsed -i notes.md"'
    "parsed -n '1,5p' notes.md"
    ''
  )
  local form
  for form in "${forms[@]}"; do
    assert_silent "${form}"
  done
}

@test "an envelope proposing sed -i prints a PreToolUse denial" {
  assert_main_prints deny \
    '{"tool_name":"Bash","tool_input":{"command":"sed -i s/a/b/ notes.txt"}}'
}
