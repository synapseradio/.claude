# Data Modeling

```sudolang
DataModeling {
  when (designing or changing types, data structures, schemas,
        interface signatures, or error channels) {
    read(~/.claude/references/data-modeling-reference.md)
  }

  when (about to write a runtime check or panic for a state
        that "should never happen") {
    read(~/.claude/references/data-modeling-reference.md § "Five moves")
      // model the state out, or accept the panic knowingly
  }
}
```
