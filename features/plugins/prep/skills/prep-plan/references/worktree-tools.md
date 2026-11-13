# Worktree tools

Read this when the plan has lanes, to fill the command slots of `assets/lane-block.md` for the tool this machine has. Every lane does the same five things whatever the tool: create a worktree on a new branch, provision it, squash its commits into one, land that commit on the trunk, and remove the worktree and branch. The plan states each as an outcome and gives the detected tool's command for it.

## Which tool

Take the first that applies:

1. a tool the session's rules or the repository's docs name for worktrees
2. the first `worktrees` finding of `scripts/detect-tools.py`
3. git itself

Where `python3` is missing, run these probes by hand:

```sh
git rev-parse --show-toplevel                        # the repository root
git worktree list --porcelain                        # the first entry is the primary checkout
git symbolic-ref --short refs/remotes/origin/HEAD    # the trunk follows "origin/"
command -v wt && wt --help | grep -i worktrunk       # worktrunk, where both succeed
```

A program named `wt` counts as worktrunk only where its help says so; other programs share the name.

## git

Needs nothing but git. No hook runs when a worktree is created, so the lane's provisioning line carries the commands.

| step | command |
| --- | --- |
| create | `git -C [primary checkout] worktree add -b [branch] [path] [base]`, with `[path]` a directory beside the primary checkout that the plan names |
| provision | the commands the lane's provisioning line lists, run in `<worktree>` |
| squash | `git -C <worktree> reset --soft "$(git -C <worktree> merge-base [trunk] HEAD)"`, then one commit through the hooks |
| land | `git -C <worktree> rebase [trunk]`, then, with the primary checkout on the trunk, `git -C [primary checkout] merge --ff-only [branch]`; with it on another branch, `git -C [primary checkout] fetch . [branch]:[trunk]` |
| remove | `git -C [primary checkout] worktree remove <worktree>`, then `git -C [primary checkout] branch -d [branch]` |

With the primary checkout on a branch other than the trunk, `git branch -d` refuses a branch the trunk already holds. Confirm it landed with `git -C [primary checkout] merge-base --is-ancestor [branch] [trunk]`, which exits 0, then delete it with `git -C [primary checkout] branch -D [branch]`.

## worktrunk

The `wt` command, <https://worktrunk.dev>. Its `-C <path>` names the worktree a command acts on, as git's does.

| step | command |
| --- | --- |
| create | `wt -C [primary checkout] switch --create [branch] --base [base] --no-cd --format json`; the `path` field of the JSON it prints is `<worktree>` |
| provision | a `pre-start` hook in the repository's `.config/wt.toml` runs as the worktree is created and finishes before the command returns; where there is none, the lane's provisioning commands |
| squash | `wt -C <worktree> step squash [trunk]`; it writes a commit message of its own, so reword it with `git -C <worktree> commit --amend -m '<message>'` |
| land | `wt -C <worktree> merge [trunk]`, which rebases onto the trunk, fast-forwards the trunk, and removes the worktree and the branch |
| remove | done by `merge`; `wt -C [primary checkout] step prune --dry-run` lists anything left |

These commands run the repository's worktrunk hooks. Where a hook command has yet to be approved on this machine, worktrunk asks first, and in a shell with nobody to answer the command stops with `Cannot prompt for approval in non-interactive environment`. `--yes` skips the question. Add it to the plan's commands only where the plan's approver accepts running those hooks unasked, and say so in the plan's Decisions; otherwise give the plan a first step in which a person approves them once.

## Another tool

Read its help for the five steps above and fill each slot with its command. For a step it lacks, use git's command from the first table. Write a must verify line for each command you have yet to see in the tool's own help output.

## A spawning tool's own worktrees

Some agent harnesses can start an agent inside a temporary worktree of its own. Read the spawning tool's description before relying on it for a lane: such a worktree may branch from the default branch whatever base the lane needs, take a name the plan cannot choose, skip the repository's provisioning hook, and vanish when the agent changes nothing. It suits a researcher or a throwaway trial. A lane that needs a named branch, a chosen base, or provisioning gets its worktree from the create step above.

## After every landing

Whatever the tool, the lane block confirms the same end state with git:

- `git -C [primary checkout] log --oneline -1 [trunk]` shows the lane's one commit
- `git -C [primary checkout] worktree list` no longer lists `<worktree>`
