---
name: plan
description: Use on every request to plan, in plan mode or outside it, such as 'plan this', 'make a plan', 'how should we approach this', or 'what are the steps'; on every request to write a plan file; on every request to prepare work for another agent or a later session to carry out, such as a brief, a handoff plan, or a spec to build from; and on every entry into plan mode. Runs planning as a loop of passes, gather, settle forks, ask, write the plan, verify readiness, and exit through ExitPlanMode, each pass with its entry condition, its act, and what ends it, so the plan reaches an executor that holds only the plan file.
---

# Plan

For every plan file you write and every exit from plan mode, optimize for a future agent that carries to its target outcomes holding only the file.

Planning runs as a loop. Each pass below states when it is entered, what it does, and what ends it, and names the pass that runs next. The readiness file decides the next pass: its open lines send the loop back until none remains.

## Terms

- executor: the agent running the plan, delegating at will, holding the plan and each file it names by absolute path, never the conversation
- work unit: work that lands as one commit
- document of record: a file the plan names as binding
- plan arm: a fork in the plan, with the act under each result
- readiness file: the plan's items, one line each, in a working file at the branch's scratchpad path, apart from the plan
- plan-changing fork: a fork whose result could change the plan's next steps

## Standing through every pass

Write for the executor.
Until approval, change only the plan file and the scratchpad.
Replace each bracket in the templates below with what it describes.
Write each pass's results into the readiness file as they arrive, so the file always shows which lines stay open.

## Entry

Entered: the skill loads, on a request to plan, a request to write a plan file, a request to prepare work for another agent, or an entry into plan mode.

Act:

Plan mode is on ? ask the user to lift it.
Open the readiness file, and keep it in this form.

```markdown
- intent: [the request, in the user's words where they carry weight]
- decision: [a choice the plan carries; source said, shown, or inferred; confirmed or open]
- known: [what a source shows, with the source and date read]
- assumed (needs verification before display to user): [what lacks a source, with the evidence to seek]
- must verify: [a claim the plan rests on, with the check that settles it]
- must ask: [a question only the user settles, open inferred decisions included]
```

Ends: the readiness file holds the intent line. Next: gather.

## The loop

Loop reads, delegates, searches, and checks until no must verify or must ask line remains and every plan-changing fork is settled. Gather, settle, and ask repeat in that cycle; write, verify readiness, and exit follow once it closes, and each sends the loop back where it meets an open line.

### 1. Gather

Entered: after entry, and each time a must verify line stands or a later pass sends the loop back.

Act: Run the reads, delegates, searches, and checks that settle each must verify line and each assumed line. Turn each result into a line: a must verify line settled becomes a known line with its source and the date read; an assumed line becomes a must verify line naming its check. Hand each unknown you meet, and each plan-changing fork, to the settle pass.

Ends: each must verify line has had its check run, and each result stands in the readiness file. Next: settle.

### 2. Settle forks

Entered: any pass meets an unknown or a plan-changing fork.

Act: Settle every plan-changing fork by the guard below, and keep each out of Invitations.

```text
settle unknown
  | only the work observes it = a plan arm, with a must ask line for each act
      under it that only the user chooses or that stops the work
  | a source or a check settles it = a must verify line
  | otherwise = a must ask line, its answer written in as a decision
```

A must verify line whose check ran and left it open goes through the guard again, where neither a source nor a check settles it.

Ends: every unknown met so far stands as a plan arm, a must verify line, or a must ask line. Next: a must verify line stands ? gather. Findings have yet to land, or a must ask line stands ? ask. Otherwise ? write the plan.

### 3. Ask

Entered: settle ends with findings yet to land, or with a must ask line open.

Act: Land findings (evidence by path, open questions, approaches with tradeoffs) in a turn of their own -> stop -> write the plan on the framing the user picks.
Ask must ask lines in grouped rounds, through an installed asking skill or plugin > AskUserQuestion.

Ends: the answers arrive. Write each answer in as a decision line, confirmed, and clear its must ask line; write the framing the user picks in as a decision line. Next: an answer opens an unknown or contradicts a known line ? settle. A must ask line stands ? ask again. Otherwise ? write the plan.

### 4. Write the plan

Entered: the user has picked a framing, no must verify or must ask line remains, and every plan-changing fork is settled.

Act: Write the plan file in the form below, by the writing lines after it.

Ends: each work unit carries its entries or its document section and its check, and each part of the chosen form holds its content or is left out as empty. Next: writing meets an unknown or a plan-changing fork ? settle. Otherwise ? verify readiness.

#### Form

The plan delegates nothing and builds on no document of record ? short form (Target outcomes, entries, Verification) : brief form.
Name once the absolute root that entry paths resolve against.

```markdown
- path: [relative to the root, or none]
- symbol: [exact, or none]
- change: [the change]
- check: [the acceptance check, and the defect it catches]
```

Entries sharing a check form one table, the check beneath.

Brief form, in order, empty parts left out:

```markdown
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
[work units in order, each as entries or a document section, with what it waits on]
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
Give each work unit at most one worker, a test written red-first for each new behavior, and one suite run before its commit.
Keep a check only where it catches a break that would otherwise ship.
Keep critic rounds, fix slices, and per-case logs out of a plan, unless the user asks for them.

### 5. Verify readiness

Entered: the plan file is written.

Act: Reread each cited source at the head of the branch the work builds on, dating each read -> check open branches and pull requests for changes to the same paths -> read the readiness file for any must verify or must ask line and any plan-changing fork still open.

Ends: each reread matches what the plan states, no open branch or pull request changes the same paths, and the readiness file holds no must verify or must ask line with every plan-changing fork settled. Next: a source changed, or an open branch or pull request changes the same paths ? gather, with the stale known lines turned back into must verify lines. A must verify line stands ? gather. A must ask line stands ? ask. Otherwise ? exit.

### 6. Exit

Entered: verify readiness ends with nothing open.

Act: Present the plan in the document register, with headers as labels and one idea per bullet -> enter plan mode only to call ExitPlanMode, planning's last step, once the readiness file holds no must verify or must ask line and every plan-changing fork is settled.
Plan mode already holds ? settle every plan-changing fork and clear every must verify and must ask line before calling ExitPlanMode.
Ask for a plan's approval only through ExitPlanMode, with AskUserQuestion kept to the plan's open questions and every prose ask for approval kept out.

Ends: ExitPlanMode returns. Approval ends the loop and lifts the limit on what you change. A rejection with feedback ? settle, with the feedback as the unknowns it raises.
