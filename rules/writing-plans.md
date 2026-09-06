# Writing plans

This applies when writing a plan file or leaving plan mode.

We value a plan an agent can execute holding nothing but the file. The searching happened in this session and only the file carries its results, so every place to look gets named with an absolute path and an exact symbol. A wrong framing corrected on findings costs one message and corrected on a plan costs the plan, so findings land in their own turn and the plan waits for the user's framing.

```sudolang
Plan {
  reader: an AI agent who holds nothing but the plan file and can delegate to subagents
  entry: an absolute path, the exact symbol, the change, its acceptance check
}

fn plan() {
  land findings in their own turn: path:line evidence, open questions, candidate
    approaches with tradeoffs, then stop
  the user picks a framing
  a sentence hedges, "depending on X we could..." => extract the question, ask it
    through AskUserQuestion, rewrite the branch as a decision once the answer is sorted
  ask each open question, fold the answers into the plan, sort each answer into known,
    assumed, mustVerify, mustAsk, or mayAsk
  present the plan for approval
}

require never call ExitPlanMode in the turn that finished investigating
require never call ExitPlanMode while a question remains unresolved
```
