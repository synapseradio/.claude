# Tools that change the plan

Read the section for each job that has a tool line in the readiness file, and skip the rest. A tool earns a place in the plan only where it changes what the plan says: a command the executor runs, a step the plan can drop, or a constraint on how units are cut. With no tool for a job, the plan uses the fallback and loses nothing it needs.

Worktree tools have a reference of their own, `references/worktree-tools.md`.

## Commit hooks

Found as `commit_hooks` by `detect-tools.py`: a hook manager's file, a `core.hooksPath` setting, or an executable hook.

Read the hook configuration and list what runs on a commit, and on which files.

- Hooks constrain how units are cut. Where a type checker or a test run fires on commit, every unit must leave the whole project passing with no other unit's work present. Cut units to fit, or put shared declarations in a contracts unit that lands first.
- Each unit's checks line names the hook, with what it runs, in place of repeating commands the hook already runs. Keep in the checks line only what the hook leaves out.
- State in Constraints that every commit goes through the hooks, and that a hook's rejection becomes the next task.
- Hooks that write files, a formatter that fixes and restages for one, change what a worker sees after a commit. Say so beside the commit rule.
- With lanes, read each hook step for state it shares across worktrees, as `references/lanes.md` directs.

Fallback: the checks line carries every command, and each worker runs them before each commit.

## Task runner

Found as `task_runner`: a justfile, a Makefile, a Taskfile, package scripts, or a mise file. A finding whose `command` is null has the file and lacks the program: use the commands the file wraps.

- Name each check and build in Tooling as the runner's recipe, `just test` for one, since the recipe is what the repository maintains. Read the recipe once and state beside it what it runs.
- Where a recipe provisions a fresh checkout, name it as each lane's provisioning.
- Where package scripts were found with a lockfile, run them through the package manager that lockfile belongs to.

Fallback: Tooling carries each raw command.

## Tracker

Found as `tracker` commands on PATH, or as a tracker in your own tool list. A command on PATH says nothing about whether it is signed in; write a must verify line with a read that proves it before the plan depends on it.

- Where the request names a ticket or an issue, read it during gather, and cite it in the plan by its id as a document of record.
- Where the work ends in a pull request, state in the finish what opens it, with its base branch, and that its title and body wait for approval before anything is posted.
- Where units map to existing tickets, name the ticket beside the unit. Create or move tickets only where the user asked for that.

Fallback: the plan cites the request itself, and the finish ends at the trunk.

## Memory store

Seen only in your own tool list, as a tool that recalls or saves notes across sessions.

- During gather, recall what the store holds on the area the plan changes: earlier decisions, lessons, failures. Treat each as a lead and confirm it against the code before it becomes a known line.
- Give the finish a line that saves the decisions made and lessons learned as a short note, with no logs.

Fallback: decisions live in the plan and the commit messages.

## Skills in the session

Seen only in your own skill list.

- An asking skill: use it for the ask pass.
- A simplify skill: give the finish block its simplify line. With none, leave that line out.
- A skill that bears on a unit's work, a framework's or a tool's: name it beside the unit, by its exact name, for the worker to load before its first change.
