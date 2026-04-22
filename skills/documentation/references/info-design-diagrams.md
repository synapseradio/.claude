# Information Design: Diagrams, Tables, Screenshots

The rules here govern non-prose assets inside a doc: diagrams, tables, screenshots. The guiding principles come from Edward Tufte and, for screenshots specifically, Eric Raymond.

## Primary sources

| URL | Topic |
|-----|-------|
| https://www.edwardtufte.com/book/the-visual-display-of-quantitative-information/ | Tufte — *The Visual Display of Quantitative Information* (publisher page) |
| https://radicalresearch.llc/EA078_Fall2024/chartJunk.html | Quoted Tufte definition of chartjunk |
| http://www.catb.org/~esr/writings/taoup/html/ch18s06.html | Raymond — information density and screenshots |

## Chartjunk

Tufte defines the failure mode:

> "The interior decoration of graphics generates a lot of ink that does not tell the viewer anything new. The purpose of decoration varies — to make the graphic appear more scientific and precise, to enliven the display, to give the designer an opportunity to exercise artistic skills. Regardless of its cause it is all non-data-ink or redundant data-ink, and it is often chartjunk."
>
> — Tufte quoted at https://radicalresearch.llc/EA078_Fall2024/chartJunk.html (primary: *The Visual Display of Quantitative Information*, https://www.edwardtufte.com/book/the-visual-display-of-quantitative-information/)

The rule that follows: every element in a diagram either carries data or is removed.

## Data-ink

The book itself is organised around the data-ink ratio and related principles:

> The book covers "the data-ink ratio. Time-series, relational graphics, data maps, multivariate designs. Detection of graphical deception: design variation vs. data variation."
>
> — https://www.edwardtufte.com/book/the-visual-display-of-quantitative-information/

The working heuristic: maximise data-ink, strip non-data-ink. If an element can be removed without losing information, remove it.

## Diagram checklist

Before publishing a diagram:

1. Name the data each mark carries. If a mark carries no data, remove it.
2. Strip gridlines, 3-D effects, ornamental borders, and decorative colour.
3. Label axes, nodes, and arrows inside the diagram where possible — not only in a caption.
4. If the diagram encodes the same relationship as a sentence, replace it with the sentence.

## Tables

A table is a condensed diagram. The same rule applies: every column earns its presence by carrying data the reader needs for the claim being made. Delete columns that are present out of habit.

## Screenshots

Raymond's caution is explicit:

> "Try to hit a happy medium in information density. Too low is as bad as too high. Use screen shots sparingly; they tend to convey little information beyond the style and feel of the interface. They are never a good substitute for clear textual description."
>
> — http://www.catb.org/~esr/writings/taoup/html/ch18s06.html

Two decisions follow:

1. Prefer textual description over screenshot when the information is textual.
2. Use screenshots to show layout, colour, or visual state the text cannot convey.

Screenshots also rot fastest — the UI changes, the screenshot does not. Budget for maintenance or prefer text.

## Agent instructions

1. Before adding a diagram, ask: does the reader need a picture, or a sentence? Default to the sentence.
2. When a diagram is right, apply the chartjunk test: remove every mark that does not carry data.
3. For tables, test each column: would the reader still understand the claim without it?
4. For screenshots, apply Raymond's caution above. If the same information is conveyed by text, write the text.
5. Cite Tufte's publisher page or the radical-research page for the chartjunk definition; cite Raymond's URL for the screenshot caution.
