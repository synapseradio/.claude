---
name: prep-plan
description: Use on every request to plan, in plan mode or outside it, such as 'plan this', 'make a plan', 'how should we approach this', or 'what are the steps'; on every request to write a plan file; on every request to prepare work for another agent or a later session to carry out, such as a brief, a handoff plan, or a spec to build from; and on every entry into plan mode. Runs planning as a loop of passes, gather, settle forks, ask, write the plan, verify readiness, and exit through ExitPlanMode, each pass with its entry condition, its act, and what ends it, so the plan reaches an executor that holds only the plan file.
---

# Prep plan

For every plan file you write and every exit from plan mode, optimize for a future agent that carries to its target outcomes holding only the plan file, each work unit starting as soon as the work it waits on is done.

Planning runs as a loop. Each pass below states when it is entered, what it does, and what ends it, and names the pass that runs next. The readiness file decides the next pass: its open lines send the loop back until none remains.

## Terms

- executor: the agent running the plan, delegating at will, holding the plan and each file it names by absolute path, never the conversation
- work unit: work that makes one commit
- waits on: a work unit waits on another where it needs that unit's code to exist, reading or calling what it creates or changes, or where both rewrite the same function or region; two units changing different parts of one file wait on neither; a lane waits on each other lane holding a unit one of its own units waits on
- foundation: work another work unit waits on, or work that settles what two or more units build against, a shared interface, fixture, or convention, or a sweep drafting each unit's red tests for one
- document of record: a file the plan names as binding
- plan arm: a fork in the plan, with the act under each result
- readiness file: the plan's items, one line each, in a working file at the branch's scratchpad path, apart from the plan
- plan-changing fork: a fork whose result could change the plan's next steps
- trunk: the branch every lane is created from and lands on
- primary checkout: the repository's original working tree, from which every lane's worktree is created
- worktree tool: the tool the session's rules or the repository's own files name for creating, rebasing, squashing, merging, and removing worktrees, and git itself where neither names one
- lane: one or more work units on a branch of their own, in a git worktree of their own, rewriting functions and regions no other running lane rewrites, and landing on the trunk as one commit
- worker: the one agent that answers for a work unit; with lanes, the one agent that answers for a lane and its worktree, from the lane's first change to its landing, spawning agents of its own only for work inside that worktree
- orchestrator: the executor while it runs lanes, working one lane itself while each other lane's agent runs in the background, and tracking every lane as a task

## Standing through every pass

Write to the executor directly, as "you".
Hold the executor, in every case, as a fresh instance holding only the plan file's content, with none of the conversation, the names it coined, or what you learned while planning.
Define in the plan's Glossary each term, label, abbreviation, and piece of context the executor needs and the rest of the plan leaves unexplained.
State each fact the executor acts on in the plan, or name the file that holds it by absolute path.
Until approval, change only the plan file and the scratchpad.
Replace each bracket in the templates below with what it describes.
Write each pass's results into the readiness file as they arrive, so the file always shows which lines stay open.

## Entry

Entered: the skill loads.

Act:

Plan mode is on ? ask the user to lift it.
Open the readiness file, and keep it in this form.

```markdown
- intent: [the request, in the user's words where they carry weight]
- decision: [a choice the plan carries; source said, shown, or inferred; confirmed or open]
- known: [what a source shows, with the source and date read]
- assumed (needs verification before display to user): [what lacks a source, with the evidence to seek]
- must verify: [a claim the plan rests on, with the check that settles it]
- must determine: [a question only the user settles, open inferred decisions included]
- unit: [one per work unit: what it changes, each unit it waits on or none, and foundation where it is]
- lane: [one per lane: each line of the lane block below that gather has settled]
```

Ends: the readiness file holds the intent line. Next: gather.

## The loop

Loop reads, delegates, searches, and checks until no must verify or must determine line remains and every plan-changing fork is settled. Gather, settle, and ask repeat in that cycle; write the plan, verify readiness, and exit follow once it closes, and each sends the loop back where it meets an open line.

### 1. Gather

Entered: after entry, and each time a must verify line stands or a later pass sends the loop back.

Act: Run the reads, delegates, searches, and checks that settle each must verify line and each assumed line. Turn each result into a line: a must verify line settled becomes a known line with its source and the date read; an assumed line becomes a must verify line naming its check. Hand each unknown you meet, and each plan-changing fork, to the settle pass.

Order the work in this pass, for every plan, with lanes or without, tested or not, working from the plan's top level down:

- Cut the whole work into foundation and the work that waits on it, then cut each part the same way, until every part is a work unit with a unit line.
- Name in each unit line each unit it waits on, with a must verify line for each wait a read has yet to show. Hold a unit as waiting only on those units, whatever order the request lists the work in.
- Look for foundation no unit yet holds: an interface, fixture, or convention that two or more units would each settle alone, and, where units add behavior, a sweep drafting their red tests. Add each as foundation, so units built apart build against one answer. With lanes, that sweep runs as each lane's first step, in every lane at once, in place of a unit of its own.
- Place foundation first, then each unit after the units it waits on. Two units, neither waiting on the other, run in parallel where more than one agent works. With one agent, among the units free to start, the one the most units wait on runs first.

The work changes files in a git repository ? find its lanes in this pass, running the reads below as one batch of parallel calls, so the questions they raise reach the ask pass:

- List the files each work unit changes, and, in each file another unit also changes, the functions or regions it rewrites, with a must verify line for each unit whose files or parts a read has yet to show.
- Join into one lane the work units that rewrite the same function or region, in the order they rewrite it. Give each other unit a lane of its own, units that change different parts of one file included; those lanes run in parallel, each owning its part, and settle the shared file as each rebases at its landing. Hold a lane as waiting on another only where one of its units needs that lane's code to exist, and name that code in its lane line. Plan every lane's worktree as created up front, before any lane's work starts. A lane that waits on another writes the red tests for its new behavior at once, and holds the rest of its work until that lane lands.
- Name the trunk, the primary checkout by absolute path, the exact commands of the checks covering each lane's files, and, by exact name, each skill you loaded while planning that bears on a lane's task.
- Read the worktree tool's configuration on the trunk for a hook that runs once as a new worktree is created, finishes before work starts in it, and provisions its dependencies. No hook provisions them ? find the commands that do, as each lane's provisioning, and write a must determine line proposing a repo-local hook of that kind that runs them. Answered yes, adding that hook becomes a lane of its own, and this plan's lanes, each created before it lands, provision themselves.
- Read every hook the lanes run, in the worktree tool's configuration and the repository's commit hooks, for a step that shares a cache, lock, or output path with another step, and hand each one to settle as a plan-changing fork: run those steps in sequence, as ordered steps of one hook, in the worktree tool's configuration or the commit-hook configuration, whichever holds them, or give the step state of its own.
- Write a lane line for each lane.

Ends: each must verify line has had its check run, each result stands in the readiness file, each work unit stands in a unit line naming what it waits on, and, where the work changes files in a git repository, each work unit stands in exactly one lane line. Next: settle.

### 2. Settle forks

Entered: any pass meets an unknown or a plan-changing fork.

Act: Settle every plan-changing fork by the guard below, and keep each out of Invitations.

```text
settle unknown
  | only the work observes it = a plan arm, with a must determine line for each act
      under it that only the user chooses or that stops the work
  | a source or a check settles it = a must verify line
  | otherwise = a must determine line, its answer written in as a decision
```

A must verify line whose check ran and left it open goes through the guard again, where neither a source nor a check settles it.

Ends: every unknown met so far stands as a plan arm, a must verify line, or a must determine line. Next: a must verify line stands ? gather. Findings have yet to land, or a must determine line stands ? ask. Otherwise ? write the plan.

### 3. Ask

Entered: settle ends with findings yet to land, or with a must determine line open.

Act: Land findings (evidence by path, open questions, approaches with tradeoffs) in a turn of their own -> stop -> write the plan on the framing the user picks.
Ask must determine lines in grouped rounds, through an installed asking skill or plugin > AskUserQuestion.

Ends: the answers arrive. Write each answer in as a decision line, confirmed, and clear its must determine line; write the framing the user picks in as a decision line. Next: an answer opens an unknown or contradicts a known line ? settle. A must determine line stands ? ask again. Otherwise ? write the plan.

### 4. Write the plan

Entered: the user has picked a framing, no must verify or must determine line remains, and every plan-changing fork is settled.

Act: Write the plan file in the form below, by the writing lines after it.

Ends: each work unit carries its entries or its document section, its check, and what it waits on, in the order gather placed them, each lane carries every line of the lane block, the finish block follows the lanes, and each part of the chosen form holds its content or is left out as empty. Next: writing meets an unknown or a plan-changing fork ? settle. Otherwise ? verify readiness.

#### Form

The plan delegates nothing and builds on no document of record ? short form (Glossary, Target outcomes, entries, Verification) : brief form.
The work changes files in a git repository ? set its work units inside lane blocks, followed by the finish block; in the short form, these take the place of the bare entries.
Name once the absolute root that entry paths resolve against. Within a lane, entry paths resolve against the lane's worktree.

```markdown
- path: [relative to the root, or none]
- symbol: [exact, or none]
- change: [the change]
- check: [the acceptance check, and the defect it catches]
```

Entries sharing a check form one table, the check beneath.

Lane block, one per lane:

```markdown
### Lane [branch]
- worktree: the orchestrator creates it up front, with every other lane's worktree and before any lane's work starts, from the primary checkout, as a new worktree on a new branch [branch] created from [trunk], through a command that runs the hooks for a new worktree, waits on no prompt, and leaves the primary checkout's branch and the orchestrator's working directory as they were; address it by the absolute path that command reports, or by the path it was given where it reports none, written `<worktree>` below
- provisioning: [the hook that provisions it as it is created, named with the file that holds it, or the commands to run in `<worktree>` before its first commit]
- files: [each path the lane may change, relative to the root, and, for each path another lane also changes, the functions or regions of it this lane owns; no other lane rewrites any of them]
- checks: [each command to run before each commit, with its passing result]
- skills: [each skill you loaded while planning that bears on this lane's task, by exact name, which this lane's agent loads through the Skill tool before its first change; or none]
- worker: [the agent that works and lands this lane, or the orchestrator]; the worker alone answers for `<worktree>`, and every change, commit, check, and landing step in it is the worker's
- delegates: [none, or each agent the worker may spawn, in the order they run, a test writer ahead of the worker's own implementation for one]; the worker writes each one's prompt, each works only inside `<worktree>` on this lane's files, reports to the worker, and holds up this lane alone
- waits on: [none, or each lane that lands before this lane's work past its red tests starts, each with the code of it this lane needs to exist; a file both lanes change makes no wait]; the orchestrator messages the worker as each one lands, and the worker rebases this lane's branch onto [trunk], from `<worktree>`, before that work starts
- commit: through the hooks with `git -C <worktree> commit -m '<message>' -- <paths>`; `git -C <worktree> status --short` prints nothing after each commit
- land, once the checks pass:
  1. Squash the lane's commits since [trunk] into one commit, from `<worktree>`, then confirm `git -C <worktree> log --oneline [trunk]..HEAD` lists one commit.
  2. Run `git -C <worktree> fetch`, then `git -C <worktree> rev-list --left-right --count [trunk]...[trunk]@{upstream}`. Both counts above zero ? stop and report both counts.
  3. Merge the lane into [trunk] from `<worktree>`, in one command where the session's worktree tool offers one: rebase the lane onto [trunk], fast-forward [trunk] to the lane's one commit, and, once the fast-forward holds, remove `<worktree>` and the branch [branch]. The rebase stops on a conflict in a file another lane also changed ? resolve it on its merits, keeping what both lanes changed, and run the lane's checks again before the fast-forward. The trunk moved or the fast-forward was refused ? repeat steps 2 and 3, at most twice more.
  4. Confirm `git -C [primary checkout] log --oneline -1 [trunk]` shows the lane's one commit.
  5. Prune from [primary checkout]: remove each worktree whose branch [trunk] already holds, together with that branch.
  The worker runs every step itself. A worker that cannot run git or the session's worktree tool hands every command in these steps to the orchestrator. The lane lands without a `skill:simplify` run: the orchestrator runs it once, in the finish block, over every lane's landed changes.
- work:
  [the lane's work units in order, each as entries or a document section]
```

Finish block, after the lanes:

```markdown
### Finish
- after: every lane lands
- on the primary checkout: [the work that needs every lane, cleanup and deletions for one, or none]
- simplify: the orchestrator, as the session's main agent, runs `skill:simplify` itself, once, over the source code the lanes landed, `git -C [primary checkout] diff [the trunk commit the lanes were created from]..[trunk]`, makes each change it calls for, and commits them on the trunk, before the suites and before any push; landed changes holding only prose, docs or instruction text for one, get no run
- suites: [each suite's command, run once on the trunk, with its passing result]
- report: each lane's landed SHA and subject, from `git -C [primary checkout] log --oneline [trunk]`
```

Brief form, in order, empty parts left out:

```markdown
## Glossary
[each term, label, abbreviation, and piece of context the plan uses that a fresh reader lacks, one line each]
## Target outcomes
[observable end states of the finished work; allowed early stops; the state changed, with evidence by path]
## Perspective
[the executor's role and job]
## Task
[what to do and what closes it; who meets the result, and what failure costs them]
## Read first
[each document of record by absolute path and the sections that matter]
## Decisions
[a table, a row per settled choice]
## Amendments
[each departure from a document of record, by section, with its source]
## Work
[work units in order, foundation first, each as entries or a document section, with what it waits on; which units run in parallel; where the work changes files in a git repository, how the lanes run, then the lane blocks, then the finish block]
## Tooling
[the exact command for each check and build]
## Constraints
[what every work unit keeps; what the work leaves standing]
## Invitations
[forks the executor settles alone, each with every result leaving the plan's next steps unchanged, and where it records each; what stops the work, limited to a failed step or evidence contradicting a settled premise, and what it reports then]
## Verification
[a check after each work unit; checks on the whole, one per target outcome; each check left to a person, with steps and passing result]
```

#### Writing lines

Cite each document of record by section, in place of copying it; where the two disagree, the plan binds.
State each fact beside the work unit it binds, with its source.
Give each removal its own entry.
Name each way a check could pass with its defect present, and what closes it.
Give each work unit at most one worker and a test written red-first for each new behavior.
List the work units in the order gather placed them, the order one agent runs them in.
State beside each unit what it waits on, and name each set of units that run in parallel.
Plan one suite run for the whole plan, as its last step before the work is declared done, with each work unit's own cheap checks before its commit; with lanes, that run is the finish block's suites line.
Keep a check only where it catches a break that would otherwise ship.
Keep critic rounds, fix slices, and per-case logs out of a plan, unless the user asks for them.

With lanes, also write these:

- Write each lane block so the orchestrator can hand it whole as the core of that lane's delegate prompt, leaving each angle-bracketed placeholder, `<worktree>` for one, for the executor to fill.
- List in each lane's files line every path its work units change, with the functions or regions the lane owns in each path another lane also changes.
- Give each lane one worker and one prompt, the lane block. Where a lane's work runs as a sequence of agents, a test writer ahead of the implementation for one, name the sequence in the lane's delegates line and leave each of those prompts to the worker, in place of an orchestrator prompt per agent.
- Open Work with the orchestrator's order: create every lane's worktree up front, before any lane's work starts; hand each lane but one to its own agent with the lane block in its prompt, every lane's worker starting at once; where lanes add behavior, each lane's red tests come first, written on its own branch by its worker or the test writer its delegates line names; message each waiting lane's worker as the lanes it waits on land; the rest of each lane's work starts as soon as each lane it waits on has landed and its tests fail for the right reason; and, once every lane lands, run the finish block in the order of its lines, its simplify line run by the orchestrator itself in place of a delegate.
- State in Constraints that a request arriving mid-work joins the lane whose functions or regions it rewrites, or waits until that lane lands, and otherwise becomes a new lane through its own lane block; that `skill:simplify` runs once, by the orchestrator in the finish block, with every lane's worker and delegates leaving it out; and that nothing is pushed before that run or without approval.

### 5. Verify readiness

Entered: the plan file is written.

Act: Reread each cited source at the head of the branch the work builds on, dating each read -> check open branches and pull requests for changes to the same paths -> read the readiness file for any must verify or must determine line and any plan-changing fork still open -> read the lane blocks for a function or region listed in two lanes, and for a path two lanes list with either leaving its part unnamed -> read the plan against the unit lines for a unit placed ahead of one it waits on, a wait the plan leaves unstated, and a wait that names a shared file in place of code the waiting unit needs.

Ends: each reread matches what the plan states, no open branch or pull request changes the same paths, no function or region stands in two lanes, each path two lanes share names each lane's part, each unit follows the units it waits on with every wait stated as the code it needs, and the readiness file holds no must verify or must determine line with every plan-changing fork settled. Next: a source changed, or an open branch or pull request changes the same paths ? gather, with the stale known lines turned back into must verify lines. A function or region stands in two lanes ? gather, joining those lanes. A shared path leaves a lane's part unnamed ? gather, listing the parts. A unit stands ahead of one it waits on, or a wait rests on a shared file alone ? gather, ordering the work again. A wait is unstated ? write the plan. A must verify line stands ? gather. A must determine line stands ? ask. Otherwise ? exit.

### 6. Exit

Entered: verify readiness ends with nothing open.

Act: Present the plan in the document register, with headers as labels and one idea per bullet -> enter plan mode only to call ExitPlanMode, planning's last step, once the readiness file holds no must verify or must determine line and every plan-changing fork is settled.
Plan mode already holds ? settle every plan-changing fork and clear every must verify and must determine line before calling ExitPlanMode.
Ask for a plan's approval only through ExitPlanMode, with AskUserQuestion kept to the plan's open questions.

Ends: ExitPlanMode returns. Approval ends the loop and lifts the limit on what you change. A rejection with feedback ? settle, with the feedback as the unknowns it raises.
