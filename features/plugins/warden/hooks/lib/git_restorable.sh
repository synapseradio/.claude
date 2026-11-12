#!/bin/bash
#
# Library for the warden hooks that must know whether git can bring a path
# back after it is removed. Source it; it defines functions only.
#
# git_restorable::why_not answers for one absolute path. A path is
# restorable when it does not exist, or when every file at or beneath it is
# tracked by git, identical to HEAD with no staged or unstaged change, and
# nothing beneath it is untracked or ignored. Every error git reports, and
# every case the check cannot settle, counts as not restorable.
#
# The caller must unset GIT_DIR, GIT_INDEX_FILE, GIT_WORK_TREE and kin, so
# git finds the repository that holds the path and not the one the caller
# inherited.
#
# Uses only what /bin/bash 3.2 on macOS offers.
#
# Stdout: the reason a path is not restorable.

#######################################
# Decide whether git can restore everything removing a path would remove.
# Arguments:
#   $1 - the absolute path, with or without trailing slashes.
# Outputs:
#   The reason on stdout when git cannot restore the path.
# Returns:
#   0 when git can restore the path or the path does not exist, 1 otherwise.
#######################################
git_restorable::why_not() {
  local path="$1" bare dir base physical='' top listing line changes
  local -a git_cmd

  bare="${path%"${path##*[!/]}"}"
  if [[ -z "${bare}" ]]; then
    echo 'is the root of the filesystem'
    return 1
  fi
  if [[ ! -e "${bare}" && ! -L "${bare}" ]]; then
    return 0
  fi
  # rm -r on link/ can empty the directory the link points at.
  if [[ "${bare}" != "${path}" && -L "${bare}" ]]; then
    echo 'is a symbolic link named with a trailing slash, which can reach the files it points at'
    return 1
  fi

  if [[ -d "${bare}" && ! -L "${bare}" ]]; then
    dir="${bare}"
    base='.'
    physical="$(cd "${bare}" && pwd -P)" || {
      echo 'is a directory that cannot be entered'
      return 1
    }
  else
    dir="${bare%/*}"
    base="${bare##*/}"
    if [[ "${dir}" == "${bare}" || -z "${dir}" ]]; then
      dir='/'
    fi
  fi

  git_cmd=(git --no-optional-locks --literal-pathspecs
    -c core.fsmonitor=false -C "${dir}")

  top="$("${git_cmd[@]}" rev-parse --show-toplevel 2>/dev/null)" || {
    echo 'is not inside a git work tree'
    return 1
  }
  if [[ -n "${physical}" && "${physical}" == "${top}" ]]; then
    echo 'is the root of a git repository, and removing it removes the .git directory'
    return 1
  fi
  "${git_cmd[@]}" rev-parse --verify --quiet HEAD >/dev/null 2>&1 || {
    echo 'sits in a repository with no commit to restore from'
    return 1
  }

  # Each line reads "<tag> <mode> <object> <stage><TAB><path>"; the tag is H
  # for an ordinary tracked file.
  listing="$("${git_cmd[@]}" ls-files -v --stage -- "${base}" 2>/dev/null)" || {
    echo 'could not be listed by git'
    return 1
  }
  if [[ -z "${listing}" ]]; then
    echo 'is not tracked by git'
    return 1
  fi
  while IFS= read -r line; do
    if [[ "${line}" != 'H '* ]]; then
      echo 'holds a file git is told to treat as unchanged or to leave out of the checkout'
      return 1
    fi
    if [[ "${line}" == 'H 160000 '* ]]; then
      echo 'holds a submodule, whose own files are not in this repository'
      return 1
    fi
  done <<<"${listing}"

  changes="$("${git_cmd[@]}" status --porcelain --ignored \
    --untracked-files=all -- "${base}" 2>/dev/null)" || {
    echo 'could not be checked by git status'
    return 1
  }
  if [[ -n "${changes}" ]]; then
    echo "is not committed and unchanged (git status: ${changes%%$'\n'*})"
    return 1
  fi
  return 0
}
