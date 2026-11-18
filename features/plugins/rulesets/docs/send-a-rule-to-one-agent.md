# Send a rule to one agent

At the end of this tutorial, an agent named `critic` receives a review checklist on top of the
rules everyone receives, and Claude can name the config line that sent it. An agent is a helper
your session starts for one task. You ask Claude for each step.

## Before you start

- The rule `voice` and the config from [Write your first rule](write-your-first-rule.md).
- An agent to aim at. The examples use one named `critic`; put the name of any agent you use in
  its place, a built-in one such as `Plan` included.

## Give the critic its own rule

1. Ask:

   ```text
   Add a rule named review-checklist that says "Check every changed line against the spec
   before approving." Give it only to the critic agent.
   ```

   Claude writes `rules/review-checklist.md` and adds a block to the config, which now holds:

   ```yaml
   models: haiku sonnet opus
   defaults: voice
   agent critic:
     include: review-checklist
   ```

   Claude reports that only the critic gains the rule:

   | Who | Receives |
   | --- | --- |
   | the main session | `voice` |
   | an agent named `critic` | `voice`, `review-checklist` |
   | every other agent | `voice` |

2. Ask why:

   ```text
   Why did critic get review-checklist?
   ```

   Claude names the line that decided it: `config.yaml:4` in the config above, under the
   condition `agent critic`, with the reference `include review-checklist`.

3. Have Claude start a critic on any small task, then ask:

   ```text
   What did the critic receive?
   ```

   Claude reports the critic's delivery with two rules, `review-checklist` and `voice`. An agent
   receives its rules when it starts, so the new rule needs no new session.

## Aim a rule by model or tool

The same kind of ask aims a rule by other facts about who receives it. Claude writes the
condition for you.

| You want the rule to reach | Ask Claude, for example | Condition Claude writes |
| --- | --- | --- |
| every agent that can run shell commands | "send the shell-safety rule to every agent with Bash" | `tools Bash` |
| every session and agent on one model | "give the deep-review rule only to opus" | `model opus` |
| two kinds of agent | "give review-checklist to the critic and thinkies agents" | `agent critic thinkies` |
| one kind of agent, except on one model | "give the planning rule to Plan agents, but not on haiku" | `agent Plan`, holding `not model haiku` |

## What you have now

One agent carries an instruction the others do not, and every such choice traces to one line of
the config.

## Related

- [Keep a rule away from one model](keep-a-rule-from-a-model.md): hold an instruction back where
  it misleads.
- [See what an agent received, and why](see-what-an-agent-received.md): read the record of a
  session and its agents.
- [The rulesets directory and config](config.md): reference for conditions and which statement
  wins.
