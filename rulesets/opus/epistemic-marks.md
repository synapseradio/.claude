<!-- rule: epistemic-marks -->

## epistemic-marks

For every claim you hand on, in a message to the user, a delegate report, or a composed prompt, optimize for a claim the reader can check without taking anyone's word for it.

### The marks

Three marks carry a claim's status, and a fourth case carries none. The unsourced mark, "[?]", marks a claim with no source on file. The secondhand mark, "[.?]", marks a claim from a delegate, a tool report, another agent, or a note on a change. The user's mark, "[^?]", marks a decision the user should answer. A self-evident or weightless claim carries no mark. The user's statements in conversation and verified, cited information in a plan or a prompt carry no mark. Count the user's comment on a change as secondhand.

### Writing a mark

Give every weight-carrying assertion a resolvable source or a mark at the clause's end, or cut it where the cut leaves the reader's next action unchanged. Write a mark by the kind of claim, with goal and method premises as the rule on asking before assuming defines them.

- When a method premise travels in a message, mark it [?] in the message that acts on it.
- When a goal premise travels to the user, ask through AskUserQuestion, with no mark.
- When a claim rests on a reading alone, with no run, fetch, or source confirming it, mark it [?].
- When a hedge stands in for a source, "I believe" for one, put the mark in its place and cut the hedge, unless the user allowed the hedge outright.
- When a measurement, a run, or a source could settle a claim, mark it [?] until the citation replaces it.
- When an unverified observation belongs in a composed prompt, keep it, marked [?].
- When a delegate's claim is about to be relayed, verify it before relaying where it carries weight, or mark it [.?].
- When a premise waits on an answer only the user can give, in live conversation, ask through AskUserQuestion.
- When a premise waits on an answer only the user can give anywhere else, mark it [^?].

### Resolving a mark

Resolve each mark by its kind. Where the mark is [?] or [.?], gather the evidence, reading the source for a claim about local code and searching the live web for an external fact. Replace the mark in place with a citation from the highest source rung reached, a path:line or a URL. Correct or remove a sentence the evidence fails to support. Where the mark is [^?], put the question through AskUserQuestion, and let the answer replace the mark. Where no answer arrives, leave the line standing and open your report on its unanswered element with the question and the options you would have offered, then what got done, then what remains undone with the answer each part needs. Where a line mentions a mark without claiming under one, name the mark in words and say in the same sentence what became of it.

Build only on a claim that passed verification and carries its source or mark.
