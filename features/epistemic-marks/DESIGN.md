# Where the mark vocabulary lives

This note records one decision: which artifact owns the list of epistemic
marks, and how the other artifact reaches it. Read it before changing a mark,
adding one, or removing one.

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
held no name for any of them, so a block message showed a reader the token
and a short gloss where the rule had taught a name. The rule also asked a
writer who refers to a mark to name it in words rather than write the token,
and the code could not supply the word it was asking for.

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

The fourth option holds. `epistemic_marks/marks.py` carries the vocabulary as a tuple of
records, each with a token, a name, a gloss and a resolution class. Every
other module reads that tuple and writes no mark as a literal, so the message
builders branch on how a mark resolves rather than respelling which tokens
verify. The tokens inside the instruction prose come from the same tuple.

The plugin is the side that ships, which settles the ownership question. Rule
text is written by whoever installs this, so the enforced vocabulary has to be
readable and checkable from here without reaching into anything they own.

`tests/test_marks_vocabulary.py` binds the sides. Both artifacts ship in this
directory, so the comparison needs no path from anyone and takes no setting:
it reads `rule-text/epistemic-marks.md`, scans it for anything mark-shaped,
and compares that set against the tuple. A disagreement is this plugin's own
defect, which is why nothing about the check is optional.

**What it buys.** Divergence turns into a red test naming the token. One edit
changes a mark's gloss, its name and its routing together. Adding a mark to
the rule text without adding it here fails a check, and so does the reverse.
The check runs identically for everyone, since there is no configuration for
an installation to get wrong or leave unset.

**What it sacrifices.** The duplication survives. Two artifacts still state
three tokens, and whoever changes one still has to change the other. The test
only reports the mismatch; it repairs nothing. Matching token sets are all it
compares. Nothing checks a gloss, because rule text writes for a reader and a
dict writes for a message, and demanding one string would damage one of them.

## What this leaves to whoever changes the plugin

`rule-text/epistemic-marks.md` must teach the three tokens `epistemic_marks/marks.py`
enforces, and no others. Its wording and structure are otherwise free.
Running the tests after a change to either side keeps the two in step.
