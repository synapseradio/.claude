<!-- rule: user-out-of-artifacts -->

## user-out-of-artifacts

For every artifact, a file on disk, a commit message, a code comment, a doc, a spec, a plan, a report, or anything a delegate writes, optimize for an artifact that states each decision as the decision itself, with every trace of who asked for it left out.

Keep the user out of every artifact. Keep "the user", "per request", "as decided", and every phrase that attributes a decision or a direction to a person out of every artifact. State the decision, and its technical reason where the unit needs one.

Keep the user's name out of every artifact and every message.

Before a commit or a write lands, read its text for any reference to the user and rewrite that sentence around the decision. Where a prompt you compose asks a delegate to write an artifact, carry this rule into the prompt.

Hold a person who uses the product, the operator of a CLI for one, as outside this rule.
