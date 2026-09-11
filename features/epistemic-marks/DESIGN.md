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

This plugin ships the first and none of the second, so the two artifacts sit
on opposite sides of an install boundary and are written by different people.
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
no rule text, so it would have to find the file on disk and parse it. That
requires knowing where somebody else keeps their rule text, which this plugin
cannot know and must not assume, and any path it guessed would break the
moment that text moved.

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

The plugin is the side that ships, which settles the ownership question. Rule
text is written by whoever installs this, so the enforced vocabulary has to be
readable and checkable from here without reaching into anything they own.

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

One constraint governs every generated string. The output is read by an agent
on a machine whose toolset this plugin cannot know, so no generated line names
a tool, and every line phrases the act to perform rather than the call to
make. `tests/test_messages.py` asserts that over the builders' output rather
than the module source, which is what catches a name reintroduced through an
f-string. Matching is exempt: `citations.py` names the tools that open a file
because it is recognizing tool calls, not writing prose.

## What a SubagentStop hook can hand back

Nothing a `SubagentStop` hook returns reaches the parent session. The hook
addresses the delegate; the delegate's own report is what carries an item to
the caller. Injecting context into the caller after a delegate returns would
need a `PostToolUse` hook on the `Agent` tool, which this plugin does not use.

The delegate's relay listing travels as `hookSpecificOutput.additionalContext`
with `hookEventName` set to `"SubagentStop"`, not as a block and not as a
`systemMessage`. A `systemMessage` reaches the user, which is the wrong
reader, and a block would stall a delegate on a question it cannot answer.

`additionalContext` continues the subagent, and it travels the same loop
protections a block does: the `stop_hook_active` input and the harness's cap
of eight consecutive continuations, per
https://code.claude.com/docs/en/hooks. So the relay group is sent on a first
pass and withheld once `stop_hook_active` is set. The first pass is the one
the listing exists for — the delegate rewrites its report with the question
surfaced — and re-sending it every pass is a loop, wasteful for all eight.
`ledger.py` is the wrong instrument for that guard: its dedup record is keyed
by the agent id inside a subagent, and the batch pass writes line fingerprints
to the same file, so a line the batch pass reported mid-turn would silently
suppress the relay notice.

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
