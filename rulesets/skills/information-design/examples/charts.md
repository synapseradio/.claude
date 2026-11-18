# Worked examples: charts and numbers

Each example shows a before, an after, and the lesson applied. The instructions are in `references/charts.md`. A full spec pair sits in `examples/samples/chart-spec.before.json` and `examples/samples/chart-spec.after.json`; run `scripts/check_chart_spec.py` on both.

## 1. A chart of one number becomes a sentence

Before: a donut chart showing 87% filled, titled "Test coverage".

After:

```text
Test coverage is 87%, up from 81% at the last release; the target is 90%.
```

Lesson: one number needs its comparison, which a sentence gives. A chart of one value adds reading work and no information.

## 2. A seven-slice pie becomes sorted bars

Before: a pie chart of support tickets by category, seven slices, with a colour legend.

After:

```text
Billing questions are a third of all support tickets
Share of tickets by category, Q2, n = 4,210

Billing        ████████████████████████████████  33%
Login          ██████████████████            19%
Export         █████████████                 14%
Integrations   ██████████                    11%
Performance    ████████                       9%
Mobile app     ███████                        8%
Other          ██████                         6%
```

Lesson: with more than three parts, the reader compares parts, and lengths compare better than angles. Sort by size, label each bar directly, colour only the bar the message is about, and say in the subtitle what the whole is.

## 3. A truncated bar chart becomes an honest one

Before: columns for two months, the value axis running from 95 to 100, so that 96 looks a fifth the height of 99.

After, option A, bars from zero:

```text
March  ███████████████████████████████████████████████▉  96%
April  █████████████████████████████████████████████████▌ 99%
```

After, option B, when the three-point change is the message, dots on a fitted, labelled scale:

```text
Uptime rose from 96% to 99% between March and April

95%        96%        97%        98%        99%       100%
 |----------●----------|----------|----------●----------|
          March                            April
```

Lesson: a bar's length is its value, so bars start at zero. When a small change matters, switch to a form that encodes by position, fit the range, label the ticks and state the numbers.

## 4. Two value axes become two panels

Before: one chart with revenue as columns on the left axis and conversion rate as a line on the right axis; the line crosses the columns in June.

After:

```text
Revenue grew while conversion stayed flat

Revenue, thousand EUR per month
 Jan ▁▂▃▄▅▆▇█ Aug        120 → 310

Conversion rate, % of visits
 Jan ▄▄▅▄▄▄▅▄ Aug        2.1 → 2.2
```

Lesson: where two scales meet is an accident of how each was stretched, and readers take the crossing as meaningful. Give each measure its own panel on a shared time axis, or index both to a common start.

## 5. Nine coloured lines become one highlighted line

Before: a line chart with nine regions, nine colours and a legend.

After:

```text
The north region is the only one still below its 2021 level
Orders per month, indexed to January 2021 = 100

(Eight regions drawn in light grey, unlabelled except as "other regions".
 North drawn in one strong colour, labelled "North" at the end of its line.
 A horizontal reference line at 100, labelled "2021 level".)
```

Lesson: past about four coloured series the reader cannot track identity. Colour the series the message is about, grey the rest for context, and label directly. If every series matters equally, use small multiples.

## 6. A descriptive title becomes the takeaway

Before:

```text
Title: Weekly cart abandonment rate
```

After:

```text
Title:    Cart abandonment fell 13 points after the checkout redesign
Subtitle: Share of carts abandoned, weekly, all regions, weeks 20 to 36
Note:     Vertical rule at week 28, labelled "Redesign shipped"
Source:   Order events, analytics warehouse
```

Lesson: when presenting a finding, the title states it and the subtitle carries the neutral description. The annotation points at the event that explains the turn. For a chart the reader explores, keep the neutral title.

## 7. A bare forecast becomes a forecast with its uncertainty

Before: a single line extending into next quarter, with the caption "Projected signups".

After:

```text
Signups next quarter: most likely 11,000 to 14,000
The line shows the central forecast. The shaded band covers 8 of 10 outcomes the
model considers possible; 1 in 10 falls above it and 1 in 10 below.

(Solid line for actuals. Dashed line for the forecast. A band that widens with distance.)
```

For a general reader, the same thing as countable outcomes:

```text
Out of 20 equally likely outcomes for the quarter:
  below 11,000   ● ●
  11,000-14,000  ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●
  above 14,000   ● ●
```

Lesson: an estimate drawn as a bare line reads as a fact. Show the range, say in words what it covers, and for a general audience use counts of outcomes.

## 8. Red and green alone become position, sign and label

Before: a table of regions with cells filled red or green and no text.

After:

```text
Change in orders vs last quarter

South   ▲ +12%
East    ▲  +4%
West    ▼  -3%
North   ▼  -9%
```

Lesson: red and green are the pair most often confused, and colour alone fails in greyscale. Carry the direction with a sign, a symbol and sorted position; colour then only reinforces. Run `scripts/check_palette.py` on any palette that must distinguish.

## 9. A chart with no text route gets one

Before:

```markdown
![chart](abandonment.png)
```

After:

```markdown
![Line chart: weekly cart abandonment drops from about 71% to 58% after the redesign in week 28.](abandonment.svg)

The rate holds between 70% and 72% from week 20 to week 27. The redesign ships in week 28.
The rate falls each week until week 32 and then holds near 58%.

| Week | Abandonment rate |
| --- | ---: |
| 20 | 71.2 |
| 28 | 69.5 |
| 32 | 58.6 |
| 36 | 57.9 |
```

Lesson: the short alternative names the chart type and its message; the description gives the shape; the table gives the values. `scripts/text_alternative.py` computes the facts and the table from the CSV.

## 10. A chart where a table was wanted

Before: a grouped bar chart of 6 plans by 5 attributes with different units (price, seats, storage, support level, uptime).

After:

```markdown
| Plan | Price per seat | Seats | Storage (GB) | Support | Uptime commitment |
| --- | ---: | ---: | ---: | --- | ---: |
| Starter | 0 | 3 | 5 | community | none |
| Team | 12 | 50 | 100 | email | 99.5% |
| Business | 24 | 500 | 1,000 | priority | 99.9% |
```

Lesson: the reader looks up exact values across attributes with different units. That is a table's job. A chart forces unlike units onto one scale and makes the reader estimate numbers the table states.

## 11. Decoration is removed and the message added

Before: a 3D column chart with a gradient background, a border, heavy gridlines, a legend for its single series, and data labels on every column.

After:

```text
(Flat columns in one colour on a plain background. Light horizontal gridlines only.
 No border, no legend. The title states the finding. The last column is labelled with
 its value, and one annotation marks the month the price changed.)
```

Lesson: remove what carries no information, lighten the scaffolding, and spend the space on the title, a direct label and the one annotation that explains the shape. Perspective distorts lengths, so 3D always goes.
