---
name: prep-plan
description: Use on every request to plan, in plan mode or outside it, such as 'plan this', 'make a plan', 'how should we approach this', or 'what are the steps'; on every request to write a plan file; on every request to prepare work for another agent or a later session to carry out, such as a brief, a handoff plan, or a spec to build from; and on every entry into plan mode. Settles up front what no single worker can settle alone, who the change serves as user stories, every interface between units with the data it passes, what runs in parallel, and how agents coordinate, and leaves test cases and the detail inside each unit to the agent that builds it. Sizes the plan to the task, from a lean one-commit plan to coordinated waves across worktrees, repositories, and sessions, with each worker's material in a run-book file beside the plan. Ends through ExitPlanMode and hands the approved plan to a coordinating agent. Use it whenever work is about to be planned, scoped, broken into steps, briefed, or handed to another agent or session, even when the request never says 'plan'.
---

# Prep plan

For every plan file you write and every exit from plan mode, optimize for an executor that reaches the target outcomes holding only the plan file, with as much of the work as possible able to start at once, and with nothing in the plan that its reader does not act on.

A plan settles, before work starts, each decision its executor would otherwise guess and no single worker can settle alone: who the change serves, where its boundaries sit, what each piece builds against, what runs at the same time, and who tells whom what. The executor is often a mid-sized model at medium effort coordinating other agents. Whatever the plan leaves implicit between units reaches it as a sequential run, a merge conflict, or a boundary built wrong. What happens inside a boundary, the test cases included, is settled by the agent that builds it, with the code open.

A plan stays short. Each line in it is one the executor acts on, two or more agents rely on, or the approval rests on. Material only one worker acts on goes in that worker's run-book file, which the executor hands over by path and never reads.

This skill's directory is `${CLAUDE_SKILL_DIR}`; where that name shows unexpanded, use the base directory the skill was loaded from. The paths below, `references/`, `assets/`, and `scripts/`, resolve against it. Read a supporting file only where a line below sends you to it, so a small task loads none of what a large one needs. The last section lists them all.

## Terms

- executor: the agent running the plan, delegating at will, holding the plan and each file it names by absolute path, never the conversation. Where the session's agent list holds a coordinator agent, one whose description claims running an approved plan, `prep:work-coordinator` for one, the executor is that agent, started by the session's main agent once the plan is approved
- work unit: work that makes one commit, which passes every check that runs on a commit with no other unit's work present
- boundary: a place where the change meets code it leaves alone, or where two work units meet
- contract: what both sides of a boundary rely on, a signature, a type, the data that crosses, a set of ids, a file or message format, a command's surface, or an error channel
- fixed contract: a contract the plan states in full, so each side builds against the plan; an open contract is one only the work can show
- behavior: something a unit makes true that a person or a consuming unit can observe, stated with the command or observation that shows it
- waits on: a work unit waits on another where it needs that unit's code to exist and no fixed contract stands in for that code, or where both rewrite the same function or region
- wave: the work units that run at the same time; the first wave waits on nothing, and each later wave waits only on earlier ones
- foundation: work another work unit waits on, or work that settles what two or more units build against, a contract, a fixture, or a convention
- heavy plan: a plan with three or more work units, or with units in more than one repository
- module map: a heavy plan's picture of its modules, how they relate, and the contract each relation carries
- run book: a directory beside the plan file, named for it with `.md` replaced by `.runbook`, holding one file per worker
- document of record: a file the plan names as binding
- plan arm: a fork in the plan, with the act under each result
- plan-changing fork: a fork whose result could change the plan's next steps
- readiness file: the plan's items, one line each, in a working file where the session keeps scratch files, apart from the plan and out of every commit

## Standing through every pass

Write to the executor directly, as "you".
Hold the executor, in every case, as a fresh instance holding only the plan file's content, with none of the conversation, the names it coined, or what you learned while planning.
Define in the plan's Glossary each term, label, abbreviation, and piece of context the executor needs and the rest of the plan leaves unexplained.
State each fact the executor acts on in the plan, or name the file that holds it by absolute path.
Cite code by symbol, with a line number only as a hint, since edits made in parallel move lines.
Until approval, change only the plan file, the readiness file, and the run-book files.
Put the plan file where the harness or the request names; with neither, beside the readiness file. One plan has one plan file, one readiness file, and at most one run book, however many repositories it changes.
Write each pass's results into the readiness file as they arrive, so the file always shows which lines stay open.
Gather only what an open readiness line asks for. Once a source settles a line, hold it settled, and reopen it only on evidence that contradicts it.

```markdown
- intent: [the request, in the user's words where they carry weight]
- story: [one target outcome as a user story, with how someone observes it done]
- size: [one per question of the size pass: its answer and the fact that decided it]
- tool: [a tool found for a job the plan has, with the evidence; or the job and "nothing found"]
- decision: [a choice the plan carries; source said, shown, or inferred; confirmed or open]
- known: [what a source shows, with the source and date read]
- assumed (needs verification before display to user): [what lacks a source, with the evidence to seek]
- must verify: [a claim the plan rests on, with the check that settles it]
- must determine: [a question only the user settles, open inferred decisions included]
- contract: [name] | [fixed or open] | [the boundary it sits on, and its statement or where the plan states it]
- unit: [name] | [what it changes] | owns: [paths, each with #region where another unit changes the same path] | provides: [contracts] | consumes: [contracts] | waits: [units, each with the code it needs, or none]
- file: [a run-book file's name] | reader: [the one agent or lane it is written for]
```

## The passes

Planning runs as a loop: frame, size, gather, settle forks, ask, write the plan, verify readiness, exit. Each pass states when it is entered, what it does, and what ends it. The readiness file decides the next pass: its open lines send the loop back until none remains.

### 1. Frame

Entered: the skill loads.

Act:

- Plan mode is on ? ask the user, in one line, to lift it, since the readiness file and the run-book files need writing. Where it stays on, keep the readiness lines in the plan file under a heading you remove before exit, and carry on.
- Open the readiness file with the intent line.
- Write the target outcomes as user stories, one story line each. Every plan carries them, a one-line fix included, because the story tells the executor whose judgment settles a detail the plan left open.

  ```markdown
  As a [person and their role], [in the situation where the need arises], I want [what they do or see], so that [what it lets them do next].
  ```

  The subject is a person who can be inconvenienced, never a system, a module, or an agent. The change serves several kinds of people, has no visible user, or its stories will shape units, boundaries, or the agents' flow ? read `references/writing-user-stories.md`.
- Find the tools this machine offers for the plan's jobs. Run `python3 "${CLAUDE_SKILL_DIR}/scripts/detect-tools.py" --repo [a path in the repository]` once and write a tool line per finding; where `python3` is missing, run the probes in `references/worktree-tools.md`. Then read your own tool and skill lists for what no script can see: a memory store, a tracker, an asking skill, a simplify skill, and, in the agent list, a coordinator agent. A tool the session's rules or the repository's docs name for a job outranks a detected one. A commit hook, a task runner, a tracker, a memory store, or a session skill was found ? read that job's section of `references/tool-leverage.md`, and no other. A worktree tool matters only where the size pass selects lanes.

Ends: the readiness file holds the intent line, a story line per target outcome, and a tool line per job. Next: size.

### 2. Size

Entered: after frame, and again each time a unit line or a contract line changes.

Act: answer each question in order and write a size line for it. Each takes its first arm unless the second arm's condition holds, so a small task gets a small plan. Each second arm names what to read, once.

```text
1 units      | the change makes one commit that passes its checks alone
                 = one unit, the lean form
             | otherwise
                 = several units -> references/contracts.md,
                   references/detail.md
2 contracts  | every boundary between two units carries a fixed contract
                 = units wait only on code no contract can stand in for
             | a contract stays open
                 = each unit consuming it waits on the unit providing it;
                   fix it in the plan, or keep the wait and say why
3 agents     | your tool list holds no tool that starts agents, or one unit, or
               every wave one unit wide, or units that share
               context from step to step, or units small enough that a
               fresh worker's prompt and first reads outweigh the work
                 = one agent works every unit, in wave order
             | a wave holds two or more sizeable units that share no state
                 = a coordinator that only coordinates, and one worker per
                   unit -> references/coordination.md, references/run-book.md
4 isolation  | one agent, and neither the session's rules nor the
               repository's docs ask for a worktree per change
                 = the working tree and branch the plan names
             | workers change one repository at the same time, or a rule
               asks for a worktree
                 = lanes -> references/lanes.md, references/worktree-tools.md
5 repos      | every changed file sits in one repository
                 = one repository
             | otherwise
                 = a block per repository, the contracts between them fixed
                   first -> references/repos-and-sessions.md
6 sessions   | the work fits one context and waits on nothing outside the
               session
                 = one session
             | it outgrows one context, or waits on a review, a deploy, or
               a person
                 = a handoff at a wave's end -> references/repos-and-sessions.md
```

Ends: each question has a size line naming the fact that decided it, and each reference a second arm names has been read. Next: gather.

### 3. Gather

Entered: after size, and each time a must verify line stands or a later pass sends the loop back.

Act: run the reads, delegates, searches, and checks that settle each must verify line and each assumed line. Turn each result into a line: a must verify line settled becomes a known line with its source and the date read; an assumed line becomes a must verify line naming its check. Hand each unknown you meet, and each plan-changing fork, to the settle pass. Where you can delegate, send the reads out in parallel and keep cutting the work while they run.

Cut the work in this pass, for every plan, at every level, from the whole down to each unit, and stop the cut at the unit's edge:

- Cut the work into units, each one commit that passes its checks alone. A piece that cannot commit green without another piece belongs in that piece's unit, or behind a contract that lets it.
- List each boundary the change meets, with one unit as with many: every exported signature, type, schema, file format, command surface, or config key that callers, tests, or another unit rely on. Read each as it stands and write a contract line for it, stating in full what stays, what it becomes, and the data that crosses it. A change that meets none gets one line saying so, with what you read to know it.
- Name in each unit line what it owns, what it provides and consumes, and each unit it waits on, with the code it needs from that unit. Hold a unit as waiting only on those units, whatever order the request lists the work in.
- With several units, name each unit's behaviors, and leave its test cases, its helpers, and the order of its work to its worker. Read inside a unit only as far as its boundaries and its behaviors need.
- Look for foundation no unit yet holds: a contract, fixture, or convention that two or more units would each settle alone. Add it as a unit, so units built apart build against one answer.
- With several units, run `python3 "${CLAUDE_SKILL_DIR}/scripts/plan-waves.py" [the readiness file]` and act on its report until the first wave is as wide as the work allows: fix each open contract it names as holding units back, split each hotspot as `references/contracts.md` describes, and clear each problem. Copy the waves it prints into the plan.
- With one agent, among the units free to start, the one the most units wait on runs first.
- Run each check the plan will name once, on the branch the work builds on, and record its result, so the executor can tell a failure it caused from one it inherited.

Each reference the size pass sent you to carries its own Gather lines. Run them here.

Ends: each must verify line has had its check run, each boundary stands in a contract line, each work unit stands in a unit line, and, with several units, `plan-waves.py` exits 0. Next: a unit line or a contract line changed since the last size pass ? size. Otherwise ? settle.

### 4. Settle forks

Entered: any pass meets an unknown or a plan-changing fork.

Act: settle every plan-changing fork by the guard below, and keep each out of Invitations. A fork whose every result stays inside one unit's owned paths changes no plan step: leave it to that unit's worker.

```text
settle unknown
  | only the work observes it = a plan arm, with a must determine line for each act
      under it that only the user chooses or that stops the work
  | a source or a check settles it = a must verify line
  | otherwise = a must determine line, its answer written in as a decision
```

A must verify line whose check ran and left it open goes through the guard again, where neither a source nor a check settles it.

Ends: every unknown met so far stands as a plan arm, a must verify line, or a must determine line. Next: a must verify line stands ? gather. Findings have yet to land, or a must determine line stands ? ask. Otherwise ? write the plan.

### 5. Ask

Entered: settle ends with findings yet to land, or with a must determine line open.

Act: land findings (evidence by path, open questions, approaches with tradeoffs, and the size the plan is taking with the fact behind each answer) in a turn of their own -> stop -> write the plan on the framing, the approach among those offered, that the user picks. A plan with one approach and nothing open has no findings to land and skips this pass.
Ask must determine lines in grouped rounds, through an installed asking skill or plugin > AskUserQuestion.

Ends: the answers arrive. Write each answer in as a decision line, confirmed, and clear its must determine line; write the framing the user picks in as a decision line. Next: an answer opens an unknown or contradicts a known line ? settle. A must determine line stands ? ask again. Otherwise ? write the plan.

### 6. Write the plan

Entered: no must verify or must determine line remains, every plan-changing fork is settled, and, where findings were landed, the user has picked a framing.

Act: fill the template the size lines select, replacing each bracket with what it describes and leaving an empty part out with its heading.

```text
form
  | one unit, one agent = assets/plan-lean.md
  | otherwise = assets/plan-brief.md, with, by size answer:
      a coordinator and workers = a run-book file per worker, references/run-book.md
      lanes = a lane entry and a lane file per lane, and the finish block,
        assets/lane-block.md
      several repositories = a repository block each, assets/repo-block.md
      a handoff = a handoff note per session boundary, assets/handoff-note.md
```

Unsure what a finished plan of either form reads like ? read `references/example-lean-plan.md` or `references/example-coordinated-plan.md`.

Writing lines, for every plan:

- Name once the absolute root that entry paths resolve against.
- Fill the Run line from the agent list: with a coordinator agent in it, the session's main agent starts that agent with the plan file's absolute path; with none, the reader runs the plan.
- Cite each document of record by section, in place of copying it; where the two disagree, the plan binds.
- State each fact beside the work unit it binds, with its source.
- State each contract two or more units rely on in full in the plan, as the exact signature, type, or format with the data that crosses, and name it wherever a unit builds against it.
- A heavy plan ? draw the module map ahead of Contracts, as `references/contracts.md` describes.
- Give each removal its own entry.
- Name each way a check could pass with its defect present, and what closes it.
- Give each work unit at most one worker.
- With one unit, name the behavior its first failing test pins. With several, state each unit's behaviors with the check that shows each, say that tests are owed red-first, and list no test case.
- With workers, write each line by its reader: the plan for what the executor acts on, two or more agents rely on, or the approval rests on, and a run-book file for what one worker acts on.
- List the work units in wave order, state beside each what it waits on, and name each wave's units.
- Plan one suite run for the whole plan, as its last step before the work is declared done, with each work unit's own cheap checks before its commit.
- Keep a check only where it catches a break that would otherwise ship.
- Keep critic rounds, fix slices, and per-case logs out of a plan, unless the user asks for them.

Each reference the size pass sent you to carries its own Write lines. Follow them here.

Ends: the plan holds its Run line, a user story per target outcome, each shared contract stated in full, a heavy plan's module map, and each work unit with its behaviors or its run-book file, its check, and what it waits on, in wave order; each part the size lines selected holds its content, and no part they left out appears; with workers, each run-book file is written and has its file line. Next: writing meets an unknown or a plan-changing fork ? settle. Otherwise ? verify readiness.

### 7. Verify readiness

Entered: the plan file is written.

Act: reread each cited source at the head of the branch the work builds on, dating each read -> check open branches and pull requests for changes to the same paths -> read the readiness file for any must verify or must determine line and any plan-changing fork still open -> with several units, run `scripts/plan-waves.py` again and compare its waves with the plan's -> read the plan as its executor would, holding nothing else: for a story whose subject is no person, a contract a unit builds against that the plan states only in part, a unit placed ahead of one it waits on, a wait the plan leaves unstated, a wait that names a shared file in place of code the waiting unit needs, a line only one worker acts on, and a unit that lists test cases or steps its worker's model settles alone -> run the Verify lines of each reference the size pass sent you to.

Ends: each reread matches what the plan states, no open branch or pull request changes the same paths, every story's subject is a person, every contract a unit builds against is stated in full, each unit follows the units it waits on with every wait stated as the code it needs, every line of the plan has the executor, two or more agents, or the approval as its reader, and the readiness file holds no must verify or must determine line with every plan-changing fork settled. Next: a source changed, or an open branch or pull request changes the same paths ? gather, with the stale known lines turned back into must verify lines. The waves differ, a unit stands ahead of one it waits on, or a wait rests on a shared file alone ? gather, cutting the work again. A story, a contract, or a wait is stated in part, a line sits with the wrong reader, or a unit lists what its worker settles ? write the plan. A must verify line stands ? gather. A must determine line stands ? ask. Otherwise ? exit.

### 8. Exit

Entered: verify readiness ends with nothing open.

Act: present the plan as a document its reader scans before reading, with headers as labels and one idea per bullet -> enter plan mode only to call ExitPlanMode, planning's last step, once the readiness file holds no must verify or must determine line and every plan-changing fork is settled.
Plan mode already holds ? settle every plan-changing fork and clear every must verify and must determine line before calling ExitPlanMode.
Ask for a plan's approval only through ExitPlanMode, with AskUserQuestion kept to the plan's open questions.

Ends: ExitPlanMode returns. A rejection with feedback ? settle, with the feedback as the unknowns it raises. Approval ends the loop ? hand the plan over by its Run line:

```text
hand over
  | the plan ends in a "Run book, to split" part
      = move each of its parts into its run-book file, remove the part from
        the plan, then take the arm below that fits
  | the Run line names a coordinator agent, and you run at the session's top level
      = start that agent once, in the background, at the model and effort its
        file pins, with a prompt holding the plan file's absolute path and
        nothing of the plan's content -> advise: answer each question it hands
        up from the plan and what you hold, put each question it marks as a
        person's to settle to the user through AskUserQuestion, send each
        answer to it by message, relay its reports, and change no file the
        plan covers
  | otherwise = run the plan yourself, as its executor
```

## Supporting files

| file | holds | read when |
| --- | --- | --- |
| [references/writing-user-stories.md](references/writing-user-stories.md) | finding the person behind a change, and how stories steer units, boundaries, contracts, and agent flow | stories shape the design, or the change has no visible user |
| [references/contracts.md](references/contracts.md) | finding boundaries, fixing contracts, turning waits into contracts, splitting a hotspot, planning researchers, drawing the module map | the plan has several units |
| [references/detail.md](references/detail.md) | which details the plan settles and which each worker settles, by the worker's model | the plan has several units |
| [references/coordination.md](references/coordination.md) | roles, roster, prompts, waves, messages, escalation, and writing for a coordinator at medium effort | a wave holds two or more sizeable units |
| [references/run-book.md](references/run-book.md) | sorting material between the plan and each worker's run-book file, the file header, and where the run book sits | the plan has a coordinator and workers |
| [references/lanes.md](references/lanes.md) | turning units into worktree lanes that each land as one commit | workers share a repository, or a rule asks for worktrees |
| [references/worktree-tools.md](references/worktree-tools.md) | choosing the worktree tool, and each tool's commands for a lane's steps | the plan has lanes |
| [references/tool-leverage.md](references/tool-leverage.md) | what a commit hook, task runner, tracker, memory store, or session skill changes in a plan | that job has a tool line |
| [references/repos-and-sessions.md](references/repos-and-sessions.md) | contracts and landing order across repositories; handoffs between sessions | several repositories, or a handoff |
| [assets/plan-lean.md](assets/plan-lean.md) | the plan form for one unit and one agent | writing a lean plan |
| [assets/plan-brief.md](assets/plan-brief.md) | the plan form for several units, with the module map, Contracts, and Coordination | writing any larger plan |
| [assets/lane-block.md](assets/lane-block.md) | the lane entry for the plan, the lane file for the run book, and the finish block | the plan has lanes |
| [assets/repo-block.md](assets/repo-block.md) | the block for one repository | several repositories |
| [assets/handoff-note.md](assets/handoff-note.md) | the note one session leaves the next | a handoff |
| [references/example-lean-plan.md](references/example-lean-plan.md) | a request and the finished one-file fix plan it produced | unsure what a lean plan reads like |
| [references/example-coordinated-plan.md](references/example-coordinated-plan.md) | a request and the finished plan and run-book file it produced, with a module map, contracts, waves, lanes, a researcher, and an integrator | unsure what a coordinated plan reads like |
| `scripts/detect-tools.py` | prints, as JSON, the repository's trunk and primary checkout and the tools found for worktrees, commit hooks, task running, and tracking | frame, once per repository |
| `scripts/plan-waves.py` | prints the waves the unit and contract lines allow, what each open contract holds back, hotspots, and problems | gather and verify, with several units |
