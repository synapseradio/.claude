<!-- rule: unasked-asides -->
## unasked-asides

For every artifact you hand on, optimize for an artifact that carries the work the user asked for, with every argument for it left out.

- aside: a justification or a comparison
- justification: rationale for work instructed or not: why the step belongs, what it buys, why you put it there
- comparison: a claim about material outside the requested change: what the other steps do, what the rest of the file lacks, where this one ranks

Count as content, in place of a case for the work:

- a clause in a plan or composed prompt naming only who meets the work's output and what failure costs them
- a clause in a composed prompt's greeting naming only the delegate's skillset or what its work makes possible

Find every clause outside what the user asked for.

clause
  | its unit's job is rationale, such as a commit body = write the rationale for your own decisions alone
  | an aside = cut it, one that checks out included
  | otherwise = keep it

Keep an aside cut from an artifact out of the delivering message and everywhere else it could resurface, a TODO included.

message
  | it hands over a prompt for another reader = make it the prompt alone and verbatim, fenced only where the prompt itself needs a fence -> put everything else in an earlier message, or hold it until asked

<!-- rule: writing-docs variant: haiku -->
## writing-docs

A doc page states what its reader observes, does, and can trust.
Keep the mechanism in the code.

<!-- rule: writing-prose -->
## writing-prose

For all natural language you write or improve that a person or a model reads, in code too, optimize for prose written under the mandatory `prose` skill: before the first line of a message or reply, a report or summary, a pull request title or body, a commit message, a documentation page or README, a code comment or docstring, an error or log message, a ticket or chat note, a plan, or a prompt or instructions for another agent, load `prose` through the Skill tool once in this context, or read `~/.claude/skills/prose/SKILL.md` in full where the Skill tool is absent, and follow it in every line you write.
