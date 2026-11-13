# Progress samples

Real output of each test framework with the flags `extra_argv` supplies, captured once from a three-test scratch suite
(a pass, a failure, and a skip; the mod suite has two passes and a failure because its kit has no skip) in a temporary
directory, never from this repository's suites.

Every command ran with `HOME`, `XDG_CACHE_HOME`, and `GIT_CONFIG_GLOBAL` pointed at scratch paths. `<scratch>` is the
temporary directory and `<worktree>` the checkout whose `uv.lock` resolved pytest 9.2.0, pytest-xdist 3.8.0, and
pytest-timeout 2.4.0. Bats is 1.14.0 and Claude Code 2.1.325. The only edit to the captured text replaces the
checkout's absolute `.venv/bin/python` path with `<worktree>/.venv/bin/python`.

| sample | working directory | command |
| --- | --- | --- |
| `pytest.txt` | `<scratch>/py` | `uv run --frozen --project <worktree> pytest tests -p no:cacheprovider -rf -v` |
| `pytest-xdist.txt` | `<scratch>/py` | `uv run --frozen --project <worktree> pytest tests -p no:cacheprovider -rf -n 2 -v` |
| `bats-tap-timing.txt` | `<scratch>/bats` | `bats --formatter tap --timing tests` |
| `plugin-test.txt` | `<scratch>/mod` | `claude plugin test <scratch>/mod` |

Each command's stdout and stderr went to the sample file. The scratch suites:

- `py/tests/test_sample.py`: `test_adds_numbers` passes, `test_rejects_wrong_sum` asserts `1 + 1 == 3`, and
  `test_skipped_case` is marked `skip(reason="not today")`.
- `bats/tests/sample.bats`: `adds numbers` passes, `rejects wrong sum` fails, and `skipped case` runs `skip "not today"`.
- `mod`: a plugin holding `.claude-plugin/plugin.json`, a `hooks/hooks.json` naming an empty module, and
  `tests/sample.test.ts` with `adds numbers` and `subtracts numbers` passing and `rejects wrong sum` failing, all
  inside `describe("sums")`.

## What the samples show

- pytest prints no duration per test and the total on a `collected 3 items` line (`2 workers [3 items]` under xdist).
  Under xdist a test prints a bare `path::name` line when it starts, then `[gwN] [ 33%] PASSED path::name` when it ends,
  and lines from both workers interleave. The `-rf` summary repeats each failure as `FAILED path::name - reason`.
- bats prints the total as `1..3` before any test, then `ok N name in 2ms`. A skip carries its reason after the timing
  as `# skip reason`. A failure is followed by `#` comment lines. The test file appears only inside those comments.
- `claude plugin test` prints a `tests/sample.test.ts:` header relative to the mod folder, then `(pass) group > name [1.21ms]`
  per test, and the total only in the last line, `Ran 3 tests across 1 file.`. Piped, none of it appears until the
  file ends: a file of two 2.5-second tests and one instant test printed every line within a single clock second,
  and only after the 5.1-second run.
