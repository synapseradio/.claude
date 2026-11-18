# Optional tools, and asking before installing

Read this when a better result needs something the machine may lack: a diagram renderer, a document converter, a chart library, a browser to check a rendered page.

Everything in this skill works on a stock machine: the scripts use only the Python standard library, and the templates are plain Markdown, JSON and self-contained HTML. Assume nothing else is present. Assume no network.

## Detect before use

Run the survey before relying on any optional tool:

```bash
python3 scripts/detect_tools.py
```

It prints each optional tool as present or missing. For a missing tool it prints what the tool adds, the route that needs no install, the install command for this platform, and what the install changes. It installs nothing.

For a tool the survey does not list, test for it directly with `command -v <name>` before the first use.

## Choose a route

| The survey says | Do |
| --- | --- |
| present | use the tool |
| missing, and the zero-install route gives the reader what they need | take the zero-install route, without asking |
| missing, and the tool gives a clearly better result for this reader | ask whether you may install it, as below |
| you cannot ask (no person is in the loop) | take the zero-install route, and say in the hand-over what the tool would have added |

The zero-install routes:

| Wanted | Zero-install route |
| --- | --- |
| a laid-out diagram image | diagram source in a fenced block for hosts that render it, or hand-written SVG for a small diagram, always with the structure as a list or table |
| a chart image | inline SVG or a self-contained HTML page, written directly, with the data as a table |
| a chart library for an interactive page | plain inline script and SVG, as in `templates/explainer.html` |
| a document in another format | Markdown, or one self-contained HTML file |
| a look at the rendered page | hand over the file and state that the rendered layout was not inspected |

## Ask before installing

Install nothing without a yes from the person. The question must let them decide from the message alone. Include:

1. What is missing.
2. What it adds over the route that needs no install, for this piece of work.
3. The exact command you would run.
4. What it changes on the machine: what gets installed, where, through which package manager, whether it downloads anything further, and how to remove it.
5. What you will do if the answer is no.

Example:

> Graphviz is not installed on this machine. With it I can lay out the 14-service dependency diagram automatically as an SVG; without it I will give you the Mermaid source and a table of the connections, which GitHub renders but a plain viewer does not.
> To install I would run `brew install graphviz`. That adds the Graphviz command-line programs through Homebrew and can be removed with `brew uninstall graphviz`.
> May I install it? If not, I will go ahead with the Mermaid source and the table.

On a yes, run exactly the command you showed, then run `detect_tools.py` again to confirm. On a no, or no answer, proceed with the zero-install route.

If the person asks for help installing, give the command for their platform from the survey, say what it needs first (a package manager, Node.js), and link the tool's own install page that the survey prints.

## Rules that hold either way

- Never download a library into a deliverable from a network address at view time; a page that needs the network breaks when opened from disk or offline. If a library is approved and installed, embed what the page needs in the file.
- Never install as a side effect of running one of this skill's scripts; they do not install, and neither should a wrapper around them.
- Use system fonts in everything you produce.
- A tool being present does not make its output right for the reader: a PNG of a chart loses the text, the data and the scaling that SVG or HTML keep.
