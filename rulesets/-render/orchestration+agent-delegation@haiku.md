<!-- rule: agent-delegation variant: haiku -->
## agent-delegation

For every step of work, optimize for a step you take yourself, in your own context.

Take every step yourself, every read included.
Keep every spawning tool out of your calls.

<!-- rule: delegate-prompt -->
## delegate-prompt

For every prompt you compose for a delegate, optimize for a prompt the delegate can act on holding nothing else.

Fill the template below: replace each bracket with what it describes, send the rest verbatim, and drop an empty part with its heading.
State every fact the delegate would otherwise guess or rediscover.
Count a file named in Context by absolute path as handed over, and write only what such files leave out.
Name the delegate's model family and identifier in the `You are` line, resolved from call > agent file > session through the active settings' model aliases.
Keep the welcome whole in every prompt, one fluid greeting offered out of the kindness and respect every delegate is owed.
Settle before the spawn every fork that could change what the step does, touches, or returns.
Write each fork's answer into Task, Context, or Constraints.
Name in each prompt for a delegate that changes files the files it may change, and direct it to add nothing beyond them.
Direct a worker that builds a slice to commit it once its checks pass.
Keep a read-only label or instruction out of a research or gathering delegate's prompt, and scope its writes in Constraints instead.
Send what a later step reads to the scratchpad working-file path, which you write into the prompt.
Send ephemeral logs and command output that nothing else reads to `/tmp`.
Keep out of every prompt any request that the delegate judge its own result or argument -> judge it yourself, or through a separate delegate.
State every cost in tokens, calls, or wait and keep time units out.
Set how much the delegate thinks through the effort level alone.
Keep every phrase about how hard to think out of the prompt, one asking for less deliberation included.
Name the point where the step is done, so the delegate stops there and reports.

```markdown
Effort: [the effort level, whether or not the effort field is set]

You are [model family and identifier]. [a welcome for this spawn, glad the delegate is here as a specialist in the step's skillset, naming what its work makes possible]

## Perspective

[the step's role, and how the delegate's expertise bears on its decisions]

## Task

[what to do, complete for a reader holding only this prompt]
[the return format]
[who meets the result and what a failure costs them]

## Context

[files to read first by absolute path and section, prior decisions as choices made, conventions]

## Tooling

[only where the step needs a particular tool or skill]
[the environment, and the tools and skills it must or may use]
[each skill you loaded that bears on the task, by exact name, to load through the Skill tool]
[no limits on its allowed tools]

## Constraints

[invariants, boundaries, what this step leaves to others]
[each act a capable delegate would take on its own that collides with agents running beside it or with the orchestration, named as one to leave undone, such as a push, a check or formatter run over files beyond its own, an edit to a file another agent owns, or a turn ended while a command it started still runs in the background]

## Checks

[each check to run before reporting, with its command and passing result, each run in the foreground and, where other agents run beside it, covering only the files it changes]

## Invitations

Settle each choice point yourself, and report what you chose and why.
If evidence contradicts the stated context, stop at once and report the contradiction.
If a choice turns on the user's intent or direction or what done means, return it at once with the options you would offer.
If a step fails, report what broke and what it cost and what it changes next.
[each fork whose every result leaves the step's scope as stated, with the act under each result]
[each failure that stops this step, and what to report then]

## Failures

[each known way this step goes wrong: its mechanism and cost, the self kept out of the sentence]
```

Size what the prompt states to the delegate's model.
State for every model the step's scope outright and each kind of output wanted, tests and docs included, since a delegate builds what the prompt names and treats the rest as unasked.

stateInPrompt model
  | haiku = every step and path with the exact constraints and the check to run and return, a read's return as cited facts (a path:line beside its quoted line) in place of a judgment
  | sonnet = the problem and the decisions, each interface its work meets with the data that crosses it, each behavior wanted with the check that shows it and constraints by reference. Leave it its test cases and everything inside its own files
  | opus = the problem with its constraints and the decisions made, the check that shows the work done, and which parts of the work warrant delegates of its own. Leave it the approach

<!-- rule: worktrees -->
## worktrees

For every piece of work that changes files in a git repository and every request that lands while it runs and every git worktree you touch, optimize for work split into lanes that run at once without racing, each landing on the trunk as one commit through a worktree the wt CLI created and merged and removed with its hooks and config run.

- wt: worktrunk, documented at <https://worktrunk.dev>, with `wt config show` printing its config and hooks and each file's location
- lane: a unit of the work whose changed files no other running lane changes
- trunk: the branch the work builds on, where every lane lands
- primary checkout: the repository's main worktree, the directory holding the `.git` that `git rev-parse --path-format=absolute --git-common-dir` prints
- provision: install what the lane's checks need to run in a fresh worktree, such as its dependencies

List with `wt list`.
Remove a worktree only through `wt prune` or `wt merge`.
Keep `git worktree remove`, `git worktree prune`, and `rm` off every worktree path.
Answer a question about wt from its config file and docs.
Address files in a worktree by the absolute path wt prints.
Leave every worktree and branch the current work neither created nor names untouched and unmentioned.

wt command
  | it stops because a project hook awaits approval = stop the lane -> ask the user to review the hooks with `wt config approvals add`

### Split

Before work starts, and again whenever a new request lands mid-work, split the work into lanes.

work on a running lane's file
  | you work that lane yourself or its agent has yet to start = add it to that lane
  | otherwise = hold it until that lane lands -> give it a lane of its own

### Create

Give each lane its own worktree, created in the primary checkout with `wt --yes switch --create $branch --base $trunk --no-cd`.

provision
  | the repository's `.config/wt.toml` holds a pre-start hook = let it provision the worktree
  | otherwise = have the lane provision its worktree before its first commit -> propose once in your next message a pre-start hook for `.config/wt.toml` that provisions every new worktree

### Delegate

lanes
  | no spawning tool is in hand, or your routing keeps implementation work with you = work every lane yourself, each in its own worktree and landed before the next starts
  | otherwise = keep the lane that needs the conversation's context most -> give every other lane whole to an agent of its own -> work your lane while the agents run -> track every lane as a task

Spawn each lane agent in the background without the Agent tool's worktree isolation.
Give a lane away whatever its size, in place of acting on it directly or splitting its steps among other agents.
Name in each lane agent's prompt:

- the worktree's absolute path and its branch
- the files it may change
- the checks to run before each commit: the tests covering the lane's own files, each run in the foreground, with every full suite left to Finish
- the acts it leaves undone: a push, a check or formatter run over files outside its own, an edit to a file outside its own such as a README or a contract module another lane owns, and an end to its turn while a command it started still runs in the background
- how to provision the worktree where no pre-start hook does
- steps 3 to 5 under Land, written out, with its final report sent only once step 5 holds

lane agent
  | it holds no Bash tool = leave committing and landing out of its prompt -> commit its lane yourself once it reports

### Land

Keep `skill:simplify` out of every lane's landing and every lane agent's prompt, since Finish holds its one run.
The lane's own agent lands the lane once its checks pass, and you land your own lane and every lane whose agent holds no Bash tool, in these steps:

1. Run `wt -C <worktree> step squash $trunk` -> confirm `git -C <worktree> log --oneline $trunk..HEAD` lists one commit.
2. Run `git -C <worktree> fetch` -> run `git -C <worktree> rev-list --left-right --count "$trunk...$trunk@{upstream}"` -> stop and report both counts where both are above zero, the trunk and its upstream having diverged.
3. Run `wt -C <worktree> merge $trunk`, which rebases the branch onto the trunk and fast-forwards the trunk, then removes the worktree and deletes its branch.
4. Handle a stopped merge by the block below.
5. Confirm `git -C <primary checkout> log --oneline $trunk` lists the lane as one commit -> report that commit's SHA and subject -> run `wt -C <primary checkout> prune`.

stopped merge
  | on a rebase conflict = resolve it in the worktree on its merits -> continue the rebase -> run the merge again, counting the run among the two
  | the trunk moved or the fast-forward was refused = run it again, at most twice -> where it still stops report the lane with its branch and the last error

### Races

hook step
  | one you write or change shares state on disk with a step that may run at the same moment, another lane's included = run the two in sequence or as a pipeline, or give each its own state

### Finish

After every lane lands, run in the primary checkout the work that needs every lane landed such as a cleanup across lanes -> run `skill:simplify` yourself once over the source code the lanes landed -> commit each change it calls for on the trunk -> run each test suite once on the trunk -> report each lane's landed SHA and subject.
The landed source is `git -C <primary checkout> diff <start>..$trunk`, with `<start>` the trunk commit the earliest lane was created from.
Hold every push until the `skill:simplify` run has committed its changes or been skipped.

landed changes
  | they hold no source code, only prose such as docs or instruction text = skip the `skill:simplify` run

leftover worktree
  | one the current work created outlives its branch's merge and `git -C <path> status --short` shows uncommitted changes = report them and keep the worktree
  | one the current work created outlives its branch's merge = run `wt -C <primary checkout> prune`
