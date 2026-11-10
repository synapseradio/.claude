# Setup and migration

Required reading: [Commands](../../../docs/commands.md), the sections on `adopt`, `compare`, and
`eject`, and [Delivery](../../../docs/delivery.md), the section "What it leaves alone".

## 25. First setup

1. Run `RUN SCRIPTS/scaffold.py --root ROOT`. It writes `manifest.yaml` (`models: []`, `flags: []`,
   `defaults: ["all:*"]`), `rules/example.md`, and the render, into a missing directory, an empty
   one, or the empty directory a first session creates.
2. Where it refuses with exit 2, the directory already holds a manifest that declares something,
   or other files: leave it, and go to the case that fits the request.
3. Replace the example: rename it (rules reference, case 5) and rewrite its text (case 2), or add
   the first real rule (case 1) and remove the example (case 4).
4. Run `RUN SCRIPTS/gate.py --root ROOT`.

## 26. Adopt an old corpus or rules folder

1. Choose the output: `ROOT` where it is missing; otherwise a new directory outside `ROOT`, since
   `adopt` refuses, with exit 2, an output that holds files, is the source, or lies inside it.
2. Run `RUN CLI adopt --from SOURCE --out OUT`. It leaves the source as it was, strips a source
   file's opening marker for its own rule, and compares what the source delivers with what `OUT`
   delivers, exiting 1 where a context differs.
3. Where a model identifier's differences are expected, run again into a new `OUT` with
   `--expect IDENTIFIER`, once per identifier.
4. Edit `OUT` as the request needs, then run `RUN CLI compare SOURCE OUT`. It names each context
   that differs, with the first rule and variant where it differs, and ends with
   `compared N contexts`.
5. Run `RUN SCRIPTS/gate.py --root OUT`.
6. Where `OUT` is not `ROOT`: after the person confirms, move the old `ROOT` aside under a new name
   and move `OUT` into its place. Keep the old directory.
7. Where the source is a folder the harness loads on its own, its rules now reach each context
   twice: move them out (rules reference, case 8).

## 27. Eject to plain files

1. Run `RUN CLI eject --out OUT --root ROOT`, `OUT` a new directory. It writes one `NAME.md` for
   each rule `defaults` gives, at its default form, and prints `wrote PATH` for each.
2. It also prints each block and each variant plain files cannot carry, with file and line. Report
   every such line to the person: those contexts lose those rules or variants once the plugin is
   gone.
3. It changes no file under `ROOT`. Uninstalling the plugin is the person's own step.
