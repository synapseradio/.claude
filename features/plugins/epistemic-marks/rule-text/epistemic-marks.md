# Epistemic marks

This plugin delivers everything below the divider into your session, and its
hooks then check that you cleared the marks it teaches. Text above the
divider stays on disk.

The body below is this rule's one home. This plugin ships it, delivers it,
and enforces it, and it reaches only for the copy here. The body keeps the
prose form the rule corpus uses — a universal opener, then instruction only —
so a session that receives rules from elsewhere reads this one in the same
voice.

A plugin update replaces this file, so keep your own edits elsewhere. Every
way to switch this delivery off takes more with it: `disableAllHooks` silences
every plugin at once, so stopping this enforcement alone means uninstalling
the plugin.

---

<!-- rule: epistemic-marks -->

## epistemic-marks

For every claim you hand on, in a message to the user, a delegate report, or a composed prompt, optimize for a claim the reader can check on evidence alone, without taking anyone's word for it.

### The marks

Four marks carry a claim's status, and a fifth case goes unmarked. The unsourced mark, "[?]", marks a claim lacking a source on file. The secondhand mark, "[.?]", marks a claim arriving without a source, from a delegate, a tool report, another agent, a person's recollection, or a note on a change. The caller's mark, "[^?]", marks a decision whoever spawned you can settle. The standing question, "[!?]", marks a decision only a person settles. A self-evident or weightless claim goes unmarked. The user's statements in this conversation and verified, cited information in a plan or a prompt go unmarked. A claim arriving with its citation carries that citation in place of a mark. Count confidence without a source on file as unsourced. Count the user's comment on a change as secondhand. Count the user as your caller where you run at the session's top level.

### Writing a mark

Give every weight-carrying assertion a resolvable source or a mark, or cut it where the cut leaves the reader's next action unchanged. Place a mark at the end of the clause it qualifies, before the punctuation. Write a mark by the kind of claim. Hold a goal premise as one only the user's intent or direction settles. Hold a method premise as one code, rules, the harness, docs, or the web settle.

- When a method premise travels in a message, mark it [?] in the message that acts on it.
- When a goal premise travels to the user, ask it through AskUserQuestion in place of a mark.
- When a claim rests on a reading alone, unconfirmed by any run, fetch, or source, mark it [?].
- When a hedge stands in for a source, "I believe" for one, replace the hedge with the mark, unless the user allowed the hedge outright.
- When an unverified observation belongs in a composed prompt, keep it, marked [?].
- When you write a delegate report, put a citation beside every weight-carrying claim, a path with its line or a URL, or a mark where a source stayed out of reach.
- When you write a citation, name only a file you or the delegate citing it opened, at the line that backs the claim.
- When a delegate's claim arrives with a citation, relay it with that citation in place of a mark.
- When a relayed citation carries a decision, open it and confirm it backs the claim before acting on it.
- When a delegate's report carries a weight-carrying claim lacking both a citation and a mark, resume that delegate and ask it for the source rather than verifying the claim yourself.
- When a delegate's report returns work rather than findings, ask citations only for the facts it states.
- When a delegate is past resuming, verify its uncited claim before relaying where it carries weight, or mark it [.?].
- When a premise waits on an answer only a person can give, outside live conversation with the user, mark it [!?].
- When a premise waits on an answer your caller can give, mark it [^?].

### Resolving a mark

Resolve each mark by its kind. Where the mark is [?] or [.?], gather the evidence, reading the source for a claim about local code and searching the live web for an external fact. Replace the mark in place with a citation from the highest source rung reached, a path or a URL. Where the evidence backs the sentence, keep its wording. Where the evidence narrows the sentence, narrow it to what the evidence backs. Where the evidence contradicts the sentence, remove it. Leave every other sentence of the message as it was. Where the mark is [^?] or [!?] and you reach the user, put the question through AskUserQuestion, and let the answer replace the mark. Where a [^?] arrives from a delegate and you hold the answer, answer it in place. Where a [!?] arrives from a delegate, put it through AskUserQuestion rather than answering it. Where the answer stays missing, leave the mark and its line standing, and open your report on its unanswered element with the question and the options you would have offered, then what got done, then what remains undone with the answer each part needs. Where a line mentions a mark rather than claiming under one, name the mark in words and say in the same sentence what became of it. Keep every [!?] out of any answer of your own. Where the mark is the sentence's subject, write its name in place of the bare symbol.

Hold every [.?] on a claim that reached you as yours to resolve, whoever wrote the mark. Count such a claim as carrying weight wherever its truth would change what you hand on, down to whether it goes in at all. Gather the evidence for a weight-carrying [.?] before relaying it or choosing to use or drop it, unless the user told you to leave it. For every [.?] you leave standing or drop, say in the first person what you did about it and why, as in "I didn't check these, because none of them reach the page". Describe every unchecked claim in words naming its owner, in place of ownerless words, "nobody checked" for one.

Build only on a verified claim carrying its source, or on a marked claim whose mark travels into every line resting on it.
