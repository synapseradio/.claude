# Worked examples: one-pagers, pitches and interactive pages

Each example shows a before, an after, and the lesson applied. The instructions are in `references/shared-pages.md`.

## 1. A chronological write-up becomes answer first

Before:

```markdown
# Search investigation

In March we noticed complaints about search. We first looked at the logs, then ran a
survey, then benchmarked three engines... (the recommendation appears in the last paragraph)
```

After:

```markdown
# Replace the search engine with the hosted option

**Ask:** approve 18,000 per year and one engineer for one quarter. Decision needed
before the Q3 planning meeting.

## Why this

| Reason | Evidence |
| --- | --- |
| Search is the top complaint | 31% of support tickets in Q1 mention search |
| The current engine cannot be fixed cheaply | relevance tuning took 6 weeks and moved satisfaction by 2 points |
| The hosted option tested best | 78% of test queries answered in the top 3, against 52% today |
```

Lesson: lead with the conclusion and the ask. Support it with a few parallel reasons, each a claim with its evidence. The story of how you found out goes in a linked appendix.

## 2. Topic slide titles become an argument

Before:

```text
1. Background
2. Market
3. Product
4. Data
5. Financials
6. Next steps
```

After:

```text
1. Small clinics still schedule by phone, and lose one booking in five to missed calls.
2. Online booking tools are built for chains and priced out of a two-person clinic's reach.
3. We give a clinic online booking that works from the phone number it already has.
4. Forty pilot clinics recovered an average of eleven bookings a month.
5. A clinic pays back the yearly price with the bookings recovered in its second month.
6. We ask for 400,000 to reach 1,000 clinics.
```

Lesson: each title is the sentence its slide proves. Read in order, the titles are the pitch, and each answers the question the one before it raised.

## 3. A slide the speaker reads becomes a slide the audience sees

Before: a slide with six bullet sentences, which the presenter reads aloud.

After:

```text
On screen:   the title "Forty pilot clinics recovered eleven bookings a month",
             one bar chart (bookings before and after, per clinic), the "after" bars
             in the accent colour.

In notes:    the six sentences, which the speaker says.

Leave-behind: the one-pager, with the same chart and the notes as text.
```

Lesson: people cannot read a paragraph and listen to the same words at once. The screen carries the picture and a few words, the voice carries the sentences, and a transcript or leave-behind serves whoever reads it later or cannot hear.

## 4. An empty tool becomes guided, then open

Before: a shared page that opens on a dashboard of filters and an empty chart, captioned "Explore our churn data".

After:

```text
On load:   Headline: "Customers who never invite a teammate are three times as likely
           to leave." Under it, the chart that shows this, preset and annotated.

Scroll:    Two more preset views, each with its sentence: by plan, by company size.

Then:      "Look at your own segment": the filters, starting from the last preset.
           The active filters are listed above the chart, with "Clear all".
```

Lesson: make the point with a fixed path first, then open the data. A reader who never touches a control still leaves with the message.

## 5. The message behind a hover comes out

Before: an interactive chart whose values, series names and the key comparison appear only in tooltips.

After:

```text
Visible without interaction: the title stating the finding, direct labels on the two
series, the values at the start and end of each line, one annotation.

On hover or focus: the exact value at any point (an addition).

Below the chart: "Show the data" opens the full table.
```

Lesson: most readers do not hover, and touch screens, print and screen readers cannot. Everything essential is on the page; interaction adds precision for those who want it.

## 6. A static claim becomes assumptions the reader can change

Before:

```text
"At current growth we will need a second warehouse in 14 months."
(The reader does not believe the growth assumption and has no way to test another.)
```

After, built on `templates/explainer.html`:

```text
Claim, in words, at the author's assumptions.

Two controls: "Monthly order growth" and "Orders one warehouse can ship".
The dashed line keeps the author's assumptions; the solid line follows the controls.

A sentence that updates live: "At 3% growth and 40,000 orders of capacity, the first
warehouse is full in month 22, eight months later than the starting assumptions."

Reset button. Table of every value. A section stating what the model leaves out.
```

Lesson: when the conclusion turns on inputs a reader may doubt, expose those inputs. Keep the author's version visible as the reference, state the result in live text, keep the controls few, and offer a reset.

## 7. Timed slides become reader-paced steps

Before: an explainer that advances through five animated scenes on a timer and loops.

After:

```text
Five steps, each a static picture with its sentence. "Next" and "Back" buttons, also
on the arrow keys. The transition between steps animates only when the reader's system
allows motion; otherwise the picture changes at once. All five steps print in sequence.
```

Lesson: the reader sets the pace. Nothing moves until they act, every state exists as a static picture, and the whole thing survives printing.

## 8. A page that needs the network becomes one file

Before: an HTML page that loads a chart library, two fonts and its data from other servers. Opened from an email attachment on a train, it shows a blank rectangle.

After:

```text
One .html file: inline styles, inline script, the data as a literal in the script,
system fonts, light and dark colours, no external requests. The chart is inline SVG
drawn by a few dozen lines of script, and the same data sits in a table in the page.
```

Lesson: a shared page must open from disk, offline, on a machine with nothing installed. Start from `templates/explainer.html`.

## 9. A dashboard of charts becomes status first

Before: twelve equally sized charts in a grid, no numbers, no indication of what is normal.

After:

```text
Top row:   Orders today 1,284 (▲ 6% vs same day last week)
           Failed payments 2.1% (target under 1.5%)   ← flagged
           Median delivery 2.3 days (target 3)

Below:     The two charts that explain failed payments: by provider, by hour.

Further:   Detail tables, collapsed.
```

Lesson: a returning reader wants to know whether anything needs attention. Lead with a few numbers, each beside the reference that makes it good or bad, flag the one that is off, and put its explanation directly under it.

## 10. A shared file explains itself

Before: a file named `analysis_v3_final.html` whose first screen is a chart titled "Results".

After:

```text
Title:      "Checkout redesign: effect on abandonment"
Under it:   "Data: weeks 20 to 36, all regions. Prepared for the checkout team's
             review. Asked of you: confirm or challenge the conclusion in section 1
             before the rollout decision."
Then:       the conclusion, then the evidence.
```

Lesson: a person who receives only the file must be able to tell what it is, how current it is, what it covers and what is asked of them.
