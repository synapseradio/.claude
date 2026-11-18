# Lanes

Read this when workers change one git repository at the same time, or when the session's rules or the repository's docs ask for a worktree per change. A lane gives each worker a branch and a working tree of its own, so nobody's half-finished edit breaks another's checks, and the trunk receives each lane as one commit.

The plan decides which units become lanes, which paths each lane owns, what each lane is based on, and which lanes run at the same time. The `worktrees` skill holds how a lane's worktree is created, provisioned, committed in, landed, and removed, and the plan carries none of those commands. Load `worktrees` through the Skill tool before the Gather lines below, so the plan asks for nothing the skill settles another way.

## Terms

- trunk: the branch every lane lands on
- primary checkout: the repository's original working tree, from which every lane's worktree is created
- lane: one or more work units on a branch of their own, in a git worktree of their own, owning files and regions no other running lane owns, and landing on the trunk as one commit
- base: the branch a lane is created from, the trunk, or another lane's branch where the lane stacks on it
- lane entry: the lane's part of the plan, what the coordinator acts on
- lane file: the lane's run-book file, what its worker acts on

## Gather

Run these reads as one batch of parallel calls, so the questions they raise reach the ask pass together.

- Turn units into lanes. Give each unit a lane of its own, with two exceptions: units that rewrite the same function or region join one lane, in the order they rewrite it, and a chain of small units one worker takes joins one lane. Units that change different regions of one file keep their own lanes, each owning its region, and settle the file as each lands.
- Choose each lane's base. A lane starts from the trunk as it stands when the lane's wave begins, so later waves start on everything landed. A lane stacks on another lane's branch only where it needs that lane's code before it lands; it then lands after its base.
- Find early starts. A lane in a later wave whose red tests rest on fixed contracts alone can be created with the first wave and write those tests while it waits.
- Take the trunk and the primary checkout from `detect-tools.py`. Where its `trunk_source` is anything but `origin/HEAD`, write a must verify line for the trunk.
- Name for each lane the exact command that runs only the tests it adds or changes, through the runner's file or name filter, and what its commit hook already runs, so the worker leaves both the suite and the hook's work unrun, and, by exact name, each skill you loaded while planning that bears on a lane's task.
- Find the commands that install what a lane's checks need in a fresh worktree, as each lane's provisioning. Whether a hook already runs them, and whether to propose one, is settled by the `worktrees` skill's Create section.
- Hand to settle, as a plan-changing fork, each hook step the `worktrees` skill's Races section has you find sharing state between lanes.
- Write a lane line per lane in the readiness file: `- lane: [branch] | units: [names] | base: [branch] | wave: [number] | worker: [agent]`.

## Write

Fill one lane entry and one lane file per lane, then the finish block, from `assets/lane-block.md`.

- Put the lane entry in the plan's Work section and the lane file in the run book, as `references/run-book.md` describes. The coordinator hands the lane file to the worker by path, with the values that fill its angle-bracketed placeholders.
- List in each lane's owns line every path its units change, with the functions or regions the lane owns in each path another lane also changes. The entry and the file carry the same line.
- Write each unit in the lane file as what it makes true, at the level `references/detail.md` gives for the worker's model, and leave its test cases to the worker.
- Give each lane one worker and one lane file. Where a lane's work runs as a sequence of agents, a test writer ahead of the implementation for one, name the sequence in the file's delegates line and leave each of those prompts to the worker.
- Leave every command that creates, provisions by hook, commits in, squashes, lands, or removes a worktree out of the plan and out of every lane file. State once in Constraints that the executor and each lane's worker load the `worktrees` skill through the Skill tool before their first change and follow it for each of those acts, and name `worktrees` in each lane file's skills line.
- With one lane and one agent, the executor is the lane's worker: write the lane entry with the lane file's body under it in the plan, then the finish block, and leave the Coordination section and the run book out.
- State in Constraints that a request arriving mid-work joins the lane whose functions or regions it rewrites, or waits until that lane lands, and otherwise becomes a new lane through an entry and a file of its own; that the trunk is never pushed before the finish block's suites pass, or without approval; and, where the finish block has a simplify line, that every lane's worker and delegates leave simplifying out.

## Verify

- No function or region stands in two lanes, and each path two lanes share names each lane's part.
- Each lane entry and each lane file holds every line of its template, and neither holds a command that creates, squashes, lands, or removes a worktree.
- The plan's Constraints send the executor and each lane's worker to the `worktrees` skill, and each lane file's skills line names it.
- Each stacked lane lands after its base, and each lane's wave follows the waves of the lanes it waits on.
- Each lane's checks pass on the trunk today, or the plan says which fail and why.
