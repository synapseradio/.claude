# Decompose: Break Wholes into Parts by Finding Natural Divisions

### 1. Define the Whole

State what is being examined. Name why decomposition helps: complexity, distinct subparts, or structural understanding needed. If unclear, ask before proceeding.

### 2. Identify Relevant Part-Whole Relations

Select only the relation types that naturally fit. Most things decompose through 1-3 types. Forcing every type creates artificial structure.

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

### 3. Find the Natural Joints

For each relevant relation type, identify where boundaries already exist. A cut sits at a joint when:

- The interface stays small: how the parts connect can be stated in far fewer words than the parts themselves
- The parts change for independent reasons
- Properties change abruptly across the boundary rather than gradually

Follow inherent structure rather than imposing arbitrary categories. Good decomposition carves at the joints that already exist.

### 4. Verify Coverage and Connections

Check that identified parts account for the whole with no gaps, and that no two parts claim the same territory — overlap double-counts effort and blurs responsibility. Then map how parts relate:

- **Dependencies**: Do some parts depend upon others?
- **Interactions**: How do parts interact? What emerges from these interactions?
- **Containment**: Is any part contained by another?

### 5. Recurse if Needed

Apply decomposition to any part that remains too complex. Name the relation type at each level: part-of composes only within a single type. Your arm counts as a component of you, and you as a member of the team, yet your arm does not belong to the team. Stop when a part can be acted on or verified directly, or when further cutting grows the interfaces more than it shrinks the parts.

## Before and After

**Before**: Apply the epistemic relation to the turn itself — map what you know, assume, must verify, and must ask. Direct attention to the vital 20%.

**After**: Trace reasoning through the parts. Look for root causes within the structure. Analyze interconnections, feedback loops, and emergent behavior between parts.

## From Parts to Questions

Decomposition earns its keep when it changes the next action — and mid-conversation, the next action often means asking. Three disciplines turn a parts map into strong questions:

- **Divide before you ask.** Never ask about an undivided whole. Choose the relation first, and the question inherits its shape: which stage (phases), which member (members), what limit (constraints).
- **Aim questions at the seams.** After cutting, spend questions on the interfaces: what crosses this boundary, who owns the crossing, what happens at the handoff. Parts lists yield confirmation; boundary questions yield discoveries.
- **Ask only what moves you across a boundary.** Decompose your own uncertainty into cases first. A question earns its slot when each possible answer lands in a different part. If every answer leaves the next action unchanged, the map needs more cutting, not the user.

One move runs upward: every whole arrives as someone else's part. Check whether the user's stated whole belongs to a larger one they did not mention — the slice may not name the real subject.

## Source

The object relations descend from Winston, Chaffin & Herrmann (1987), "A Taxonomy of Part-Whole Relations," Cognitive Science 11(4), 417-444 ([PDF](https://ifaa.unifr.ch/Public/TNAEntryPage/ref/Winston1987.pdf)). The paper's central finding motivates the recursion caveat: part-of composes within one relation type and fails across types. Qualities and the task relations extend beyond the source taxonomy.
