#!/usr/bin/env bash
# Claude Code status line — mirrors the Starship prompt style.
# Receives JSON on stdin; outputs a single status line.
#
# Colors: Open Color hex values (https://yeun.github.io/open-color/).
#   directory  → blue.6  (#228be6)   git branch → blue.5  (#339af0)
#   staged     → teal.5  (#20c997)   modified   → yellow.6(#fab005)
#   untracked  → gray.5  (#adb5bd)   brackets   → gray.6  (#868e96)
#   context    → cyan.6  (#15aabf)   model      → gray.6  (#868e96)

input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# ── Open Color ANSI (truecolor) ─────────────────────────────────────────
function oc() {
  case "$1" in
    blue.6)    printf '\033[38;2;34;139;230m' ;;
    blue.5)    printf '\033[38;2;51;154;240m' ;;
    teal.5)    printf '\033[38;2;32;201;151m' ;;
    yellow.6)  printf '\033[38;2;250;176;5m' ;;
    gray.5)    printf '\033[38;2;173;181;189m' ;;
    gray.6)    printf '\033[38;2;134;142;150m' ;;
    cyan.6)    printf '\033[38;2;21;170;191m' ;;
    green.6)   printf '\033[38;2;64;192;87m' ;;
    reset)     printf '\033[0m' ;;
  esac
}

# ── Directory ────────────────────────────────────────────────────────────
if [[ -n "$cwd" ]]; then
  dir="${cwd/#$HOME/⌂}"
  IFS='/' read -ra parts <<< "$dir"
  count="${#parts[@]}"
  if (( count > 3 )); then
    dir="⑂ ${parts[$((count-3))]}/${parts[$((count-2))]}/${parts[$((count-1))]}"
  fi
fi

# ── Git branch + status ─────────────────────────────────────────────────
git_info=""
if git_root=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null); then
  branch=$(git -C "$git_root" symbolic-ref --short HEAD 2>/dev/null \
           || git -C "$git_root" rev-parse --short HEAD 2>/dev/null)

  staged=$(git -C "$git_root" diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
  modified=$(git -C "$git_root" diff --name-only 2>/dev/null | wc -l | tr -d ' ')
  untracked=$(git -C "$git_root" ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')

  indicators=""
  (( staged > 0 ))    && indicators+="$(oc teal.5)●${staged}$(oc reset) "
  (( modified > 0 ))  && indicators+="$(oc yellow.6)◐${modified}$(oc reset) "
  (( untracked > 0 )) && indicators+="$(oc gray.5)○${untracked}$(oc reset) "
  indicators="${indicators% }"

  if [[ -n "$indicators" ]]; then
    git_info=" $(oc blue.5)▸${branch}$(oc reset) $(oc gray.6)⎡$(oc reset)${indicators}$(oc gray.6)⎤$(oc reset)"
  else
    git_info=" $(oc blue.5)▸${branch}$(oc reset)"
  fi
fi

# ── Context usage ────────────────────────────────────────────────────────
ctx_info=""
if [[ -n "$used" ]]; then
  ctx_info=" $(oc cyan.6)ctx:${used}%$(oc reset)"
fi

# ── Model ────────────────────────────────────────────────────────────────
model_info=""
if [[ -n "$model" ]]; then
  model_info=" $(oc gray.6)${model}$(oc reset)"
fi

# ── Assemble ─────────────────────────────────────────────────────────────
printf '%s%s%s%s' "$(oc blue.6)${dir}$(oc reset)" "$git_info" "$ctx_info" "$model_info"
