# Runtime

Required reading: [Delivery](../../../docs/delivery.md) in full, and
[Where records live](../../../docs/records.md).

Case 19, the toggle, lives in SKILL.md under Toggle.

## 20. Launch with flags

1. Confirm each flag is declared in `ROOT/config.yaml` (config reference, case 9).
2. Set `RULESETS_FLAGS` in the environment that starts the session, a comma-separated list, as
   `RULESETS_FLAGS=strict,brief` before the launch command.
3. A misspelled or undeclared flag is dropped, and the session start shows a notice naming it.
4. Confirm with case 21: the flags column of the session's delivery line lists each flag.

## 21. What a session or a delegate received

1. Find the session identifier: `SESSION` for this session; for another, list `STATE/audit/`,
   whose directory names are session identifiers with every character other than letters,
   digits, `-`, and `_` removed.
2. Run `RUN SCRIPTS/session_report.py show --session ID --root ROOT`. It exits 1 where either check
   printed a line.
3. Read its three sections:
   - `deliveries`: one tab-separated line per delivery that reached a context: the scope
     (`session`, `delegate`, or `switch`), the model, the model's source, the rule count, the flags
     (or `-`), and the delegate identifier for a delegate.
   - `delivery-check`: each rule a delivery sent that the config and pool would not compose now,
     or composes now and the delivery lacked, or at a different variant, and each later part
     never sent or sent with other text. A line here means the directory changed since, or a
     delivery went wrong.
   - `load-check`: each file the harness loaded that is named for a rule of the pool, a rule still
     loading from the harness's own rules folder (rules reference, case 8).
4. For a rule list, read `STATE/audit/ID/deliveries.jsonl`: one JSON record per delivery, its
   `rules` naming each rule with its variant, and its `notices` naming anything skipped,
   withheld, or left out.

## 22. No rules arriving

Work down the list, stopping at the first that explains it.

1. Run case 21. A `deliveries` section with no line means no delivery reached the session: confirm
   the plugin is installed and enabled.
2. Run `RUN --version`. Where it prints no version, no interpreter runs the engine: install PyYAML
   for Python 3.15 or later, or set `RULESETS_PYTHON` to an interpreter's path or name.
3. Run `RUN CLI check --root ROOT`. A missing or unparsable config makes delivery send the
   default form of every rule in the pool, with a notice. A directory that holds an older config
   file and no `config.yaml` is such a case (setup and migration reference, case 28).
4. A rule count of 0: the config references no rule for that context. Run case 15 of the
   inspecting reference with its facts, then case 16 for the rule expected.
5. Rules arrive, but not the expected one: go to case 16 of the inspecting reference.

## 23. Prune a session's records

1. Confirm the session identifier, and confirm with the person before deleting.
2. Delete the directory `STATE/audit/ID/`. Every other session's records, and the session's model
   record under `STATE/models/`, stay as they were.

## 24. Try another wording and compare

1. Declare a flag for the trial, as `try-terse` (config reference, case 9).
2. Write the new wording as a variant, `ROOT/rules/NAME@VARIANT.md` (rules reference, case 3).
3. Add a block that sets it under the flag (config reference, case 11), then run the gate:

   ```yaml
   flag try-terse:
     include: NAME@VARIANT
   ```

4. Ask the person to launch two sessions that differ only by the flag, one with
   `RULESETS_FLAGS=try-terse` and one without, to run the same task in each, and to give you both
   session identifiers.
5. Run `RUN SCRIPTS/session_report.py compare A B`. It prints each session's flags, then each scope
   whose rules differ: `session`, and `delegate TYPE #N` for the Nth delegate of one agent type.
   Under a scope, `NAME  A: VARIANT  B: default` names the variant each session received,
   `absent` where it received no such rule.
6. Confirm the only rule differing is `NAME`. Any other line means the two sessions composed from
   different directories or facts; read both sessions with case 21.
