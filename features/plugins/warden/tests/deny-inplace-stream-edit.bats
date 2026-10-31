#!/usr/bin/env bats
#
# Tests for deny-inplace-stream-edit.sh, the PreToolUse Bash guard that
# denies an in-place stream edit.
#
# The denial cases cover the flag spellings that rewrite a file: a short-flag
# cluster carrying i, the long --in-place, and gawk's `-i inplace`. The silent
# cases cover read-only stream editing, which stays allowed, and a mention of
# the flag inside a quoted argument, which edits nothing.

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/deny-inplace-stream-edit.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"
}

@test "sed -i is denied" {
  assert_denies "sed -i 's/old/new/' notes.md"
}

@test "sed -i with a BSD backup argument is denied" {
  assert_denies "sed -i '' 's/old/new/' notes.md"
}

@test "sed -i with a suffix is denied" {
  assert_denies "sed -i.bak 's/old/new/' notes.md"
}

@test "sed with a short-flag cluster containing i is denied" {
  assert_denies "sed -Ei 's/old/new/' notes.md"
}

@test "sed --in-place is denied" {
  assert_denies "sed --in-place 's/old/new/' notes.md"
}

@test "gsed -i is denied" {
  assert_denies "gsed -i 's/old/new/' notes.md"
}

@test "awk -i inplace is denied" {
  assert_denies "awk -i inplace '{print}' notes.md"
}

@test "an in-place edit after && is denied" {
  assert_denies "git ls-files && sed -i 's/old/new/' notes.md"
}

@test "an in-place edit after a semicolon is denied" {
  assert_denies "cd /tmp; sed -i 's/old/new/' notes.md"
}

@test "an in-place edit inside a subshell is denied" {
  assert_denies "(sed -i 's/old/new/' notes.md)"
}

@test "a denial points at Edit and Write" {
  run_bash_hook "sed -i 's/old/new/' notes.md"
  [[ "$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")" == *'Edit or Write'* ]]
}

@test "read-only sed stays silent" {
  assert_silent "sed 's/old/new/' notes.md"
}

@test "sed -n in a pipeline stays silent" {
  assert_silent "grep -n TODO notes.md | sed -n '1,5p'"
}

@test "awk without inplace stays silent" {
  assert_silent "awk '{print \$1}' notes.md"
}

@test "the flag named inside a quoted argument stays silent" {
  assert_silent 'echo "sed -i is banned here"'
}

@test "an unrelated command stays silent" {
  assert_silent 'rg --files-with-matches TODO'
}

@test "sed -i wrapped in sudo is denied" {
  assert_denies "sudo sed -i s/a/b/ /etc/hosts"
}

@test "a word ending in sed stays silent" {
  assert_silent "parsed -i 's/old/new/' notes.md"
}

@test "sed named inside a path stays silent" {
  assert_silent 'echo "/usr/local/bin/notsed -i notes.md"'
}

@test "sed -n stays allowed when wrapped in a word that ends in sed" {
  assert_silent "parsed -n '1,5p' notes.md"
}

@test "an empty command stays silent" {
  assert_silent ''
}

# The wrapper word the sudo case needs is bare, and no regex tells `sudo` from
# `echo`. Denying a harmless unquoted echo is the accepted cost of catching a
# real `sudo sed -i`. Pinned so a widening that drops it is a decision, not a
# drift, and so a reader meeting the denial finds it named here.
@test "an unquoted echo of the flag is denied, the cost of the wrapper word" {
  assert_denies "echo sed -i s/a/b/ notes.md"
}
