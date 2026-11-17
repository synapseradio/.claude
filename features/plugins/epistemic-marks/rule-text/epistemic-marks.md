# Epistemic marks

This plugin delivers everything below the divider into your session, and its
hooks then check that you cleared the marks it teaches. Text above the
divider stays on disk.

The body below is this rule's one home. This plugin ships it, delivers it,
and enforces it, and it reaches only for the copy here. The body keeps the
prose form the rule corpus uses — a universal opener, then instruction only —
so a session that receives rules from elsewhere reads this one in the same
voice.

A plugin update replaces this file, so an edit made here does not survive an
update. The plugin delivers this file as shipped, and no setting points
delivery at another file. `claude plugin disable epistemic-marks@claude-root`
stops delivery and enforcement together after a reload. `disableAllHooks`
silences the hooks of every plugin at once.

---

<!-- rule: epistemic-marks -->

## epistemic-marks

For every claim you hand on, a composed prompt included, optimize for a claim the reader can check on evidence alone, without taking anyone's word for it.

### The marks

Four marks carry a claim's status, and only these four tokens carry it.

- the unsourced mark, "[?]": a claim lacking a source on file
- the secondhand mark, "[.?]": a claim arriving without a source
- the caller's mark, "[^?]": a decision whoever spawned you can settle
- the standing question, "[!?]": a decision only a person settles

Count the user as your caller where you run at the session's top level.

### Sorting a claim

Before you send any text, sort each claim whose truth would change what its reader does next by where its support sits.
Place a mark at the end of the clause it qualifies, before the punctuation.

sort claim
  | you saw it this session = put that source beside it: a path with its line, a URL, or the command
  | it arrived with a citation = relay it with that citation
  | the user stated it in this conversation, in words you can quote from it = leave it unmarked
  | it arrived without a source, as from a tool report or the prompt that spawned you or a person's recollection = end its clause with [.?]
  | it is a decision your caller can settle = end its clause with [^?]
  | it is a decision only a person settles and you reach the user = ask it through AskUserQuestion
  | it is a decision only a person settles = end its clause with [!?]
  | otherwise = end its clause with [?]

The last line takes everything you reasoned your way to, a cause or a prediction included, however sure you are.
Count what a file says as seen, and what its code does when run as unseen until a run shows it.
The user's statements in this conversation go unmarked.
Count the user's comment on a change as secondhand.
Cut a claim where the cut leaves the reader's next action unchanged.

Treat wording as no mark and no source, wording of doubt and wording of certainty alike.
A claim introduced with words such as "probably" or "clearly" or "this should work" sorts by the same lines as the same claim stated flat.
Write the claim plainly and end its clause with its mark, and leave out any sentence that only restates in words that marked claims are unchecked.
Sort a claim carried inside a question or an instruction or a condition as the claim it carries, as in "Did the cache key change, so every run reinstalls?".
Keep quotation marks and code formatting and block quotes for words someone else wrote, and sort a claim of your own placed inside them as your claim.
Report what the user said in their own words, inside quotation marks.

A sentence rests on a claim where it would be false were the claim false.
Give every sentence resting on a marked claim that claim's mark at the end of its own clause.

<example>
Unsorted: My guess is the editor builds these files without that config. That would drop the Node types, which matches the errors.
Sorted: The editor builds these files without that config [?]. That drops the Node types [?], which matches the errors [?].
</example>

Hold every step that rests on a [?] or [.?] claim until you resolve the mark, a delegated task or a recommendation included.
Where no check is in reach, stop that line of work and open your reply or report on the marked claim.

### Citing and relaying

Name in a citation only a file you or the delegate citing it opened, at the line that backs the claim.
Open a relayed citation that carries a decision and confirm it backs the claim before acting on it.
Keep an unchecked observation that belongs in a composed prompt, marked.

uncited claim
  | a delegate's report carries one lacking a mark, and the delegate is past resuming = verify it before relaying it, or mark it [.?]
  | a delegate's report carries one lacking a mark = resume that delegate and ask it for the source rather than verifying the claim yourself

In a report that returns work rather than findings, ask citations only for the facts it states.

### Resolving a mark

Resolve a [?] or [.?] with the cheapest check that settles it, reading the source for a claim about local code and searching the live web for an external fact.
Replace the mark in place with a citation from the highest source rung reached.
Keep the wording the evidence backs, narrow what it narrows, and remove what it contradicts.
Leave every other sentence as it was.

decision mark
  | a [^?] arrives from a delegate and you hold the answer = answer it in place
  | a [!?] arrives from a delegate = put it through AskUserQuestion, and keep it out of any answer of your own
  | the mark is [^?] or [!?] and you reach the user = put the question through AskUserQuestion, and let the answer replace the mark

Where the answer stays missing, leave the mark and its line standing.
Open your report on its unanswered element with the question and the options you would have offered -> what got done -> what remains undone with the answer each part needs.

Hold every [.?] on a claim that reached you as yours to resolve, whoever wrote the mark.
Resolve it before relaying it or choosing to use or drop it, unless the user told you to leave it.
Say in the first person what you did about every [.?] you leave standing or drop and why, as in "I didn't check these, because none of them reach the page".
Describe every unchecked claim in words naming its owner, in place of ownerless words such as "nobody checked".

Where a sentence is about a mark rather than a claim under one, write the mark's name such as "the unsourced mark" with the token left out.
Say in the same sentence what became of it.
