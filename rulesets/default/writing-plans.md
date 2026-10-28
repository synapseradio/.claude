<!-- rule: writing-plans -->

## writing-plans

For every plan file you write and every exit from plan mode, optimize for a plan an agent can carry to its target outcomes holding only the file.

The executor is the agent that runs the plan, delegating as it sees fit. A work unit is work that lands as one commit. A document of record is a file the plan names as binding.
Write for the executor, who holds the plan and every file it names by absolute path, and none of the conversation behind it. Count naming a file as handing over its content.

### Before writing

Plan outside plan mode, asking the user to lift it where it holds. Until the plan is approved, change nothing beyond the plan file and the scratchpad.

Land findings in their own turn: evidence by path, open questions, and candidate approaches with tradeoffs. Then stop, and let the user pick a framing. Write the plan only after that pick.

Settle every unknown by what answers it:

```haskell
settle unknown
  | only the work observes it = an arm in the plan, with the act under each result
  | a source or a check       = a must verify line
  | only the user             = a must ask line, its answer written in as a decision
```

Before exit, reread each cited source at the head of the branch the work builds on, and date the read. Check open branches and pull requests for changes to the same paths.

### The form

In each template below, replace each bracket with what it describes.

The plan delegates nothing and builds on no document of record ? use the short form (Target outcomes, entries, Verification) : use the brief form.

Name once the absolute root that entry paths resolve against. Give each entry this form, one key per line.

```markdown
- path: [relative to the root, or none]
- symbol: [the exact symbol, or none]
- change: [the change]
- check: [the acceptance check, and the defect it catches]
```

Set entries that share a check as rows of one table, the check beneath it.

Give the brief form these parts, in this order. Leave out each part the work leaves empty.

```markdown
## Target outcomes

[each end state, as a condition a reader can observe on the finished work; the early stops allowed; the state the work changes, with evidence by path]

## Perspective

[the executor's role and job]

## Task

[what to do and what closes it; the stakes: who meets the result in the end, and what a failure costs them]

## Read first

[each document of record by absolute path, with the sections that matter]

## Decisions

[a table, one row per settled choice]

## Amendments

[each departure from a document of record, by section, with its source]

## Work

[the work units in order, each as entries or a document section, with what it waits on]

## Tooling

[the exact command for each check and build]

## Constraints

[what every work unit keeps; what the work leaves as it stands]

## Invitations

[the forks the executor settles alone, and where it records each; what stops the work, and what it reports then]

## Verification

[the check after each work unit; the checks on the whole, one per target outcome among them; any check left to a person, with its steps and passing result]
```

### Writing the parts

Point at a document of record by section, in place of copying it. Hold the plan as binding where the two disagree. State a fact beside the work unit it binds, with its source. Give each removal its own entry. Name each way a check could pass with its defect present, and what closes it.

### Readiness

Keep a readiness file at the branch's scratchpad path, out of the plan file, one line per item, in this form.

```markdown
- intent: [the request, in the user's words where they carry weight]
- decision: [a choice the plan carries, with its source: said, shown, or inferred, and confirmed or open]
- known: [what a source shows, with the source and the date read]
- assumed (needs verification before display to user): [what lacks a source, with the evidence to seek]
- must verify: [a claim the plan rests on, with the check that settles it]
- must ask: [a question only the user settles]
```

Count an inferred decision still open as a must ask line. Resolve must verify and must ask lines in a loop, through reads, delegates, searches, and checks, until both kinds are empty.
Ask the must ask lines in grouped rounds: an installed skill or plugin for asking questions exists ? through it : through AskUserQuestion.

### Exit

Give a plan presented as a deliverable the document register, in which a header is a label and a bullet holds one idea. Present the plan for approval, entering plan mode only to call ExitPlanMode as planning's last step. Call ExitPlanMode only once investigation is complete and the plan is ready to share with the user.
