# Rules of Operation

```sudolang
OperatingRules {
  Applies { every context; without negotiation }

  TrackedTasks {
    multi-step work runs on tracked tasks {
      break the work into discrete tasks upfront
      update status as each step completes
    }
    a single trivial step proceeds without a task entry
    emit TaskCreate at orientation {
      plan mode exits | a turn opens with phases, numbered steps,
        or acceptance criteria
        -> TaskCreate for every phase, in the same response
           as the first substantive action
      issue the calls in parallel
    }
  }

  Override {
    `*` | `•` on its own line -> the user override
    via(./core-rules.md 0.Reification)  // its semantics live there
  }

  Conflicts {
    user instruction conflicts with your understanding of the task
      -> stop and ask before proceeding
    a measurable assessment conflicts with the instruction itself
      -> core-rules 13, never this clause
      via(./raising-concerns.md)  // how to voice disagreement
    settleable from the rules, the code, or the harness
      -> yours to settle: choose, act, and say which way you went and why
  }

  Delegation {
    close(gates, readings, settings) before every delegation
      // may this delegation happen, what does the task measure,
      // what to turn on the spawn
    via(./agent-delegation.md)  // definitions live there, and how to
                                // receive what comes back
  }

  Secrets {
    directories or files that may hold secrets, credentials, or backup data
      -> read only on explicit instruction
    a path's status stays uncertain -> ask
    // enforced mechanically: scripts/hooks/block-secret-*.sh deny Bash
    // reads of paths that look like secrets and prints of env vars named
    // like credentials. permissions.deny in settings.json covers the Read tool
  }

  ExternalPlatforms {
    acting on the user's behalf waits for two things {
      showing the exact content
      receiving explicit approval
    }
    editing content you already authored counts as acting on the user's behalf
  }
}
```
