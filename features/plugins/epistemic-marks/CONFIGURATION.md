# Configure epistemic-marks

One setting configures the plugin: the environment variable `VERIFY_MARKS_STATE_DIR`, which names the directory where the hooks keep their record.

## The record

- Contents: a SHA-256 fingerprint of each line the hooks have shown Claude, never the line's text, and the number of times the current turn's reply has been sent back.
- Lifetime: a record file left unused for a day is deleted at the next round of tool use.

## Where it lives

| Condition | Directory |
| --- | --- |
| `VERIFY_MARKS_STATE_DIR` is set | that directory |
| it is unset, and Claude Code sets `CLAUDE_PLUGIN_DATA`, as it does for every hook | `verify-marks` in that data directory |
| neither is set | `epistemic-marks-verify-marks` in the system temporary directory |

## A directory the hooks cannot write

Point the variable at a directory the hooks can create and write. Without a record, a reply goes back at most once per turn, each check shows every finding again, and the reminders while Claude works stop.
