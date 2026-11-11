# Rule files

Required reading: [The rulesets directory and config](../../../docs/config.md), the sections
"Words used here" and "The rulesets directory".

Every case here runs inside the frame SKILL.md sets: "Before any edit" first, "After any change"
last. A pool file delivers nothing by being there; a rule reaches a context only through a
reference in the config.

## The form the engine holds a rule file to

`check` reports each of these, as an error (e) or a warning (w):

- One rule per file, holding the rule's text alone. Delivery writes the marker line
  `<!-- rule: NAME -->` and a blank line before each body, so a file that opens on a marker draws
  `marker-for-another-rule` (w) where the marker names another rule or form.
- A body of at most 9,000 characters, counting the marker line and the blank line after it;
  beyond that, `oversize-body` (e), and delivery withholds the rule.
- No naming another rule: its name in backticks, its file name, a link to its file, or the
  phrases "rule name" and "the name rule" draw `cross-reference` (w). A bare word is no mention.
- Every cited path exists under `ROOT/references/`: a missing one draws `dangling-reference` (w),
  and a path outside the configuration directory draws `external-reference` (w). A path with a
  `<placeholder>` segment is no citation.
- No frontmatter carrying a condition, `rule-condition` (e); frontmatter that does not parse is
  `frontmatter-unparsable` (e).
- A variant `NAME@VARIANT.md` needs the default form `NAME.md`, which may be empty;
  `variant-without-default` (e) otherwise, and delivery withholds the rule.

## 1. Add a rule

1. Write `ROOT/rules/NAME.md` holding the rule's text, in the form above.
2. Reference it. Where `defaults` includes `all.*`, every context already receives it.
   Otherwise add `NAME` to the list that serves the contexts it belongs in: `defaults` for every
   context, a named set, or a block (config reference, cases 12 and 13).
3. In the impact diff, confirm `+ NAME` stands under each context it should reach and under no
   other.

## 2. Edit a rule's text

Directly: edit `ROOT/rules/NAME.md`, or `NAME@VARIANT.md` for one variant.

Through a render:

1. Run `RUN CLI render --root ROOT`, then edit the rule's section in a file under `ROOT/-render/`,
   keeping every marker line as it stands.
2. Run `RUN CLI split ROOT/-render/FILE.md --root ROOT` before any other `render` run, which
   replaces the render folder and drops the edit.
3. Where `split` refuses, repair the marker lines its message names and run it again.

A text edit leaves the impact diff empty, since every context keeps the same rules. Confirm the new
text with `CLI render --out` (inspecting reference, case 15).

## 3. Add a variant and set it

1. Write `ROOT/rules/NAME@VARIANT.md` as a complete body, which replaces the default form wherever
   the variant is set. `NAME.md` must exist.
2. Set it with `NAME@VARIANT` under `include` in the block whose contexts should receive it (config
   reference, case 11).
3. Run `RUN CLI explain NAME --root ROOT` with the facts of one such context, and confirm the
   variant attribute names `VARIANT`.

## 4. Remove a rule or a variant

1. Find every reference: search `ROOT/config.yaml` for `NAME`, `NAME@`, `.NAME`, and `rules.NAME`.
   For one variant, search for `NAME@VARIANT`.
2. Confirm with the person before deleting any file.
3. Remove each reference, then delete `ROOT/rules/NAME.md` and every `ROOT/rules/NAME@*.md`, or only
   `NAME@VARIANT.md` for a variant. A reference left standing to a deleted name is an
   `undeclared-reference` error.

## 5. Rename a rule

1. Confirm no `ROOT/rules/NEW.md` or `NEW@*.md` exists.
2. Move `OLD.md` to `NEW.md` and each `OLD@VARIANT.md` to `NEW@VARIANT.md`, with `git mv` where
   the directory is tracked.
3. Rewrite every config reference to `OLD`, in each form step 1 of case 4 lists.
4. In the impact diff, confirm `- OLD` and `+ NEW` stand under exactly the same contexts.

## 6. Split a rule over 9,000 characters

1. Find the seam where the text divides into two instructions, each standing on its own text.
2. Write two new rules, each under 9,000 characters with its marker. Neither names the other.
3. Split each variant at the same seam, since a variant replaces the whole body.
4. Replace every reference to the old rule with references to both, then remove the old rule
   (case 4).
5. In the impact diff, confirm the two new rules arrive wherever the old one did.

## 7. Clear `check` warnings

Run `RUN CLI check --root ROOT`. Each line reads `FILE:LINE: warning [KIND] SUBJECT: MESSAGE`.

| Kind | Clear it by |
| --- | --- |
| `never-included` | adding a reference (case 1, step 2), or removing the rule (case 4); ask the person which |
| `cross-reference` | rewriting the sentence to state its instruction itself, leaving the other rule unnamed |
| `dangling-reference` | putting the cited file under `ROOT/references/`, or correcting the path |
| `external-reference` | moving the cited file under `ROOT/references/` and citing it there |
| `stray-directory` | moving a directory that holds no rule out of the rulesets directory, after asking the person |
| `too-many-parts` | withholding rules from that context or shortening them, since a delivery carries at most 10 parts of 9,000 characters |
| `marker-for-another-rule` | deleting the opening marker line |

## 8. Move a rule out of the harness's own rules folder

The harness loads `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/rules/` and a project's `.claude/rules/` on
its own, so a rule kept there and in the pool reaches a context twice.

1. Read the file. Where its frontmatter scopes it to file paths, it carries a condition the pool
   cannot hold; leave it where it is and say why.
2. Write its body, without frontmatter or a marker line, to `ROOT/rules/NAME.md`, and reference it
   (case 1, step 2).
3. After the person confirms, delete the harness copy.
4. In the next session, run `RUN CLI load-check --session ID --root ROOT` with that session's
   identifier; it prints nothing for `NAME` once nothing still loads it.
