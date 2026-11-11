# rulesets

Compose the rules each Claude Code session and delegate receives, from one pool of rule files and
one config, `config.yaml`. A rule is a text file. The config says which rules reach which context: every
context, one model, one agent, or any session where you set a flag. The plugin delivers the result
through hooks and records what it delivered, so you can read back what any context received.

[INSTALL.md](INSTALL.md) covers installing the plugin. The pages below cover what it does and how
to drive it.

| Page | Read it when |
| --- | --- |
| [Delivery](docs/delivery.md) | you want to know which context receives rules, when, in how many parts, and what the plugin leaves alone |
| [The rulesets directory and config](docs/config.md) | you write a rule, a variant, a set, a flag, or a condition block, or need to know which statement wins |
| [Commands](docs/commands.md) | you run `check`, `explain`, `render`, `split`, `eject`, `adopt`, `compare`, the session record commands, or a toggle |
| [Where records live](docs/records.md) | you read or prune what a session received |

The `rulesets` skill drives all of this from a session: type `/rulesets:rulesets`, or ask in words,
such as "add a rule for my delegates" or "why did this delegate get that rule".
