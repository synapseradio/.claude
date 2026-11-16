# How much the plan settles

Read this when the plan has several work units. A plan fixes what no single worker can settle alone and stops there. Each worker settles the rest for its own slice, at the level its model can be trusted with. A plan that goes further spends planning tokens on choices a worker makes better with the code open, and hands every reader lines that are someone else's job.

## Where a detail belongs

Sort each detail by the first arm that fits.

```text
place detail
  | two or more units must agree on it: a signature, a type, the data that
    crosses a boundary, an id, a file format, a naming scheme
      = the plan, as a contract or a shared convention, stated in full
  | only a person chooses it: scope, a target outcome, a trade between outcomes
      = the plan, as a decision
  | a wrong choice is costly to undo, or no check the worker runs would catch it
      = the plan, as a decision or a constraint
  | planning found it and reading the unit's own paths would miss it: a test
    elsewhere that pins the old behavior, a caller with a special need, a trap
    in a library
      = that unit's "known in advance" line
  | it sits inside one unit's owned paths, and a check catches a wrong choice
      = the unit's worker
```

The last arm holds every test case, the inputs and expected values of each test, the names of helpers and private types, the layout of files inside the owned paths, the order of work inside the unit, and how each behavior is built.

## What each unit states

State each unit as what it makes true, never as how.

- behaviors: one line per thing a person or a consuming unit observes once the unit lands, each with the command that shows it, the unit's test command for most. Take each from a user story's "Done when" line or from a contract the unit provides. A behavior says what holds, "a bucket never refills above its capacity"; the inputs and numbers that prove it are a test case, and belong to the worker.
- contracts: the ones it provides and consumes, by name.
- owned paths: where it may write.
- checks: the commands that pass before its commit.
- known in advance: the facts the fourth arm above places here.

Name the kinds of output the unit owes outright: tests, docs, a migration. A worker builds what its lines name and treats the rest as unasked, so a unit that wants tests says "write the tests for each behavior, red first", and leaves the cases to the worker.

State an edge case only where a person decided it or a contract fixes it, as a behavior: "an unrecognised theme reads as dark". Leave the worker to find the cases that follow from the contracts and the behaviors.

## The level for each model

Choose each worker's model first, by what its unit asks of it, then its effort, then write its lines to that model's level. Effort is the one control for how much a worker thinks, so set it in the Roster and write nothing about thinking into the worker's lines.

| worker's model | suits | effort | the plan or its run-book file states | the worker settles |
| --- | --- | --- | --- | --- |
| smallest | a read, a list, a mechanical edit, an operation stated whole | low for one short stated step, medium for anything with a check to run | every step in order, every path, the exact change, the command to run and the output to return | nothing beyond the steps |
| mid-sized | building a unit against fixed contracts | medium, high for a long or hard unit | the behaviors with their checks, the contracts by name, the owned paths, the kinds of output owed, the facts known in advance | test cases, internals, order of work, the edge cases the contracts imply |
| strongest | an integrator whose wiring needs design, a unit with an open contract, a unit whose approach is unsettled | medium | the problem, the constraints, the contracts at its edge, the decisions made, the check that shows it done, and which parts warrant delegates of its own | the approach, the design inside its boundary, and everything the mid-sized row lists |

A unit that needs more than its row to be buildable is cut wrong or given to the wrong model. Fix a missing contract, split the unit, or move it up a row, in place of adding steps.

Give a unit to the smallest model only where every step can be written now. A unit whose steps depend on what the worker finds belongs to the mid-sized row.

## Verify

- No unit's lines list test cases, test inputs, helper names, or steps, apart from a unit given to the smallest model.
- Every behavior names the command that shows it.
- Every unit that owes tests, docs, or a migration says so in words.
- Every detail two units must agree on stands in the Contracts section or in Shared conventions.
