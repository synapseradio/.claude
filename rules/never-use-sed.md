# Never Use sed for Edits

The ban covers in-place substitution over a stream, rather than writing a file
from a program. `sed -i` applies a pattern it never shows you to a file it never
reads back, so a wrong match mangles the rest silently. A script reads its input,
transforms it, reports what it did, and leaves a way back.

```sudolang
NeverUseSedForEdits {
  Applies { always }

  StreamEditors = [sed, gsed, awk, `perl -i`, etc]
    // in-place substitution driven by a pattern, reporting nothing it matched

  Constraints {
    never use StreamEditors to modify a file
    prefer Edit or Write wherever either expresses the change
      // they match exactly, fail loudly on a wrong match,
      // and never silently mangle the rest of the file
    triviality is no exemption {
      one-line substitution -> Edit
      in-place delete       -> Edit
      appending a line      -> Edit|Write
    }
    // enforced mechanically: scripts/hooks/deny-inplace-stream-edit.sh
    // denies sed/gsed -i and awk -i inplace as a PreToolUse hook on Bash;
    // the wider ban (perl -i and kin) rests on this prose alone
  }

  Allowed {
    StreamEditors for read-only inspection in a pipeline
      // touches no file on disk; the ban covers writing only

    a script in a real language: Python, TypeScript, JavaScript, Ruby, or the
    like, under ScriptedEdit
      // reach for one where the change is mechanical and repeats across many
      // files or many lines, and Edit would spend a call per instance
  }

  ScriptedEdit {
    Applies { a script modifying more than a single line of code }

    Requirements {
      reversible before it runs {
        `git commit` or `git stash` FIRST
          // the script's whole effect becomes the only uncommitted diff,
          // so `git checkout` returns the tree
        no checkpoint -> do not run the script
      }

      idempotent {
        running it again changes nothing further
        run it a second time and confirm it reports no change
      }

      match exact strings rather than loose patterns
      report what changed, and read the diff before moving on
    }
  }
}
```
