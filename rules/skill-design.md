# Skill Design

When designing a new Agent Skill, changing an existing one, or judging
whether one holds up.

Invoke the skill-design skill and let it route: Design before a
SKILL.md exists, Refactor when the user wants change, Audit for
judgment without change. Deciding what a skill should be belongs
there; building, testing, and packaging belong with skill-creator.

A skill helps because its author decided things once, and every
executor that loads it inherits those decisions; every decision the
skill leaves open must close from what the skill provides. For that
closure test in full, and for the mode contracts, read
[skill-design-reference.md](~/.claude/references/skill-design-reference.md).
