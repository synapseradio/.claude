# Writing plans

This applies when writing a plan file or leaving plan mode.

```sudolang
write for an AI agent who holds nothing but the plan file and can delegate to subagents
name every place to look: absolute paths, exact symbols, the change, its acceptance
  check, since you already did that searching and only the file carries its results

Constraints {
  findings land in their own turn before any plan: file:line evidence,
    open questions, candidate approaches with tradeoffs, then stop;
    the plan waits for the user to pick a framing, since a wrong framing
    corrected on findings costs one message and corrected on a plan
    costs the plan
  never call ExitPlanMode in the turn that finished investigating
  never call ExitPlanMode while a question remains unresolved
  a sentence hedges ("depending on X we could...") => extract the question,
    ask it through AskUserQuestion, rewrite the branch as a decision after sort
  ask each open question, fold the answers into the plan, sort for each answer,
    then present the plan for approval
}
```
