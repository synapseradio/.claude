# Writing plans

This applies when writing a plan file or leaving plan mode.

Write for an AI agent who holds nothing but the plan file and can delegate to subagents. Name every place to look: absolute paths, exact symbols, the change, and its acceptance check, since you already did that searching and only the file carries its results.

Never call ExitPlanMode while a question remains unresolved. When a sentence hedges ("depending on X we could..."), extract the question, ask it through AskUserQuestion, and rewrite the branch as a decision after sort. Ask each open question, fold the answers into the plan, sort for each answer, then present the plan for approval.
