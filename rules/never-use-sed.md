# Never Use sed for Edits

```sudolang
NeverUseSedForEdits {
  Applies { always }

  StreamEditors = [sed, gsed, awk, any other stream editor]

  Constraints {
    never use StreamEditors to modify a file
    always use Edit or Write instead
      // they match exactly, fail loudly on a wrong match,
      // and never silently mangle the rest of the file
    triviality is no exemption {
      one-line substitution -> Edit
      in-place delete       -> Edit
      appending a line      -> Edit|Write
    }
  }

  Allowed {
    StreamEditors for read-only inspection in a pipeline
      // touches no file on disk — the ban is on using them to write
  }
}
```
