# Voice and Style

The convergent voice of developer documentation across Google, Microsoft, GitLab, and Django. The rules below are the intersection: where any two of the four sources explicitly state the rule, it is named here with both quotes.

## Primary sources

| URL | Topic |
|-----|-------|
| https://developers.google.com/style | Google developer documentation style guide — home |
| https://developers.google.com/style/voice | Google — Active voice |
| https://developers.google.com/style/tone | Google — Voice and tone |
| https://learn.microsoft.com/en-us/style-guide/welcome/ | Microsoft Writing Style Guide — Welcome |
| https://learn.microsoft.com/en-us/style-guide/top-10-tips-style-voice | Microsoft — Top 10 tips |
| https://docs.gitlab.com/development/documentation/styleguide/ | GitLab documentation style guide |
| https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/ | Django writing documentation |

## Voice

Google:

> "aim for a voice and tone that's conversational, friendly, and respectful without using slang or being overly colloquial or frivolous; a voice that's casual and natural and approachable, not pedantic or pushy. Try to sound like a knowledgeable friend who understands what the developer wants to do."
>
> — https://developers.google.com/style/tone

Microsoft:

> "warm and relaxed, crisp and clear, and ready to lend a hand."
>
> — https://learn.microsoft.com/en-us/style-guide/welcome/

GitLab:

> "The voice in the documentation should be conversational but brief, friendly but succinct."
>
> — https://docs.gitlab.com/development/documentation/styleguide/

The three converge: conversational, brief, friendly. No slang, no pedantry.

## Active voice

Google:

> "use active voice (in which the grammatical subject of the sentence is the person or thing performing the action) instead of passive voice."
>
> — https://developers.google.com/style/voice

GitLab allows passive where the grammatical subject would be awkward:

> Active voice default; passive allowed where "GitLab as the subject can be awkward."
>
> — https://docs.gitlab.com/development/documentation/styleguide/

Default active. Break for documented reason only.

## Tense and person

Use present tense and second person — a convergent convention of the three developer-guide voices above. State "the API returns" not "the API will return." Address the reader as "you," not "the user."

## Contractions and the serial comma

Microsoft top-10 tips:

> "Write like you speak... Project friendliness. Use contractions... Be brief. Give customers just enough information to make decisions confidently. Prune every excess word... When in doubt, don't capitalize... Remember the last comma [Oxford/serial comma]."
>
> — https://learn.microsoft.com/en-us/style-guide/top-10-tips-style-voice

Two concrete rules the agent can check:

- Use contractions (`it's`, `don't`, `you'll`).
- Use the serial (Oxford) comma.

## Region and grammar

GitLab states an explicit dialect:

> "Write in US English with US grammar."
>
> — https://docs.gitlab.com/development/documentation/styleguide/

Adopt the dialect of the project's own style guide. If none exists, default to US English per GitLab.

## Forbidden and discouraged words

Google:

> Avoid: "Placeholder phrases like *please note* and *at this time*... Using phrases like *simply*, *It's that simple*, *It's easy*, or *quickly* in a procedure... Exclamation marks... Wackiness, zaniness, and goofiness... Internet slang."
>
> — https://developers.google.com/style/tone

Django:

> "Try to avoid using words that minimize the difficulty involved in a task or operation, such as 'easily', 'simply', 'just', 'merely', 'straightforward'... People's experience may not match your expectations, and they may become frustrated when they do not find a step as 'straightforward' or 'simple' as it is implied to be."
>
> — https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/

### The list the forbidden-words script scans for

`simply`, `easily`, `just`, `merely`, `straightforward`, `quickly`, `obviously`, `clearly`.

This is the intersection of Google's and Django's named words plus two (`obviously`, `clearly`) that imply reader ability.

**Caveat: the list is heuristic.** Words like `just` (meaning "only") and `clearly` (non-style sense) have legitimate uses. Triage results; do not blindly fix every hit. The spirit of both sources is *diminishing uses*, not every grammatical instance.

## Inclusive language

Django:

> Gender-neutral pronouns: "he or she… use they. him or her… use them."
>
> — https://docs.djangoproject.com/en/dev/internals/contributing/writing-documentation/

## Docs-as-single-source-of-truth

GitLab:

> "Documentation is the single source of truth (SSoT)."
>
> — https://docs.gitlab.com/development/documentation/styleguide/

Do not contradict docs elsewhere (README, marketing, blog posts). If the doc is wrong, fix the doc, not the substitute.

## Brevity discipline

Microsoft's brevity rule is explicit:

> "Be brief. Give customers just enough information to make decisions confidently. Prune every excess word."
>
> — https://learn.microsoft.com/en-us/style-guide/top-10-tips-style-voice

And Raymond, from a different tradition, reinforces it:

> "Don't think for a moment that volume will be mistaken for quality."
>
> — http://www.catb.org/~esr/writings/taoup/html/ch18s06.html

## Agent instructions

1. Before drafting, load this file; before declaring a draft done, run `scripts/find-forbidden-words.sh` on it.
2. Default to active voice, present tense, second person. Break the default only with a reason stateable in one sentence.
3. Use contractions; use the serial comma.
4. When invoking a voice rule in a review, cite the specific URL (Google vs. Microsoft vs. GitLab vs. Django) so the reader can adjudicate the source themselves.
5. Treat the forbidden-words list as aggressive. Read each hit before deleting it; some are legitimate uses.
