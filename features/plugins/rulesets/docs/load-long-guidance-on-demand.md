# Load long guidance on demand

At the end of this tutorial, a long rule has become a one-line pointer, and its full text sits in
a skill that loads only when the work calls for it. A skill is a folder of instructions Claude
Code loads by name. You ask Claude for each step.

## Before you start

- The rule `voice` and the config from [Write your first rule](write-your-first-rule.md). The
  example rule is short; the steps are the same for a long one.

## Turn a rule into a pointer to a skill

1. Ask:

   ```text
   Move the body of the voice rule into a skill named voice-guide, and leave the rule as a
   pointer to it.
   ```

   Claude writes the skill, shortens the rule, and pairs the two in the config:

   ```text
   ~/.claude/rulesets/
     config.yaml
     rules/
       voice.md        Before you write for a person, load `voice-guide` through the Skill tool.
     skills/
       voice-guide/
         SKILL.md      the full guidance
   ```

   ```yaml
   models: haiku sonnet opus
   defaults: voice
   skills:
     voice: voice-guide
   ```

   Claude also links the skill so it loads by name, and reports the line `voice-guide: linked`.

2. Type `/voice-guide` in the session. The skill loads, which shows the link works. Agents
   started from now on list `voice-guide` among their skills.

3. Ask for the check:

   ```text
   Check my rules.
   ```

   Claude reports no errors and no warnings. The check holds the pairing: it reports a pointer
   that never names its skill, and a pairing whose rule or skill is missing.

## What you have now

A short rule in every context and a long guide loaded on demand, kept together in one directory.

## Related

- [Measure what your rules cost](measure-what-rules-cost.md): see the tokens the move saved.
- [The rulesets directory and config](config.md): reference for skills and pairings.
- [Delivery](delivery.md): reference for how skills are linked at session start.
