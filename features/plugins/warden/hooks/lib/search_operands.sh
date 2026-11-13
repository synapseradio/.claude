#!/bin/bash
#
# Library for the warden hooks that must tell the pattern operand of grep and
# rg from the files they open. Source it; it defines functions and constants
# only. Uses only what /bin/bash 3.2 on macOS offers.

# Options whose next word is a value, for grep and for rg. Single letters are
# the option characters; a letter inside a cluster takes the rest of the word
# as its value, or the next word where nothing follows it.
readonly GREP_VALUE_LETTERS='ABCDdefm'
readonly RG_VALUE_LETTERS='ABCEMTdefgjmrt'
readonly SEARCH_LONG_VALUE_OPTIONS=' --after-context --before-context --context --binary-files --devices --directories --exclude --exclude-dir --exclude-from --include --label --max-count --glob --iglob --type --type-not --type-add --max-columns --max-depth --maxdepth --threads --max-filesize --replace --encoding --ignore-file --sort --sortr --engine '

#######################################
# Print one grep or rg program with its pattern operands taken out, so a
# word that only names what to search for is not read as a path to open.
# The pattern is the first word that is no option, unless -e or --regexp
# gives it, in which case each of those operands is a pattern; -f and --file
# name a file of patterns, which is read, so that operand stays. rg --files
# has no pattern.
# Arguments:
#   $1 - grep or rg.
#   The rest - the words after the program name.
# Outputs:
#   The program name and the words that remain, on one line.
#######################################
search_without_pattern() {
  local program="$1" letters word kept="$1" rest letter index
  local pattern_first=1 skip=0 positional_only=0
  shift
  if [[ "${program}" == grep ]]; then
    letters="${GREP_VALUE_LETTERS}"
  else
    letters="${RG_VALUE_LETTERS}"
  fi

  for word in "$@"; do
    # The word after an option that takes a value.
    if [[ "${skip}" == drop ]]; then
      skip=0
      continue
    fi
    if [[ "${skip}" == keep ]]; then
      skip=0
      kept+=" ${word}"
      continue
    fi

    if ((positional_only == 0)) && [[ "${word}" == -- ]]; then
      positional_only=1
      kept+=" ${word}"
      continue
    fi

    if ((positional_only == 0)) && [[ "${word}" == --* ]]; then
      case "${word}" in
      --regexp=*)
        pattern_first=0
        continue
        ;;
      --regexp)
        pattern_first=0
        skip=drop
        continue
        ;;
      --file=* | --files)
        pattern_first=0
        ;;
      --file)
        pattern_first=0
        skip=keep
        ;;
      *)
        [[ "${SEARCH_LONG_VALUE_OPTIONS}" == *" ${word} "* ]] && skip=keep
        ;;
      esac
      kept+=" ${word}"
      continue
    fi

    if ((positional_only == 0)) && [[ "${word}" == -?* ]]; then
      # A cluster of short options; the first that takes a value ends it.
      rest="${word#-}"
      index=0
      while ((index < ${#rest})); do
        letter="${rest:index:1}"
        if [[ "${letters}" == *"${letter}"* ]]; then
          case "${letter}" in
          e)
            pattern_first=0
            if ((index + 1 < ${#rest})); then
              continue 2
            fi
            skip=drop
            continue 2
            ;;
          f)
            pattern_first=0
            ;;
          esac
          if ((index + 1 == ${#rest})); then
            skip=keep
          fi
          break
        fi
        index=$((index + 1))
      done
      kept+=" ${word}"
      continue
    fi

    # A positional word: the first is the pattern unless an option gave one.
    if ((pattern_first)); then
      pattern_first=0
      continue
    fi
    kept+=" ${word}"
  done
  printf '%s\n' "${kept}"
}

#######################################
# Print one program line with the pattern operands of a search program taken
# out. A line whose program is no search program prints unchanged; ripgrep
# counts as rg.
# Arguments:
#   $1 - the program line from command_words::resolve.
# Outputs:
#   The line on stdout.
#######################################
search_line_without_pattern() {
  local -a words
  IFS=' ' read -r -a words <<<"$1"
  case "${words[0]-}" in
  grep | rg | ripgrep)
    [[ "${words[0]}" == ripgrep ]] && words[0]=rg
    search_without_pattern "${words[0]}" "${words[@]:1}"
    ;;
  *)
    printf '%s\n' "$1"
    ;;
  esac
}
