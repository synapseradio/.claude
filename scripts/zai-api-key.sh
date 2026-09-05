#!/bin/bash
#
# apiKeyHelper for the Z.ai GLM profile.
#
# Prints the Z.ai API token on stdout so Claude Code can use it as the
# Anthropic credential. Claude Code requires that only the key reach
# stdout, so every diagnostic goes to stderr.
#
# The token lives outside this repository, in the dotty-managed secrets
# file. It reaches this script through the environment when the invoking
# process inherited it, and through that file otherwise.
#
# Globals: ZAI_ANTHROPIC_AUTH_TOKEN
# Stdout:  the token
# Stderr:  a diagnostic when the token is absent
# Exit:    0 with the token, 1 without it

set -euo pipefail

readonly SECRETS_FILE="${HOME}/.dotfiles/shell/lib/private/secrets"

if [[ -z "${ZAI_ANTHROPIC_AUTH_TOKEN:-}" && -r "${SECRETS_FILE}" ]]; then
  # shellcheck source=/dev/null
  . "${SECRETS_FILE}" || true
fi

if [[ -z "${ZAI_ANTHROPIC_AUTH_TOKEN:-}" ]]; then
  echo "ZAI_ANTHROPIC_AUTH_TOKEN is unset and ${SECRETS_FILE} does not define it." >&2
  echo "Store it with: dotty env set ZAI_ANTHROPIC_AUTH_TOKEN=... -s" >&2
  exit 1
fi

printf '%s\n' "${ZAI_ANTHROPIC_AUTH_TOKEN}"
