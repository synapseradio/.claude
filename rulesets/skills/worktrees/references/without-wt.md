# Without wt

Read this in full when `scripts/which-tool.sh` prints `git`, meaning `wt` is not on PATH. The wt steps in `SKILL.md` need worktrunk; each row below replaces one of them with plain git. Every other step in `SKILL.md`, the fetch and divergence check in Land step 2 and the stopped-merge block included, runs as written, with `git -C <worktree> rebase $trunk` as the rebase.

`$base` is the branch Create's `--base` names, `$trunk` unless the lane is stacked.

| Step | Command | Replaces |
| --- | --- | --- |
| create | `git -C <primary checkout> worktree add -b $branch <worktree> $base`, with `<worktree>` a new directory beside the primary checkout, named after the branch | Create's `wt --yes switch --create` |
| provision | the lane's own provisioning commands, run in `<worktree>` before its first commit, since no hook runs at creation | Create's pre-start hook |
| squash | `git -C <worktree> reset --soft "$(git -C <worktree> merge-base $trunk HEAD)"` -> `git -C <worktree> commit -m '<message>'`, so the repository's commit hooks run | Land step 1 and the squash under Assigned worktree |
| land | `git -C <worktree> rebase $trunk` -> with the primary checkout on the trunk, `git -C <primary checkout> merge --ff-only $branch`; with it on another branch, `git -C <primary checkout> fetch . $branch:$trunk` | Land step 3 |
| remove | `git -C <primary checkout> worktree remove <worktree>` -> `git -C <primary checkout> branch -d $branch` | Land step 3's removal and the `wt prune` of Land step 5 |

With the primary checkout on a branch other than the trunk, `git branch -d` refuses a branch the trunk already holds. Confirm the landing with `git -C <primary checkout> merge-base --is-ancestor $branch $trunk`, which exits 0, then delete the branch with `git -C <primary checkout> branch -D $branch`.

## Another tool

another tool
  | the session's rules or the repository's docs name a worktree tool other than wt, and it is on PATH = read its help for the five steps in the table -> fill each row with its command -> for a step it lacks, use the git command in the table -> run no command of its that you have not seen in its own help output
  | otherwise = use the git commands in the table
