# Charts and tables of numbers

Read this when numbers must be shown: whether a chart is the right form, which chart, what it should say, and whether it says it truthfully.

Drawing mechanics, such as mark sizes, palette construction and hover behaviour, belong to whatever chart tooling is in use. This file decides what the chart is and checks that it is honest and readable.

Write the decisions down in `templates/chart-spec.json` before drawing, and run `scripts/check_chart_spec.py` on it.

## Contents

- Decide whether it is a chart
- Choose the form from the question
- Encode the important thing in the strongest channel
- Say the message in words
- Keep it honest
- Show uncertainty
- Remove what does not inform
- Check list

## Decide whether it is a chart

### Start from the reader's question

- When: before choosing any form.
- Do: write the question the reader brings, in their words, and the one sentence they should be able to repeat after looking. If you cannot write the sentence, you are still exploring the data; explore first, then present.
- Check: `question` and `takeaway` are filled in the spec.

### Prefer a sentence, number or table when one suffices

- When: the data is one or two numbers, or the reader will look up exact values.
- Do: state one or two numbers in a sentence with their comparison. Use a table when readers look up individual values, need exact figures, or compare along several attributes with different units. Use a chart when the shape matters: a trend, a gap, a ranking, a cluster, an outlier. Pair a chart with a table when both matter.
- Check: `scripts/choose_form.py --question value` or `--question lookup` describes your case, or the message is about a shape.

## Choose the form from the question

### Let the question pick the chart

- When: the content is a chart.
- Do: classify the question, count the items and series, and run the chooser.

```bash
python3 scripts/choose_form.py --question compare --items 8
python3 scripts/choose_form.py --question trend --series 7 --points 24
python3 scripts/choose_form.py --question part-to-whole --items 3
python3 scripts/choose_form.py --list
```

  The questions it knows for numbers: `value`, `lookup`, `compare`, `rank`, `trend`, `part-to-whole`, `distribution`, `relationship`, `deviation`, `flow`, `spatial`. Add `--over-time`, `--ordered`, `--uncertain`, `--audience expert` or `--medium interactive` where they hold.
- Check: the form in the spec is the one the chooser returned, or the spec's notes say why another fits this reader better.

### Prefer a form the reader already knows

- When: choosing between a familiar form and a novel one that fits the data slightly better.
- Do: for a general audience use bars, lines, dots and tables. Use a less familiar form (box plot, connected scatter, Sankey, horizon chart) only for readers who know it, or teach it on the spot with a labelled example and a sentence on how to read it.
- Check: a reader meeting the chart cold could say what a mark stands for.

## Encode the important thing in the strongest channel

### Rank the channels

- When: mapping fields to visual properties.
- Do: give the measure the message is about the most accurately read channel available, and work down.

| Rank | For quantities and ordered values | For categories |
| --- | --- | --- |
| 1 | position on a shared scale | position in separate regions or panels |
| 2 | position on unaligned scales | colour hue |
| 3 | length | shape |
| 4 | angle, slope | pattern or texture |
| 5 | area | |
| 6 | colour lightness or saturation | |
| 7 | volume | |

  People read position and length accurately, angle and area roughly, and colour intensity only as more or less. So: compare with bars or dots on one axis; never ask the reader to compare areas, bubbles or 3D volumes for a precise answer; use colour intensity for overview patterns such as heatmaps and maps.
- Check: the measure named in the takeaway sits on position or length. `check_chart_spec.py` warns when no measure does.

### Give colour one job

- When: colour appears in the chart.
- Do: decide which job it has, and use the matching scheme.

| Job | Scheme |
| --- | --- |
| highlight | one strong colour for the subject of the message, grey for everything else |
| identity of categories | distinct hues, at most about four in colour, the rest grey or in separate panels |
| magnitude | one hue from light to dark |
| polarity around a midpoint | two hues with a neutral middle |

  Keep one colour for one thing across every chart in the same document. Never use a rainbow scale for magnitude. Add a second cue wherever colour carries identity, and run `scripts/check_palette.py` on the palette with its background.
- Check: `colour.job` is set in the spec, `second_cue` is set when the job is identity, and the palette check exits 0.

### Compare by putting things side by side on one scale

- When: the reader must compare groups, periods or scenarios.
- Do: put the things compared next to each other on a shared axis. For many series, draw small multiples: the same small chart repeated, one per series, with identical axes, ordered meaningfully. Readers compare what they can see at once far better than what they must remember from another page or animation frame.
- Check: the two things the takeaway compares are visible together, on the same scale.

## Say the message in words

### State the takeaway in the title when making a claim

- When: the chart supports one finding you are presenting.
- Do: write the finding as the title ("Abandonment fell 13 points after the redesign"). Put the measure, unit, scope and period in the subtitle. Readers remember the title's message above all else in the chart, so the title must say only what the data shows.
- When instead: the chart is reference material, the reader is exploring, or the finding is contested. Then write a neutral descriptive title and let the reader conclude.
- Check: the title's claim can be verified by looking at the chart, and the subtitle answers "what, where, when, in what unit".

### Label directly

- When: the chart has series, categories or notable points.
- Do: write names on or beside the marks they name. Replace a legend with direct labels wherever they fit; if a legend is needed, order it as the marks are ordered. Label the axis with what it measures and its unit. Label values on the marks only where the reader needs the number.
- Check: the reader never has to match a colour swatch to a mark across the chart.

### Annotate what the reader should see

- When: a point, a turn, a gap or an event explains the message.
- Do: mark it in the chart with a short note at the spot: the event that changed the trend, the threshold, the outlier and its reason. Keep to the few annotations that serve the takeaway.
- Check: each annotation supports the takeaway, and a reader who sees only the chart gets the same point as one who reads the text around it.

### Name the source and the date

- When: every chart.
- Do: state where the data comes from and what period it covers, in a note under the chart.
- Check: `data.source` and `data.period` are filled in the spec.

## Keep it honest

### Make the picture proportional to the numbers

- When: every chart.
- Do: keep the visual size of an effect equal to its size in the data. Start bar and area scales at zero, since their length is the value. Use even intervals on every axis; mark any break or log scale in words. Scale symbols by area, and say so. No perspective, no 3D.
- Check: a bar twice as long stands for a number twice as large. `check_chart_spec.py` rejects a length form with a non-zero baseline and any `effects`.

### Choose a line chart's range on purpose

- When: a line or dot chart, where position carries the value and a zero baseline is optional.
- Do: set the range so that the variation that matters to the reader is visible and neither flattened nor inflated: usually a little wider than the data's range, or a range the domain treats as meaningful. Show the tick labels clearly and state the range in the text alternative. If the reader should judge the change against the total, start at zero.
- Check: `reason_not_zero` is filled when the baseline is not zero, and the chart's impression matches a sentence stating the change with its numbers.

### Use one value scale

- When: two measures with different units are tempting to overlay.
- Do: draw two panels, one above the other, sharing the horizontal axis; or convert both to an index or to percent change from a common start and draw them on one scale. Two independent value axes let the author manufacture any crossing or correlation by rescaling, and readers misread them.
- Check: `value_scale.count` is 1.

### Show enough context to judge the number

- When: a figure could look large or small depending on what surrounds it.
- Do: include the comparison a fair reader would ask for: a longer period, the base rate, the denominator, the peer group, the target. Give rates as well as counts when groups differ in size. Adjust money for inflation over long spans, and say so.
- Check: the question "compared to what?" is answered inside the chart or its subtitle.

### Do not imply what the data cannot show

- When: the data is a correlation, a sample, a model output or a short series.
- Do: say which it is. Avoid a causal title for a correlation. Avoid a trend line through a handful of points. Keep the gaps where data is missing visible. State exclusions and definitions that change the picture.
- Check: every claim in the title and annotations is one the method supports.

## Show uncertainty

### Show that an estimate is an estimate

- When: values come from a sample, a model, a forecast or a noisy measurement.
- Do: show the uncertainty or state it; a bare line or bar reads as a certainty. Say in words what the displayed range means.
- Check: `uncertainty.shown` is true with `as` and `meaning` filled whenever `data.estimated` is true.

### Choose the form by the audience

- When: drawing uncertainty.
- Do:

| Audience and medium | Form |
| --- | --- |
| general readers, static | outcomes as countable dots (for example twenty dots, each one outcome in twenty), or a shaded band with a plain label; state odds as "about 3 in 20" |
| general readers, interactive or animated | a set of possible outcomes drawn one after another, plus a static summary |
| readers trained in statistics | an interval, labelled with its kind and level, or the full distribution |
| a forecast path | a fan of widening bands, or a handful of sample paths |

  A bar with an error whisker is widely misread: readers treat values inside the bar as likelier than values above it, and rarely know which interval the whisker shows. If you use an interval mark, put it on a dot, and label it.
- Check: the caption or annotation names what the range covers, and a general reader could say roughly how likely a given outcome is.

## Remove what does not inform

### Strip the non-data ink, then add back what helps

- When: finishing any chart.
- Do: remove borders, background fills, heavy gridlines, redundant tick marks, decorative icons, shadows, gradients and repeated labels. Lighten what remains of the scaffolding so the data is the darkest thing. Then add what carries the message: the title, direct labels, the annotation.
- Check: erasing any remaining element would lose information or orientation.

### Embellish only for a reason

- When: the chart is for a broad audience and must be noticed and remembered, as in a pitch, a poster or a public page.
- Do: one recognisable image or pictogram tied to the subject can make the chart more memorable without reducing accuracy, provided it distorts no value and covers no data. For analysis, dashboards and documentation, leave it out.
- Check: with the embellishment removed, every value reads the same.

## Check list

1. The spec names the question and the takeaway.
2. The form came from the question and the data's shape.
3. The key measure is on position or length, on one scale.
4. The title says the message or neutrally describes; the subtitle gives measure, unit, scope, period; marks are labelled directly; the source and date are stated.
5. The picture is proportional: zero baseline for bars, no dual axis, no 3D.
6. Estimates show their uncertainty in a form this audience reads.
7. Colour has one job, passes `check_palette.py`, and never works alone.
8. The chart has a short alternative and a description or table (`scripts/text_alternative.py`).
9. `check_chart_spec.py` exits 0, and you looked at the rendered result, or said that you could not.
