# Debugging

This applies when debugging a problem.

```sudolang
fn debug {
  state the hypothesis before changing anything, let the cheapest test decide it
  the user identifies a root cause => investigate that cause first, since it rests
    on an observation you never witnessed; hold every alternative diagnosis
    until definitively ruled out
  your measurement runs against their diagnosis => voice it once,
    investigate their cause either way
  cause named => repair with the smallest change that keeps the unit's job
}
```
