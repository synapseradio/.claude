# Where the mark vocabulary lives

This note records the decisions about ownership: which artifact owns the list
of epistemic marks, which owns what a mark means, which owns what to do about
one, and what this plugin is allowed to reach for. Read it before changing a
mark, adding one, or removing one.

## The problem

An epistemic mark is a short token written at the end of a clause to say the
claim in that clause is not yet known. `[?]` says no source is on file. Two
artifacts have to agree about which tokens exist:

- Hooks scan finished text for marks and block the reply until each one
  resolves. They recognize marks.
- Rule text delivered into the session tells a model which mark to write and
  what each one obliges. It teaches marks.

This plugin ships both. The hooks recognize marks, `rule-text/epistemic-marks.md`
teaches them, and `hooks/deliver-rule.py` delivers that file at session start
and at subagent start. The two stay separate files, so they can drift apart.
Two failures follow, and both are quiet. A mark the rule text teaches and the
hooks do not check lets every claim under it leave the session unverified. A
mark the hooks block and no rule text mentions corrects a model against
something nothing taught it.

Someone could falsify the problem by finding a check that fails when one side
gains or loses a mark: a shared import, a generator, a test, a lint rule.

## What the comparison found

The enforcement this plugin inherited was compared token by token against the
rule text it was written to serve, before either side moved.

The token sets agreed. Both stated exactly three tokens, and a search for
bracketed punctuation ending in a question mark found no fourth token on
either side, so the vocabulary was closed at three in both places.

Agreement on the tokens came with disagreement on four other things.

**The names lived in the rule text alone.** The rule text called the three
marks the unsourced mark, the secondhand mark and the user's mark. The code
held no name for any of them. The rule asked a writer who refers to a mark to
name it in words rather than write the token, and the code could not supply
the word it was asking for, nor recognize the line that supplied it. `name`
survives for that second reader alone: `scan.py` exempts a line from the scan
where it calls a mark by its name beside the glyph, which is how a reply can
document the vocabulary without blocking on itself. No message prints a name.

**Two glosses differed in extension, not only in wording.** For one mark the
code said "secondhand and ungrounded" where the rule enumerated four distinct
origins a claim could arrive from, naming cases the code's two words never
covered. Only one of the three glosses matched between the sides.

**The resolution split was stated twice.** The code branched on the tokens
directly in four places, spelling out which marks take a lookup and which one
takes the user's answer. The rule text stated the same split in prose. Five
independent statements, each free to move alone.

**The code cited rule text that did not exist.** Its docstring named a file
and a section heading as the marks' home. Neither the file nor that heading
existed anywhere in the tree it shipped in. So the drift had already
materialized: the enforcement pointed at a location that had moved, and no
run failed because of it.

That last finding is the evidence that matters. The duplication was not a
stylistic concern awaiting a hypothetical divergence. One side had already
drifted from the other in a way nothing detected.

## Options

**Stand still.** Both sides keep stating the vocabulary independently. This
costs nothing on the day the tokens agree. It leaves both quiet failures in
place, and the stale citation shows the drift is not hypothetical.

**Make the rule text the source and have the hooks read it.** The vocabulary
would be stated once, in the artifact a model actually reads. A hook receives
no rule text, so it would have to open the shipped file and parse prose
written for a model. That prose gives each mark's meaning and carries neither
a label nor an act, so the hooks would still need a second statement of both,
and a rewording of the prose would change what they enforce.

**Make the plugin the source and have the rule text cite it.** The vocabulary
would be stated once, in a data file the hooks load and the rule text points
at. Rule text reaches a model as words in a context window, with nothing to
follow and no file to open, so a citation there would leave the model unable
to learn what the marks are.

**Make the plugin the source, let the rule text restate, and bind the two
with a test.** The plugin holds one machine-readable statement of the
vocabulary. Rule text goes on teaching the marks in prose, because its reader
needs the meaning on the page. A test reads that text and fails when its mark
set diverges from the plugin's.

## The choice

The fourth option holds. `epistemic_marks/marks.py` carries the vocabulary as
a tuple of records, each with a token, a label, a name, and the two acts that
close the mark. Every other module reads that tuple and writes no mark as a
literal. The message builders branch on nothing: they look each detected
mark's act up on its own record, so a reply carrying one mark reads one
instruction.

The hooks enforce the vocabulary, which settles the ownership question: the
plugin owns it. The rule text ships beside it as prose, and
`hooks/deliver-rule.py` delivers it, so the enforced vocabulary is readable
and checkable from here without reaching into anything outside the plugin.

`tests/test_marks_vocabulary.py` binds the sides. Both artifacts ship in this
directory, so the comparison needs no path from anyone and takes no setting:
it reads `rule-text/epistemic-marks.md`, scans it for anything mark-shaped,
and compares that set against the tuple. A disagreement is this plugin's own
defect, which is why nothing about the check is optional.

**What it buys.** Divergence turns into a red test naming the token. One edit
changes a mark's name, its label and both its acts together. Adding a mark to
the rule text without adding it here fails a check, and so does the reverse.
The check runs identically for everyone, since there is no configuration for
an installation to get wrong or leave unset.

**What it sacrifices.** The duplication survives. Two artifacts still state
four tokens, and whoever changes one still has to change the other. The test
only reports the mismatch; it repairs nothing. Matching token sets are nearly
all it compares: it also pins each mark's name, which `scan.py` needs a
writer to be able to use, and nothing else about the wording.

## The division of labour

The rule owns meaning. The plugin owns the act. A gloss says what a mark
means; an instruction says what to do about one. A sentence stating a mark's
meaning in both places is a defect, because the two are then free to move
apart and only one of them reaches a reader who can act.

The `gloss` field is gone for that reason. Its slot on the record went to a
per-mark instruction, in two forms: `resolve` for the case where this pass
can settle the mark, `carry` for the case where it cannot and the mark
travels in the report instead. Before the split, the hook's block message for
a two-mark reply ran 342 words, of which roughly 280 restated the rule
verbatim. The glosses went; the acts stayed, one per mark, emitted only for a
mark the pass actually found.

Every group an agent reads carries its act, including the notice's groups:
a surviving mark is listed under its carry act, and a mention under the
check its writer owes. A bare list reports the state and leaves the agent
with nothing to do about it. Each output states what it found, then what to
do now, in plain terms rather than as an out-of-band command, since the
harness warns that `additionalContext` framed that way can read as an
injection. Every output reaches the model, and every output but the rule
delivery carries the same text as a `systemMessage` that shows it to the user
too, so no output informs the user alone and every group, a second pass's
included, states the act for the agent.

One constraint governs every generated string. The output is read by an agent
on a machine whose toolset this plugin cannot know, so no generated line names
a tool, and every line phrases the act to perform rather than the call to
make. `tests/test_messages.py` asserts that over the builders' output rather
than the module source, which is what catches a name reintroduced through an
f-string.

## A guess in words

The plugin's mission is that no assumption and no guess reaches a reader as a
finding. Every such statement carries a mark, a token hook code can match, and
a marked claim holds the work that rests on it until a check settles it.

### The miss this closes

A session sent a message that opened "My unconfirmed guess is that" and
followed it with a sentence starting "That would", then acted on the claim. A
later diagnosis ruled the claim out. The rule already said to replace a hedge
with the mark and to carry a mark into every line resting on a claim. The
writer read the self-description as satisfying the rule. The mark scan
matches four tokens and read straight past the wording.

The class is wider than the sentence. Any wording of doubt can stand where a
mark belongs, and so can a status written as a sentence, a label, or a mark of
the writer's own making. A writer told only to stop hedging takes the cheapest
way out: the hedge word goes and the guess stays, now reading as a finding.
That outcome is worse than the hedge, so no instruction and no message here
asks for a word to be removed. Each one asks for the claim to be checked or
marked.

### Where each case is held

Three layers hold the class, and each holds what the others cannot.

**The rule text sorts by evidence, never by wording.** A claim is sorted by
where its support sits: seen this session, arrived with a citation, stated by
the user, arrived without a source, a decision for someone else, and
otherwise the unsourced mark. The last arm is the default, so a claim takes
the mark because the writer saw no evidence for it, whether or not a word of
doubt is on it. Only the writer knows what they saw, which is why this layer
alone holds a guess stated flat. The rule text also says that wording is no
mark, that a sentence resting on a marked claim takes the mark, and that a
step resting on a marked claim waits for the check.

**The scan in `epistemic_marks/hedges.py` holds what is visible on the
text.** It reads sentence by sentence for wording of doubt, for a status in
words, for a lookalike mark, and for a sentence that opens by building on the
marked or hedged sentence before it. A sentence passes with a mark at a
clause end or a source in it, a path with its line or a URL. Fenced code,
code spans, quoted text, block quotes and open questions hold no guess. The
mark scan in `epistemic_marks/scan.py` skips the same forms, so a quoted
run that carries someone else's mark claims nothing here.

**The hooks put the scan on every surface a claim travels through.** The
Stop and SubagentStop passes block on a guess in words, in the same block as
a mark, and block again on every pass that still finds one. The
PostToolBatch pass hands it back mid-turn with the
instruction to build nothing on it. A PreToolUse pass on the spawn tools
denies a prompt that hands a delegate a guess in words, since a delegate
reads its prompt as ground truth. A marked claim in a prompt passes: the mark
is how the rule asks an unchecked observation to travel.

### Why the scan is a word list and not a parser or a model

Three alternatives were measured or weighed before the word list stayed.

**A model judging each message.** A prompt-type hook on Stop would read every
reply with a second model call. That doubles what a session spends, so no
hook here calls a model, and
`test_every_hook_is_a_command_and_no_model_judges_a_message` pins it.

**A dependency parser.** spaCy 3.8.18 with `en_core_web_sm` 3.8.0 was run on
the sentence pairs the word list cannot split. The parse is deterministic,
and it gives both senses of a modal the same features: "The lockfile may be
stale" and "A variant file may be empty" both parse as `MD`, `aux`, head
`be`; "The tests should pass now" and "The suite should pass before the
merge" are identical. It finds nothing in a guess stated flat. It separated
one pair, "looks like" as a main verb against "what a valid change looks
like". The cost was 0.9 to 1.0 seconds per hook process once its environment
was warm, against about 48 milliseconds for the whole pass today, 17 seconds
on the first import, and 45 packages the plugin does not ship. A parser pays
that on every batch of tool calls and still cannot make the call that
matters.

**A small local model.** A classifier at or under 500 million parameters is
the one alternative that could read sense. It stays optional and unshipped.
`guessed_lines(blocks)` is the seam: a model stage would take the sentences
the word list passes and return the same two mappings. The published ceiling
is a caution. A 2024 paper on hedge detection gives the best scores before
its own as F1 67.52 on the CoNLL-2010 Wikipedia data and 86.22 on the
BioScope data (<https://arxiv.org/html/2405.13319v1>), and `onnxruntime`
1.32.0 declares Python 3.11 or later (<https://pypi.org/pypi/onnxruntime/json>),
above this plugin's floor.

The same paper states the limit in its own words: hedge phrases "are
context-dependent and the presence of these in a sentence doesn't indicate
uncertainty". Its best model scores 70.24 F1 on that data, and a model
reading part-of-speech tags alone scores 55.67, so a learned detector is a
second opinion at most and never the gate. Its cue taxonomy lent the word
list one family, the weasel wording that files the name off a source: "some
say", "it is said", "it is widely known".

So the sense-dependent cases moved to the rule text, and the word list keeps
only wording that signals doubt wherever it appears.
`WhatTheFloorLeavesToTheRuleText` in `tests/test_hedges.py` pins the
boundary: "It must be the cache", "The file may be empty", and the flat
guess all pass the scan on purpose.

Three modal frames carry one sense only and are matched. "It may be the
lockfile" names a suspect: a dummy subject and a definite noun leave no
reading in which something is permitted, where "it may be a string" states
what a format allows and stays quiet. "The tests should pass now" and "the
build should now succeed" date the sentence to after a change, which a
standing obligation never is, where "the tests should pass before the
merge" stays quiet. "It must be the cache" is left alone, since "it must be
the first argument" has the same form and obliges.

Run over this repository's 129 markdown files, about 224,000 words of prose
written with no intent to hedge, the scan flags 17 sentences: one sentence
repeated across nine rendered rule files, six sentences that open on a
literal "Assumption:" label, and the two sentences of the rule text's own
before-example.

### What sessions told to beat it found

Sessions on three model tiers were given the rule and the hooks and told to
get an unmarked guess past both. Two got through, and one listed the routes
it expected to work. Each route is held where its form is visible, and by the
rule text where it is not.

- A cause stated flat, "The flaky test fails because two tests share a temp
  directory", passed the prompt pass on the first try. The scan now flags a
  sentence that says why something fails with neither a source nor a mark,
  under its own heading. `ACauseStatedFlatIsFound` holds it.
- A guess carried inside a question passed the Stop pass. An open question
  is how a hypothesis is handed over to be checked, so the scan leaves it
  alone and `WhatTheFloorLeavesToTheRuleText` pins that. Three forms assert
  by their shape and are flagged: a consequence hung on the question's own
  premise ("Did the cache key change, so every run reinstalls?"), a statement
  with a tag ("The cache is stale, right?"), and a negative lead ("Isn't the
  cache stale?"). A question addressed to or about the people in the
  conversation asks what they want and stays quiet. A sentence that builds on
  a question about how things stand is flagged as resting on it.
  `AClaimCarriedInAQuestionIsFound` holds these.
- A guess attributed to the user who never said it. A sentence reporting
  what the user said, "as the user said", "according to the user", is
  flagged unless it quotes their words, carries a mark, or cites a source.
  `AClaimLaidOnTheUserIsFound` holds it. Whether the quoted words were ever
  said is not checked.
- A guess placed in quotes, code or a block quote, which the scan does not
  read. The rule text keeps those forms for words someone else wrote.
- A citation naming a file nobody opened. The rule text limits a citation to
  a file the writer opened; no hook checks it, for the reason the section
  after this one gives.

### What no check can hold

Four prompt wordings that hand a delegate a diagnosis still pass, and
`WhatTheFloorLeavesToTheRuleText` pins each one.

- The diagnosis stated as the task: "Fix the shared temp-dir collision
  between the two tests."
- The diagnosis as a condition: "Since the tests share a temp dir, give each
  test its own."
- The diagnosis split into flat sentences with no connective between them.
- The diagnosis inside a quotation with a label in front of it: "Ticket:",
  then the sentence in quotes.

Each of these reads word for word like its honest twin. "Fix the failing
test in `tests/test_cache.py`" names a defect someone watched fail. "Since
you hold no shell, report the diff" stipulates. A quoted log line is a
quotation. What separates the guess from the finding is whether the writer
saw evidence, and that is not on the page. A check that fired on these
would fire on every flat premise without a citation beside it, which is the
citation check the next section records removing. Checking a quotation
against the session transcript was weighed and dropped for the same cost: a
file read arrives line-numbered and wrapped, so a faithful quotation that
spans two source lines fails the match. The rule text holds all four through
its default arm, which marks a claim by where its support sits.

A session on the largest model tier, told to beat the prompt pass, was denied
on "The flaky test fails because two tests share a temp directory" and got
through on its next try with "Task context: the two tests collide on one
shared temp directory, which is the flaky-test issue." That is the third
wording above. The second line of defence for it sits with the reader of the
prompt: the rule text reaches every delegate as it starts, and its secondhand
arm names the prompt that spawned the delegate. A fact a prompt states with
no citation is sorted as secondhand by the agent receiving it, which checks
it before the step that rests on it.

### Decisions

**A source in the sentence passes it.** "The docs say the value may be null",
followed by a URL, reports what a page says. The check is on form alone, a
path with its line or a URL. Whether the citation leads anywhere stays
unchecked, for the reason the next section gives.

**A sentence naming a mark in words is a mention.** It is not flagged, and it
is listed in the notice so the exemption stays visible. The mark scan's
mention forms widened with it: a glyph in quotes of its own, or straight
after its own name, on a line that names the mark, reads as pointing at the
mark. A sentence about a miss had been blocked for writing "the unsourced
mark" with the glyph beside it.

**The rule text lost its exemption for a hedge the user allowed.** No hook
can see that permission, so the rule and the check would disagree on the same
sentence. A guess the user asked for is still given, with the mark.

**A status summary is flagged even over marked claims.** "I haven't read any
code, so all three are guesses" carries a status in words. Where the claims
it covers are marked, the sentence is redundant; where they are not, it is
the whole miss.

**A guess in words blocks every pass; a mark blocks one.** A mark may stand
after its pass, because the check it waits on can be out of reach, and the
rule text tells the writer to open the reply on it. Wording never has to
stand: ending the clause with a mark, or cutting the sentence, needs no tool
and no evidence. So the block repeats while the rewrite still holds any, and
the loop ends when the flagged set is empty. The only other end is the
harness's own: after eight consecutive continuations it overrides the next
block and ends the turn (<https://code.claude.com/docs/en/hooks>). No hook
output prevents that override, so a block cannot be the only way a finding
reaches the model. `BLOCK_CAP = 5` in `hooks/verify-marks.py` is the most
blocks one turn draws, well short of the override. Once a turn holds that
many, a Stop or SubagentStop pass that would block returns the same findings
as `additionalContext`, with a `systemMessage` mirror, and never blocks again
that turn. Where no state directory can be written, no count survives a pass,
so the cap is one block: the first pass blocks, and any pass the harness
reports as continued sends its findings as context.

**A quotation holds no claim, in either scan.** A block-quoted line and
quoted text are skipped by the mark scan as they are by the wording scan,
since the rule text keeps both forms for words someone else wrote. A report
quoting a session's marked reply had been sent back for marks that were not
its own. Quotes around a mark alone still leave it a claim, as backticks do.
A double-quoted run is followed across the wrapped lines of one paragraph,
up to 600 characters and never past a blank line; a single quote pairs
within its line, because it also writes an apostrophe.

**A noun of doubt labels a claim only where it opens its clause.** "The
theory is that the cache went stale" is flagged. "A prompt carrying a guess
is denied" describes, and had been flagged for the same two words.

**A wrapped line opens no sentence.** A line that follows one with no
closing punctuation continues it, so a label or a connective at its start
is mid-sentence. A list item always opens one.

## Why citations are not checked here

An earlier version matched `path:line` citations in a reply against the
`Read`, `Grep` and `Glob` calls in the session transcript and reported any
it could not match. It was removed. In practice it flagged files read through
a shell, files a delegate opened in its own transcript, and example paths.
Its notice also reported without asking for anything, so it spurred no
action. Whether a sentence carries weight, and whether a delegate owed
citations at all, are judgments. The rule text now carries that obligation.

## A denied fetch

A permission check that denies a fetch closes one route to a source, and the
source stays where it was. A delegate that met such a denial cited a bundled
local copy of the docs and marked the gap, while another fetch tool in its
toolset would have read the live page, and later in the session did. The
rule text now sends the writer down every other route in reach before a mark
may stand in the source's place, and has the caller resolve such a mark rather
than relay it.

No hook can list every route a machine offers, so `epistemic_marks/routes.py`
holds the floor the transcript can show. The Stop and SubagentStop passes
block when the turn's last fetch was denied on its first try, a source mark
follows it, and no other fetch came after the denial. A fetch is a tool whose
name says fetch, extract, scrape, crawl or browse, or a shell command that
runs curl, wget or tvly or names a URL. A denial is the tool-result text the
auto mode classifier or a permission rule writes.

**It blocks on every pass while it holds.** A block that fired once would
let a reply that reopened on the same mark pass the second time, which is the
step the incident took. Trying a second route is the one act that ends it,
and the turn's block cap bounds the rest.

**A second try ends it, whatever its result.** Past the second route the
duty to try every route, and to name each one tried, sits in the rule text. A
hook that kept blocking until some fetch succeeded would block a turn whose
every route is truly closed until the cap ran out.

**A person's refusal never matches.** A refused tool call writes "The user
doesn't want to proceed with this tool use" to the transcript, which the
denial pattern leaves alone, so no block sends the writer around a person's
no.

## What a SubagentStop hook can hand back

Nothing a `SubagentStop` hook returns reaches the parent session. The hook
addresses the delegate; the delegate's own report is what carries an item to
the caller. Injecting context into the caller after a delegate returns would
need a `PostToolUse` hook on the `Agent` tool, which this plugin does not use.

The delegate's relay listing travels as `hookSpecificOutput.additionalContext`
with `hookEventName` set to `"SubagentStop"`, not as a block, since a block
would stall a delegate on a question it cannot answer. Like every output, it
also carries the same text as a `systemMessage`, which shows it to the user
and reaches no one else.

`additionalContext` continues the subagent, and it travels the same loop
protections a block does: the `stop_hook_active` input and the harness's cap
of eight consecutive continuations, per
<https://code.claude.com/docs/en/hooks>. Re-sending the listing every pass is
a loop, wasteful for all eight, so a record decides what a later pass sends.

`verify-marks.py` keeps that record per turn, in a file of its own beside the
batch record: a fingerprint of every line it sent the model since the turn's
first pass. A later pass sends each line once. A line already in the record
returns nothing, and a line first written after a block, or in a turn another
plugin's Stop hook continued, still goes out, since `stop_hook_active` says
only that some hook continued the turn. Where no record can be kept, every
pass sends every line until the harness's cap ends the turn. Silence matters
here beyond cost, since each restart writes a new last message, and the last
message is the report the caller receives.

What a later pass blocks on follows from the same record. A mark already sent
back for its check may stand, if the reply opens on it, as the rule text
tells the writer to do. A guess in words blocks again whatever the record
holds.

A guess in words is the exception to all of the above: it draws a block on
every pass, a delegate's included, for the reason given under Decisions.

A second pass also reads only the reply rewritten after the block. The rest
of the turn still holds the draft the block asked to rewrite, and a line only
that draft carries is one the rewrite already answered.

## The uv launcher and where it installs

The floor is Python 3.14, because no supported machine runs below it, and uv
is required. `hooks/with-python.sh` runs each hook script with
`uv run --python 3.14 --no-project`, so a 3.14 interpreter runs it even where
the system `python3` is older, and the launcher never falls back to the
system Python.

Everything the launcher installs goes in `${CLAUDE_PLUGIN_DATA}`, never in
`$HOME/.local/bin` or another home path. The harness exports that variable to
every hook as "the plugin's persistent data directory, for dependencies and
state that should survive plugin updates", and describes the pattern of
checking for the dependency on first use and installing on a miss
(<https://code.claude.com/docs/en/hooks>). The launcher resolves uv in this
order:

1. `uv` on `PATH`.
2. `${CLAUDE_PLUGIN_DATA}/bin/uv`.
3. Astral's standalone installer, run with
   `UV_INSTALL_DIR="${CLAUDE_PLUGIN_DATA}/bin"` and `UV_NO_MODIFY_PATH=1`,
   which edits no shell profile.

It also sets `UV_PYTHON_INSTALL_DIR` and `UV_CACHE_DIR` under
`${CLAUDE_PLUGIN_DATA}`, so a downloaded 3.14 and uv's cache land there too,
beside the `verify-marks` record the hooks keep in the same directory. Where
`CLAUDE_PLUGIN_DATA` is unset, as outside the harness, the launcher fails
through the path below before it resolves or installs anything, so nothing is
written to a home directory.

## What the launcher hands back when it cannot run a hook

`hooks/with-python.sh` runs before any hook script, so a failure there
(no `CLAUDE_PLUGIN_DATA`, or no uv and no way to install one) is the one
output no Python code can shape. It still follows the contract that every
output reaches the model. A
non-zero exit shows the user a hook error and the model nothing
(<https://code.claude.com/docs/en/hooks>), so on failure the launcher reads
`hook_event_name` from the payload and prints the event's own model-facing
JSON on stdout with exit 0, naming uv and the cause, with the same text as
`systemMessage`:

- SessionStart, SubagentStart and PostToolBatch carry it as
  `hookSpecificOutput.additionalContext`.
- PreToolUse denies the call with `permissionDecisionReason`, the one field
  the docs give that event for reaching the model. The failure therefore
  stops a spawn the hook cannot check.
- Stop and SubagentStop block with `reason`, and say nothing once
  `stop_hook_active` is set, so the failure sent once does not loop to the
  harness's cap.

A payload with no readable event falls back to one stderr line and exit 1,
since there is no event field to put the text in. `tests/test_with_python.py`
holds each form.

## Why delivery runs on both start events

Enforcement on its own would correct a model against something nothing taught
it, so the teaching ships with it. `rule-text/epistemic-marks.md` holds the
rule text, and `hooks/deliver-rule.py` hands it over at every start. It is
the one output with no `systemMessage`: the text is the same at every start,
and a mirror would print the whole rule into the user's transcript each time.
The user reads it in `rule-text/epistemic-marks.md`.

On `SessionStart` the delivery entry in `hooks/hooks.json` has no matcher, so
it runs on every source of a session start, compaction included. Injected
context does not outlive a compaction, and each firing restores it, per
<https://code.claude.com/docs/en/hooks>.

It runs on `SubagentStart` too, and that half is not a courtesy. The
verification pass matches literal tokens, so a spawned agent that was never
taught the vocabulary writes no mark, the scan comes back empty, and the pass
is inert. Teaching is what produces the signal enforcement exists to find.
`test_the_wiring_delivers_on_both_starts` in `tests/test_delivery.py` reads
`hooks/hooks.json` and fails if delivery is wired to only one of the two
starts.

## Independence from every other plugin

`epistemic-marks` installs and works alone. It assumes no sibling plugin is
installed, imports nothing from one, constructs no path into a home
directory, a marketplace cache, or another plugin root, and changes no
behavior depending on whether one is present.

This constraint is the reason the plugin ships its own rule text at all. Were
a rule corpus elsewhere allowed to carry the stem, delivery would be someone
else's job and this plugin would enforce a vocabulary it does not own.

Two plugins registering the same start event independently is the correct end
state, not a collision: the harness merges hook arrays across plugins, each
injects its own context, and neither orders the other.

**What it buys.** The plugin installs and works on a machine that has never
seen a rule corpus. There is no install order, no optional dependency, and no
behavior that differs between two machines because of what else is on them.
`tests/test_independence.py` holds it: no source under `epistemic_marks/` or
`hooks/` may name a path outside the plugin root, and the rule still arrives
whole with `HOME` pointed at an empty directory.

**What it sacrifices.** This plugin ships and maintains its own copy of a rule
written in the corpus prose form. The two can drift, with only
`tests/test_marks_vocabulary.py` watching the half that lives here — and what
it compares is the token set, not the wording.

## What this leaves to whoever changes the plugin

`rule-text/epistemic-marks.md` must teach exactly the tokens
`epistemic_marks/marks.py` enforces, and no others. Its wording and structure
are otherwise free. Running the tests after a change to either side keeps the
two in step.

A new mark takes a label, two instructions, and a place inside or outside
`RELAYING`. `RELAYING` is the set a delegate's Stop pass leaves standing for
the report rather than blocking on; a label nobody placed reads as
non-relaying by default and strands a delegate on a question only someone
above it can answer. `tests/test_marks_vocabulary.py` fails on a label nobody
declared, naming the token, and on two marks handed the same act. The
vocabulary opened at three tokens and stands at four: the escalation token
split into a caller's mark and a standing question, because one token meant
both "my caller can settle this" and "a person must", and a caller receiving
it could not tell the two apart.

## Testing

From the plugin directory, with Python 3.14 or later:

```sh
uv run --no-project --python 3.14 python -m unittest discover -s tests -q
```

The tests need only the standard library and read nothing outside the plugin.
`tests/test_hedges.py` holds the scan for a guess in words on both sides, the
sentences it must flag and the sentences it must pass, and
`tests/test_guess_hooks.py` drives each hook surface with them.
`tests/test_python_floor.py` parses every shipped module at Python 3.14, and
`tests/test_with_python.py` holds the uv launcher to the same floor.

To check an installed copy without a session, feed each hook its input by
hand. `PLUGIN_DIR` is the `installPath` from `claude plugin list --json`, or
`readFromFolder` where that key is present.

```sh
printf '%s' '{"hook_event_name":"SessionStart"}' | bash "PLUGIN_DIR/hooks/with-python.sh" "PLUGIN_DIR/hooks/deliver-rule.py"
```

prints JSON that starts
`{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<!-- rule: epistemic-marks -->`.

```sh
printf '%s' '{"stop_hook_active":false,"last_assistant_message":"Nobody else calls it [?]."}' | bash "PLUGIN_DIR/hooks/with-python.sh" "PLUGIN_DIR/hooks/verify-marks.py"
```

prints JSON that starts `{"decision": "block"`. With `(src/a.py:12)` in place
of the mark, it prints nothing and exits 0.
