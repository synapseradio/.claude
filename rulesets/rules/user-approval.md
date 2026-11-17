## user-approval

For every act that deletes or removes or exposes or publishes or defers a fix, optimize for an act the user approved before it ran.

approve act
  | deleting data a newer verified source disproves = back it up under a name no generator glob matches such as `backup-<file>.before-<item>-removal.json` -> delete it unasked -> rerun its generator -> confirm the stale output is gone
  | deleting a run log, a trace dump, or a discarded draft in the scratchpad = delete it unasked with `trash <path>`
  | deleting other data = only on the user's confirmation
  | removing existing functionality = only on the user's explicit approval, asked for where it is missing
  | reading a file that may hold secrets, credentials, or backups = only on explicit instruction
  | acting for the user on an external platform, edits to your own content included = only after showing the exact content and getting explicit approval
  | deferring a fix for a break = only on the user's explicit authorization

Count a pull request's exact content as its title and description, and a push's as its command.
Count a plan's approval as approval of each act on an external platform whose exact content the plan's own text held when approved, and as no ground for content changed since.
