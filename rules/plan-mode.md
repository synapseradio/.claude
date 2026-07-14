# Plan Mode: Resolve Questions Before Exiting

Applies whenever plan mode ends.

Never call ExitPlanMode while a question remains unresolved. Ask each open question through AskUserQuestion first, fold the answers into the plan, and present the plan for approval only after it closes every fork.

A plan that hedges ("depending on X we could...") signals an unresolved question. Extract the question, ask it, then rewrite the branch as a decision.
