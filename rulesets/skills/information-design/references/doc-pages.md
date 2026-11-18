# Doc pages

Read this when writing or restructuring a page a person will consult: a README, a how-to, a reference page, a concept page, a runbook, a report, a long reply laid out with headings.

Most readers of a page scan it before they read any of it, and many never read all of it. They look at the title, the headings and the first words of paragraphs, and decide where to stop. Design the page for that reader. Sentence-level style is outside this file.

Start a new page from `templates/doc-page.md`. Check a finished page with `scripts/lint_doc_page.py`.

## Contents

- Decide what kind of page it is
- Build the top of the page
- Make the structure scannable
- Pick the form for each piece
- Layer the detail
- Check list

## Decide what kind of page it is

### Give the page one job

- When: before outlining.
- Do: name the reader's need, and write the page for that need alone.

| The reader wants to | Page kind | Shape |
| --- | --- | --- |
| learn by doing, guided | tutorial | one path, numbered steps, a visible result after each, no choices |
| get a specific task done | how-to | the goal in the title, prerequisites, numbered steps, how to confirm it worked |
| look something up | reference | consistent entries in a predictable order, tables, no narrative |
| understand why or how it works | explanation | prose with diagrams and examples, background and trade-offs |

  A page that mixes kinds serves none of its readers. Split it and link the parts.
- Check: the title and opening tell the reader which kind this is, and no section belongs to another kind.

### Sort each piece of content by type

- When: a draft mixes instructions, descriptions and definitions in running paragraphs.
- Do: mark each piece as one of these types and give it the form in the table.

| Content type | Says | Form |
| --- | --- | --- |
| procedure | what the reader does | numbered steps |
| process | what happens, by whom or what | numbered stages or a flow diagram |
| principle | a rule or policy to follow | a short statement, with its reason |
| concept | what a term means | definition, an example, a near miss |
| structure | what the parts are | a labelled diagram or a table of parts |
| fact | a value or a specification | a table or key-value list |

- Check: no block holds two types. A step that contains a definition has the definition moved out.

## Build the top of the page

### Put the point first

- When: every page, and every section.
- Do: state the conclusion, the answer or the purpose in the first sentences. Follow with what most readers need next, then the detail fewer need. A reader who stops anywhere has got the most important part so far.
- Check: cover everything but the title and first paragraph. A reader could still say what the page gives them and whether to go on.

### Open with what the page is for

- When: under the title.
- Do: write one short paragraph: what this covers, who it is for, and what the reader can do after it. For a how-to, add what they need before starting.
- Check: `lint_doc_page.py` reports no `opening-missing` or `opening-long`.

## Make the structure scannable

### Write headings that carry meaning alone

- When: writing any heading.
- Do: make each heading name what its section holds, in the reader's words, specific enough that it could not sit on another page. Put the distinguishing words first. Keep headings parallel in form within a level: all tasks, or all topics. Use each heading text once on the page.
- Check: read the headings alone, top to bottom. They work as a table of contents, and a reader can tell which section answers their question. `lint_doc_page.py` reports `heading-duplicate`, `heading-long`, `heading-skip`.

### Front-load paragraphs and list items

- When: writing body text under any heading.
- Do: start each paragraph and each list item with the words that tell the reader what it is about. A scanning eye catches the first two or three words of each line down the left side and little else.
- Check: read only the first three words of every paragraph and item; the page's content is still recognisable.

### Keep units short and labelled

- When: a section grows.
- Do: one idea per paragraph. Break a section that runs past a screen of unbroken prose with a subheading, a list or a table. Keep the outline to three heading levels; a fourth level means the page should split.
- Check: `lint_doc_page.py` reports no `paragraph-long`, `section-wall` or `heading-deep`.

### Group, and keep groups small

- When: a list, a menu, a set of options or a set of sections holds many items.
- Do: sort items the reader must hold in mind into groups of about four, each group with a label. A list the reader only scans to find one item can be long, if it is sorted in an order they can predict: alphabetical, numeric, or by sequence.
- Check: no flat list of unlike items runs past nine; `lint_doc_page.py` reports `list-long`.

### Use emphasis sparingly

- When: marking a term or warning.
- Do: bold the one or two terms per section a scanning reader must catch. Use a callout only for something whose miss causes damage. Emphasis on many things marks none of them.
- Check: `lint_doc_page.py` reports no `emphasis-heavy`; each callout names a consequence.

### Keep the same thing in the same place

- When: a set of pages, or repeated entries on one page.
- Do: give parallel pages and entries the same sections in the same order with the same labels, and call one thing by one name throughout.
- Check: two sibling pages laid side by side line up heading for heading.

## Pick the form for each piece

Run `scripts/choose_form.py --list` for the full set of questions and forms. The common cases on a page:

| The content | Form | Why |
| --- | --- | --- |
| actions in order | numbered list, one action per item, verb first | the reader keeps their place |
| parallel items with no order | bulleted list, one grammatical shape | the eye compares like with like |
| two or more things compared on the same attributes | table | a grid reads both ways |
| a term and its value | key-value list or two-column table | the value has an address |
| a cause, a reason, a trade-off | sentences | the connecting words carry the meaning, and a list drops them |
| conditions that decide an outcome | decision table | the reader finds their row |
| something typed or pasted | code block with its language named | exact characters, copyable |
| parts and connections | diagram plus a text equivalent | see `diagrams.md` |

Rules for tables: one kind of thing per row and one attribute per column; a header row; units in the header; numbers right-aligned to the same precision; rows sorted by what the reader looks up; at most about seven columns.

Rules for steps: one action per step; the expected result stated after the step that produces it; a warning placed before the step it concerns; a condition written at the start of the step ("If the build fails, ...").

## Layer the detail

### Show the common path; put the rest a step away

- When: a page must serve both the frequent case and rare or advanced cases.
- Do: put what most readers need in the main flow. Move advanced options, edge cases, background and long output to a later section, a linked page, or a collapsed block with a label that says what is inside. Keep anything needed for safety or correctness in the main flow.
- Check: a first-time reader can finish the common task without opening anything, and every collapsed label tells a reader whether they need it.

### Link with words that name the target

- When: writing any link.
- Do: use the destination's name or what the reader gets there as the link text.
- Check: `lint_doc_page.py` reports no `link-text`.

### Give every image a text alternative

- When: the page holds an image, chart or diagram.
- Do: write alternative text saying what it shows and why it is there, and follow `multiple-channels.md` for charts and diagrams.
- Check: `lint_doc_page.py` reports no `image-alt`.

## Check list

1. The page has one job, and the opening states it.
2. The point comes first on the page and in each section.
3. The headings alone read as a contents list, in the reader's words.
4. Each piece has the form that fits its type: steps, table, sentences, diagram.
5. No unbroken stretch of prose runs past a screen.
6. The common path is complete without opening any optional detail.
7. `lint_doc_page.py` exits 0.
