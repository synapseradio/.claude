# Writing Code

```sudolang
WritingCode {
  reference = ~/.claude/references/writing-code-reference.md

  when (writing or modifying source code) {
    read(reference § "Code qualities")
  }

  when (adding or modifying behavior) {
    read(reference § "The implement flow")
  }
}
```
