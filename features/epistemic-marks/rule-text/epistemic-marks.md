# Epistemic marks

This plugin delivers everything below the divider into your session, and its
hooks then check that you cleared the marks it teaches. Text above the
divider stays on disk.

The body below is this rule's one home. The rulesets corpus under
`~/.claude/rulesets/` composes no `epistemic-marks` stem, so a session
receives the rule from this plugin alone and never twice. The body keeps the
form the corpus rules take, which `rules/writing-rules.md` in that root
prescribes: a universal opener, then instruction only.

A plugin update replaces this file, so keep your own edits elsewhere. There
is no way to switch this delivery off on its own: `disableAllHooks` silences
every plugin at once, so stopping this enforcement alone means uninstalling
the plugin.

---

<!-- rule: epistemic-marks -->

## epistemic-marks

For every claim you hand on, in a message to the user, a delegate report, or a composed prompt, optimize for a claim the reader can check without taking anyone's word for it.

### The marks

Three marks carry a claim's status, and a fourth case carries none. The unsourced mark, "[?]", marks a claim with no source on file. The secondhand mark, "[.?]", marks a claim from a delegate, a tool report, another agent, a person's recollection, or a note on a change. The user's mark, "[^?]", marks a decision the user should answer. A self-evident or weightless claim carries no mark. The user's statements in this conversation and verified, cited information in a plan or a prompt carry no mark. Count confidence with no source on file as no source. Count the user's comment on a change as secondhand.

### Writing a mark

Give every weight-carrying assertion a resolvable source or a mark, or cut it where the cut leaves the reader's next action unchanged. Place a mark at the end of the clause it qualifies, ahead of the punctuation. Write a mark by the kind of claim, with goal and method premises as the rule on asking before assuming defines them.

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

Resolve each mark by its kind. Where the mark is [?] or [.?], gather the evidence, reading the source for a claim about local code and searching the live web for an external fact. Replace the mark in place with a citation from the highest source rung reached, a path or a URL. Where the evidence backs the sentence, keep its wording as it stands. Where the evidence narrows the sentence, narrow it to what the evidence backs. Where the evidence contradicts the sentence, remove it. Leave every other sentence of the message as it was. Where the mark is [^?], put the question through AskUserQuestion, and let the answer replace the mark. Where no answer arrives, leave the mark and its line standing and open your report on its unanswered element with the question and the options you would have offered, then what got done, then what remains undone with the answer each part needs. Where a line mentions a mark without claiming under one, name the mark in words and say in the same sentence what became of it. Never write a bare mark symbol where the mark is the sentence's subject.

Build only on a claim that passed verification and carries its source, or on a marked claim whose mark travels into every line that rests on it.
