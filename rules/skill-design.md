# Skill Design

When designing a new Agent Skill, changing an existing one, or judging
whether one holds up.

Route by the state of the world. Enter Design before a SKILL.md exists,
Refactor when the user wants change, Audit to judge without changing
anything. Read
[skill-design-reference.md](../references/skill-design-reference.md) for
those mode contracts and for the closure test in full.

Close every decision a skill leaves open from what that skill itself
provides. A skill helps because its author settled scope, naming, and
process once, and every executor loading it inherits those decisions
rather than remaking them. Wherever a skill leaves a part unsupplied and
offers no way to find it, you have found work.

Run the six-question authoring pipeline whenever creating a skill or
redesigning its content: research sweep, imaginary total reference,
superset synthesis, collider, manifestation design, encoding and naming.
Read [skill-authoring-pipeline.md](../references/skill-authoring-pipeline.md)
and follow it as written. Design mode decides what to build, and that
pipeline governs what goes inside it.
