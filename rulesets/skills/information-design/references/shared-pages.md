# Shared pages: one-pagers, pitches and interactive explainers

Read this when the artifact will be sent to people who were not in the conversation and must stand on its own: a one-page summary, a proposal or pitch, a slide sequence, a dashboard, an interactive page where the reader changes inputs.

Templates: `templates/one-pager.md`, `templates/pitch.md`, `templates/explainer.html`.

## Contents

- Shape the argument
- One-pagers
- Pitches and slide sequences
- Interactive explainers
- Dashboards
- Make it travel
- Check list

## Shape the argument

### Lead with the answer and the ask

- When: the reader must decide, approve, fund or act.
- Do: put the conclusion and what you want from the reader at the top, in one or two sentences. Under it, give the few reasons that support it, each a statement. Under each reason, give its evidence. A reader who stops after the top knows the ask; one who reads a level down knows why.
- Check: the first screen answers "what is this, what do you want from me, and by when or under what condition".

### Group the support into a few parallel reasons

- When: organising the body.
- Do: sort supporting points into three or four groups that do not overlap and that together cover the case. State each group as a claim. Order them by importance, by sequence, or by the structure of the thing discussed, and keep that one ordering.
- Check: each group heading is a sentence someone could disagree with, and no point fits two groups.

### Guide first, then let the reader explore

- When: the artifact has both a message and data the reader may want to examine.
- Do: open with a fixed, author-led path that makes the point: a short sequence of views with the message stated in each. After the point is made, open the material up: filters, the full table, the controls. Do not open with an empty tool and expect the reader to find the story.
- Check: a reader who touches nothing still gets the message, and the free exploration comes after it.

### Frame without slanting

- When: writing the title, the opening and the annotations. The framing decides what readers take away, more than the data does.
- Do: make each headline claim one the evidence on the page supports as shown. State what was left out and why. Give the strongest counter-consideration its own line.
- Check: someone who disagrees would accept the headline as an accurate description of the evidence shown.

## One-pagers

### Fit one decision on one page

- When: writing a summary, proposal or brief.
- Do: use the fixed sections of `templates/one-pager.md`: the ask, the situation, the proposal, the evidence, the cost and risk, the alternatives, the next step. Keep each to a few lines. Put one figure or table at most, the one that carries the argument. Link everything else.
- Check: it fits one printed page or one screen and a bit, and every section has content specific to this case.

### Make numbers comparable

- When: the page holds costs, benefits or metrics.
- Do: give each number its unit, its period and its comparison. Put parallel numbers in a table with the same units. Round to the precision the decision needs.
- Check: no number stands without "per what" and "compared to what".

## Pitches and slide sequences

### One message per slide, stated in its title

- When: building slides or a paged sequence.
- Do: write each slide's title as the sentence that slide proves. The body is the evidence for that sentence: one chart, one diagram, one short list or one quote. If a slide needs two titles, make two slides.
- Check: read the titles alone, in order. They tell the whole argument.

### Order the sequence as a story with a turn

- When: ordering slides.
- Do: use the arc in `templates/pitch.md`: the situation the audience recognises, the problem or change that makes it untenable, what is at stake, the proposal, the evidence it works, what it costs and risks, the ask. Open with the audience's situation, in their terms.
- Check: each slide answers the question the previous one raised.

### Decide whether it will be presented or read

- When: before designing slides.
- Do: for slides shown while someone speaks, keep the picture and a few words on screen and put the sentences in speaker notes. For a deck sent to be read alone, write full-sentence titles and enough text for each slide to be understood without a voice, or send a written page instead. If it must do both, make the read-alone version and present from it sparingly, or make two versions.
- Check: you know which case this is, and a person in that case can follow every slide.

### Direct attention on each slide

- When: a slide holds a chart, table or diagram.
- Do: highlight the one part the title is about with a single contrasting colour or a callout, and mute the rest. Build a complex picture in stages only if each stage adds one idea.
- Check: the eye lands first on the part the title names.

## Interactive explainers

### Keep the essentials visible without interaction

- When: any interactive page. Most readers of a shared page scroll and read; few click, hover or type.
- Do: show the message, the main picture and the key numbers on load, with sensible defaults already set. Put nothing essential behind a hover, a tab, a click or a collapsed block. Interaction lets a willing reader go further.
- Check: load the page and touch nothing: the claim, its evidence and its limits are all on screen or reachable by scrolling. Print the page: nothing essential is missing.

### Let the reader change the assumptions

- When: the point depends on inputs the reader may doubt or want to vary.
- Do: expose those inputs as controls, and bind the picture and the stated result to them so both update at once. Start from the author's assumptions and show them as a reference the reader's settings are compared against. Offer a reset. Keep to about four controls; each one more divides attention.
- Check: moving a control changes a number or mark the reader is looking at, immediately, and the starting state can be restored in one action.

### State the result in words, live

- When: controls change a picture.
- Do: write the outcome as a sentence that updates with the controls ("At 8% growth the value doubles by step 9"). A reader who cannot see the chart, or cannot read it, gets the result from the sentence. Announce it to assistive technology as a status.
- Check: the sentence changes when a control changes, and is correct at the extremes of each control.

### Overview first, then detail on request

- When: the data is larger than one view.
- Do: show the whole first, at a level where its shape is visible. Then let the reader narrow by filtering or zooming, and get the details of one item on request. Keep the reader oriented: show what filter is active and how to clear it.
- Check: the first view shows all the data in some form, and every filtered view says what it is filtered to.

### Give the reader control of pace and motion

- When: content unfolds in steps or animates.
- Do: advance on the reader's action, never on a timer. Provide next and back. Let animation be paused and replayed, and show a static sequence when the reader's system asks for reduced motion.
- Check: nothing moves or changes until the reader acts, except in response to their last action.

### Build for every input and every screen

- When: any control or interactive mark.
- Do: use native controls (button, range input, select, details). Make every action available from the keyboard, with a visible focus indicator. Make each target at least 24 by 24 CSS pixels. Give text a contrast ratio of at least 4.5 to 1 with its background, and large text and meaningful graphics at least 3 to 1. Give every control a visible label. Lay out in one column that reflows on a narrow screen.
- Check: complete every interaction with the keyboard alone; run `scripts/check_palette.py` with `--text` for the colours used.

### Ship one file that opens anywhere

- When: delivering an interactive page.
- Do: put markup, styles, script and data in a single HTML file with no network requests, system fonts only, and both light and dark colours. It then opens from a file path, an attachment or any static host. Start from `templates/explainer.html`.
- Check: open the file with the network off; it renders and works.

## Dashboards

### Lead with the state of things, in words and numbers

- When: a page readers return to for status.
- Do: lead with the few numbers that say whether things are fine, each with its comparison (target, previous period) and direction. Follow with the charts that explain them, then the detail tables. Keep one scale and one colour meaning for the same measure everywhere on the page.
- Check: a returning reader can tell from the first screen whether anything needs their attention, and where.

### Show a number with what makes it good or bad

- When: displaying a metric.
- Do: next to the value, show the reference that gives it meaning, as a second number or a compact bar against a target. Avoid dials and gauges; they spend the most space on the least information.
- Check: every headline number can be judged good, bad or normal from what is beside it.

## Make it travel

### Make the artifact self-explaining

- When: anything shared beyond the conversation.
- Do: state on the artifact what it is, the date of the data, the scope, and what is asked of the reader. Define terms the audience may not share. Spell out the conversation's shorthand.
- Check: a person who receives only this file, with no message around it, knows what it is and what to do with it.

### Look at what you made

- When: before handing over anything rendered.
- Do: render it and look: overlapping labels, clipped text, wrong order, empty states, narrow-screen layout. If you cannot render or view it in this environment, say so plainly in the hand-over, and name what remains unchecked.
- Check: the hand-over message says either that the rendered result was inspected, or exactly what was not.

## Check list

1. The ask and the answer are at the top.
2. Three or four parallel reasons, each a claim, each with its evidence.
3. Slide titles alone tell the argument; one message per slide.
4. Without any interaction, the page delivers its message and its limits.
5. Controls are few, labelled, keyboard-operable, and reset in one action; the result is stated in live text.
6. Nothing advances on a timer; motion has a static equivalent.
7. The file is self-contained and self-explaining.
8. The rendered result was looked at, or the hand-over says it was not.
