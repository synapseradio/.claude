# Skills

Required reading: [The rulesets directory and config](../../../docs/config.md), the section
"Skills".

Every case here runs inside the frame SKILL.md sets: "Before any edit" first, "After any change"
last. A skill under `ROOT/skills/` loads by name in every session once its link stands in
`~/.claude/skills/`; a pairing in the config makes a rule the pointer to it and changes no delivery.

## The form the engine holds a skill to

`check` reports each of these, as an error (e) or a warning (w):

- A folder `ROOT/skills/NAME/` holding `SKILL.md`; `skill-file` (e) otherwise. Other files may
  sit beside it.
- `SKILL.md` opens on a `---` frontmatter block that parses as a YAML mapping and holds a
  non-empty `description`; `skill-frontmatter` (e) otherwise.
- A frontmatter `name`, where written, equal to `NAME`, and `NAME` other than `synced`;
  `skill-name` (e) otherwise.
- A `skills` entry pairs one rule name, with no `@variant`, with one skill name;
  `pairing-shape` (e) otherwise.
- The paired rule stands in the pool, `pairing-unknown-rule` (e), and the paired skill under
  `ROOT/skills/`, `pairing-unknown-skill` (e).
- Every file of the paired rule, its default form and each variant, names the skill in backticks,
  as `` `NAME` ``; `pointer-unnamed` (w) otherwise.

## 30. Add a skill

1. Write `ROOT/skills/NAME/SKILL.md` with frontmatter holding `name: NAME` and a `description`
   that says what the skill does and when it loads, then the body.
2. Run `RUN CLI skills --link`, and confirm the line `NAME: linked`.
3. Confirm the skill loads by name: a delegate started afterwards lists `NAME` among its
   skills, and `/NAME` runs it.

## 31. Pair a rule with a skill

1. Move the rule's body into the skill (case 30), leaving `ROOT/rules/RULE.md` as a pointer that
   names the skill in backticks and says when to load it, as "load `NAME` through the Skill tool
   before X". Give each variant `RULE@VARIANT.md` the same pointer.
2. Add the entry under `skills` in `ROOT/config.yaml`:

   ```yaml
   skills:
     RULE: NAME
   ```

3. Run `RUN CLI check --root ROOT`, and clear every error it reports.

## 32. Check and link skills

1. Run `RUN CLI check --root ROOT` for the form above.
2. Run `RUN CLI skills` to preview each link; it writes nothing and exits 1 where a skill is
   unlinked, blocked, or stale.
3. Run `RUN CLI skills --link` to write them. Where a line says `blocked`, another entry stands at
   `~/.claude/skills/NAME`: move it aside, then run the command again.

Run step 3 against `ROOT` alone, never with `--root` naming a git worktree's copy: a link into a
worktree breaks once the worktree is removed. The session-start hook writes the same links into
`ROOT` on its own.

## 33. Remove a skill

1. Remove its entry under `skills` in `ROOT/config.yaml`, and restore the paired rule's body.
2. Delete `ROOT/skills/NAME/`, then run `RUN CLI skills --link`, which removes its stale link.
