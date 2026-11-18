---
name: worktrees
description: >-
  Mandatory procedure for every piece of work that changes files in a git repository, at any size. Load it before the first edit, write, or commit in a git repository, a one-file fix or a config change included: before you fix a bug, implement a feature, refactor, rename, add a test, update docs or config, or carry out a plan there; before you split work into parallel lanes or hand part of it to another agent; when a new request lands while file-changing work runs; when your prompt assigns you a worktree or a branch; and before you create, list, commit in, squash, merge, land, or remove a git worktree or its branch. It holds how to split the work into lanes that run at once without racing, how to give each lane a worktree created with the `wt` CLI (worktrunk) and provision it, what a lane agent's prompt names, how a lane commits, squashes to one commit, and lands on the trunk, what to do with a stopped merge, a hook awaiting approval, or a superseded worktree, the finish run after every lane lands, and the plain git commands that stand in for each wt step on a machine where `wt` is not on PATH. Use it whenever you are about to change, add, delete, or commit files under version control, and on requests such as "fix this", "implement", "change these files", "edit", "refactor", "add a test", "update the config", "commit this", "merge the branch", "land it", "clean up the worktrees", even where the request never says "worktree".
---

# Worktrees

For every piece of work that changes files in a git repository and every request that lands while it runs and every git worktree you touch, optimize for work split into lanes that run at once without racing, each landing on the trunk as one commit through a worktree the wt CLI created and merged and removed with its hooks and config run.

## Notation

- `A -> B`: step A then step B of one instruction
- guard block: a name line then `| condition = act` lines, the first that fits taken and `otherwise` last
- `<name>` and `$name`: a value you fill in before running the command, such as `<worktree>` or `$trunk`

## Terms

- wt: worktrunk, documented at <https://worktrunk.dev>, with `wt config show` printing its config and hooks and each file's location
- lane: a unit of the work whose changed files no other running lane changes
- trunk: the branch the work builds on, where every lane lands
- primary checkout: the repository's main worktree, the directory holding the `.git` that `git rev-parse --path-format=absolute --git-common-dir` prints
- provision: install what the lane's checks need to run in a fresh worktree, such as its dependencies
- lane agent: an agent given one lane whole
- `<worktree>`: the absolute path of a lane's worktree, as wt printed it
- `$trunk` and `$branch`: the trunk's name and the lane's branch name

## Which sections bind you

role
  | your prompt assigns you a worktree = follow Every worktree, Commit, and Assigned worktree, with the steps of Land that Assigned worktree sends you to -> leave Split, Create, Delegate, and Finish to your caller
  | a caller spawned you and its prompt names where to make the change, a checkout or a branch, without assigning a worktree = make the change there -> follow Every worktree, leaving every other section to your caller
  | otherwise = follow every section but Assigned worktree

Without wt binds every role, and only where `wt` is not on PATH.

## Every worktree

List with `wt list`.
Remove a worktree only through `wt prune` or `wt merge`, or through `wt remove` in the superseded case below, or through the remove row of `references/without-wt.md` where `wt` is not on PATH.
Keep `git worktree prune` and `rm` off every worktree path, and keep `git worktree remove` off every worktree path except in the remove row of `references/without-wt.md`, where `wt` is not on PATH.
Answer a question about wt from its config file and docs.
Address files in a worktree by the absolute path wt prints.
Leave every worktree and branch the current work neither created nor names untouched and unmentioned.

wt command
  | it stops because a project hook awaits approval = stop the lane -> ask the user to review the hooks with `wt config approvals add`

superseded worktree
  | its work landed by another route or was replaced, so `wt merge` would land superseded code = back up its commits with `git -C <primary checkout> bundle create <file> <branch>`, the file in the scratchpad directory -> confirm `git -C <primary checkout> bundle verify <file>` passes -> save its uncommitted changes, untracked files included, as a patch or tarball in the same directory -> remove it with `wt -C <primary checkout> remove <branch> -D`, adding `-f` where it holds uncommitted changes

## Split

Before work starts, and again whenever a new request lands mid-work, split the work into lanes.

work on a running lane's file
  | you work that lane yourself or its agent has yet to start = add it to that lane
  | otherwise = hold it until that lane lands -> give it a lane of its own

## Create

Give each lane its own worktree, created in the primary checkout with `wt --yes switch --create $branch --base $trunk --no-cd`.
Where a script reads the new worktree's path, add `--format json` and take the path from the `path` field of the JSON wt prints.

stacked lane
  | a lane needs another lane's code before that lane lands = create it with `--base` naming that lane's branch -> land it after that lane lands

early lane
  | a lane waits on another lane's landing and holds work that rests on none of that lane's code, such as tests written against a contract stated in full = create its worktree at once -> do that work -> once the awaited lane lands, run `wt -C <worktree> step rebase $trunk` before the rest

provision
  | the repository's `.config/wt.toml` holds a pre-start hook = let it provision the worktree
  | otherwise = have the lane provision its worktree before its first commit -> propose once in your next message a pre-start hook for `.config/wt.toml` that provisions every new worktree

## Delegate

lanes
  | no spawning tool is in hand, or your routing keeps implementation work with you = work every lane yourself, each in its own worktree and landed before the next starts
  | otherwise = keep the lane that needs the conversation's context most -> give every other lane whole to an agent of its own -> work your lane while the agents run -> track every lane as a task

Spawn each lane agent in the background without the Agent tool's worktree isolation.
A worktree the spawning tool makes on its own may branch from the default branch whatever base the lane needs, take a name you cannot choose, skip the repository's provisioning hook, and vanish when its agent changes nothing, so keep it for an agent that only reads or runs a throwaway trial.
Give a lane away whatever its size, in place of acting on it directly or splitting its steps among other agents.
Name in each lane agent's prompt:

- the worktree's absolute path and its branch
- the files it may change
- the checks to run before each commit: the tests covering the lane's own files, each run in the foreground, with every full suite left to Finish
- the acts it leaves undone: a push, a check or formatter run over files outside its own, an edit to a file outside its own such as a README or a contract module another lane owns, and an end to its turn while a command it started still runs in the background
- that every change a formatter or linter makes, in a file outside its own too, stays as the tool left it and goes into its commit, unreverted and unadjusted by hand
- how to provision the worktree where no pre-start hook does
- that it lands its lane as the `worktrees` skill directs, loading the skill through the Skill tool, with its final report sent only once step 5 under Land holds

lane agent
  | it holds no Bash tool = leave committing and landing out of its prompt -> commit its lane yourself once it reports

## Commit

Commit with `git -C <worktree> add <paths>` naming the lane's own paths and every file a formatter or linter changed, in a file outside the lane's files too -> confirm `git -C <worktree> diff --cached --name-only` lists only them -> `git -C <worktree> commit -m '<message>'`, with no pathspec, leaving every formatter or linter change as the tool left it, unreverted and unadjusted by hand.
After each commit, confirm `git -C <worktree> status --short` prints nothing.

## Land

Keep `skill:simplify` out of every lane's landing and every lane agent's prompt, since Finish holds its one run.
The lane's own agent lands the lane once its checks pass, and you land your own lane and every lane whose agent holds no Bash tool, in these steps:

1. Run `wt -C <worktree> step squash $trunk` -> confirm `git -C <worktree> log --oneline $trunk..HEAD` lists one commit.
2. Run `git -C <worktree> fetch` -> run `git -C <worktree> rev-list --left-right --count "$trunk...$trunk@{upstream}"` -> stop and report both counts where both are above zero, the trunk and its upstream having diverged. Skip this step where the trunk has no upstream.
3. Run `wt -C <worktree> merge $trunk`, which rebases the branch onto the trunk and fast-forwards the trunk, then removes the worktree and deletes its branch.
4. Handle a stopped merge by the block below.
5. Confirm `git -C <primary checkout> log --oneline $trunk` lists the lane as one commit -> report that commit's SHA and subject -> run `wt -C <primary checkout> prune` -> confirm `git -C <primary checkout> worktree list` no longer lists `<worktree>`.

Leave the squashed commit as the squash wrote it, with `git commit --amend` kept out after every squash.

stopped merge
  | on a rebase conflict = resolve it in the worktree on its merits, keeping what both lanes changed -> continue the rebase -> run the lane's checks again -> run the merge again, counting the run among the two
  | the trunk moved or the fast-forward was refused = run it again, at most twice -> where it still stops report the lane with its branch and the last error

## Races

Before two lanes run at once, read every hook they run, in wt's config and in the repository's commit hooks, for a step that shares a cache, a lock, or an output path with another step.

hook step
  | one you write or change shares state on disk with a step that may run at the same moment, another lane's included = run the two in sequence or as a pipeline, or give each its own state
  | one you found shares state on disk with a step that may run at the same moment = report it before the lanes start, with both repairs: the two run in sequence, or each given its own state

## Finish

After every lane lands, run in the primary checkout the work that needs every lane landed such as a cleanup across lanes -> run `skill:simplify` yourself once over the source code the lanes landed -> commit each change it calls for on the trunk -> run each test suite once on the trunk -> report each lane's landed SHA and subject.
The landed source is `git -C <primary checkout> diff <start>..$trunk`, with `<start>` the trunk commit the earliest lane was created from.
Hold every push until the `skill:simplify` run has committed its changes or been skipped.

landed changes
  | they hold no source code, only prose such as docs or instruction text = skip the `skill:simplify` run

leftover worktree
  | one the current work created outlives its branch's merge and `git -C <path> status --short` shows uncommitted changes = report them and keep the worktree
  | one the current work created outlives its branch's merge = run `wt -C <primary checkout> prune`

## Assigned worktree

For every worktree your prompt assigns you, optimize for a branch that reaches its merge as one commit, with every other worktree and branch as you found it.

Take the primary checkout from your prompt in every command here and under Every worktree.
Leave every worktree and branch your prompt neither assigns nor names untouched and unmentioned.
Keep `skill:simplify` out of the assigned worktree's work, since the session's main agent runs it once after every planned worktree merges.
Run the tests covering the files your work changes, in the foreground, and leave every full test suite to the session's main agent, which runs each once after every planned worktree merges.
Send your final report only after the merge, or after the squash where your caller merges.
Commit as Commit directs, with your assigned files as the lane's own paths.

Before you merge the assigned worktree's branch, or ask your caller to merge it, squash the branch's commits into one.
Squash with `wt -C <worktree> step squash <target>`, naming as `<target>` the branch the merge goes into -> confirm `git -C <worktree> log --oneline <target>..HEAD` lists one commit.
Leave the squashed commit as the squash wrote it, with `git commit --amend` kept out after every squash.
Before any merge, run `git -C <worktree> fetch` -> run `git -C <worktree> rev-list --left-right --count "<target>...<target>@{upstream}"`.

counts
  | both above zero, `<target>` and its upstream having diverged = stop and report both counts
  | otherwise = merge, by the steps your prompt writes out, or by steps 3 to 5 under Land with `<target>` as `$trunk` where your prompt writes none

After the merge, run `wt -C <primary checkout> prune`, with the primary checkout your prompt names.
Remove a worktree only through `wt prune` or `wt merge`, or through `wt remove` in the superseded case under Every worktree, or through the remove row of `references/without-wt.md` where `wt` is not on PATH, with the primary checkout your prompt names.

## Without wt

This section binds every role, and only where `wt` is not on PATH.
Run `bash <skill directory>/scripts/which-tool.sh` once, with `<skill directory>` the directory holding this file (the base directory the harness prints when it loads the skill, or `~/.claude/skills/worktrees`).

tool
  | it prints `wt` = use the wt steps above, and use no command from `references/without-wt.md` and no `git worktree remove`, whatever stops a wt command, a hook awaiting approval included, since only wt runs the repository's worktree hooks and config
  | it prints `git` = read `<skill directory>/references/without-wt.md` in full -> follow it in place of the wt steps it names

## References

reference
  | a command in your plan has a wt equivalent you do not know, or you need a `wt step`, `wt prune`, `wt organize`, or alias flag = read `<skill directory>/references/wt-commands.md` in full
  | branches build on each other, a stack needs creating, rebasing, restacking, retargeting, or submitting, or a rebase stopped = read `<skill directory>/references/stacks.md` in full
  | you spawn or brief agents that change files, own a lane agent's landing, or clean up or delete worktrees and branches = read `<skill directory>/references/lane-practice.md` in full
  | you commit, squash, or set work aside inside a worktree = read `<skill directory>/references/git-commit-in-worktree.md` in full
