# Progressive Enhancement: Writing and Structuring Thoughts

Every output must work at a baseline — plain prose, complete sentences, no formatting required to land the meaning. Structure (headers, tables, lists, code blocks, diagrams) is enhancement: it activates when the medium renders it and the reader has the context to absorb it.

## Baseline first, enhancement under it

- The first sentence carries the load-bearing claim. A reader who stops there should not be misled.
- Subsequent paragraphs layer evidence, qualifications, and detail. The reader stops where their need is met.
- If you remove every header, table, and list, the prose underneath must still be coherent. Strip the scaffolding in your head before sending.

## Structure earns its place

- **Lists** are for items that are genuinely parallel. If the items aren't logically the same kind of thing, prose conveys it better; the list is false ornament.
- **Tables** are for genuinely tabular data — rows and columns where every cell in a column is the same kind of value. If a row's cells are heterogeneous, the table is doing the work of a paragraph and should be one.
- **Headers** are for sections a reader might want to skip to. If the document has no skipping audience, headers add weight without value.
- **Code blocks** are for code, commands, file paths, and verbatim strings. Not for emphasis, not for visual variety. A reader piping the page through plain text should still understand which strings are literal.
- **Diagrams** carry the burden of being legible without their caption — and of degrading to a meaningful description when the image cannot render.

## Don't assume the rendering medium

Markdown may not render at the destination — chat clients, plain-text exports, terminals without color, screen readers, downstream LLMs that strip formatting. The unformatted form must still work. This is the writing analogue of the CLI rule that every feature degrades when fzf, color, or a TTY is absent.

## Don't assume the reader's vocabulary

Define jargon on first use, or use the plain word. Acronyms expand on first appearance. A reader without the term should still follow the load-bearing claim — the term is the enhancement; the meaning is the baseline.

## When in doubt, write the prose first

If you find yourself reaching for a list, a table, or a header before the prose exists, you are designing the scaffolding before knowing what it holds. Write the paragraph first; then ask whether structure helps. Most of the time, the paragraph was enough.
