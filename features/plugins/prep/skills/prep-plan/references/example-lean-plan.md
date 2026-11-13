# Example: a lean plan

A one-file bug fix. The size pass answered one unit, so the plan has no contracts section, no coordination, and no lanes. It still carries a user story, the boundary the fix must keep, a test written first, and the state of the checks before work. The machine had a justfile and a hook manager, so the plan names a recipe and the hook in place of raw commands.

**Example 1:**

Input: "Invoices exported by our Auckland office show due dates a day off from the ones Los Angeles exports. Plan a fix."

Output:

````markdown
# Export invoice due dates in UTC, for accountants reconciling across offices

Goal: `ledger export` writes every due date as a UTC calendar date, whatever timezone the machine is in.

## Glossary

- root: `/work/ledger`; every relative path below resolves against it
- branch: `fix-export-utc`, created from `main` in the working tree at the root
- export: the `ledger export --format csv` command, which writes one row per invoice
- due date: the `due_on` column, a calendar date with no time

## Target outcomes

- As an accountant reconciling invoices exported by a colleague in another office, I want each due date to match the date on the invoice itself, so that I stop chasing invoices that only look a day overdue.
  - Done when: `TZ=Pacific/Auckland just export-sample` and `TZ=America/Los_Angeles just export-sample` print the same `due_on` for invoice `INV-1042`: `2031-03-01`.

## Boundaries

- `formatDueDate`, in `src/export/dates.ts`, stays as it is; relied on by `src/export/csv.ts` and `src/export/pdf.ts`

  ```ts
  export function formatDueDate(due: Date): string // "YYYY-MM-DD"
  ```

- The CSV column order and header names stay as they are; `tests/export/csv.snapshot.test.ts` pins them.

## Work

You make this change yourself, as one commit.

| path | symbol | change |
| --- | --- | --- |
| `src/export/dates.ts` | `formatDueDate` | build the string from `getUTCFullYear`, `getUTCMonth`, and `getUTCDate` in place of the local-time getters |
| `tests/export/dates.test.ts` | `formatDueDate` cases | add a case for `2031-03-01T00:00:00Z` under `TZ=Pacific/Auckland` and under `TZ=America/Los_Angeles`, each expecting `2031-03-01` |

- test first: the Los Angeles case fails before the change with `2031-02-28`, since local time there is still the day before.
- check: `just test tests/export/dates.test.ts` passes. It catches a getter left in local time.
- commit: `git commit -m 'fix(export): format due dates in UTC' -- src/export/dates.ts tests/export/dates.test.ts`, through the lefthook pre-commit hook, which runs the formatter and the type checker.

## Constraints

- `formatDueDate` keeps its signature and its output format.
- Leave `formatTimestamp` in the same file alone; it prints local time on purpose, for the on-screen receipt.

## Verification

- before the work: `just test` passed on `main` at `4c1d2ab`, read 2031-02-11.
- `TZ=Pacific/Auckland just export-sample` and `TZ=America/Los_Angeles just export-sample` both print `2031-03-01` for `INV-1042`. The sample holds only midnight-UTC dates, so this could pass with a defect in dates that carry a time; the new unit cases close that.
- `just test`, once, after the commit: every suite passes.
````

</example>
