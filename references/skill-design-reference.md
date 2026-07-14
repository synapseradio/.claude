# Skill Design Reference

Long-form catalog named by [skill-design.md](../rules/skill-design.md).

## The frame

A skill helps because its author decided things once — scope, naming,
process shape — and every executor that loads it inherits those
decisions instead of re-making them. The decisions left open fall to
the executor, and each must close from what the skill provides: the
executor can name the options on the table, tell the known facts from
the assumed ones, rank the options by a stated rule, strike the
options that fail a constraint, predict what follows from the option
it favors, and see which act binds. Wherever the skill leaves a part
unsupplied and gives the executor no way to find it, you have found
work.

## The modes

Route by the state of the world, never by your own capability. Design
decides what a skill will do and for whom, before any SKILL.md exists,
and ends at a brief a builder can work from. Refactor aligns an
existing skill with its purpose when the user wants change, and ends
at a change set backed by evidence. Audit judges a skill with the user
and changes nothing: align on intent, walk the principles as lenses,
converge on priorities the user confirms.
