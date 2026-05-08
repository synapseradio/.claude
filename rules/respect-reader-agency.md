# Respect Reader Agency

<when> writing prose a human will read — documentation, code comments, READMEs, PR descriptions, chat replies, longer outputs.

Companion to [writing-for-humans.md](./writing-for-humans.md). That rule governs diction and slop. This one governs the relationship between writer and reader, and what the prose presumes about the person on the other end of it.

## Do not break the fourth wall

<never> Tell the reader why they are reading. No "Common reasons you're here", no "If you're integrating this", no "You're probably wondering why X". The reader knows what brought them in. Stating it presumes a journey the writer cannot witness.

<never> State anything that depends on knowing the reader's experience. Patterns to refuse on sight: "common problems", "typical tasks", "your day-to-day workflow", "things you'll commonly see", "the usual case", "you might bump into", "if your PR diff surprises you", "developers often".

<never> Tell the reader who they are, what they seek, what they care about, what they recognize, or what they fail to recognize. The audience profile shapes the writing. The prose itself does not name it.

<prefer> Write the information directly, in third person or imperative. Let the reader supply their own reason for being there.

## Tone for documentation and comments

<always> Long, grammatically correct, conversational, casual prose. A reader should hear a colleague explaining the thing in full sentences, not a telegram and not an academic paper.

<never> Sacrifice grammatical completeness for brevity.

<never> Use a semicolon to save space or save context. A semicolon joins two complete clauses for rhythm or contrast. It is not a soft period for cramming a second thought into the same line.

<prefer> Two sentences over one stitched-together sentence when each carries its own thought.

## No hyphen-compounded constructions in body prose

<never> Compound modifiers joined by hyphens in body prose. "Type-checked" becomes "type checked" or gets rewritten. "Tracking-plan changes" becomes "changes to the tracking plan". "High-context audience" becomes "audience that supplies context".

<prefer> Rewrite the phrase rather than reach for a hyphen. If the hyphen exists to compress two words into one modifier, the prose can almost always be loosened to carry the same meaning across more words.

### Exclusion

Established hyphenated terms that exist as identifiers — package names, file paths, CSS properties (`box-sizing`), domain vocabulary already hyphenated in the codebase or quoted from external sources — are kept verbatim. The rule applies to compounds the writer invented, not to words the writer is quoting.

The rule applies to prose the writer outputs into a reader-facing artifact. Rule files in this directory may use compound modifiers as section labels or meta references where they aid scanability for the model.
