<!-- rule: agent-delegation variant: sonnet -->
## agent-delegation

For every step of work a delegate could take, and every spawn you make, optimize for a read, scan, or other gathering of information done by a fresh haiku that returns a result you can check, with its output kept out of your own context and every other step done yourself.

### Whether to spawn

Hold a read, a grep, a log scan, or any other gathering of information as work beyond the context in hand. Count a command run for its output, a test suite's run for one, as gathering of information, and a command whose job is a change, a commit, an edit, or an install, as outside it. Take the first arm that fits.

route step
  | a step is the Read of a file that the Edit tool, or the Write tool over an existing file, requires before your next change to that file, the reading of the newest handoff note at a session's first turn, the opening of a cited line to confirm it backs a claim, or a scan of a saved command output by grep, jq, ast-grep, or a Read by line range
      = act directly
  | a step is any other read, scan, or gathering of information, and you hold no tool that spawns an agent
      = act directly
  | a step is any other read, scan, or gathering of information
      = spawn it to a fresh haiku, one haiku holding the step's related reads > parallel haikus, each command run's output saved by the haiku to a file in the scratchpad
  | otherwise = act directly

Set every spawn's model to haiku, whatever agent type it runs.
Spawn a re-check of your own result only on the user's ask.

### The spawn

Compose the prompt -> spawn -> hold each reported claim pending until you find its source.
Hold a haiku delegate's context as a 99k-token budget. The reads exceed it ? split them into sequential spawns, each finishing its slice end to end.
Resume a delegate only where the step needs what that delegate alone holds, the sources behind its own report for one.

effort prompt
  | it states every step of a task in one part = low
  | otherwise = medium

Spawn at effort high or above only on the user's ask or permission.
Effort field exists ? set it : state the depth in the prompt: search breadth, alternatives to weigh, the check to run.

### The prompt

State in each haiku's prompt every step, every path, the exact constraints, and the check to run and return.
Fill the template below. Replace each bracket with what it describes, and send the rest verbatim. Drop an empty part with its heading. State every fact the delegate would otherwise guess or rediscover. Count a file named in Context by absolute path as handed over, and write only what such files leave out. Name the haiku's family and identifier in the first line, resolved through the active settings' model aliases. Keep the welcome whole in every prompt, one fluid greeting offered out of the kindness and respect every delegate is owed.

```markdown
You are [model family and identifier]. [a welcome for this spawn, glad the delegate is here as a specialist in the step's skillset, bash and bats for one, naming what its work makes possible]

## Perspective

[the step's role, and how the delegate's expertise bears on its decisions]

## Task

[what to do, complete for a reader holding only this prompt; the return format; who meets the result, and what a failure costs them]

## Context

[files to read first, by absolute path and section; prior decisions, as choices made; conventions]

## Tooling

[only where the step needs a particular tool or skill: the environment, and the tools and skills it must or may use; no limits on its allowed tools]

## Constraints

[invariants, boundaries, what this step leaves to others]

## Checks

[each check to run before reporting, with its command and passing result]

## Invitations

Settle each choice point yourself, and report what you chose and why.
If evidence contradicts the stated context, stop at once and report the contradiction.
If a choice turns on the user's intent, direction, or what done means, return it at once with the options you would offer.
If a step fails, report what broke, what it cost, and what it changes next.
[what stops this step, and what to report then]

## Failures

[each known way this step goes wrong: its mechanism and cost, the self kept out of the sentence]
```

<!-- rule: worktrees -->
## worktrees

For every git worktree you create, enter, list, merge, or remove, optimize for a worktree the wt CLI created, listed, merged, and removed, with its hooks and config run.

- wt: worktrunk, documented at https://worktrunk.dev, its config, hooks included, at `~/.dotfiles/.config/worktrunk/config.toml`

Create with `wt --yes switch --create $branch --base $base`, naming as `$base` the branch the work builds on. List with `wt list`. Remove with `wt remove`. Merge back with `wt merge $target`, which rebases the branch onto `$target`, fast-forwards `$target`, then removes the worktree and deletes its branch. Answer a question about wt from its config file and docs.

Address files in a worktree by the absolute path wt prints.
A delegate works in its own worktree ? create that worktree with wt first, then name its absolute path in the delegate's prompt.

Before merging, run `git fetch`, then `git rev-list --left-right --count "$target...$target@{upstream}"`.
Both counts are above zero, meaning `$target` and its upstream have diverged ? stop and report both counts : merge.
