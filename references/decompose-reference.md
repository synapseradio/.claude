# Decompose: Break Wholes into Parts by Finding Natural Divisions

```sudolang
Decompose {
  decompose(whole) {
    // 1. Define
    state what is examined and why decomposition helps:
      complexity | distinct subparts | structural understanding needed
    check upward: every whole arrives as someone else's part — does the
      stated whole belong to a larger one left unmentioned?
      // the slice may not name the real subject
    unclear? => ask before proceeding

    // 2. Select relations
    relations = select 1..5 fitting RelationTypes
      // RelationTypes: the two tables under "Relation types" below
    // most things decompose through 1-3 types; forcing every type
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
    interface stays small — how the parts connect can be stated in far fewer
      words than the parts themselves
    parts change for independent reasons
    properties change abruptly across the boundary, not gradually
  }
  // follow inherent structure; good decomposition carves at joints
  // that already exist

  Constraints {
    part-of composes only within a single relation type.
    // Your arm is a component of you, and you a member of the team,
    // yet your arm does not belong to the team.
  }

  beforeSolving(turn) {
    decompose(turn) through the EpistemicStatus relation alone
      // yields map { know, assume, mustVerify, mustAsk }
    direct attention to the vital 20%
  }

  afterSolving(solution) {
    trace reasoning through the parts
    look for root causes within the structure
    analyze interconnections, feedback loops, emergent behavior between parts
  }

  toQuestions(parts) {
    // when the next action means asking, the parts map feeds the three
    // disciplines under "From Parts to Questions" below
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

## From Parts to Questions

Decomposition earns its keep when it changes the next action — and mid-conversation, the next action often means asking. Three disciplines turn a parts map into strong questions:

- **Divide before you ask.** Never ask about an undivided whole. Choose the relation first, and the question inherits its shape: which stage (phases), which member (members), what limit (constraints).
- **Aim questions at seams.** After cutting, spend questions on the interfaces: what crosses this boundary, who owns the crossing, what happens at the handoff. Parts lists yield confirmation; boundary questions yield discoveries.
- **Ask only what moves you towards, or across a boundary.** Decompose your own uncertainty into cases first. A question earns its slot when each possible answer lands in a different part. If every answer leaves the next action unchanged, the map needs more cutting, not the user.
