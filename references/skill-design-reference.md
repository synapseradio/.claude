# Skill Design Reference

Long-form catalog named by [skill-designer](../agents/skill-designer.md).
That agent holds the trigger and the routing.

```sudolang
SkillDesignReference {
  ExecutorMoves {
    // the decisions a skill leaves open fall to the executor, and
    // each must close from what the skill provides. closing takes
    // six moves. a skill that blocks one has left work behind.
    name the options on the table
    tell the known facts from the assumed ones
    rank the options by a stated rule
    strike the options that fail a constraint
    predict what follows from the option favored
    see which act binds
  }

  Modes {
    Design {
      when: before any SKILL.md exists
      decides: what the skill will do, and for whom
      endsAt: a brief a builder can work from
    }
    Refactor {
      when: the user wants change
      does: align an existing skill with its purpose
      endsAt: a change set backed by evidence
    }
    Audit {
      when: judging without changing
      does {
        align on intent
        converge on priorities the user confirms
      }
      changes: nothing
    }
  }
}
```
