## git-commit

For every commit, commit message, pull request, and move between branches, optimize for a commit whose message says what the diff does and why, and whose hooks ran.

### The message

The repo states a format through a commitlint, commitizen, or gitlint config, an enabled commit-msg hook, a documented convention, or a consistent branch history ? follow it exactly : open on one line of the form `$type($scope): $description`, with the type one of feat, fix, docs, style, refactor, perf, test, build, ci, chore, or revert, chosen by what the diff does; the scope optional, reused where the branch or repo already uses one; the description imperative, lowercase at its start, without a trailing period, writing identifiers in their real casing; and a body after one blank line saying why the change happened, for the decisions that were yours to make.
Keep URLs and co-author trailers out of every message.

### The commit

Commit once the work unit's checks pass, with no approval asked -> report what landed.
A skill's step says review, then commit ? commit, then report the diff.
Keep every push and every post to an external platform on its own approval.
During a multi-step build, commit at each green checkpoint, each delegate committing only its own paths with `git commit -- <paths>`, and end every slice with `git status --short` empty.
Treat a pending review as no ground for holding work uncommitted. Carry the checkpoint instruction into every prompt for a delegate that edits files.
Stage generated copies in the same commit as the source they derive from.
Verify the staged set with `git diff --cached --name-only`, with a planning artifact in it only on the user's ask -> compose the message -> commit.
A hook rejects ? make the rejection the next task, fix the cause, and commit anew.
Keep `--no-verify` out of every command.

### Branches

The repository is public and others push to or review the branch ? open the PR from your fork.
Split a change into one pull request per team that owns code it touches, and treat a pull request's small size as no ground for folding it into another. Give every line of work its own worktree.
Before showing a pull request's title and body, a draft offered as an option or one a delegate wrote included, run `thinkies:communicate` over them, checking that they read concise, relatable, written for their reader and purpose, and at the right altitude.
A stack is reordered, a branch moving below its former base ? run `gh pr edit <n> --base <new parent>` for every pull request whose parent changes, the new parent already on the remote -> push.
A migration, import, or sweep meets a branch ? date it by its last commit -> the branch is more than three days old and other than the trunk ? take nothing from it.
Rebasing ? autosquash by default, resolving conflicts on their merits.

### Conflicts

A rebase stops on conflicts and its todo holds more picks than `git rev-list --count <onto>..ORIG_HEAD` ? test each pick with `git merge-base --is-ancestor <sha> <onto>`.
Most picks are ancestors of `<onto>` ? `git rebase --abort` -> replay only the branch's own commits with `git rebase --onto <onto> <parent of the branch's first commit>` -> confirm `git diff <old parent> <old tip>` matches `git diff <onto> HEAD`.
A lockfile conflicts ? check out one side whole, `git checkout --ours <lockfile>` or `--theirs` -> run the package manager's install to regenerate it -> confirm the tree is clean -> continue.
Keep every hand edit out of a lockfile.
A rebase touched a lockfile ? compare it with the tested tree, `git diff ORIG_HEAD HEAD -- <lockfile>`.
