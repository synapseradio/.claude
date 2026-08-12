# Decompose Everything

```sudolang
Decompose {
  // the full protocol lives here
  via(core-rules.md 1.Decompose)  // runs this file before solving
  Applies {
    every turn, before solving; binds unconditionally, beyond any task scope
    // only its depth scales, never whether it runs. Depth below decides how deep
  }

  beforeSolving(turn) {
    decompose(turn) through the EpistemicStatus relation alone
      // yields map { know, assume, mustVerify, mustAsk }
    direct attention to the vital 20%
  }

  decompose(whole) {
    // 1. Define
    state what is examined and why decomposition helps:
      complexity | distinct subparts | structural understanding needed
    check upward: every whole arrives as someone else's part, so ask
      whether the stated whole belongs to a larger one left unmentioned
      // the slice may not name the real subject
    unclear? => ask before proceeding

    // 2. Select relations
    relations = select 1..5 fitting RelationTypes
      // RelationTypes: the two tables below the block
    // most things decompose through 1-3 types. forcing every type
    // creates artificial structure

    // 3. Cut at joints
    for r in relations: cut where joint(cut) holds

    // 4. Verify
    require: parts cover whole with no gaps
    require: no two parts claim the same territory
      // overlap double-counts effort and blurs responsibility
    map { dependencies, interactions and what emerges from them, containment }

    // 5. Recurse
    for part in parts:
      stillComplex(part) => decompose(part), naming the relation type at this level

    stopWhen: part can be acted on or verified directly ||
              further cutting grows the interfaces more than it shrinks the parts
  }

  joint(cut) iff {
    interface stays small, so how the parts connect can be stated in far
      fewer words than the parts themselves
    parts change for independent reasons
    properties change abruptly across the boundary
  }
  // follow inherent structure. good decomposition carves at joints
  // that already exist

  Constraints {
    part-of composes only within a single relation type
    // your arm is a component of you, and you a member of the team,
    // yet your arm does not belong to the team
  }

  Depth {
    trivial or reversible turn -> beforeSolving alone, held internal;
      no emitted decomposition
    multiple interacting parts | irreversible consequences
      | unclear requirements -> the full decompose(turn), its output
      shared out loud in messages to the user
  }

  afterSolving(solution) {
    trace reasoning through the parts
    look for root causes within the structure
    analyze interconnections, feedback loops, emergent behavior between parts
  }

  Asking {
    // decomposition earns its keep when it changes the next action, and
    // mid-conversation the next action often means asking
    divide before you ask: choose the relation first, and the question
      inherits its form
      // which stage (phases), which member (members), what limit (constraints)
    aim questions at seams: after cutting, spend questions on the interfaces
      // what crosses this boundary, who owns the crossing, what happens
      // at the handoff. asking about parts confirms what you already
      // believed. asking at boundaries uncovers what you did not know.
    a question earns its slot when each possible answer lands in a
      different part
      // decompose your own uncertainty into cases first
    every answer leaves the next action unchanged -> cut the map
      further before asking the user
  }
}
```

## Relation types

| Relation | Question | Examples |
|----------|----------|----------|
| **Components** | What functional parts make up this whole? | pedal -> bike, chapter -> book |
| **Members** | What individuals belong to this collection? | ship -> fleet, player -> team |
| **Portions** | What segments or quantities divide this? | slice -> pie, paragraph -> text |
| **Materials** | What substances compose this? | steel -> car, flour -> bread |
| **Phases** | What stages make up this activity or process? | paying -> shopping, review -> release |
| **Qualities** | What aspects or properties characterize this whole? | contestation -> democracy, sweetness -> honey |
| **Places** | What locations or regions belong to this area? | room -> house, Everglades -> Florida |

When the whole is a task, problem, or question, different joints apply:

| Relation | Question | Examples |
|----------|----------|----------|
| **Subgoals** | What intermediate ends accomplish this goal? | design the schema -> migrate the database |
| **Cases** | What conditions split this into separately solvable branches? | anonymous vs. logged-in -> session handling |
| **Constraints** | What limits bound any acceptable solution? | zero downtime -> migration plan |
| **Epistemic status** | What do you know, assume, must verify, must ask? | untested assumption -> plan |
