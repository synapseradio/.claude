<!-- rule: writing-plans -->

## writing-plans

For every plan file you write and every exit from plan mode, optimize for a plan an agent can execute holding nothing but the file.

Write for a reader who is an AI agent holding nothing but the plan file, able to delegate to subagents. Give each entry this form, one key-value pair per line, with each bracketed description replaced by the content it describes.

```markdown
- path: [the absolute path]
- symbol: [the exact symbol]
- change: [the change]
- check: [its acceptance check]
```

Land findings in their own turn: path:line evidence, open questions, and candidate approaches with tradeoffs. Then stop, and let the user pick a framing. Never write the plan before the user has picked it. Where a sentence hedges, "depending on X we could...", extract the question, ask it through AskUserQuestion, and rewrite the branch as a decision once the answer is sorted. Ask each open question, fold the answers into the plan, and sort each answer into the slices of the turn, one key-value pair per slice. The same bracket convention holds.

```markdown
- known: [evident to be true]
- assumed: [cited evidence sought for or against]
- must verify: [required to proceed]
- must ask: [progress waits on it]
- may ask: [compounds the speed of progress]
```

Give a plan presented as a deliverable the document register, in which a header is a label and a bullet holds one idea. Present the plan for approval. Never call ExitPlanMode in the turn that finished investigating. Never call ExitPlanMode while a question remains unresolved.
