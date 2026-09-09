<rule name="writing-plans">

## writing-plans

When you are writing a plan file or leaving plan mode, optimize for a plan an agent can execute holding nothing but the file.

The search happened in this session. The file is all that travels from it to the agent who executes. A wrong framing corrected on findings costs one message, and corrected on a plan costs the plan. The user's framing sets what the plan is for, so a plan written before it has to guess at that.

A plan's reader is an AI agent who holds nothing but the plan file and can delegate to subagents. Each entry takes this form, one key-value pair per line, with each bracketed description replaced by the content it describes.

```markdown
- path: [the absolute path]
- symbol: [the exact symbol]
- change: [the change]
- check: [its acceptance check]
```

Land findings in their own turn: path:line evidence, open questions, and candidate approaches with tradeoffs. Then stop. The user picks a framing. Where a sentence hedges, "depending on X we could...", extract the question, ask it through AskUserQuestion, and rewrite the branch as a decision once the answer is sorted. Ask each open question, fold the answers into the plan, and sort each answer into the slices of the turn, one key-value pair per slice. The same bracket convention holds.

```markdown
- known: [evident to be true]
- assumed: [cited evidence sought for or against]
- must verify: [required to proceed]
- must ask: [progress waits on it]
- may ask: [compounds the speed of progress]
```

A plan presented as a deliverable takes the document register, in which a header is a label and a bullet holds one idea. Present the plan for approval. Never call ExitPlanMode in the turn that finished investigating. Never call ExitPlanMode while a question remains unresolved.

</rule>
