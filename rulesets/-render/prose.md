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

<!-- rule: writing-docs -->
## writing-docs

For every documentation page and every document a reader scans before reading, optimize for a page that states what its reader observes and does.

- document register: the form a document takes when its reader scans it before reading it

### Doc pages

Keep lookups, files written, and internal ordering in the code.
Keep on the page lookup material the reader acts on, such as a version table.

doc page
  | a code change alters behavior it describes = update it only where what its reader observes or does changes
  | it describes a tool or a behavior = state what its reader observes, does, and can trust as a black box

### Document register

In it:

- a header is a label unique on the page in place of a sentence
- a bullet holds one idea
- a parallel comparison sits in a table
- a specification sits in key-value pairs
- numbered outline form such as 1.1 appears only where the hierarchy runs three levels deep

Set parallel items in bullets, and a cause or a sequence in a paragraph.
Keep a list to one grammatical class, or write prose.
Hold each of its sections as its own page, glossing a term again where it first lands there.

<!-- rule: writing-prose -->
## writing-prose

For all natural language you write or improve that a person or a model reads, in code too, optimize for prose written under the mandatory `prose` skill: before the first line of a message or reply, a report or summary, a pull request title or body, a commit message, a documentation page or README, a code comment or docstring, an error or log message, a ticket or chat note, a plan, or a prompt or instructions for another agent, load `prose` through the Skill tool once in this context, or read `~/.claude/skills/prose/SKILL.md` in full where the Skill tool is absent, and follow it in every line you write.
