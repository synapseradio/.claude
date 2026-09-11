# epistemic-marks

Blocks a reply that still carries a claim nobody checked.

## What it enforces

An epistemic mark is a short token written at the end of a clause to say the
claim in that clause is not yet known. This plugin enforces four:

| Mark | Name | Label |
| --- | --- | --- |
| `[?]` | the unsourced mark | `needs_citation` |
| `[.?]` | the secondhand mark | `needs_verification` |
| `[^?]` | the caller's mark | `escalate_decision` |
| `[!?]` | the standing question | `ask_user` |

What each mark means and how it resolves is the rule's to say, and the rule
text says it. What the plugin holds is what to do about a mark it found: one
act for the case where this pass can settle it, one for the case where it
travels in the report instead.

The last two split what used to be one token. A caller receiving a report can
now tell an item it could settle itself from one that has to reach a person,
without opening the delegate's transcript.

A mark inside a fenced code block does not count. Neither does one inside a
longer inline code span, nor one written in a span of its own on a line that
also calls that mark by name, since a sentence naming the mark it shows is
documenting the mark rather than claiming under it. A backticked mark on a
line naming no mark still counts, so the exemption costs a writer the words.
Every skipped mention is listed back to you, so it never passes in silence.

Three events drive it:

- **Stop** blocks the turn once and asks for each mark's resolution. A second
  pass in the same cycle reports whatever survived instead of blocking again,
  so a mark that outlives its verification stands in front of the user rather
  than looping.
- **SubagentStop** runs with `--delegate`. A subagent reaches no user, so the
  caller's mark and the standing question are left standing and listed back to
  the subagent, apart from each other, for its own report to carry to the
  caller. Nothing this hook returns reaches the caller directly; the report
  does.
- **PostToolBatch** runs with `--batch` and never blocks, since stopping the
  agentic loop mid-task costs more than the claim it flags. It reaches a claim
  while the turn can still act on it, and reports each line once per session.

## It checks the citations too

A mark is a negative signal: it says a claim has no source yet. The positive
signal is the citation that replaces it. That makes a fabricated citation the
cheapest way to look verified, so a `path:line` citation in a reply is
checked against the `Read`, `Grep` and `Glob` calls of the session.

This never blocks and never asks for a rewrite. A citation naming a file
nothing in the session opened produces one notice naming the citation. It
fires on citations the agent wrote itself, so it never has to judge whether a
turn gathered enough evidence. A citation inside a fenced block is part of an
example and draws nothing.

## It teaches the marks and enforces them, as one unit

Install it and it works. There is nothing to configure and nothing to write.

Enforcement on its own would correct a model against something nothing taught
it, so the teaching ships with it. `rule-text/epistemic-marks.md` holds the
rule text and a delivery hook hands it over at every start. That hook runs on
every session start, resume, clear, fork and compaction, because injected
context does not outlive a compaction and each firing restores it.

It runs on **SubagentStart** too, and that half is not a courtesy. The
verification pass matches literal tokens, so a spawned agent that was never
taught the vocabulary writes no mark, the scan comes back empty, and the pass
is inert. Teaching is what produces the signal enforcement exists to find. A
test reads `hooks/hooks.json` and fails if delivery is wired to only one of
the two starts.

The two halves are a pair, with no switch between them. `epistemic_marks/marks.py` is the
vocabulary the hooks enforce, and a test compares the shipped rule text
against it, so the text a session is taught cannot drift from what gets
blocked.

This plugin reads none of your files. It imports nothing of yours, opens no
manifest, and holds no path into your configuration. It assumes no other
plugin is installed and changes nothing depending on whether one is.
`tests/test_independence.py` holds that promise: no source under
`epistemic_marks/` or `hooks/` may name a path outside the plugin root, and
the rule still arrives whole with the home directory pointed at nothing.

## Installing

```sh
claude plugin marketplace add <this repository>
claude plugin install epistemic-marks
```

The harness has to support `SubagentStart`, verified on Claude Code 2.1.268.
One that fires `SubagentStop` and not `SubagentStart` runs the verification
pass against agents nothing taught, and the plugin cannot detect that from
inside a hook, so no version floor is enforced.

The hooks need Python 3.14 or later. `hooks/with-python.sh` picks the
interpreter that runs them, trying `EPISTEMIC_MARKS_PYTHON` first, then
`python3.14`, then `python3`. Where the interpreter you want is under another
name or path, export `EPISTEMIC_MARKS_PYTHON` pointing at it. Where nothing on
the path serves, each hook exits with one line on stderr naming the
requirement and the session runs with no rule delivered and no verification,
as `hooks/with-python.sh` explains.

## Confirming the hooks are live

Run `/hooks` and look for five entries: `with-python.sh` running
`deliver-rule.py` under `SessionStart` and `SubagentStart`, and
`with-python.sh` running `verify-marks.py` under `Stop`, `SubagentStop` and
`PostToolBatch`.

To watch one fire, write a sentence carrying a mark and end the turn. The
reply gets blocked once and comes back with the resolution the mark takes. A
reply whose claims all carry a path or a URL passes untouched. To drive the
hook directly, from the plugin directory:

```sh
echo '{"stop_hook_active":false,"last_assistant_message":"Nobody else calls it [?]."}' \
  | python3.14 hooks/verify-marks.py
```

That prints a `block` decision. Replacing the mark with a citation prints
nothing and exits 0, which is how the hook passes a reply. The launcher form,
`bash hooks/with-python.sh hooks/verify-marks.py`, runs the same check through
the interpreter selection the hooks use.

## Turning it off

There is no way to disable one hook of a plugin. `disableAllHooks` is all or
nothing and silences every plugin's hooks at once. To stop this enforcement
alone, uninstall the plugin.

## Where it keeps state

The batch pass records which lines it already reported, so one sentence draws
one report per session instead of one per tool batch.

That record holds a SHA-256 fingerprint of each line and never the line
itself. Recognizing a line it has seen is all deduplication needs, and a
fingerprint cannot disclose the text it stands for. Nothing from your
conversation is written to disk.

It goes to the data directory the harness gives the plugin, which survives an
update, and to your system temporary directory when there is none. Nothing is
written inside the plugin directory, since an update replaces it and orphans
whatever sits there. Losing the record costs one repeated report. Entries
older than a day are pruned.

## Tests

```sh
python3.14 -m pytest tests -q
```

They take no setup and read nothing outside the plugin. Beyond the hooks'
behavior they compare the shipped rule text against `epistemic_marks/marks.py`: a mark
the text teaches and the hooks ignore would leave every claim under it
unverified, and a mark the hooks block and the text never mentions would
correct a model against nothing. A failure names the token.

`DESIGN.md` records why the vocabulary lives in `epistemic_marks/marks.py` and what that
choice sacrifices.
