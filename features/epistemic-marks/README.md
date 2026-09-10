# epistemic-marks

Blocks a reply that still carries a claim nobody checked.

## What it enforces

An epistemic mark is a short token written at the end of a clause to say the
claim in that clause is not yet known. This plugin enforces three:

| Mark | Name | What it says | How it resolves |
| --- | --- | --- | --- |
| `[?]` | the unsourced mark | no source on file | a lookup that yields a citation |
| `[.?]` | the secondhand mark | secondhand and ungrounded | a lookup that yields a citation |
| `[^?]` | the user's mark | awaits an answer only the user supplies | the user's answer, and nothing else |

A mark inside a fenced code block does not count, and neither does one inside
a longer inline code span, since a sentence quoting a mark is discussing it
rather than claiming under it.

Three events drive it:

- **Stop** blocks the turn once and asks for each mark's resolution. A second
  pass in the same cycle reports whatever survived instead of blocking again,
  so a mark that outlives its verification stands in front of the user rather
  than looping.
- **SubagentStop** runs with `--delegate`. A subagent reaches no user, so the
  user's mark rides up in the report under an `UNANSWERED` opening.
- **PostToolBatch** runs with `--batch` and never blocks, since stopping the
  agentic loop mid-task costs more than the claim it flags. It reaches a claim
  while the turn can still act on it, and reports each line once per session.

## It teaches the marks and enforces them, as one unit

Install it and it works. There is nothing to configure and nothing to write.

Enforcement on its own would correct a model against something nothing taught
it, so the teaching ships with it. `rule-text/epistemic-marks.md` holds the
rule text and a fourth hook delivers it at session start. That hook runs on
every session start, resume, clear, fork and compaction, because injected
context does not outlive a compaction and each firing restores it.

The two halves are a pair, with no switch between them. `epistemic_marks/marks.py` is the
vocabulary the hooks enforce, and a test compares the shipped rule text
against it, so the text a session is taught cannot drift from what gets
blocked.

This plugin reads none of your files. It imports nothing of yours, opens no
manifest, and holds no path into your configuration.

## Installing

```sh
claude plugin marketplace add <this repository>
claude plugin install epistemic-marks
```

Python 3.14 is a prerequisite.

## Confirming the hooks are live

Run `/hooks` and look for four entries: `deliver-rule.py` under
`SessionStart`, and `verify-marks.py` under `Stop`, `SubagentStop` and
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
nothing and exits 0, which is how the hook passes a reply.

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
