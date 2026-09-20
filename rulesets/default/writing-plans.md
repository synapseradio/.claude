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

Land findings in their own turn: evidence by path, open questions, and candidate approaches with tradeoffs. Then stop, and let the user pick a framing. Never write the plan before the user has picked it. Where a sentence hedges, "depending on X we could...", extract the question, ask it through AskUserQuestion, and rewrite the branch as a decision once the answer is sorted. Ask each open question and fold the answers into the plan. Close the plan with what stands after the answers, in this form, one line per slice, with each bracketed description replaced by the content it describes.

```markdown
- known: [what a source in hand shows, with the source]
- assumed: [what is held with no source, with the evidence to seek]
- must verify: [a claim the next step rests on, with the check that settles it]
- must ask: [a question only the user settles that blocks the next step]
- may ask: [a question whose answer shortens the work and blocks nothing]
```

Give a plan presented as a deliverable the document register, in which a header is a label and a bullet holds one idea. Present the plan for approval. Never call ExitPlanMode in the turn that finished investigating. Never call ExitPlanMode while a question remains unresolved.
