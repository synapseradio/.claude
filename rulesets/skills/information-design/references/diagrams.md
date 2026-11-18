# Diagrams and renders

Read this when showing structure rather than numbers: an architecture, a flow, a sequence, a state machine, a hierarchy, a timeline, a labelled picture of a thing, a rendered mock-up.

A diagram earns its place when the content is spatial or relational, so that position on the page can stand for a relation and the reader can find things by looking. A diagram that only decorates a list costs more to read than the list.

## Contents

- Decide whether it is a diagram
- Give the diagram one question
- Make every mark mean one thing
- Lay it out for the eye
- Label and explain
- Give the structure a text route
- Renders and mock-ups
- Check list

## Decide whether it is a diagram

### Draw only what words cannot hold in line

- When: tempted to add a diagram.
- Do: use a diagram when the reader must see connections, containment, branching, parallel activity or position. Use a numbered list for a straight sequence, a table for options against criteria, a decision table for combinations of conditions. Run the chooser on the structure:

```bash
python3 scripts/choose_form.py --question process --items 7 --branches 3
python3 scripts/choose_form.py --question structure --items 14
python3 scripts/choose_form.py --question steps --items 6
```

  The questions it knows for structure: `steps`, `process`, `decision`, `structure`, `hierarchy`, `interaction`, `states`, `schedule`, `options`.
- Check: the diagram shows at least one relation a list of its labels would lose.

## Give the diagram one question

### One diagram, one question, one level

- When: scoping a diagram.
- Do: write the question it answers ("which services does a checkout request pass through?"). Include only what answers it. Keep every box at the same level of detail: all systems, or all components inside one system, or all classes. For a second question, draw a second diagram.
- Check: the caption states the question or the answer, and no box is a detail of another box's insides unless it is drawn inside it.

### Stay within what a reader can trace

- When: the diagram grows.
- Do: keep to about a dozen nodes. Past that, draw an overview whose boxes are groups, and a detail diagram per group, with each group named identically in both. Keep participants in a sequence diagram to about six.
- Check: a reader can follow any one path from start to end without losing it; node count is at or under the limit, or the diagram is split.

## Make every mark mean one thing

### Fix the visual vocabulary

- When: choosing shapes, colours, line styles and arrowheads.
- Do: let each visual property encode one thing, and only one, across the diagram and across sibling diagrams: shape for kind of node, line style for kind of connection, colour for one grouping or for highlight. Leave a property uniform if it has nothing to encode. Use at most about four kinds of each.
- Check: for every difference in shape, colour, line or size, you can say what it means; no difference is accidental. Two things that look the same are the same kind.

### Make arrows say what moves

- When: drawing any connection.
- Do: label each arrow with what crosses it or what the relation is ("order placed", "reads", "depends on"), and point it in the direction of that flow. Use one arrow meaning per diagram; if you must mix data flow and dependency, give them different line styles and a key.
- Check: no arrow is unlabelled unless every arrow in the diagram has the same stated meaning.

### Add a key for anything not labelled in place

- When: the diagram uses more than one shape, colour or line style.
- Do: include a small key, or label the first instance of each in place.
- Check: a reader new to the notation can decode every mark from the diagram itself.

## Lay it out for the eye

### Let position carry meaning, or nothing

- When: placing elements.
- Do: pick a reading direction and keep it: left to right or top to bottom for flow and time. Put things that belong together close together, and enclose a group in a labelled boundary. Align elements on a grid; a misalignment reads as a difference. Give elements of equal rank equal size.
- Check: the main path runs in one direction without doubling back, and nearness always signals relatedness.

### Minimise crossings and bends

- When: routing connections.
- Do: reorder nodes to remove line crossings, keep lines straight or with one bend, and keep the main path the straightest. Where many things connect to one shared thing, show the shared thing once as a labelled bar or boundary rather than a star of crossing lines.
- Check: you can count the crossings, and each remaining one was unavoidable.

### Show the main path first

- When: a flow has a normal case and exceptions.
- Do: draw the normal path prominently, straight through the middle. Put error and edge paths to the side in a lighter weight, or in their own diagram.
- Check: a reader's eye lands on the normal path first.

## Label and explain

### Label in the reader's vocabulary, in place

- When: naming elements.
- Do: use the names the reader will meet elsewhere: in the code, the UI, the docs. Put text inside or beside the element. Keep labels horizontal. Use a real text size: nothing the reader must zoom to read.
- Check: every name in the diagram appears with the same spelling in the surrounding text.

### Pair the diagram with its sentence

- When: placing the diagram in a page or reply.
- Do: put the sentence that says what the diagram shows directly before it, and walk the main path in words directly after it, using the same names in the same order.
- Check: the text around the diagram and the diagram never use two names for one thing.

## Give the structure a text route

### Write the structure as text too

- When: every diagram.
- Do: give a short alternative that says what kind of diagram it is and its point. Then give the structure in text: for a flow, the numbered steps with each branch; for a structure, a list of parts and a list of "A sends X to B" lines; for a hierarchy, an indented list; for states, a table of state, event and next state. Diagram source such as Mermaid in a fenced block is not this text route: it is another encoding to decode.
- Check: a reader with the text alone could redraw the diagram's nodes and connections.

### Prefer text-based source the reader can render

- When: producing a diagram in a Markdown context.
- Do: write the diagram as source in a fenced block when the destination renders it; otherwise produce an SVG file, which stays sharp and keeps its text selectable. Run `scripts/detect_tools.py` to see which renderers the machine has. Without one, deliver the source plus the text route, and say that the layout has not been looked at.
- Check: the reader can open what you delivered with what they have.

## Renders and mock-ups

### Show a render at the fidelity of the decision

- When: showing a UI mock-up, a layout or a visual concept.
- Do: match the finish to the question. For "is this the right structure?", show boxes and real labels with no styling, so reviewers discuss structure. For "is this the right look?", show the styled version. Use realistic content, including long names, empty states and error states, since placeholder text hides the problems.
- Check: the render's level of polish matches what you want feedback on, and you say which.

### Point at what changed

- When: showing a before and after, or a proposed change in a larger picture.
- Do: put before and after side by side at the same scale and crop, and mark the differences with a callout or highlight. Number the callouts and explain each number in text.
- Check: a reader can find every difference without hunting.

## Check list

1. The diagram answers one stated question at one level of detail.
2. About a dozen nodes or fewer, or split into overview and details.
3. Every shape, colour and line style means one thing, with a key.
4. Every arrow is labelled and points the way things flow.
5. One reading direction, aligned, few crossings, main path prominent.
6. Names match the surrounding text.
7. A text route gives the same structure.
8. You looked at the rendered result, or said that you could not.
