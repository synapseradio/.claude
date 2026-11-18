# Check your rules before they are delivered

At the end of this tutorial, Claude has checked every rule file and the config in one pass, shown
you a finding, and cleared it. One check reports every mistake at once, so you fix them before
any agent works from a broken instruction. You ask Claude for each step.

## Before you start

- The rule `voice` and the config from [Write your first rule](write-your-first-rule.md).

## Find a rule that reaches no one

1. Ask for a rule without saying who receives it:

   ```text
   Write a rule file named review-checklist that says "Check every changed line against
   the spec before approving." Leave the config as it is for now.
   ```

   Claude writes `rules/review-checklist.md` and reports the file. The config still holds:

   ```yaml
   models: haiku sonnet opus
   defaults: voice
   ```

2. Ask for the check:

   ```text
   Check my rules.
   ```

   Claude reports one warning, on `rules/review-checklist.md`: the rule is never included, since
   no list in the config names it. A rule file reaches a session or agent only through the
   config.

3. Ask Claude to clear it:

   ```text
   Give review-checklist to the critic agent, then check again.
   ```

   Claude adds the block and reports a check with no errors and no warnings.

## Read errors and warnings apart

| Finding | What the plugin does | Example |
| --- | --- | --- |
| a warning | delivers as usual | a rule that no list includes, a rule whose text names another rule |
| an error | holds the affected rule or block back, and says so at session start | a version of a rule with no default wording, a name in the config that nothing declares |

Each finding names its file and line. Ask "clear the check errors" and Claude works through them,
asking you where a fix is a choice, such as whether to include an unused rule or remove it.

## What you have now

A check to ask for after any edit, and before you rely on a new rule.

## Related

- [See what an agent received, and why](see-what-an-agent-received.md): confirm what a running
  session got.
- [Commands](commands.md): reference for every error and warning the check reports.
