<!-- rule: writing-plans -->

## writing-plans

For every plan file you write and every exit from plan mode, optimize for a plan an agent carries to its target outcomes holding only the file.

- executor: the agent running the plan, delegating at will, holding the plan and each file it names by absolute path, never the conversation
- work unit: work that lands as one commit
- document of record: a file the plan names as binding
- plan arm: a fork in the plan, with the act under each result
- readiness file: the plan's items, one line each, at the branch's scratchpad path, apart from the plan

Write for the executor.
Plan mode is on ? ask the user to lift it.
Until approval, change only the plan file and the scratchpad.
Land findings (evidence by path, open questions, approaches with tradeoffs) in a turn of their own -> stop -> write the plan on the framing the user picks.

settle unknown
  | only the work observes it = a plan arm
  | a source or a check settles it = a must verify line
  | otherwise = a must ask line, its answer written in as a decision

### Form

Replace each bracket with what it describes.
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
[forks the executor settles alone, and where it records each; what stops the work, and what it reports then]
## Verification
[a check after each work unit; checks on the whole, one per target outcome; each check left to a person, with steps and passing result]
```

Cite each document of record by section, in place of copying it; where the two disagree, the plan binds.
State each fact beside the work unit it binds, with its source.
Give each removal its own entry.
Name each way a check could pass with its defect present, and what closes it.

### Readiness

Keep a readiness file in this form.

```markdown
- intent: [the request, in the user's words where they carry weight]
- decision: [a choice the plan carries; source said, shown, or inferred; confirmed or open]
- known: [what a source shows, with the source and date read]
- assumed (needs verification before display to user): [what lacks a source, with the evidence to seek]
- must verify: [a claim the plan rests on, with the check that settles it]
- must ask: [a question only the user settles, open inferred decisions included]
```

Loop reads, delegates, searches, and checks until no must verify or must ask line remains.
Ask must ask lines in grouped rounds, through an installed asking skill or plugin > AskUserQuestion.

### Exit

Reread each cited source at the head of the branch the work builds on, dating each read -> check open branches and pull requests for changes to the same paths -> present the plan in the document register, with headers as labels and one idea per bullet -> enter plan mode only to call ExitPlanMode, planning's last step, once the readiness file holds no must verify or must ask line.
