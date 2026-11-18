<!-- rule: agent-delegation -->
## agent-delegation

For every step a delegate could take and every spawn through any spawning tool, a delegate's own included, optimize for a step done by the cheapest model able to take it through a spawn that pays its cost in tokens and wait and returns a result the caller can check.

- gauges:
  - inference: what the delegate must infer beyond the prompt and its evidence
  - span: whether the work fits one context
  - reversibility: the cost of undoing a wrong result
  - verifiability: the check outside the delegate that catches a wrong answer
  - surviving critiques: critique findings awaiting repair
- gathering: any read or command run for its output, a test suite's run included, never one that changes state
- shared focus: anything two or more agents in one orchestration read or write or state, a term or a convention included
- roster: the orchestration's running agents, each with its address and the slice it owns
- plan work: a step that carries out an approved plan, its landing and its finish included

### Whether to spawn

Keep the conversation with the user, the routing, the prompts you compose and the grounding of what comes back.
Hold gathering as work beyond the context in hand.

route step
  | no spawning tool is in hand = act directly
  | plan work with you at the session's top level = spawn it once for the whole plan in the background at sonnet and effort medium, its prompt holding the plan file's absolute path -> answer what it hands up -> relay its reports -> leave every file the plan covers to it and its delegates
  | a thinkies skill run other than `thinkies:check-notes` = spawn it at opus and effort high -> relay only its final output
  | any work on a shell file but running it, a git hook or a bats suite included = spawn it with a prompt for the task
  | it finishes in one tool call with the context in hand = act directly
  | git work needing judgment as it goes, such as a rebase with conflicts = spawn it
  | a git operation whose command you can state whole, outside a slice you built = spawn it at haiku
  | an observed failure of unknown cause = spawn it
  | a break's fix would pull you off the current task = spawn it
  | the Read that Edit or an overwriting Write requires before your next change = act directly
  | the newest handoff note read at a session's first turn = act directly
  | a cited line opened to confirm it backs a claim = act directly
  | a scan of saved command output = act directly
  | any other gathering = spawn a fresh haiku, one holding the step's related reads > parallel haikus, each saving every command run's output to a scratchpad file
  | a unit of a plan whose units run in sequence on one working tree = act directly, whatever delegates the plan names, its gathering spawned as above and every verdict on its work judged by you
  | sizeable work independent of the step in hand = spawn it
  | it finishes with the context in hand = act directly
  | a map or an implementation or a critique or a design or a plan = spawn it

Spawn one delegate where one completes the task.
Spawn a re-check of your own result only on the user's ask.

change
  | it edits only comment text, JSDoc included = commit it with no check run and no runner spawned

### The spawn

Take the gauges -> choose the agent type whose description claims the step, then model and effort by the blocks below -> compose the prompt -> spawn -> hold each reported claim pending until you find its source.

span
  | it exceeds one context, a haiku delegate's held as a 99k-token budget = split the work into sequential spawns that each finish a slice end to end, in place of one layer across every feature

model
  | the user named one = that model
  | the step's route line names one = that model
  | a read, a verbatim copy of a prepared payload, or a git operation the prompt states whole = haiku
  | implementing from a design, refining a diff, or critiquing = sonnet
  | a design, a plan, or an irreversible edit = opus
  | the prompt states every step, reading verifies the result, and no file changes = haiku
  | scope stated, open questions few and named = sonnet
  | scope broad, or several unknowns to settle as it goes = opus
  | otherwise = sonnet

Spawn fable only on the user's ask, once per ask.

effort prompt
  | the user asked for or permitted one = that effort
  | a sonnet delegate's prompt states every step in one part = low
  | the delegate runs on sonnet = medium
  | the step's route line names one = that effort
  | it states every step of a task in one part = low
  | otherwise = medium

effort field
  | it exists = set it
  | otherwise = state the depth in the prompt: search breadth, alternatives to weigh, the check to run

### What comes back

Resume a delegate only where the step needs what it alone holds, such as the sources behind its own report.

return
  | review findings = send the delegate that did the work only the user's decisions and defects in the behavior the task requests -> drop every other finding, unmentioned and unasked
  | a question handed up in a message or a report = answer one under the caller's mark from the plan and what you hold -> put one under the standing question to the user through AskUserQuestion -> send the answer through SendMessage at its agent ID, which resumes it where it stopped

### Agents running at once

agents
  | two or more run at once and a shared focus exists or could arise = keep each agent's roster current in its prompt and then by message, telling every running agent when one joins -> give all agents their shared conventions worded identically -> direct each agent to agree each wording or decision through SendMessage with every agent whose files state it before settling it -> address every final report to the caller

wait
  | one agent's edits wait on another's finishing = direct the finisher to message the waiter with what it changed and decided

Let agents edit each file one at a time.

<!-- rule: delegate-prompt -->
## delegate-prompt

For every prompt you compose for a delegate, optimize for a prompt the delegate can act on holding nothing else, composed under the mandatory `delegate-prompt` skill: before the first line of a prompt for any spawn through any spawning tool, a workflow stage's prompt and a fork's included, load `delegate-prompt` through the Skill tool once in this context, or read `~/.claude/skills/delegate-prompt/SKILL.md` in full where the Skill tool is absent, and follow it in every prompt you send.

<!-- rule: worktrees -->
## worktrees

For every piece of work that changes files in a git repository and every request that lands while it runs and every git worktree you touch, optimize for work split into lanes that run at once without racing, each landing on the trunk as one commit through a worktree the wt CLI created and merged and removed with its hooks and config run.

- wt: worktrunk, documented at <https://worktrunk.dev>, with `wt config show` printing its config and hooks and each file's location
- lane: a unit of the work whose changed files no other running lane changes
- trunk: the branch the work builds on, where every lane lands
- primary checkout: the repository's main worktree, the directory holding the `.git` that `git rev-parse --path-format=absolute --git-common-dir` prints
- provision: install what the lane's checks need to run in a fresh worktree, such as its dependencies

List with `wt list`.
Remove a worktree only through `wt prune` or `wt merge`, or through `wt remove` in the superseded case below.
Keep `git worktree remove`, `git worktree prune`, and `rm` off every worktree path.
Answer a question about wt from its config file and docs.
Address files in a worktree by the absolute path wt prints.
Leave every worktree and branch the current work neither created nor names untouched and unmentioned.

wt command
  | it stops because a project hook awaits approval = stop the lane -> ask the user to review the hooks with `wt config approvals add`

superseded worktree
  | its work landed by another route or was replaced, so `wt merge` would land superseded code = back up its commits with `git -C <primary checkout> bundle create <file> <branch>`, the file in the scratchpad directory -> confirm `git -C <primary checkout> bundle verify <file>` passes -> save its uncommitted changes, untracked files included, as a patch or tarball in the same directory -> remove it with `wt -C <primary checkout> remove <branch> -D`, adding `-f` where it holds uncommitted changes

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
- that every change a formatter or linter makes, in a file outside its own too, stays as the tool left it and goes into its commit, unreverted and unadjusted by hand
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
