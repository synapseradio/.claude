<!-- rule: git-commit -->
## git-commit

For every commit and pull request and move between branches, optimize for a commit whose message says what the diff does and why and whose hooks ran.

### The message

format
  | the repo states one, a consistent branch history included = follow it exactly
  | otherwise = open on one line of the form `$type($scope): $description`, then a body after one blank line saying why the change happened for the decisions that were yours to make

- `$type`: one of `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`, chosen by what the diff does
- `$scope`: optional, reused where the branch or repo already uses one
- `$description`: imperative and lowercase at its start, without a trailing period, with identifiers in their real casing

Keep URLs and co-author trailers out of every message.

### The commit

Commit once the work unit's checks pass, with no approval asked -> report what landed.
Keep every push and every post to an external platform on its own approval.
During a multi-step build, commit at each green checkpoint and end every slice with `git status --short` empty.
Each delegate commits only its own paths with `git commit -- <paths>`.
Treat a pending review as no ground for holding work uncommitted.
Carry the checkpoint instruction into every prompt for a delegate that edits files.
Stage generated copies in the same commit as the source they derive from.
Verify the staged set with `git diff --cached --name-only`, with a planning artifact in it only on the user's ask -> compose the message -> commit.
Keep `--no-verify` out of every command.

skill step
  | it says review then commit = commit -> report the diff

worktree
  | you work in one made for the work = commit with `git -C <worktree> commit -- <paths>` naming the worktree by its absolute path, and leave `git -C <worktree> status --short` empty after each commit

hook
  | it rejects = make the rejection the next task -> fix the cause -> commit anew

### Branches

Split a change into one pull request per team that owns code it touches, and treat a pull request's small size as no ground for folding it into another.
Before showing a pull request's title and body, run `thinkies:communicate` over them, a draft offered as an option or one a delegate wrote included.
Check that they read concise and relatable, written for their reader and purpose, and at the right altitude.
Rebase with autosquash by default, resolving conflicts on their merits.

fork
  | the repository is public and others push to or review the branch = open the PR from your fork

teams
  | their parts break apart = one pull request with one commit per owning team holding all its files, shared part first, each commit's scope naming the team and its trailer the team's handle

stack
  | it is reordered, a branch moving below its former base = run `gh pr edit <n> --base <new parent>` for every pull request whose parent changes, the new parent already on the remote -> push

branch
  | a migration, import, or sweep meets one other than the trunk whose last commit is more than three days old = take nothing from it

### Conflicts

Keep every hand edit out of a lockfile.

rebase
  | it stops on conflicts and its todo holds more picks than `git rev-list --count <onto>..ORIG_HEAD` = test each pick with `git merge-base --is-ancestor <sha> <onto>` -> where most are ancestors of `<onto>` run `git rebase --abort` -> replay only the branch's own commits with `git rebase --onto <onto> <parent of the branch's first commit>` -> confirm `git diff <old parent> <old tip>` matches `git diff <onto> HEAD`

lockfile
  | it conflicts = check out one side whole with `git checkout --ours <lockfile>` or `--theirs` -> run the package manager's install to regenerate it -> confirm the tree is clean -> continue
  | a rebase touched it = compare it with the tested tree, `git diff ORIG_HEAD HEAD -- <lockfile>`
