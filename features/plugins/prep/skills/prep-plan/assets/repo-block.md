# Repository block

One block per repository the plan changes, in landing order. Replace each bracket with what it describes.

```markdown
### Repository [name]

- root: [the absolute path of its primary checkout; entry paths in this block resolve against it]
- trunk: [its trunk, and the trunk commit at planning]
- lands: [its place in the landing order, and the contract that sets it: before [repository], which consumes [contract]]
- provides: [each cross-repository contract it owns, by the name the Contracts section uses]
- consumes: [each cross-repository contract it builds against, and how the other side's change reaches it: a published version, a pinned commit, a linked checkout]
- rules: [branch naming, commit form, and review requirements that differ from the other repositories]
- checks: [each command, run from this root, with its result on the trunk as it stands]
- workers: [the agents that work here and nowhere else]
- work:
  [its units in wave order, as unit blocks or lane blocks]
```
