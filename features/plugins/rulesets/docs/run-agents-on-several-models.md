# Run one kind of agent on several models

At the end of this tutorial, three agents of one kind have started from one message, each on a
different model, and each has opened on the rules for its own model. A small model carries a short
wording while a large one carries the full text. You ask Claude for each step.

## Before you start

- The rule `review-checklist` for the `critic` agent, from
  [Send a rule to one agent](send-a-rule-to-one-agent.md).
- The models `haiku`, `sonnet` and `opus` declared in the config, as
  [Write your first rule](write-your-first-rule.md) leaves them.

## Give each model its own wording

1. Ask for a shorter wording on the small model:

   ```text
   Add a version of review-checklist named brief that says "Check the riskiest changed
   lines against the spec." Give critics on haiku the brief version.
   ```

   Claude writes `rules/review-checklist@brief.md` and nests a condition for the model inside the
   critic's block. The config now holds:

   ```yaml
   models: haiku sonnet opus
   defaults: voice
   agent critic:
     include: review-checklist
     model haiku:
       include: review-checklist@brief
   ```

   | A critic on | Receives |
   | --- | --- |
   | haiku | `voice`, `review-checklist@brief` |
   | sonnet or opus | `voice`, `review-checklist` |

2. Start the agents in one message:

   ```text
   Spawn three critics to review my last change, on haiku, sonnet and opus.
   ```

   Claude starts three critics, naming a model for each, and the plugin gives each one the rules
   for the model named for it.

3. Ask what each one opened on:

   ```text
   What did each critic receive?
   ```

   Claude reports three agent deliveries, one per model: the haiku critic with the `brief`
   version, and the sonnet and opus critics with the full checklist.

Within one message, the plugin matches agents of one kind to their models in the order they
start, and Claude Code does not promise that order. Where each agent must be certain of its own
model's rules, ask for the agents one message at a time.

## What you have now

One kind of agent that opens on rules sized for whichever model runs it.

## Related

- [Keep a rule away from one model](keep-a-rule-from-a-model.md): withhold a rule from a model
  in place of rewording it.
- [Measure what your rules cost](measure-what-rules-cost.md): see the tokens each agent carries.
- [Delivery](delivery.md): reference for how an agent's model is decided.
