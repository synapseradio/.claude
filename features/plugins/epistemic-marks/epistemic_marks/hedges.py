"""Finding a guess written in words where a mark belongs.

A mark is a token a hook can match. "My guess", "probably" and "I haven't
checked this, but" say the same thing in words, and the mark scan reads
straight past them. This module finds that wording, sentence by sentence, and
the sentences that build on a guessed or marked claim without carrying the
mark onward.

The lexicon is a floor, kept to wording that signals doubt in nearly every
sentence it appears in. A word that doubts in one sentence and permits or
obliges in the next ("may", "should", "must") is matched only in a frame
where it doubts, and left alone elsewhere: a dependency parse gives both
senses the same tag, relation and head, so no deterministic reader splits
them. The rule text carries those, and every guess stated with no wording of
doubt at all. DESIGN.md records the measurements behind where the floor sits.
"""

import re
from collections.abc import Iterator

from .marks import MARK_NAMES, MARKS
from .scan import BLANK, claim_lines, claim_text, marked_lines

GUESS = "guess"
CAUSE = "cause"
REST = "rest"
ASKED = "asked"
SAID = "said"

# A sentence ends at closing punctuation followed by space and anything but a
# lowercase letter, which keeps "e.g. this" whole.
BOUNDARY = re.compile(r"(?<=[.!?])\s+(?![a-z])")

# What a list item, a heading or emphasis puts before a sentence's first word.
LEAD = re.compile(r"^(?:\s*(?:[-*+]|\d+[.)]|#+)\s+)?(?:[\s*_]|\x00)*")

# A source by its form alone: a URL, or a path with its line.
CITATION = re.compile(r"https?://\S+|[\w~./-]*\w\.\w{1,8}:\d+")

_NOUN = r"(?:guess|hunch|hypothesis|suspicion|theory|speculation|conjecture|assumption)"
_READING = (
    r"(?:understanding|impression|recollection|reading|sense|belief|expectation|bet"
    r"|instinct|intuition|gut feeling)"
)
_CHECK = r"(?:check(?:ed)?|verif(?:y|ied)|confirm(?:ed)?|test(?:ed)?)"
_NOT_DONE = r"(?:haven't|have not|hadn't|didn't|did not|couldn't|could not|not yet)"
_IT = r"(?:it|this|that|these|those|them|any of (?:it|this|that))"

HEDGES = (
    # A stance verb in the first person.
    r"\b(?:I|we)\s+(?:(?:would|do|also|still|really|strongly|now|just|only|don't|do not)\s+)*"
    r"(?:think|believe|suspect|assume|presume|imagine|guess|reckon|gather|doubt|bet"
    r"|speculate|surmise|take it)\b",
    r"\b(?:I|we)'d\s+(?:also\s+|still\s+)?"
    r"(?:think|guess|imagine|assume|say|bet|wager|venture|reckon)\b",
    r"\bI(?:'m| am)\s+(?:only\s+|just\s+|still\s+)?"
    r"(?:guessing|assuming|betting|speculating|inclined to (?:think|believe))\b",
    # A noun that labels the claim as a guess.
    rf"\b(?:my|our)\s+(?:\w+\s+){{0,2}}?(?:{_NOUN}|{_READING})\b",
    r"\b(?:best|educated|rough|wild|working|leading|current|initial|first|pure|mere"
    rf"|tentative)\s+{_NOUN}\b",
    # The bare noun labels a claim only where it opens its clause: "the
    # theory is that" against "a prompt carrying a guess is denied".
    r"(?:^|[,;:—\u2013]\s*|\b(?:and|but|so|then|yet|while)\s+)(?:\x00|[\s*_>#-])*"
    r"(?:(?:the|one|another|other|second|third|main|top|alternative|competing)\s+){0,3}"
    r"(?:guess|hunch|hypothesis|suspicion|theory|conjecture|speculation)(?:\s+(?:is|was)\b|\s*:)",
    r"\b(?:(?<!for )a hunch|an inkling|at a guess|just a guess|only a guess|a gut feeling)\b",
    # A status summary standing over other claims: "all three are guesses".
    r"\b(?:is|are|was|were)\s+(?:all\s+|both\s+|just\s+|only\s+|still\s+)?(?:an?\s+|my\s+)?"
    r"(?:guess(?:es|work)?|hunch(?:es)?|assumptions?|hypothes[ei]s|theor(?:y|ies))\b",
    r"\b(?:unconfirmed|speculative|speculation|guesswork|conjecture)\b",
    r"\b(?:is|are|was|were|remains?|still|as yet|so far|currently)\s+(?:unverified|untested)\b",
    # An adverb or adjective of doubt.
    r"\b(?:probably|presumably|plausibly|supposedly|seemingly|apparently|conceivably"
    r"|possibly|perhaps|maybe|(?:un)?likely|ostensibly|allegedly|reportedly|purportedly"
    r"|in all likelihood|in theory|chances are|odds are)\b",
    r"\bit(?:'s| is)\s+(?:quite\s+|entirely\s+|also\s+)?possible\s+(?:that|the)\b",
    r"\b(?:possible|potential|plausible|probable)\s+(?:root\s+)?"
    r"(?:cause|causes|explanation|culprit|reason)\b",
    r"\b(?:is|are|it's|that's|seems|sounds)\s+(?:quite\s+|entirely\s+|very\s+)?"
    r"(?:plausible|probable)\b",
    # Seeming.
    r"\bseem(?:s|ed)?\b",
    r"\bappear(?:s|ed)?\s+(?:to|that|as if|as though)\b",
    r"(?<!\bof )\bit appears\s+(?:that|the|a|an|this|these|there|as if|as though|like)\b",
    # "What a valid change looks like" describes; "looks like the cache" doubts.
    r"(?:^|\b(?:it|this|that|which)\s+)(?:\x00|[\s*_>#-])*looks?\s+(?:like|as if|as though)\b"
    r"(?=\s+\w)(?!\s+(?:this|that|the following)\b)",
    r"\b(?:sounds|feels|smells)\s+like\b",
    # A modal, in the frames where it doubts.
    r"(?<!\byou )\bmight\b(?!\s+(?:want|like|prefer|consider|as well)\b)",
    # "May" doubts about the past and about a cause. "The file may be empty"
    # states what a format allows, so the bare "may be" is left to the rule.
    r"\bmay\s+(?:very\s+)?well\b",
    r"\bmay\s+(?:also\s+|still\s+|not\s+|simply\s+|just\s+|even\s+)*have\s+"
    r"(?:been|gone|broken|left|lost|kept|held|run|come|made|taken|got|gotten|\w+ed)\b",
    r"\bmay\s+(?:also\s+|not\s+)?be\s+(?:that|because|due|caused|related|why|what"
    r"|responsible|causing|the\s+(?:cause|culprit|reason|issue|problem))\b",
    r"\bcould\s+(?:well\b|be\s+(?:that|because|due|caused|related|why)\b)",
    # An identification: "it may be the lockfile" names a suspect, where "it
    # may be a string" states what a format allows.
    r"\b(?:it\s+(?:may|could)|(?:this|that)\s+may)\s+(?:also\s+|just\s+|simply\s+|still\s+)?"
    r"be\s+(?:the|your|our|my|its|their|one of)\b",
    # "Should" predicts in these frames and obliges in the rest: "that should
    # fix it" against "you should fix it" and "the function should return".
    r"(?<!\byou )(?<!\bwe )(?<!\bI )\bshould\s+(?:now\s+|then\s+|just\s+|also\s+)?"
    r"(?:fix|resolve|solve|suffice|do the trick|do it)\b",
    r"\b(?:this|that|it|which|\w*fix|patch|change|workaround)\s+should\s+"
    r"(?:now\s+|then\s+|just\s+|also\s+|all\s+)?(?:work|be\s+(?:enough|sufficient|fine"
    r"|safe|okay|ok|good|all set|working|fixed|resolved))\b",
    r"\b(?:cause|culprit|reason|explanation|problem|issue)\s+should\s+be\b",
    # "Now" and "again" date the sentence to after a change, which a
    # standing obligation never is.
    r"(?<!\byou )(?<!\bwe )(?<!\bI )\bshould\s+now\s+"
    r"(?:pass|work|succeed|compile|build|run|be)\b",
    r"(?<!\byou )(?<!\bwe )(?<!\bI )\bshould\s+(?:pass|work|succeed|compile|build|run"
    r"|go green|be green|be passing)\s+(?:now|again)\s*[.!]?\s*$",
    r"\b(?:would|'d)\s+(?:guess|imagine|wager|venture|hazard)\b",
    # The limit of what the writer knows, or confidence in place of a source.
    r"\bas far as I\s+(?:know|can tell|can see|understand|remember|recall|am aware)\b",
    r"\b(?:afaik|afaict|iirc)\b",
    r"\bif I\s+(?:recall|remember)\b",
    r"\bif memory serves\b",
    r"\bto (?:the best of )?my knowledge\b",
    r"\boff the top of my head\b",
    r"\bfrom what I\s+(?:can tell|can see|understand|recall|remember|gather|know)\b",
    r"\bas I\s+(?:recall|remember|understand it)\b",
    r"\bnot\s+(?:100%\s+|entirely\s+|completely\s+|fully\s+|totally\s+|quite\s+)(?:sure|certain)\b",
    r"\bI(?:'m| am)\s+(?:(?:fairly|pretty|quite|reasonably|almost|rather|somewhat|very)\s+)?"
    r"(?:sure|certain|confident|positive|convinced)\b",
    r"\b(?:almost|most) certainly\b",
    r"\b(?:no doubt(?!\s+(?:wording|words?|phrases?|markers?|language)\b)|undoubtedly|surely)\b",
    r"\bsafe to (?:say|assume)\b",
    r"\bstands to reason\b",
    r"\b(?:can't|cannot) rule out\b",
    # A source with its name filed off, the weasel wording of the hedge
    # detection literature (https://arxiv.org/html/2405.13319v1).
    r"(?:^|[.;:,]\s+|\x00\s*)(?:some|many|most|people|experts|others)\s+"
    r"(?:say|believe|think|argue|claim|report)\b",
    r"\bit(?:'s| is)\s+(?:said|believed|thought|rumou?red|well known"
    r"|(?:widely|commonly|generally)\s+(?:known|believed|accepted|held))\b",
    r"\b(?:rumou?r has it|word is that|everyone knows|common knowledge)\b",
    # The stance as a sentence, on either side of the claim.
    rf"\b{_NOT_DONE}\s+(?:yet\s+|actually\s+)?{_CHECK}(?:\s+{_IT})?(?:\s+yet)?\s*[,;]?\s*"
    r"(?:but|though|however)\b",
    rf"\b(?:but|though|although|however)\b[^.!?]{{0,40}}?\b{_NOT_DONE}\s+"
    rf"(?:actually\s+|yet\s+)?{_CHECK}\s+{_IT}\b",
    r"\((?:unverified|untested|unconfirmed|unchecked|not\s+(?:yet\s+)?(?:verified|confirmed"
    r"|tested|checked)|needs?\s+(?:verif\w+|confirm\w+|checking)|to be (?:verified|confirmed)"
    r"|tbc|citation needed|guess)\b[^)]*\)",
    # A mark of the writer's own making.
    r"\(\?\)",
    r"\[\?\?+\]",
    r"\[(?:unverified|unconfirmed|unsourced|untested|guess|assumption|citation needed"
    r"|needs?\s+(?:source|citation|verification)|tbc)\](?!\()",
)

# A label the sentence opens on.
OPENING_HEDGES = (
    r"(?:unverified|untested|unchecked|tentative(?:ly)?|assumption|assumed|caveat)\s*[:,—\u2013-]",
)

# How a sentence opens when it builds on the one before it. An opening that
# announces the writer's own next step is left alone.
_NEXT_STEP = r"(?!,?\s+(?:I|I'll|I'm|I've|we|we'll|let|let's|next|now|first)\b)"
RESTS = (
    r"(?:that|this|which|it)\s+would\b",
    r"(?:that|this|which)\s+(?:also\s+|then\s+)?(?:explains?|match(?:es)?|means|fits"
    r"|accounts for|lines up|implies|is why|is consistent with|leaves|makes|causes|breaks)\b",
    r"(?:so|therefore|hence|thus|consequently|accordingly|as a result|if so|in that case"
    rf"|if that(?:'s| is) (?:right|true|correct|the case)|it follows)\b{_NEXT_STEP}",
)

# A diagnosis: why something fails. The one flat guess with a visible form,
# and a sentence the rule leaves unfinished without a source or a mark.
_FAILS = (
    r"(?:fail\w*|break\w*|broke\w*|crash\w*|error\w*|slow\w*|flak\w*|hang\w*|hung"
    r"|tim(?:es|ed|ing)\s+out|stall\w*|regress\w*)"
)
CAUSES = (
    rf"\b{_FAILS}\b[^.!?]{{0,60}}?\bbecause\b",
    r"\bthe\s+(?:root\s+)?(?:cause|culprit)\s+(?:is|was)\b",
    r"\b(?:is|was|are|were)\s+caused\s+by\b",
    r"\bthe\s+reason\s+(?:is|was)\b",
)

# A statement laid on the user. Their words go unmarked only where a reader
# can find them, so the report of one needs the quotation beside it.
_SAY = r"(?:said|stated|noted|mentioned|confirmed|reported|explained|pointed out|told (?:me|us))"
ATTRIBUTIONS = (
    r"(?<!when )(?<!if )(?<!once )(?<!after )(?<!until )(?<!whenever )"
    r"(?<!what )(?<!whatever )(?<!which )(?<!where )"
    rf"\bthe user\s+(?:(?:has|had|already|also|just)\s+)*{_SAY}\b"
    r"(?!\s+(?:to|it|so|them|otherwise)\b)",
    r"\baccording to the user\b",
    r"\bper the user\b(?!')",
)

# A question that asserts. An open question hands a hypothesis over to be
# checked and is left alone. These three forms do more: a negative lead, a
# consequence hung on the question's own premise, and a statement with a
# tag asking only for agreement. A question to or about the people in the
# conversation asks what they want, so those subjects are left out.
_FACT = r"(?:did|does|do|is|are|was|were|has|have|had)"
_NOT_US = r"(?!you\b|we\b|i\b)"
ASSERTING_QUESTIONS = (
    rf"^{_FACT}n't\s+{_NOT_US}",
    rf"^{_FACT}\s+{_NOT_US}[^?]*,\s+(?:so|which|meaning|causing|and\s+(?:so|that|therefore|thus))\b",
    rf"^(?!(?:{_FACT}|you|we|i|shall|should|can|could|would|will|want|let|what|why|how|where"
    rf"|when|which|who)\b)[^?]*,\s*(?:right|correct|no|yes|true"
    rf"|{_FACT}n't\s+(?:it|they|he|she|that|there))\s*\?",
)
# A question about how things stand, which the next sentence can build on.
FACT_QUESTION = re.compile(rf"^(?:{_FACT}|could|might|can|may)(?:n't)?\s+{_NOT_US}", re.IGNORECASE)

LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)]|#+)\s+")
# How a line ends where its sentence ends with it.
ENDS_A_SENTENCE = re.compile(r"[.!?:][\s*_)\]\x00]*$")
HEDGE = re.compile("|".join(HEDGES), re.IGNORECASE)
ATTRIBUTION = re.compile("|".join(ATTRIBUTIONS), re.IGNORECASE)
ASSERTING_QUESTION = re.compile("|".join(ASSERTING_QUESTIONS), re.IGNORECASE)
QUOTE_MARK = re.compile(r"[\"“\u2018']")
OPENING_HEDGE = re.compile("|".join(OPENING_HEDGES), re.IGNORECASE)
RESTING = re.compile("|".join(RESTS), re.IGNORECASE)
DIAGNOSIS = re.compile("|".join(CAUSES), re.IGNORECASE)


def _sentences(line: str, masked: str) -> Iterator[tuple[str, str]]:
    """Each sentence of the line, as the raw text and the text a guess can sit in.

    `masked` is the line with its code spans, quoted text and mentioned
    glyphs blanked at equal length, so a full stop inside any of them ends
    no sentence and the raw slice still lines up with the masked one.
    """
    start = 0
    for boundary in [*BOUNDARY.finditer(masked), None]:
        end = boundary.start() if boundary else len(line)
        if line[start:end].strip():
            yield claim_text(line[start:end]), masked[start:end]
        start = boundary.end() if boundary else end


def _named_marks(sentence: str) -> list[str]:
    lowered = sentence.lower()
    return [mark for mark in MARKS if MARK_NAMES[mark].lower() in lowered]


def guessed_lines(blocks: list[str]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Sentences guessing in words, sentences resting on a guess, and mentions.

    The first mapping holds, under GUESS, each sentence that hedges with
    neither a mark nor a source in it, under CAUSE each sentence that states
    why something fails with neither, and under REST each sentence that opens
    by building on a marked, hedged or diagnosing sentence right before it
    and carries neither itself, under SAID each sentence reporting what the
    user said without their words, and under ASKED each question whose form
    asserts. Fenced code, code spans, quoted text, block quotes and open
    questions hold no guess. The second mapping holds, keyed by mark, each
    sentence that hedges while naming a mark in words: it blocks nothing, and
    the Stop pass reports it so the exemption stays visible.
    """
    lines = [line for block in blocks for line in block.splitlines()]
    found = {GUESS: [], CAUSE: [], SAID: [], REST: [], ASKED: []}
    named = {mark: [] for mark in MARKS}
    resting_ground = False
    # Whether the line above stopped mid-sentence, so this line's first
    # words continue it and open nothing.
    wrapped = False
    for line, (prose, _mentioned) in zip(lines, claim_lines(lines), strict=True):
        if not prose:
            resting_ground = wrapped = False
            continue
        continues = wrapped and not LIST_ITEM.match(line)
        wrapped = not ENDS_A_SENTENCE.search(prose)
        for raw, masked in _sentences(line, prose):
            opening = "" if continues else LEAD.sub("", masked, count=1)
            continues = False
            hedged = bool(HEDGE.search(masked) or OPENING_HEDGE.match(opening))
            builds = resting_ground and bool(RESTING.match(opening))
            diagnoses = bool(DIAGNOSIS.search(masked))
            marked = any(mark in masked for mark in MARKS)
            covered = marked or bool(CITATION.search(raw))
            mentioned = _named_marks(masked)
            if mentioned:
                resting_ground = False
                if hedged and not covered:
                    for mark in mentioned:
                        if raw not in named[mark]:
                            named[mark].append(raw)
                continue
            if masked.rstrip(" \t*_" + BLANK).endswith("?"):
                asserts = bool(ASSERTING_QUESTION.match(opening)) and not covered
                if asserts and raw not in found[ASKED]:
                    found[ASKED].append(raw)
                resting_ground = asserts or bool(FACT_QUESTION.match(opening))
                continue
            quoted = BLANK in masked and bool(QUOTE_MARK.search(raw))
            said = bool(ATTRIBUTION.search(masked)) and not (covered or quoted)
            if not covered:
                kind = (
                    GUESS
                    if hedged
                    else CAUSE
                    if diagnoses
                    else SAID
                    if said
                    else REST
                    if builds
                    else None
                )
                if kind and raw not in found[kind]:
                    found[kind].append(raw)
            resting_ground = marked or hedged or builds or said or (diagnoses and not covered)
    return (
        {kind: hits for kind, hits in found.items() if hits},
        {mark: hits for mark, hits in named.items() if hits},
    )


def unchecked_claims(
    blocks: list[str],
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    """Everything a pass has to act on: marked lines, guesses in words, and mentions.

    The mentions of both scans are merged under the mark each one names.
    """
    lines_by_mark, mentions = marked_lines(blocks)
    wording, named = guessed_lines(blocks)
    for mark, sentences in named.items():
        held = mentions.setdefault(mark, [])
        held.extend(sentence for sentence in sentences if sentence not in held)
    return lines_by_mark, wording, {mark: mentions[mark] for mark in MARKS if mark in mentions}
