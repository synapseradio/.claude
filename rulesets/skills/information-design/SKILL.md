---
name: information-design
description: >-
  Reference for conveying anything to a person: an explanation, lesson, doc page, table, chart, diagram, pitch or interactive page. Load it before you explain or show something, to fit the form to the reader, teach in steps, and reach more than one sense.
---

# Information design

Information design is deciding what form an idea takes so that a particular person can find it, understand it, trust it and use it. It covers every form: sentences, steps, tables, numbers, charts, diagrams, examples, things to try, and sound or touch where the medium has them.

This is a reference. Settle the five questions below, follow the route for your task, and open only the files that route names.

## Before any form: five questions

Answer these in a line each before you choose a form. Where an answer is missing and would change the form, ask; otherwise state the assumption you made.

1. **Who is the reader, and what do they already know?** Name the first term they will not know.
2. **What question do they bring?** Write it in their words.
3. **What will they do with the answer?** Decide, act, look up, learn, or pass it on.
4. **Where will they meet it?** A chat reply, a rendered page, a slide with a speaker, a printout, a small screen, a screen reader.
5. **What can they not use?** A sense, a colour distinction, a tool, the network, your conversation's context.

## Route by task

| You are about to | Read | Start from | Check with |
| --- | --- | --- | --- |
| explain a concept, teach, onboard, or answer "how does this work" | `references/teaching.md` | `templates/explanation.md` | the check list in the reference |
| decide between a sentence, list, table, chart or diagram | this file, "Pick the form" | | `scripts/choose_form.py` |
| write or restructure a doc page, README, runbook or report | `references/doc-pages.md` | `templates/doc-page.md` | `scripts/lint_doc_page.py` |
| show numbers: a chart, a table of figures, a metric | `references/charts.md` | `templates/chart-spec.json` | `scripts/check_chart_spec.py`, `scripts/check_palette.py` |
| draw a diagram, or show a render or mock-up | `references/diagrams.md` | | the check list in the reference |
| write a one-pager, proposal, pitch or slide sequence | `references/shared-pages.md` | `templates/one-pager.md`, `templates/pitch.md` | the check list in the reference |
| build an interactive page, explainer or dashboard to share | `references/shared-pages.md` | `templates/explainer.html` | open it with the network off; keyboard only |
| reach readers who differ in senses, knowledge or preference; add text alternatives | `references/multiple-channels.md` | | `scripts/text_alternative.py`, `scripts/check_palette.py` |
| choose between two pieces of advice that conflict | `references/tradeoffs.md` | | |
| use a renderer, converter or library the machine may lack | `references/optional-tools.md` | | `scripts/detect_tools.py` |

Most tasks cross routes: a doc page with a chart reads both files. Read `references/multiple-channels.md` whenever the artifact holds anything that is not text.

Worked before-and-after examples for each route are in `examples/`: `explanations.md`, `doc-pages.md`, `charts.md`, `diagrams.md`, `shared-pages.md`. Open the one for your route when you want to see an instruction applied.

### When a better result needs a tool the machine lacks

Everything here works on a stock machine. If a diagram renderer, a converter or a chart library would give this reader a clearly better result, run `scripts/detect_tools.py`. If the tool is missing, ask the person whether you may install it, stating what is missing, what it adds over the route that needs no install, the exact command, and what it changes on the machine. Install only on a yes; otherwise take the zero-install route. `references/optional-tools.md` has the wording and the routes.

## Pick the form

The reader's question picks the form. Run the chooser for any case not obvious from this table.

| The reader asks | Give them |
| --- | --- |
| what is the number? | a sentence with the number and its comparison |
| what is the exact value for this item? | a table |
| which is bigger, what is the order, how did it change, how is it spread, do these move together? | a chart, by `scripts/choose_form.py` |
| what do I do, in what order? | numbered steps |
| which case am I in? | a decision table |
| which option should I pick? | a recommendation, then a comparison table |
| what connects to what, what contains what, who sends what to whom? | a diagram with a text route |
| why? what does this mean? | sentences, with an example |
| what happens if I change this? | a worked example, or controls to move |

## Rules that hold in every form

1. **Point first.** The conclusion, the answer or the purpose comes before its support, on the page and in each section.
2. **One job per unit.** One question per chart and diagram, one job per page, one message per slide, one idea per paragraph, one action per step.
3. **Form follows content.** Sequence in steps, parallel facts in a table, quantity on a shared scale, relations in a diagram, reasons in sentences.
4. **Say it in words as well.** Every picture has a title or sentence that states what it shows, and a text equivalent that carries the same information. The message survives with nothing clicked, hovered or played, and in print.
5. **Label in place.** Names sit on the things they name, in the reader's vocabulary, the same name everywhere.
6. **Never one sense alone.** No distinction rests on colour alone, no instruction on position, shape or sound alone.
7. **Proportional and sourced.** The visual size of an effect matches its size in the data; estimates show their uncertainty; the source and date are stated. A guess is marked as a guess in every form, a table cell and a diagram box included.
8. **Few things at once.** Include what changes what the reader does next. Put the rest a layer down, behind a link or a labelled section, and say that it exists. About four new items before they are used.
9. **Look at what you made.** Render and inspect it, or say plainly that you could not.

## Scripts

All scripts use only the Python standard library, run on Python 3.9 or later, need no network, install nothing, and write only to standard output. Run them from this skill's directory:

```bash
uv run --no-project scripts/<name>.py <arguments>     # where uv is present
python3 scripts/<name>.py <arguments>                 # otherwise
```

| Script | Does | Exit status |
| --- | --- | --- |
| `choose_form.py --question Q [--items N --series N --points N --branches N]` | names the form for a reader's question and the data's or structure's shape, with what to build and avoid; `--list` shows the questions | 0 |
| `lint_doc_page.py PAGE.md [--strict]` | reports where a Markdown page resists scanning: title, opening, headings, long prose, lists, tables, links, image alternatives | 1 on an error |
| `check_chart_spec.py SPEC.json` | checks a chart's decisions before drawing: message, scale, series, colour, uncertainty, text alternative | 1 on an error |
| `check_palette.py --colors '#hex,#hex' [--background '#hex' --text '#hex']` | checks contrast with the background and separation under colour-vision deficiency and in greyscale | 1 on a failure |
| `text_alternative.py DATA.csv [--unit U --form 'line chart']` | prints the facts for a chart's long description and its data as a Markdown table | 0 |
| `detect_tools.py` | lists optional tools as present or missing, with the zero-install route and the install command to ask about | 0 |

Each script takes `--help`, and all but `text_alternative.py` take `--json`. Sample inputs are in `examples/samples/`.

## Boundaries

This skill decides form, order, honesty and reach. It leaves these to other guidance where that exists in your context:

- how sentences are worded: writing-style guidance;
- how a piece is prepared with the person it speaks for: communication guidance;
- chart colours, mark sizes, palettes and hover behaviour: chart-building guidance;
- producing the rendered chart or diagram file: visualization tooling.

Where none of those is present, this skill's references are enough to produce a sound result in plain Markdown, SVG or self-contained HTML.

## Before you hand over

1. The five questions have answers, and the form matches the reader's question.
2. The route's check script exits 0, or its check list holds.
3. Every non-text item has its text equivalent.
4. The hand-over says what was rendered and inspected, and what was not.
