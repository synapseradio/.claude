#!/usr/bin/env bash
# Claude Code status line — mirrors the Starship prompt style configured in
# ~/.dotty/config/starship/starship.toml. Receives JSON on stdin; writes a
# single line to stdout.
#
# Layout
#   <dir>  ▸<branch> ▴<ahead> ▿<behind> ⎡<status>⎤ ▴+<adds> ▿−<dels> [⊕<pr>] ctx:<n>% <model>
#
# Status indicators (circle family, matches [git_status] in starship.toml:217):
#   ●staged   ◐modified  ○untracked  ◎renamed  ⊘deleted  ⊗conflicted  ◉stashed
#   ✓ shows alone when the working tree is clean. Brackets are dropped
#   entirely on a clean repo with no upstream divergence.
#
# Colors (Open Color hex; consistent with starship.toml):
#   directory  blue.6  #228be6     git branch  blue.5   #339af0
#   ahead      green.6 #40c057     behind      red.6    #fa5252
#   staged     teal.5  #20c997     modified    yellow.6 #fab005
#   untracked  gray.5  #adb5bd     renamed     blue.4   #4dabf7
#   deleted    red.6   #fa5252     conflicted  pink.6   #e64980
#   stashed    violet.6 #845ef7    brackets    gray.6   #868e96
#   added      green.6 #40c057     removed     red.6    #fa5252
#   pr-link    blue.6  #228be6     context     cyan.6   #15aabf
#   model      gray.6  #868e96
#
# PR segment: a single ⊕ icon that hyperlinks to the open PR for this
# branch, or to the new-PR compare page when no PR exists yet. The URL
# and state come from ~/.dotty/plugins/git/pr-link.sh --state, which
# emits "state<TAB>url" with state ∈ open|none|unknown — or empty
# output on the default branch / detached HEAD / unparseable remote,
# so the segment self-suppresses in those cases.
#
# Color encodes whether a PR is open: blue.6 means an open PR exists
# (or the resolver could not check), gray.5 means no PR yet and the
# click drops the user on the compare page to create one.

input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# ── Open Color ANSI (truecolor) ─────────────────────────────────────────
function oc() {
  case "$1" in
  blue.6) printf '\033[38;2;34;139;230m' ;;
  blue.5) printf '\033[38;2;51;154;240m' ;;
  blue.4) printf '\033[38;2;77;171;247m' ;;
  teal.5) printf '\033[38;2;32;201;151m' ;;
  yellow.6) printf '\033[38;2;250;176;5m' ;;
  gray.5) printf '\033[38;2;173;181;189m' ;;
  gray.6) printf '\033[38;2;134;142;150m' ;;
  cyan.6) printf '\033[38;2;21;170;191m' ;;
  green.6) printf '\033[38;2;64;192;87m' ;;
  red.6) printf '\033[38;2;250;82;82m' ;;
  pink.6) printf '\033[38;2;230;73;128m' ;;
  violet.6) printf '\033[38;2;132;94;247m' ;;
  reset) printf '\033[0m' ;;
  esac
}

# ── Directory ────────────────────────────────────────────────────────────
dir=""
if [[ -n "$cwd" ]]; then
  dir="${cwd/#$HOME/⌂}"
  IFS='/' read -ra parts <<<"$dir"
  count="${#parts[@]}"
  if ((count > 3)); then
    dir="⑂ ${parts[$((count - 3))]}/${parts[$((count - 2))]}/${parts[$((count - 1))]}"
  fi
fi

# ── Git ─────────────────────────────────────────────────────────────────
git_info=""
if git_root=$(git -C "${cwd:-.}" rev-parse --show-toplevel 2>/dev/null); then
  branch=$(git -C "$git_root" symbolic-ref --short HEAD 2>/dev/null ||
    git -C "$git_root" rev-parse --short HEAD 2>/dev/null)

  staged=$(git -C "$git_root" diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
  modified=$(git -C "$git_root" diff --name-only 2>/dev/null | wc -l | tr -d ' ')
  untracked=$(git -C "$git_root" ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')
  renamed=$(git -C "$git_root" diff --cached --name-only --diff-filter=R 2>/dev/null | wc -l | tr -d ' ')
  deleted=$(git -C "$git_root" diff --cached --name-only --diff-filter=D 2>/dev/null | wc -l | tr -d ' ')
  conflicted=$(git -C "$git_root" ls-files -u 2>/dev/null | awk '{print $4}' | sort -u | grep -c .)
  stashed=$(git -C "$git_root" stash list 2>/dev/null | wc -l | tr -d ' ')

  # Ahead/behind only makes sense when an upstream is set;
  # in a freshly initialized branch `rev-parse @{u}` errors
  # and we want zeros, not noise on the prompt. The triple-
  # dot in `HEAD...@{u}` is the symmetric-difference syntax
  # `--left-right --count` expects; left=ahead, right=behind.
  ahead=0
  behind=0
  if git -C "$git_root" rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
    if read -r ahead behind < <(git -C "$git_root" rev-list --left-right --count 'HEAD...@{u}' 2>/dev/null); then
      :
    fi
  fi
  ahead=${ahead:-0}
  behind=${behind:-0}

  # Sum line metrics across both unstaged and staged diffs.
  # `--shortstat` formats as " N files changed, M insertions(+), K deletions(-)"
  # with insertions or deletions absent when zero, so we
  # extract each independently and tolerate either being
  # missing. Empty scope = unstaged; --cached = staged.
  added_lines=0
  removed_lines=0
  for scope in "" "--cached"; do
    ss=$(git -C "$git_root" diff $scope --shortstat 2>/dev/null)
    [[ -z "$ss" ]] && continue
    i=$(echo "$ss" | grep -oE '[0-9]+ insertion' | grep -oE '^[0-9]+')
    d=$(echo "$ss" | grep -oE '[0-9]+ deletion' | grep -oE '^[0-9]+')
    added_lines=$((added_lines + ${i:-0}))
    removed_lines=$((removed_lines + ${d:-0}))
  done

  ahead_behind=""
  ((ahead > 0)) && ahead_behind+="$(oc green.6)▴${ahead}$(oc reset) "
  ((behind > 0)) && ahead_behind+="$(oc red.6)▿${behind}$(oc reset) "

  indicators=""
  ((staged > 0)) && indicators+="$(oc teal.5)●${staged}$(oc reset) "
  ((modified > 0)) && indicators+="$(oc yellow.6)◐${modified}$(oc reset) "
  ((untracked > 0)) && indicators+="$(oc gray.5)○${untracked}$(oc reset) "
  ((renamed > 0)) && indicators+="$(oc blue.4)◎${renamed}$(oc reset) "
  ((deleted > 0)) && indicators+="$(oc red.6)⊘${deleted}$(oc reset) "
  ((conflicted > 0)) && indicators+="$(oc pink.6)⊗${conflicted}$(oc reset) "
  ((stashed > 0)) && indicators+="$(oc violet.6)◉${stashed}$(oc reset) "

  # ✓ shows only when the working tree is clean AND there
  # is some upstream divergence to bracket alongside it —
  # a fully clean, fully synced repo drops the brackets
  # entirely so the prompt collapses to just the branch.
  # This matches starship's `up_to_date`, which displays
  # only when no other status indicator is active.
  #
  # Bracket padding is symmetric: a leading space inside `⎡`
  # mirrors the trailing space each indicator carries after
  # its count, so the layout reads `⎡ ●1 ◐2 ⎤` with one
  # space of inner padding on both sides.
  if [[ -z "$indicators" ]]; then
    if [[ -z "$ahead_behind" ]]; then
      brackets=""
    else
      brackets="$(oc gray.6)⎡$(oc reset) $(oc green.6)✓$(oc reset) $(oc gray.6)⎤$(oc reset)"
    fi
  else
    brackets="$(oc gray.6)⎡$(oc reset) ${indicators}$(oc gray.6)⎤$(oc reset)"
  fi

  ahead_behind="${ahead_behind% }"

  metrics=""
  ((added_lines > 0)) && metrics+=" $(oc green.6)▴+${added_lines}$(oc reset)"
  ((removed_lines > 0)) && metrics+=" $(oc red.6)▿−${removed_lines}$(oc reset)"

  git_info=" $(oc blue.5)▸${branch}$(oc reset)"
  [[ -n "$ahead_behind" ]] && git_info+=" ${ahead_behind}"
  [[ -n "$brackets" ]] && git_info+=" ${brackets}"
  git_info+="${metrics}"
fi

# ── PR segment ──────────────────────────────────────────────────────────
pr_info=""
if [[ -n "${git_root:-}" ]]; then
  pr_state=""
  pr_url=""
  IFS=$'\t' read -r pr_state pr_url < <(cd "$git_root" &&
    "$HOME/.dotty/plugins/git/pr-link.sh" --state 2>/dev/null) || true
  if [[ -n "$pr_url" ]]; then
    case "$pr_state" in
    none) icon_color="$(oc gray.5)" ;;
    *) icon_color="$(oc blue.6)" ;; # open or unknown
    esac
    osc8_open=$'\e]8;;'
    osc8_close=$'\e\\'
    pr_info=" ${icon_color}${osc8_open}${pr_url}${osc8_close}⊕${osc8_open}${osc8_close}$(oc reset)"
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
printf '%s%s%s%s%s' \
  "$(oc blue.6)${dir}$(oc reset)" \
  "$git_info" \
  "$pr_info" \
  "$ctx_info" \
  "$model_info"
