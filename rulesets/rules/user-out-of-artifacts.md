## user-out-of-artifacts

For every artifact and message and command, anything a delegate writes included, optimize for text that states each decision as the decision itself with every trace of who asked for it left out.

Keep every phrase attributing a decision or a direction to a person out of every artifact, "per request" for one.
State the decision, and its technical reason where the unit needs one.
Keep the user's name out of every artifact and every message.
Keep every account name out of every path you write, in code no shell runs included.
Before a commit or a write lands, read its text for any reference to the user -> rewrite that sentence around the decision.
Hold a person who uses the product, such as the operator of a CLI, as outside this rule.

home path
  | in text a shell runs, a Bash call or a shell script's code = write it as `"$HOME/..."`
  | in text a person or a model reads, a code comment included = write it with a leading `~`

prompt
  | one you compose asks a delegate to write an artifact = carry this rule into it
