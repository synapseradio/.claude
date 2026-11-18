# Edit everything one agent receives in one document

At the end of this tutorial, you have read everything one agent receives as a single document,
edited one part of it, and seen the edit land in that rule's own file. Use this to read an
agent's instructions the way the agent meets them, top to bottom. You ask Claude for each step.

## Before you start

- The rule `review-checklist` for the `critic` agent, from
  [Send a rule to one agent](send-a-rule-to-one-agent.md).

## Edit the document, then send the edit home

1. Ask for the document:

   ```text
   Show me everything the critic receives so I can edit it in one place.
   ```

   Claude writes one file and tells you where it is. It holds each rule the critic receives, in
   name order, each under a line that names it:

   ```text
   <!-- rule: review-checklist -->
   Check every changed line against the spec before approving.

   <!-- rule: voice -->
   Answer in plain words, point first.
   ```

2. Edit the text under one of the marker lines, in your editor or by asking Claude, and leave
   the marker lines as they are. For example, change the checklist to end "before you approve."

3. Ask Claude to send the edit home:

   ```text
   Write my edits in that document back to the rules.
   ```

   Claude reports each rule file it wrote, here `rules/review-checklist.md` alone. A section you
   left as it was changes no file.

4. Ask what the critic receives now:

   ```text
   Show me what the critic receives now.
   ```

   The document shows the new checklist text. Every other agent that receives the rule gets the
   same new text, since the rule lives in one file.

## What you have now

A way to edit one agent's instructions as a whole while each rule stays in its own file.

## Related

- [See what an agent received, and why](see-what-an-agent-received.md): check what a running
  agent got against this document.
- [Measure what your rules cost](measure-what-rules-cost.md): see what an edit adds to each
  agent's context.
- [Commands](commands.md): reference for the render and split steps Claude runs here.
