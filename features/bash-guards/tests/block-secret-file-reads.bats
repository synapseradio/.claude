#!/usr/bin/env bats
#
# Tests for block-secret-file-reads.sh, the PreToolUse guard that denies a
# read of a secret-shaped path.
#
# The guard carries two branches, and the plugin registers both: the Bash
# branch reads the proposed shell command, and the Read branch reads a file
# path.
#
# Half the cases here are paths that must stay readable, because a pattern
# is only as good as what it leaves alone. Each of those pairs with a
# denial it sits next to: /private/tmp against a dotfiles private store,
# rotate-secrets.sh against secrets.sh, .secrets.baseline against
# .secrets, secrets.env.example against secrets.env, and .envrc against
# .env. A guard that denied the left-hand side of any pair would be turned
# off within a day.

setup() {
  HOOK="${BATS_TEST_DIRNAME}/../hooks/block-secret-file-reads.sh"
  load "${BATS_TEST_DIRNAME}/hook-helper.bash"

  # The helper points BASH_GUARDS_BANNED_READS at this test's own temporary
  # directory, so the defaults are what a case sees until it writes that
  # file itself.
  #
  # A home-shaped path for the cases that need one. It exists only for the
  # length of this test, and holds no file: the guard matches command text
  # and opens nothing.
  FAKE_HOME="${BATS_TEST_TMPDIR}/home/pilot"
}

@test "cat of an SSH private key is denied" {
  assert_denies 'cat ~/.ssh/id_rsa'
}

@test "an SSH key named without its directory is denied" {
  assert_denies 'base64 id_ed25519'
}

@test "reading AWS credentials under \$HOME is denied" {
  assert_denies 'cat $HOME/.aws/credentials'
}

@test "grepping the GnuPG directory by absolute path is denied" {
  assert_denies "grep -r . ${FAKE_HOME}/.gnupg/private-keys-v1.d"
}

@test "reading a kube config is denied" {
  assert_denies 'cp ~/.kube/config /tmp/config'
}

@test "reading .env is denied" {
  assert_denies 'cat .env'
}

@test "reading .env.local is denied" {
  assert_denies 'head -n 20 .env.local'
}

@test "reading a named local env file is denied" {
  assert_denies 'cat .env.production.local'
}

@test "an input redirect from .env is denied" {
  assert_denies 'while read -r line; do echo "${line}"; done < .env'
}

@test "a private store in a dotfiles checkout is denied" {
  assert_denies 'cat ~/dotfiles/shell/lib/private/tokens.sh'
}

@test "a private store in a dotted dotfiles checkout is denied" {
  assert_denies 'cat ~/.dotfiles/private/keys.sh'
}

@test "a private store under an absolute home is denied" {
  assert_denies "cat ${FAKE_HOME}/dotfiles/private/env"
}

@test "the macOS real /tmp stays readable" {
  assert_silent 'cat /private/tmp/build.log'
}

@test "the macOS real /var stays readable" {
  assert_silent 'tail -n 50 /private/var/log/system.log'
}

@test "a project's own private directory stays readable" {
  assert_silent 'cat src/private/index.ts'
  assert_silent 'cat docs/private/notes.md'
}

@test "a readme inside a dotfiles checkout stays readable" {
  assert_silent 'cat ~/dotfiles/README.md'
}

@test "secrets.env is denied" {
  assert_denies 'cat secrets.env'
}

@test "secrets.sh and its shell variants are denied" {
  assert_denies 'cat config/secrets.sh'
  assert_denies 'cat secrets.zsh'
  assert_denies 'cat secrets.bash'
}

@test "a file with the .secrets extension is denied" {
  assert_denies 'grep -r . prod.secrets'
}

@test "a .secrets directory is denied" {
  assert_denies 'cat .secrets/token'
}

@test "a script that manages secrets stays readable" {
  assert_silent 'cat scripts/rotate-secrets.sh'
  assert_silent 'cat manage-secrets.py'
}

@test "an example or template beside a secrets file stays readable" {
  assert_silent 'cat secrets.env.example'
  assert_silent 'cat secrets.env.template'
}

@test "a detect-secrets baseline stays readable" {
  assert_silent 'cat .secrets.baseline'
}

@test "a word merely containing private stays readable" {
  assert_silent 'cat privateer.txt'
}

@test "a fragment in the banned-reads file is denied" {
  printf '%s\n' 'credentials' >"${BASH_GUARDS_BANNED_READS}"
  assert_denies 'cat ~/work/credentials.yaml'
}

@test "a banned fragment is matched literally, not as a regex" {
  printf '%s\n' 'my.store' >"${BASH_GUARDS_BANNED_READS}"
  assert_denies 'cat ~/my.store/token'
  assert_silent 'cat ~/myXstore/token'
}

@test "a banned fragment needs no escaping to hold" {
  printf '%s\n' 'keys[1].pem' >"${BASH_GUARDS_BANNED_READS}"
  assert_denies 'cat ~/vault/keys[1].pem'
}

@test "a banned-reads denial names the file the fragment came from" {
  printf '%s\n' 'credentials' >"${BASH_GUARDS_BANNED_READS}"
  run_bash_hook 'cat ~/work/credentials.yaml'
  [[ "$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")" == *"${BASH_GUARDS_BANNED_READS}"* ]]
}

@test "a banned fragment still needs a read command to deny" {
  printf '%s\n' 'credentials' >"${BASH_GUARDS_BANNED_READS}"
  assert_silent 'echo "rotate the credentials next week"'
}

@test "comments and blank lines in the banned-reads file are skipped" {
  printf '%s\n' '# what I keep out of reach' '' '   ' 'credentials' \
    >"${BASH_GUARDS_BANNED_READS}"
  assert_denies 'cat ~/work/credentials.yaml'
  assert_silent 'cat README.md'
}

@test "a missing banned-reads file leaves every default in force" {
  export BASH_GUARDS_BANNED_READS="${BATS_TEST_TMPDIR}/absent.conf"
  assert_denies 'cat ~/.ssh/id_rsa'
  assert_silent 'cat README.md'
}

@test "an empty banned-reads file leaves every default in force" {
  : >"${BASH_GUARDS_BANNED_READS}"
  assert_denies 'cat .env'
  assert_silent 'cat README.md'
}

@test "the Read branch denies a dotfiles private store" {
  assert_denies_read "${FAKE_HOME}/dotfiles/shell/lib/private/env.sh"
}

@test "the Read branch denies a banned fragment" {
  printf '%s\n' 'credentials' >"${BASH_GUARDS_BANNED_READS}"
  assert_denies_read "${FAKE_HOME}/work/credentials.yaml"
}

@test "the Read branch leaves the macOS real /tmp alone" {
  assert_silent_read '/private/tmp/build.log'
}

@test "a Bash denial names the matched pattern and the command" {
  local reason
  run_bash_hook 'base64 id_ed25519'
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'SSH private key'* ]]
  [[ "${reason}" == *'command would read'* ]]
}

@test "a Read denial names the matched pattern and the path" {
  local reason
  run_read_hook "${FAKE_HOME}/.aws/credentials"
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason' \
    <<<"${HOOK_OUTPUT}")"
  [[ "${reason}" == *'.aws'* ]]
  [[ "${reason}" == *'Read would open'* ]]
}

@test "reading a project file stays silent" {
  assert_silent 'cat README.md'
}

@test "reading .envrc stays silent" {
  assert_silent 'cat .envrc'
}

@test "reading a shell rc file stays silent" {
  assert_silent 'cat ~/.zshrc'
}

@test "naming .env inside an echo stays silent" {
  assert_silent 'echo "keep .env out of git"'
}

@test "an empty command stays silent" {
  assert_silent ''
}

@test "a tool the guard does not cover stays silent" {
  run_hook_envelope '{"tool_name":"Write","tool_input":{"file_path":".env"}}'
  assert_no_decision 'a Write of .env'
}

@test "the Read branch denies an SSH private key path" {
  assert_denies_read "${FAKE_HOME}/.ssh/id_ed25519"
}

@test "the Read branch denies an .env path" {
  assert_denies_read "${FAKE_HOME}/projects/app/.env"
}

@test "the Read branch stays silent on a source file" {
  assert_silent_read "${FAKE_HOME}/projects/app/README.md"
}
