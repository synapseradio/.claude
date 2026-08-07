# Skill Design

```sudolang
SkillDesign {
  Applies { designing a new Agent Skill, changing an existing one,
            or judging whether one holds up }

  Closure {
    a skill helps because its author settled scope, naming, and
      process once, and every executor loading it inherits those
      decisions rather than remaking them
    close every decision a skill leaves open from what the skill
      itself provides
    a part left unsupplied, with no way to find it -> you have
      found work
  }

  Modes {
    route by the state of the world, never by your own capability {
      no SKILL.md exists yet     -> Design
      the user wants change      -> Refactor
      judging, changing nothing  -> Audit
    }
    entering any mode -> read(../references/skill-design-reference.md)
      in full
      // the mode contracts and the executor moves live there
  }

  Pipeline {
    a skill or its reference material gets created or substantially
      redesigned -> the six-question authoring pipeline {
      read(../references/skill-authoring-pipeline.md) in full
      follow it as written
      Design   -> enter at ResearchSweep
      Refactor -> enter at whichever stage the evidence reopens
        // the pipeline sends work backward freely, so a substantial
        // redesign rejoins wherever its findings land
      Audit    -> never enters   // Audit changes nothing
    }
    the brief complete -> the skill-creator skill builds and
      evaluates from it
  }
}
```
