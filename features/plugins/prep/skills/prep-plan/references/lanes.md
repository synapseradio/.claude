# Lanes

Read this when workers change one git repository at the same time, or when the session's rules or the repository's docs ask for a worktree per change. A lane gives each worker a branch and a working tree of its own, so nobody's half-finished edit breaks another's checks, and the trunk receives each lane as one commit.

## Terms

- trunk: the branch every lane lands on
- primary checkout: the repository's original working tree, from which every lane's worktree is created
- lane: one or more work units on a branch of their own, in a git worktree of their own, owning files and regions no other running lane owns, and landing on the trunk as one commit
- base: the branch a lane is created from, the trunk, or another lane's branch where the lane stacks on it
- worktree tool: the tool that creates, squashes, lands, and removes worktrees here, as the tool line in the readiness file names it, and git itself where nothing else was found

## Gather

Run these reads as one batch of parallel calls, so the questions they raise reach the ask pass together.

- Turn units into lanes. Give each unit a lane of its own, with two exceptions: units that rewrite the same function or region join one lane, in the order they rewrite it, and a chain of small units one worker takes joins one lane. Units that change different regions of one file keep their own lanes, each owning its region, and settle the file as each rebases at its landing.
- Choose each lane's base. A lane starts from the trunk as it stands when the lane's wave begins, so later waves start on everything landed. A lane stacks on another lane's branch only where it needs that lane's code before it lands; it then lands after its base, rebasing onto the trunk first.
- Find early starts. A lane in a later wave whose red tests rest on fixed contracts alone can be created with the first wave, write those tests while it waits, and rebase onto the trunk before the rest of its work.
- Take the trunk and the primary checkout from `detect-tools.py`. Where its `trunk_source` is anything but `origin/HEAD`, write a must verify line for the trunk.
- Name the exact commands of the checks covering each lane's files, and, by exact name, each skill you loaded while planning that bears on a lane's task.
- Read `references/worktree-tools.md` for the tool the tool line names, and take from it the commands the lane block's slots need.
- Find how a new worktree gets its dependencies. Read the worktree tool's configuration on the trunk for a hook that runs once as a worktree is created and finishes before work starts in it. None provisions them ? find the commands that do, as each lane's provisioning. Where the worktree tool supports such hooks, also write a must determine line proposing a repository-local one that runs those commands; answered yes, adding it becomes a lane of its own in the first wave.
- Read every hook the lanes run, in the worktree tool's configuration and the repository's commit hooks, for a step that shares a cache, a lock, or an output path with another step, and hand each one to settle as a plan-changing fork: run those steps in sequence, or give the step state of its own.
- Write a lane line per lane in the readiness file: `- lane: [branch] | units: [names] | base: [branch] | wave: [number] | worker: [agent]`.

## Write

Fill one lane block per lane, then the finish block, from `templates/lane-block.md`.

- Write each lane block so the coordinator hands it whole as the core of that lane's prompt, leaving each angle-bracketed placeholder for the run to fill.
- List in each lane's owns line every path its units change, with the functions or regions the lane owns in each path another lane also changes.
- Give each lane one worker and one prompt, the lane block. Where a lane's work runs as a sequence of agents, a test writer ahead of the implementation for one, name the sequence in the lane's delegates line and leave each of those prompts to the worker.
- State each landing step as its outcome and as the worktree tool's exact command for it. The outcome lets a worker without that tool reach the same state through git.
- With one lane and one agent, the executor is the lane's worker: write the lane block and the finish block, and leave the Coordination section out.
- State in Constraints that a request arriving mid-work joins the lane whose functions or regions it rewrites, or waits until that lane lands, and otherwise becomes a new lane through a lane block of its own; that the trunk is never pushed before the finish block's suites pass, or without approval; and, where the finish block has a simplify line, that every lane's worker and delegates leave simplifying out.

## Verify

- No function or region stands in two lanes, and each path two lanes share names each lane's part.
- Each lane block holds every line of the template, with the command slots filled for the tool the tool line names.
- Each stacked lane lands after its base, and each lane's wave follows the waves of the lanes it waits on.
- Each lane's checks pass on the trunk today, or the plan says which fail and why.
