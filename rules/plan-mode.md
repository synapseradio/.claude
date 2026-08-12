# Plan Mode: Resolve Questions Before Exiting

```sudolang
PlanModeExit {
  Applies { whenever plan mode ends }
  // this file governs leaving the mode
  via(./writing-plans.md)  // the plan file's content answers there

  a question remains unresolved -> never call ExitPlanMode {
    ask each open question through AskUserQuestion first
    fold the answers into the plan
    present the plan for approval only after it closes every fork
  }

  Hedge {
    spot   { "depending on X we could..." }
      // a plan that hedges signals an unresolved question
    repair { extract the question; ask it; rewrite the branch as a decision }
  }
}
```
