---
name: prep-plan
description: Use on every request to plan, in plan mode or outside it, such as 'plan this', 'make a plan', 'how should we approach this', or 'what are the steps'; on every request to write a plan file; on every request to prepare work for another agent or a later session to carry out, such as a brief, a handoff plan, or a spec to build from; and on every entry into plan mode. Runs planning as a loop of passes, gather, settle forks, ask, write the plan, verify readiness, and exit through ExitPlanMode, each pass with its entry condition, its act, and what ends it, so the plan reaches an executor that holds only the plan file.
---

# Prep plan

For every plan file you write and every exit from plan mode, optimize for a future agent that carries to its target outcomes holding only the plan file.

Planning runs as a loop. Each pass below states when it is entered, what it does, and what ends it, and names the pass that runs next. The readiness file decides the next pass: its open lines send the loop back until none remains.

## Terms

- executor: the agent running the plan, delegating at will, holding the plan and each file it names by absolute path, never the conversation
- work unit: work that makes one commit
- document of record: a file the plan names as binding
- plan arm: a fork in the plan, with the act under each result
- readiness file: the plan's items, one line each, in a working file at the branch's scratchpad path, apart from the plan
- plan-changing fork: a fork whose result could change the plan's next steps
- trunk: the branch every lane is created from and lands on
- primary checkout: the repository's original working tree, from which every lane's worktree is created
- lane: one or more work units on a branch of their own, in a git worktree of their own, changing files no other running lane changes, and landing on the trunk as one commit
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
- lane: [one per lane: each line of the lane block below that gather has settled]
```

Ends: the readiness file holds the intent line. Next: gather.

## The loop

Loop reads, delegates, searches, and checks until no must verify or must determine line remains and every plan-changing fork is settled. Gather, settle, and ask repeat in that cycle; write the plan, verify readiness, and exit follow once it closes, and each sends the loop back where it meets an open line.

### 1. Gather

Entered: after entry, and each time a must verify line stands or a later pass sends the loop back.

Act: Run the reads, delegates, searches, and checks that settle each must verify line and each assumed line. Turn each result into a line: a must verify line settled becomes a known line with its source and the date read; an assumed line becomes a must verify line naming its check. Hand each unknown you meet, and each plan-changing fork, to the settle pass.

The work changes files in a git repository ? find its lanes in this pass, running the reads below as one batch of parallel calls, so the questions they raise reach the ask pass:

- List the files each work unit changes, with a must verify line for each unit whose files a read has yet to show.
- Join into one lane every work unit that changes a file another unit changes. Give each other unit a lane of its own. A lane that needs another lane's result waits on that lane, and is created only once that lane lands.
- Name the trunk, the primary checkout by absolute path, the exact commands of the checks covering each lane's files, and, by exact name, each skill you loaded while planning that bears on a lane's task.
- Read `.config/wt.toml` on the trunk for a pre-start hook that provisions dependencies in a new worktree. No hook provisions them ? find the commands that do, as each lane's provisioning, and write a must determine line proposing a repo-local pre-start hook that runs them. Answered yes, adding that hook becomes a lane of its own, and lanes created before it lands still provision themselves.
- Read every hook the lanes run, in `.config/wt.toml` and the repository's commit hooks, for a step that shares a cache, lock, or output path with another step, and hand each one to settle as a plan-changing fork: run those steps in sequence, as a pipeline of `[[<hook>]]` entries in `.config/wt.toml` or its commit-hook equivalent, or give the step state of its own.
- Write a lane line for each lane.

Ends: each must verify line has had its check run, each result stands in the readiness file, and, where the work changes files in a git repository, each work unit stands in exactly one lane line. Next: settle.

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

Ends: each work unit carries its entries or its document section and its check, each lane carries every line of the lane block, the finish block follows the lanes, and each part of the chosen form holds its content or is left out as empty. Next: writing meets an unknown or a plan-changing fork ? settle. Otherwise ? verify readiness.

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
- worktree: create it from the primary checkout with `wt --yes switch --create [branch] --base [trunk] --no-cd`, and address it by the absolute path wt prints, written `<worktree>` below
- provisioning: [the pre-start hook in `.config/wt.toml` provisions it, or the commands to run in `<worktree>` before its first commit]
- files: [each path the lane may change, relative to the root; no other lane changes any of them]
- checks: [each command to run before each commit, with its passing result]
- skills: [each skill you loaded while planning that bears on this lane's task, by exact name, which this lane's agent loads through the Skill tool before its first change; or none]
- worker: [the agent that works and lands this lane, or the orchestrator]
- waits on: [each lane that lands before this lane's worktree is created, or none]
- commit: through the hooks with `git -C <worktree> commit -m '<message>' -- <paths>`; `git -C <worktree> status --short` prints nothing after each commit
- land, once the checks pass:
  1. Run `skill:simplify` over the lane's changes, and commit what it yields.
  2. Squash the lane to one commit with `wt -C <worktree> step squash [trunk]`, then confirm `git -C <worktree> log --oneline [trunk]..HEAD` lists one commit.
  3. Run `git -C <worktree> fetch`, then `git -C <worktree> rev-list --left-right --count [trunk]...[trunk]@{upstream}`. Both counts above zero ? stop and report both counts.
  4. Run `wt -C <worktree> merge [trunk]`. The trunk moved or the fast-forward was refused ? repeat steps 3 and 4, at most twice more.
  5. Confirm `git -C [primary checkout] log --oneline -1 [trunk]` shows the lane's one commit.
  The worker runs every step. A worker that cannot run git or wt runs `skill:simplify`, and the orchestrator runs every git and wt command in these steps.
- work:
  [the lane's work units in order, each as entries or a document section]
```

Finish block, after the lanes:

```markdown
### Finish
- after: every lane lands
- on the primary checkout: [the work that needs every lane, cleanup and deletions for one, or none]
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
[work units in order, each as entries or a document section, with what it waits on; where the work changes files in a git repository, how the lanes run, then the lane blocks, then the finish block]
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
Plan one suite run for the whole plan, as its last step before the work is declared done, with each work unit's own cheap checks before its commit; with lanes, that run is the finish block's suites line.
Keep a check only where it catches a break that would otherwise ship.
Keep critic rounds, fix slices, and per-case logs out of a plan, unless the user asks for them.

With lanes, also write these:

- Write each lane block so the orchestrator can hand it whole as the core of that lane's delegate prompt, leaving each angle-bracketed placeholder, `<worktree>` for one, for the executor to fill.
- List in each lane's files line every path its work units change.
- Open Work with the orchestrator's order: create the worktree of every lane that waits on none, hand each lane but one to its own agent with the lane block in its prompt, create each waiting lane's worktree once the lanes it waits on land, and run the finish block once every lane lands.
- State in Constraints that a request arriving mid-work joins the lane whose files it changes, or waits until that lane lands, and otherwise becomes a new lane through its own lane block; and that nothing is pushed without approval.

### 5. Verify readiness

Entered: the plan file is written.

Act: Reread each cited source at the head of the branch the work builds on, dating each read -> check open branches and pull requests for changes to the same paths -> read the readiness file for any must verify or must determine line and any plan-changing fork still open -> read the lane blocks for a path listed in two lanes.

Ends: each reread matches what the plan states, no open branch or pull request changes the same paths, no path stands in two lanes, and the readiness file holds no must verify or must determine line with every plan-changing fork settled. Next: a source changed, or an open branch or pull request changes the same paths ? gather, with the stale known lines turned back into must verify lines. A path stands in two lanes ? gather, joining those lanes. A must verify line stands ? gather. A must determine line stands ? ask. Otherwise ? exit.

### 6. Exit

Entered: verify readiness ends with nothing open.

Act: Present the plan in the document register, with headers as labels and one idea per bullet -> enter plan mode only to call ExitPlanMode, planning's last step, once the readiness file holds no must verify or must determine line and every plan-changing fork is settled.
Plan mode already holds ? settle every plan-changing fork and clear every must verify and must determine line before calling ExitPlanMode.
Ask for a plan's approval only through ExitPlanMode, with AskUserQuestion kept to the plan's open questions.

Ends: ExitPlanMode returns. Approval ends the loop and lifts the limit on what you change. A rejection with feedback ? settle, with the feedback as the unknowns it raises.
