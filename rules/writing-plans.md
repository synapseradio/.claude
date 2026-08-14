# Writing plan files

```sudolang
WritingPlans {
  Applies { writing plans, or plan mode }
  // the plan file's content, and leaving the mode

  Audience {
    an AI agent capable of subagent delegation executes the instructions
    the plan file reaches them before anything else they see
    they hold no context outside the plan file's contents
  }

  guarantee their success {
    give specific places to look
      // so they lose no time or focus to context gathering
      // you have already accomplished
  }

  PlanModeExit {
    Applies { whenever plan mode ends }
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
}
```
