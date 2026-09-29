<!-- rule: user-out-of-artifacts -->

## user-out-of-artifacts

For every artifact, a file on disk, a commit message, a code comment, a doc, a spec, a plan, a report, or anything a delegate writes, optimize for an artifact that states each decision as the decision itself, with no trace of who asked for it.

Keep the user out of every artifact. Write no "the user", no "per request", no "as decided", and no phrase that attributes a decision or a direction to a person. State the decision, and its technical reason where the unit needs one.

Never write the user's name, in an artifact or in a message.

Before a commit or a write lands, read its text for any reference to the user and rewrite that sentence around the decision. Where a prompt you compose asks a delegate to write an artifact, carry this rule into the prompt.

Hold a person who uses the product, the operator of a CLI for one, as outside this rule.
