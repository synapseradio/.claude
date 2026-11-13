#!/bin/bash
#
# PreToolUse hook for the Bash tool.
#
# Refuses (permissionDecision: "deny") a command that runs text not standing
# as a command of its own: command substitution $( ), backticks, process
# substitution <( ) and >( ), zsh's =( ), and a subshell ( ) where a command
# starts. A guard reading the command reads what the substitution names, not
# what it produces, so the text that runs is not the text anyone approved.
#
# The shell runs these forms inside double quotes and inside an unquoted
# here-document too, so only single quotes, ANSI-C $'' strings, a backslash
# escape, a here-document with a quoted delimiter, and a comment make them
# inert. Arithmetic $(( )) and (( )), an array assignment, and a glob
# qualifier use parentheses without running a command and stay allowed.
#
# One exemption: a $( ) whose whole text is a read-only query from
# EXEMPT_QUERIES, written in letters, digits, spaces, and _./=:@%+,- alone,
# so it can hold no second step, redirect, quote, or nested substitution.
# A git query may carry `-C <path>` after git: the path is a literal in those
# characters, or a double-quoted string opening with $HOME/ and holding only
# those characters after it. Any other variable, backtick, or substitution in
# the path leaves the text outside the exemption.
#
# Globals: none.
# Stdin:   PreToolUse hook JSON envelope.
# Stdout:  hookSpecificOutput JSON when denying; nothing when allowing.
# Exit:    0 in all cases (the decision travels on stdout, not the exit code).

set -euo pipefail

readonly DENIAL_REASON='Command substitution, backticks, process substitution, and subshells run text that is not its own command, so the guards never read what runs. Run each step as its own command and pass its output on as a literal value, commit a multi-line message with git commit -F <file>, or write the step as a script file in the scratchpad and run that file.'

# Read-only queries a $( ) may hold, matched as the whole text or as its
# first words followed by a space.
readonly -a EXEMPT_QUERIES=(
  'pwd'
  'git rev-parse'
  'git branch --show-current'
  'wt stack base'
)

readonly SAFE_QUERY_PATTERN='^[A-Za-z0-9 _./=:@%+,-]*$'

# `git -C <path> <rest>`: the path is a literal word in the safe characters,
# or a double-quoted string that opens with $HOME/. BASH_REMATCH[2] holds the
# rest, which still has to pass SAFE_QUERY_PATTERN.
# Single quotes are intentional: the pattern matches the literal `$HOME`.
# shellcheck disable=SC2016
readonly GIT_DIR_PATTERN='^git -C ("\$HOME/[A-Za-z0-9 _./=:@%+,-]*"|[A-Za-z0-9_./=:@%+,-]+) (.*)$'

#######################################
# Emit a deny decision and exit.
# Outputs:
#   The permission decision JSON on stdout.
#######################################
deny() {
  jq -nc --arg reason "${DENIAL_REASON}" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

#######################################
# Report whether a substitution's text is an exempt read-only query. A
# `git -C <path>` prefix is set aside, as GIT_DIR_PATTERN describes, and the
# query is then judged as `git` plus the rest.
# Arguments:
#   $1 - the text between $( and ).
# Returns:
#   0 when exempt, 1 otherwise.
#######################################
is_exempt_query() {
  local text="$1" query
  [[ "${text}" != *$'\n'* ]] || return 1
  # Collapse runs of spaces and trim, so spacing cannot dodge the match.
  while [[ "${text}" == *'  '* ]]; do
    text="${text//  / }"
  done
  text="${text# }"
  text="${text% }"
  if [[ "${text}" =~ ${GIT_DIR_PATTERN} ]]; then
    text="git ${BASH_REMATCH[2]}"
  fi
  [[ "${text}" =~ ${SAFE_QUERY_PATTERN} ]] || return 1
  for query in "${EXEMPT_QUERIES[@]}"; do
    if [[ "${text}" == "${query}" || "${text}" == "${query} "* ]]; then
      return 0
    fi
  done
  return 1
}

#######################################
# Check the text after a $( opener at an index; deny unless exempt.
# Globals:
#   CMD, POS
# Outputs:
#   Moves POS past the closing ) of an exempt query.
#######################################
check_substitution() {
  local rest="${CMD:POS+2}" inner
  [[ "${rest}" == *')'* ]] || deny
  inner="${rest%%)*}"
  is_exempt_query "${inner}" || deny
  POS=$((POS + 2 + ${#inner}))
}

#######################################
# Scan the body lines of the here-documents opened on the line just ended.
# Globals:
#   CMD, POS, LEN, HEREDOC_DELIMS, HEREDOC_QUOTED, HEREDOC_STRIP
# Outputs:
#   Moves POS to the newline ending the last body; denies on a live form.
#######################################
scan_heredoc_bodies() {
  local index line end rest j char next inner
  for index in "${!HEREDOC_DELIMS[@]}"; do
    while ((POS < LEN)); do
      rest="${CMD:POS+1}"
      line="${rest%%$'\n'*}"
      end=$((POS + 1 + ${#line}))
      POS="${end}"
      if [[ "${HEREDOC_STRIP[index]}" == 1 ]]; then
        while [[ "${line}" == $'\t'* ]]; do line="${line#$'\t'}"; done
      fi
      [[ "${line}" == "${HEREDOC_DELIMS[index]}" ]] && break
      [[ "${HEREDOC_QUOTED[index]}" == 1 ]] && continue
      j=0
      while ((j < ${#line})); do
        char="${line:j:1}"
        next="${line:j+1:1}"
        case "${char}" in
        "\\") j=$((j + 1)) ;;
        '`') deny ;;
        '$')
          if [[ "${next}" == '(' && "${line:j+2:1}" != '(' ]]; then
            inner="${line:j+2}"
            [[ "${inner}" == *')'* ]] || deny
            is_exempt_query "${inner%%)*}" || deny
          fi
          ;;
        esac
        j=$((j + 1))
      done
    done
  done
  HEREDOC_DELIMS=()
  HEREDOC_QUOTED=()
  HEREDOC_STRIP=()
}

#######################################
# Record a here-document opened at POS (on "<<"), and move past its word.
# Globals:
#   CMD, POS, LEN, HEREDOC_DELIMS, HEREDOC_QUOTED, HEREDOC_STRIP
#######################################
open_heredoc() {
  local strip=0 quoted=0 word='' char
  POS=$((POS + 2))
  if [[ "${CMD:POS:1}" == '-' ]]; then
    strip=1
    POS=$((POS + 1))
  fi
  while [[ "${CMD:POS:1}" == ' ' || "${CMD:POS:1}" == $'\t' ]]; do
    POS=$((POS + 1))
  done
  while ((POS < LEN)); do
    char="${CMD:POS:1}"
    case "${char}" in
    ' ' | $'\t' | $'\n' | ';' | '&' | '|' | '<' | '>' | '(' | ')') break ;;
    "'" | '"' | "\\") quoted=1 ;;
    *) word="${word}${char}" ;;
    esac
    POS=$((POS + 1))
  done
  POS=$((POS - 1))
  HEREDOC_DELIMS+=("${word}")
  HEREDOC_QUOTED+=("${quoted}")
  HEREDOC_STRIP+=("${strip}")
}

main() {
  local char next prev in_double=0 command_start=1 word_start=1 arith=0
  CMD="$(jq -r '.tool_input.command // ""')"
  [[ "${CMD}" == *'('* || "${CMD}" == *'`'* ]] || return 0
  LEN="${#CMD}"
  POS=0
  HEREDOC_DELIMS=()
  HEREDOC_QUOTED=()
  HEREDOC_STRIP=()

  while ((POS < LEN)); do
    char="${CMD:POS:1}"
    next="${CMD:POS+1:1}"

    # Inside double quotes only substitutions and escapes matter.
    if ((in_double)); then
      case "${char}" in
      "\\") POS=$((POS + 1)) ;;
      '"') in_double=0 ;;
      '`') deny ;;
      '$')
        if [[ "${next}" == '(' ]]; then
          if [[ "${CMD:POS+2:1}" == '(' ]]; then
            POS=$((POS + 2))
          else
            check_substitution
          fi
        fi
        ;;
      esac
      POS=$((POS + 1))
      continue
    fi

    # Inside arithmetic, parentheses group numbers; substitutions still run.
    if ((arith > 0)); then
      case "${char}" in
      '(') arith=$((arith + 1)) ;;
      ')') arith=$((arith - 1)) ;;
      '`') deny ;;
      '$')
        if [[ "${next}" == '(' && "${CMD:POS+2:1}" != '(' ]]; then
          check_substitution
        fi
        ;;
      esac
      POS=$((POS + 1))
      continue
    fi

    case "${char}" in
    "'")
      prev="${CMD:POS+1}"
      [[ "${prev}" == *"'"* ]] || break
      prev="${prev%%\'*}"
      POS=$((POS + 1 + ${#prev}))
      command_start=0
      word_start=0
      ;;
    '"')
      in_double=1
      command_start=0
      word_start=0
      ;;
    "\\")
      POS=$((POS + 1))
      command_start=0
      word_start=0
      ;;
    '`') deny ;;
    '$')
      if [[ "${next}" == "'" ]]; then
        # ANSI-C string: skip to the closing quote, honouring escapes.
        POS=$((POS + 2))
        while ((POS < LEN)) && [[ "${CMD:POS:1}" != "'" ]]; do
          [[ "${CMD:POS:1}" == "\\" ]] && POS=$((POS + 1))
          POS=$((POS + 1))
        done
      elif [[ "${next}" == '(' ]]; then
        if [[ "${CMD:POS+2:1}" == '(' ]]; then
          arith=2
          POS=$((POS + 2))
        else
          check_substitution
        fi
      elif [[ "${next}" == '{' ]]; then
        # A parameter expansion's brace opens no command.
        POS=$((POS + 1))
      fi
      command_start=0
      word_start=0
      ;;
    '<' | '>')
      if [[ "${next}" == '(' ]]; then
        deny
      fi
      if [[ "${char}" == '<' && "${next}" == '<' && "${CMD:POS+2:1}" != '<' ]]; then
        open_heredoc
      elif [[ "${char}" == '<' && "${next}" == '<' ]]; then
        POS=$((POS + 2))
      fi
      word_start=1
      ;;
    '=')
      if ((word_start)) && [[ "${next}" == '(' ]]; then
        deny
      fi
      word_start=0
      ;;
    '(')
      if ((command_start)); then
        if [[ "${next}" == '(' ]]; then
          arith=2
          POS=$((POS + 1))
        else
          deny
        fi
      fi
      word_start=0
      ;;
    '#')
      if ((word_start)); then
        while ((POS + 1 < LEN)) && [[ "${CMD:POS+1:1}" != $'\n' ]]; do
          POS=$((POS + 1))
        done
      fi
      ;;
    $'\n')
      if ((${#HEREDOC_DELIMS[@]} > 0)); then
        scan_heredoc_bodies
      fi
      command_start=1
      word_start=1
      ;;
    ';' | '&' | '|' | '{' | '!')
      command_start=1
      word_start=1
      ;;
    ' ' | $'\t')
      word_start=1
      ;;
    *)
      command_start=0
      word_start=0
      ;;
    esac
    POS=$((POS + 1))
  done

  return 0
}

main "$@"
