# Debugging

This applies when debugging a problem.

We value a repair that follows a hypothesis a test decided. The user's named root cause rests on an observation we never witnessed, so it gets investigated first and every alternative stays open until ruled out. A change made before the hypothesis is stated leaves nobody able to say what the change tested.

```sudolang
fn debug() {
  state the active hypothesis before changing anything, let the cheapest test decide it
  the user identifies a root cause => investigate that cause first, hold every alternative
    diagnosis until ruled out
  your measurement runs against their diagnosis => voice it once, investigate their
    cause either way
  cause named => repair with the smallest change that keeps the unit's job
}
```
