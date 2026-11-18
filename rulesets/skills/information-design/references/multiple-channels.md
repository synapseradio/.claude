# More than one channel

Read this when one form may not reach every reader, or when an idea has a shape that one form carries badly. A channel is a route into the reader: written words, a picture, a table, a number, a worked example, something to manipulate, speech, sound, touch.

Two reasons to use more than one. People build a stronger model from words and a picture together than from either alone. And any single channel is closed to someone: a reader who cannot see the chart, cannot hear the narration, cannot tell the colours apart, or reads in a second language.

## Contents

- Choose the channel by the content
- Combine channels so they help
- Make every channel optional for someone
- What each medium offers
- Check list

## Choose the channel by the content

### Match the form to the shape of the idea

- When: choosing how to carry any idea.
- Do: pick the primary channel from what the content is, and give that channel to every reader.

| The content is | Carry it mainly in |
| --- | --- |
| a sequence of actions | numbered steps |
| a reason, a cause, an argument | sentences |
| parallel facts about parallel things | a table |
| a quantity compared, or changing | a chart, with the key numbers in words |
| parts and their connections, or positions in space | a diagram or picture |
| a relationship between inputs and an outcome | a worked example, or controls to move |
| a sound, a rhythm, a pronunciation | audio, with a written description |
| a physical action | a demonstration or picture sequence, with steps in words |

- Check: the primary form matches the row for the content, whatever the reader said about how they like to learn.

### Offer alternatives to all readers, and let them choose

- When: a reader says they are "a visual learner" or similar, or you are tempted to guess a reader's type.
- Do: take a stated preference as a request and honour it: lead with the form they asked for. Keep the form the content needs as well. Matching the form to a reader's self-described type has not been shown to improve learning; matching the form to the content, and offering more than one, has.
- Check: the reader got what they asked for, and nothing the content needs was dropped to give it.

## Combine channels so they help

### Put words and picture together

- When: a picture, chart or diagram appears with text about it.
- Do: put each label on or next to the part it names. Put the sentence that discusses a figure directly before or after it. Remove legends and keys the reader must look back and forth to decode, where a direct label fits.
- Check: no label is separated from its referent by more than a glance, and no figure sits on a different screen from its discussion.

### Give each representation a job

- When: adding a second or third representation of the same thing.
- Do: decide what it adds. It may carry different information (the chart shows the trend, the table gives exact values). It may narrow how the other is read (a picture that fixes what an ambiguous sentence means). It may show the same structure in a new form so the reader abstracts it (a case, then the formula). Cut a representation that has no such job.
- Check: for each representation, you can finish the sentence "this one is here so that the reader can ...", differently for each.

### Tie the representations to each other

- When: two or more representations of one idea share a page.
- Do: use the same names, the same order, the same units and the same colours for the same things in all of them. Say in words how they correspond where it is not obvious. A reader spends effort translating between forms, and unlinked forms cost more than they give.
- Check: pick any item in one representation; its counterpart in the others is found by the same name or colour.

### Signal what matters

- When: a picture or page holds more than the one thing the reader needs right now.
- Do: point at it: an arrow, a highlight colour used once, a callout, a bold term, a heading. Strip the picture of detail that serves no point on the page.
- Check: the cued element is the one the surrounding text talks about, and there is one cue per point.

### Keep spoken and written words from competing

- When: a person will speak over the artifact: a pitch deck, a recorded walkthrough, a narrated animation.
- Do: put on screen the picture and a few key words, and let the voice carry the sentences. Showing the full spoken text as on-screen text at the same moment makes people read and listen at once, and they take in less. Provide the full text as captions or a transcript that each viewer can turn on.
- Check: no slide or frame shows a paragraph that the speaker reads out; captions or a transcript exist.

### Use motion only for change

- When: animating anything.
- Do: animate to show a change over time, a transition between two states, or a cause producing an effect. Let the reader start, pause and replay it. Provide the key frames as a static sequence, and honour a reduced-motion setting by showing that sequence instead.
- Check: with motion disabled, the page still shows the before, the after, and what changed.

## Make every channel optional for someone

### Give every non-text item a text equivalent

- When: the artifact holds an image, chart, diagram, audio or video.
- Do: write the equivalent that carries the same information.

| Item | Equivalent |
| --- | --- |
| a simple image | a short text alternative saying what it shows and why it is there |
| a chart | a short alternative naming the chart type and its message, and a longer description or data table |
| a diagram | a short alternative, and the structure as a list or table: the parts, and what connects to what |
| audio | a transcript |
| video | captions, and a description of what is shown where the sound does not say it |
| an interactive control | a visible label, a keyboard route, and the result stated in text |

  `scripts/text_alternative.py` computes the facts and the table for a chart's data.
- Check: with images off and sound off, a reader can still get every point. Read the text equivalents alone and confirm.

### Refer to things by name, never by sense alone

- When: instructions or explanations point at something.
- Do: name the thing: "select **Export** in the toolbar". A reference by colour, shape, size, position or sound alone ("the green button", "the box on the right", "after the beep") fails for a reader who does not get that sense, or whose layout differs. A sensory cue may be added to a name.
- Check: delete every colour, shape, position and sound word from the instruction; it still identifies the thing.

### Never let colour work alone

- When: colour distinguishes, ranks or flags anything.
- Do: add a second cue that carries the same distinction: a text label, a shape, a pattern, a position, an icon with a name. Roughly one man in twelve and one woman in two hundred has a colour-vision deficiency, most often between red and green.
- Check: view it in greyscale; every distinction survives. `scripts/check_palette.py` reports the pairs that merge.

### Carry structure in the markup, where structure is heard

- When: the artifact is a page a screen reader or other tool may read.
- Do: use real headings in order, real lists, real tables with header cells, and link text that names its target. Visual styling that only looks like structure is silent to these readers.
- Check: the outline of headings alone reads as a table of contents for the page. `scripts/lint_doc_page.py` checks heading order and link text in Markdown.

### Give numbers a second form

- When: a number carries the point and the reader may not have a feel for its size.
- Do: state it exactly once, then give it a form the reader can picture: a comparison to something familiar, a ratio in whole numbers ("about 3 in 20"), or a per-person or per-item amount. Keep one denominator when comparing risks.
- Check: a reader could say whether the number is big or small, and compared to what.

### Keep drawings made of characters out of the reading order

- When: a reply or page may be read aloud by a screen reader, or pasted where fonts differ.
- Do: carry structure with real lists, tables and headings. A box drawn from line characters, an arrow built from punctuation, or a row of symbols used as a divider is read out character by character and falls apart in a proportional font. If a character drawing helps sighted readers, put it in a code block and give the same structure in words beside it. Use a symbol or emoji only next to the word it stands for.
- Check: read the text top to bottom as a flat stream of words; every relation is still stated.

### Write for the ear when it will be heard

- When: the output will be spoken: a voice reply, a script, narration, a page read by a screen reader.
- Do: say how many parts are coming, then name each as it arrives ("three steps; first, ..."). Keep one number or one comparison to a sentence, round it, and put the unit after it. Put the subject and verb early; a listener cannot look back. Repeat the key name in place of "it" or "the former". Close by restating the point. Replace a table with one sentence per row, in a fixed pattern.
- Check: read it aloud once without looking at the page; nothing depends on layout, and no sentence has to be heard twice.

### Write for a reader in a second language

- When: the audience is broad, public or international, or unknown.
- Do: use the common word, one term per thing, and full sentences with their small words kept in. Leave out idioms, wordplay and culture-bound references, or explain them. Write dates with the month as a word and numbers with their unit. Short sentences translate better, by person or by machine.
- Check: each sentence still means the same when translated word by word.

### Lighten the load for a tired or interrupted reader

- When: always; a reader's attention and memory vary with their day as well as with the person.
- Do: keep one task per screen, state where the reader is in a sequence ("step 2 of 5"), repeat the needed value at the point of use so nothing has to be carried from another page, and make every step safe to resume.
- Check: a reader who stops at any point and returns can tell where they were and what comes next.

### Add sound or touch where the medium has them

- When: the medium supports audio or physical output, and a reader cannot use the visual form, or the content is itself temporal.
- Do: for a data series, offer a description in words first; a pitch-mapped sound rendering of a trend can add to it and cannot replace it. For a document that will be embossed or printed for touch, keep diagrams sparse, lines well separated, and labels few with a key. Always keep the text route.
- Check: the non-visual form was added to a complete text equivalent, and the reader can get every point from the text alone.

## What each medium offers

| Medium | Channels you have | What to add for reach |
| --- | --- | --- |
| a chat reply | sentences, lists, tables, code blocks, maths, diagram source in a fenced block | describe any diagram in words as well; keep tables narrow |
| a Markdown doc page | the above, plus images and links | text alternatives, heading outline, descriptive links |
| a self-contained HTML page | the above, plus inline SVG, controls, disclosure, audio, motion | keyboard operation, visible focus, status text for results, reduced-motion and dark-mode handling, print layout |
| slides with a speaker | picture, few words, voice | speaker notes or transcript; a version that reads without the speaker |
| a printed page | static picture and text, no colour guaranteed | patterns or labels in place of colour; everything expanded |

## Check list

1. The primary form matches the shape of the content.
2. Every representation has its own job and shares names, order, units and colours with the others.
3. Labels sit on what they name.
4. Every image, chart, diagram, audio and video item has a text equivalent that carries the same points.
5. No distinction depends on colour alone, and no instruction on a sense alone.
6. Motion is controllable and has a static equivalent.
7. A reader who asked for a particular form got it.
