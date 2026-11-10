#!/bin/bash
#
# Library for the warden hooks that judge a Bash command by the program it
# runs. Source it; it defines functions only.
#
# command_words::resolve prints one line for each program the command text
# would run: the program's name, then its arguments, separated by spaces.
# A program runs when it stands at a command position: the start of the
# text, or the start of any part after &&, ||, ;, |, &, a newline, or a
# subshell, $( or backtick opener. The wrappers sudo, command, xargs, env,
# exec, nohup, nice, and time, shell keywords such as then and do, and
# leading VAR=value assignments are stepped over to the program behind them.
# The programs in a `sh -c` string and behind find -exec are listed too.
#
# Text inside quotes, a comment, or a here-document body names no program,
# so `echo "rm x"` lists echo alone. A quoted argument stays one word: its
# spaces and newlines come out as the placeholders below.
#
# Uses only what /bin/bash 3.2 on macOS offers, and stays quiet under
# `set -u`.
#
# Globals: CW_WORD, CW_IN_WORD, CW_SEGMENT, CW_DEPTH.
# Stdout:  the program lines.

# Single quotes are intentional: `$(` is matched as literal text.
# shellcheck disable=SC2016
# Stand in for a space or a newline inside a quoted word.
CW_SPACE=$'\001'
CW_NEWLINE=$'\005'

# Depth of nested `sh -c` strings under inspection.
CW_DEPTH=0

# The word, the part, and the in-progress flag of the scan under way.
CW_WORD=''
CW_IN_WORD=0
CW_SEGMENT=''

#######################################
# Append one character to the word being built, as a placeholder when it
# is whitespace.
# Globals:
#   CW_WORD, CW_IN_WORD, CW_SPACE, CW_NEWLINE
# Arguments:
#   $1 - the character.
#######################################
command_words::add_char() {
  case "$1" in
  ' ' | $'\t') CW_WORD+="${CW_SPACE}" ;;
  $'\n') CW_WORD+="${CW_NEWLINE}" ;;
  *) CW_WORD+="$1" ;;
  esac
  CW_IN_WORD=1
}

#######################################
# Close the word being built and add it to the current part.
# Globals:
#   CW_WORD, CW_IN_WORD, CW_SEGMENT
#######################################
command_words::end_word() {
  if ((CW_IN_WORD)); then
    CW_SEGMENT+="${CW_SEGMENT:+ }${CW_WORD}"
    CW_WORD=''
    CW_IN_WORD=0
  fi
}

#######################################
# Close the current part and print it when it holds any word.
# Globals:
#   CW_SEGMENT
# Outputs:
#   The part on stdout, its words separated by spaces.
#######################################
command_words::end_segment() {
  command_words::end_word
  if [[ -n "${CW_SEGMENT}" ]]; then
    printf '%s\n' "${CW_SEGMENT}"
    CW_SEGMENT=''
  fi
}

#######################################
# Read the delimiter word of a here-document that opens at an index.
# Arguments:
#   $1 - the text.
#   $2 - the index just after the <<.
# Outputs:
#   "<dash>:<delimiter>:<next index>" on stdout, where dash is 1 for <<-.
#   Prints nothing when no delimiter word follows.
#######################################
command_words::heredoc_delimiter() {
  local text="$1" index="$2" dash=0 delimiter='' char quote=''
  if [[ "${text:index:1}" == '-' ]]; then
    dash=1
    index=$((index + 1))
  fi
  while [[ "${text:index:1}" == ' ' || "${text:index:1}" == $'\t' ]]; do
    index=$((index + 1))
  done
  # A digit or an operator after << is a shift, not a delimiter.
  [[ "${text:index:1}" =~ ^[A-Za-z_\'\"\\]$ ]] || return 0
  while ((index < ${#text})); do
    char="${text:index:1}"
    if [[ -n "${quote}" ]]; then
      index=$((index + 1))
      if [[ "${char}" == "${quote}" ]]; then
        quote=''
      else
        delimiter+="${char}"
      fi
      continue
    fi
    case "${char}" in
    \' | \")
      quote="${char}"
      ;;
    \\) ;;
    ' ' | $'\t' | $'\n' | ';' | '|' | '&' | '(' | ')' | '<' | '>') break ;;
    *) delimiter+="${char}" ;;
    esac
    index=$((index + 1))
  done
  printf '%s:%s:%s\n' "${dash}" "${delimiter}" "${index}"
}

#######################################
# Step past the bodies of the here-documents opened on the line just ended.
# Arguments:
#   $1 - the text.
#   $2 - the index of the first character after the newline.
#   $3 - the pending here-documents, one "<dash>:<delimiter>" per line.
# Outputs:
#   The index after the last body on stdout.
#######################################
command_words::skip_heredocs() {
  local text="$1" index="$2" pending="$3" entry dash delimiter line compare
  while [[ -n "${pending}" ]]; do
    entry="${pending%%$'\n'*}"
    pending="${pending#"${entry}"}"
    pending="${pending#$'\n'}"
    dash="${entry%%:*}"
    delimiter="${entry#*:}"
    while ((index < ${#text})); do
      line="${text:index}"
      line="${line%%$'\n'*}"
      index=$((index + ${#line} + 1))
      compare="${line}"
      if [[ "${dash}" == 1 ]]; then
        compare="${compare#"${compare%%[!$'\t']*}"}"
      fi
      [[ "${compare}" == "${delimiter}" ]] && break
    done
  done
  printf '%s\n' "${index}"
}

#######################################
# Split command text into its parts and print each part on a line, its
# words separated by spaces. Command substitutions and subshells print as
# parts of their own, ahead of the part that holds them.
# Globals:
#   CW_WORD, CW_IN_WORD, CW_SEGMENT
# Arguments:
#   $1 - the command text.
# Outputs:
#   One part per line on stdout.
#######################################
command_words::split() {
  local text="$1" length index=0 char pair top rest content
  local stack='' saved='' pending='' entry delimiter_info next_index
  length=${#text}
  CW_WORD=''
  CW_IN_WORD=0
  CW_SEGMENT=''

  while ((index < length)); do
    char="${text:index:1}"
    pair="${text:index:2}"
    top="${stack: -1}"

    if [[ "${top}" == D ]]; then
      case "${char}" in
      \\)
        command_words::add_char "${text:index+1:1}"
        index=$((index + 2))
        continue
        ;;
      '"')
        stack="${stack%?}"
        ;;
      '$')
        if [[ "${pair}" == '$(' ]]; then
          saved+=$'\004'"${CW_IN_WORD}"$'\003'"${CW_WORD}"$'\003'"${CW_SEGMENT}"
          CW_WORD=''
          CW_IN_WORD=0
          CW_SEGMENT=''
          stack+=P
          index=$((index + 1))
        else
          command_words::add_char "${char}"
        fi
        ;;
      '`')
        saved+=$'\004'"${CW_IN_WORD}"$'\003'"${CW_WORD}"$'\003'"${CW_SEGMENT}"
        CW_WORD=''
        CW_IN_WORD=0
        CW_SEGMENT=''
        stack+=B
        ;;
      *)
        command_words::add_char "${char}"
        ;;
      esac
      index=$((index + 1))
      continue
    fi

    case "${char}" in
    \\)
      if [[ "${text:index+1:1}" == $'\n' ]]; then
        command_words::end_word
      else
        command_words::add_char "${text:index+1:1}"
      fi
      index=$((index + 2))
      continue
      ;;
    "'")
      rest="${text:index+1}"
      if [[ "${rest}" == *\'* ]]; then
        content="${rest%%\'*}"
      else
        content="${rest}"
      fi
      content="${content// /${CW_SPACE}}"
      content="${content//$'\t'/${CW_SPACE}}"
      content="${content//$'\n'/${CW_NEWLINE}}"
      CW_WORD+="${content}"
      CW_IN_WORD=1
      index=$((index + ${#content} + 2))
      continue
      ;;
    '"')
      stack+=D
      CW_IN_WORD=1
      ;;
    '$' | '(' | '`')
      if [[ "${char}" == '`' && "${top}" == B ]]; then
        command_words::end_segment
        entry="${saved##*$'\004'}"
        saved="${saved%$'\004'*}"
        CW_IN_WORD="${entry%%$'\003'*}"
        entry="${entry#*$'\003'}"
        CW_WORD="${entry%%$'\003'*}"
        CW_SEGMENT="${entry#*$'\003'}"
        stack="${stack%?}"
      elif [[ "${char}" == '$' && "${pair}" != '$(' ]]; then
        command_words::add_char "${char}"
      else
        saved+=$'\004'"${CW_IN_WORD}"$'\003'"${CW_WORD}"$'\003'"${CW_SEGMENT}"
        CW_WORD=''
        CW_IN_WORD=0
        CW_SEGMENT=''
        if [[ "${char}" == '`' ]]; then
          stack+=B
        else
          stack+=P
        fi
        [[ "${char}" == '$' ]] && index=$((index + 1))
      fi
      ;;
    ')')
      if [[ "${top}" == P ]]; then
        command_words::end_segment
        entry="${saved##*$'\004'}"
        saved="${saved%$'\004'*}"
        CW_IN_WORD="${entry%%$'\003'*}"
        entry="${entry#*$'\003'}"
        CW_WORD="${entry%%$'\003'*}"
        CW_SEGMENT="${entry#*$'\003'}"
        stack="${stack%?}"
      fi
      ;;
    '&')
      # The & of >&1, <&3, and &> is part of a redirect, not a separator.
      if ((index > 0)) && [[ "${text:index-1:1}" == '>' || "${text:index-1:1}" == '<' ]] ||
        [[ "${text:index+1:1}" == '>' ]]; then
        command_words::add_char "${char}"
      else
        command_words::end_segment
      fi
      ;;
    ';' | '|')
      command_words::end_segment
      ;;
    $'\n')
      command_words::end_segment
      if [[ -n "${pending}" ]]; then
        index="$(command_words::skip_heredocs "${text}" $((index + 1)) "${pending}")"
        pending=''
        continue
      fi
      ;;
    ' ' | $'\t')
      command_words::end_word
      ;;
    '#')
      if ((CW_IN_WORD)); then
        command_words::add_char "${char}"
      else
        rest="${text:index}"
        rest="${rest%%$'\n'*}"
        index=$((index + ${#rest}))
        continue
      fi
      ;;
    '<')
      if [[ "${pair}" == '<<' && "${text:index+2:1}" != '<' ]]; then
        delimiter_info="$(command_words::heredoc_delimiter "${text}" $((index + 2)))"
        if [[ -n "${delimiter_info}" ]]; then
          command_words::end_word
          next_index="${delimiter_info##*:}"
          delimiter_info="${delimiter_info%:*}"
          pending+="${pending:+$'\n'}${delimiter_info}"
          index="${next_index}"
          continue
        fi
      fi
      command_words::add_char "${char}"
      ;;
    *)
      command_words::add_char "${char}"
      ;;
    esac
    index=$((index + 1))
  done

  # Unwind anything left open by an unbalanced opener.
  command_words::end_segment
  while [[ -n "${saved}" ]]; do
    entry="${saved##*$'\004'}"
    saved="${saved%$'\004'*}"
    CW_IN_WORD="${entry%%$'\003'*}"
    entry="${entry#*$'\003'}"
    CW_WORD="${entry%%$'\003'*}"
    CW_SEGMENT="${entry#*$'\003'}"
    command_words::end_segment
  done
}

#######################################
# Print the options of a wrapper that take a value in the next word.
# Arguments:
#   $1 - the wrapper's name.
# Outputs:
#   The options, space-separated and space-padded, on stdout.
#######################################
command_words::value_options() {
  case "$1" in
  sudo) printf '%s\n' ' -u -g -h -p -C -D -R -T -U -r -t ' ;;
  env) printf '%s\n' ' -u -C -S ' ;;
  xargs) printf '%s\n' ' -I -n -P -L -s -E -d -a ' ;;
  exec) printf '%s\n' ' -a ' ;;
  nice) printf '%s\n' ' -n ' ;;
  *) printf '%s\n' ' ' ;;
  esac
}

#######################################
# Print the program one part runs, and the programs it carries in a shell
# -c string or behind find -exec.
# Arguments:
#   The part's words.
# Outputs:
#   One program line per program on stdout.
#######################################
command_words::emit_command() {
  local -a words=("$@")
  local count=$# index=0 name word values line script position
  local -a inner

  while ((index < count)); do
    word="${words[index]}"
    name="${word##*/}"
    if [[ "${word}" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      index=$((index + 1))
      continue
    fi
    case "${name}" in
    then | do | else | elif | if | while | until | '{' | '!')
      index=$((index + 1))
      ;;
    sudo | env | xargs | exec | command | nohup | nice | time)
      index=$((index + 1))
      values="$(command_words::value_options "${name}")"
      while ((index < count)) && [[ "${words[index]}" == -* ]]; do
        word="${words[index]}"
        # `command -v rm` looks rm up and runs nothing.
        if [[ "${name}" == command && ("${word}" == -v || "${word}" == -V) ]]; then
          return 0
        fi
        if [[ "${values}" == *" ${word} "* ]]; then
          index=$((index + 2))
        else
          index=$((index + 1))
        fi
      done
      ;;
    *) break ;;
    esac
  done
  ((index < count)) || return 0

  name="${words[index]##*/}"
  line="${name}"
  for ((position = index + 1; position < count; position++)); do
    line+=" ${words[position]}"
  done
  printf '%s\n' "${line}"

  case "${name}" in
  bash | sh | zsh | dash | ksh)
    for ((position = index + 1; position < count - 1; position++)); do
      if [[ "${words[position]}" =~ ^-[A-Za-z]*c[A-Za-z]*$ ]]; then
        script="${words[position + 1]}"
        script="${script//${CW_SPACE}/ }"
        script="${script//${CW_NEWLINE}/$'\n'}"
        command_words::resolve "${script}"
        break
      fi
    done
    ;;
  find | gfind)
    for ((position = index + 1; position < count; position++)); do
      case "${words[position]}" in
      -exec | -execdir | -ok | -okdir)
        inner=()
        while ((position + 1 < count)); do
          position=$((position + 1))
          [[ "${words[position]}" == ';' || "${words[position]}" == '+' ]] && break
          inner+=("${words[position]}")
        done
        command_words::emit_command ${inner[@]+"${inner[@]}"}
        ;;
      esac
    done
    ;;
  esac
}

#######################################
# Print each program the command text would run.
# Globals:
#   CW_DEPTH
# Arguments:
#   $1 - the command text.
# Outputs:
#   One line per program on stdout: its name, then its arguments.
#######################################
command_words::resolve() {
  local line
  local -a words
  ((CW_DEPTH < 3)) || return 0
  CW_DEPTH=$((CW_DEPTH + 1))
  while IFS= read -r line; do
    IFS=' ' read -r -a words <<<"${line}"
    command_words::emit_command ${words[@]+"${words[@]}"}
  done < <(command_words::split "$1")
  CW_DEPTH=$((CW_DEPTH - 1))
}
