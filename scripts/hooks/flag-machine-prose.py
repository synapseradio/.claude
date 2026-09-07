#!/usr/bin/env python3
"""Stop hook: flags the strings machine prose supplies and the prose rules cut.

Scans the assistant text of the turn that just finished for the strings
that rules/writing-prose.md sends away by mechanism: the em dash, the
conjunction that rejects an alternative, the mirror opener, the generic
word for structure, inflated vocabulary, the emoji, the summary on a short
message, the stock opener or closer, the earning idiom, the label that
withholds the point, the virtue verdict, the hedge standing for a source,
the cushioning hedge, the self-reference, and the strawman opener. The rule
states each mechanism and one example at most, and this file lists the
instances, so a reader of the rule meets no list and the list has one
owner.

Each hit reports the sentence it sits in under the rule line it fails. The
hook blocks the stop once and asks for the reply re-emitted with each string
cut. When `stop_hook_active` is set, a Stop hook already blocked this cycle,
so the hook reports the survivors through `systemMessage` and lets the turn
end.

Precision over recall, since a false hit on every reply costs more than a
missed one. A string counts as a mention and draws no hit inside fenced
code, inside an inline code span, inside straight or curly double quotation
marks that close on the same line, on a blockquote line, or inside a URL.
Single quotation marks stay in play, since an apostrophe would open one.
Classes a scan cannot tell from legitimate prose stay with the rule alone:
the abstraction as subject, the nominalization, the copula category, the
passive that launders agency, and the tense words of a source comment.

The transcript parse and the fence logic come from verify-marks.py beside
this file, so the two Stop hooks read the turn the same way.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path


def sibling(name):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


marks = sibling("verify-marks")

SHORT_MESSAGE_WORDS = 200
EN_DASH = chr(0x2013)

RULES = (
    (
        "em dash",
        "Write a comma, a colon, or a period for an em dash, since the dash hides "
        "the relation between the clauses it joins.",
        re.compile(f"—| {EN_DASH} "),
    ),
    (
        "rejecting conjunction",
        "Write what holds, alone, for a conjunction that rejects an alternative, "
        "since the rejection makes the audience hold a thing nobody had in view.",
        re.compile(r"\b(rather than|instead of|as opposed to)\b", re.IGNORECASE),
    ),
    (
        "mirror",
        "Write the affirmative for a mirror, a claim paired with the rejection of "
        "a claim nobody made, since the audience spends attention on the rejected thing.",
        re.compile(r"\bnot (just|merely|simply)\b", re.IGNORECASE),
    ),
    (
        "generic structure word",
        "Name the structure, or what depends on it, for a generic word for "
        "structure, since the generic word names nothing the audience can check.",
        re.compile(
            r"\b(the|its|their|this|that|what|whose|our|your|my) shape\b|\bload-bearing\b",
            re.IGNORECASE,
        ),
    ),
    (
        "inflated vocabulary",
        "Write the plain word for an inflated one, since a rare word makes the "
        "audience translate it.",
        re.compile(
            r"\b(delv(e|es|ed|ing)|leverag(e|es|ed|ing)|robust(ly)?|seamless(ly)?"
            r"|utiliz(e|es|ed|ing)|streamlin(e|es|ed|ing))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "emoji",
        "Write no emoji unless the user asks for one, since an emoji carries a "
        "mood no reader can check.",
        re.compile("[\U0001f300-\U0001faff✅❌⚠✨⭐]"),
    ),
    (
        "summary on a short message",
        "Write no summary on a message under 200 words, since the audience meets "
        "the whole message in the same breath.",
        re.compile(r"\bTL;?DR\b", re.IGNORECASE),
    ),
    (
        "stock opener or closer",
        "Open and close on substance, since a stock opener or closer carries "
        "nothing the audience can act on.",
        re.compile(
            r"\b(I'?d be happy to|happy to help|great question|dive (in|into)|go ahead and"
            r"|let me know if|hope (this|that) helps|feel free to)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "earning idiom",
        "State the condition under which a thing applies, or what it does, for the "
        "earning idiom, since the idiom asserts a verdict without its condition.",
        re.compile(
            r"\bearn(s|ed|ing)? (its|their|a|an|the|his|her) "
            r"(place|keep|mention|spot|seat|right|way|name|title)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "withheld point",
        "State the thing directly for a label that withholds the point, since the "
        "label makes the audience wait for it.",
        re.compile(
            r"\bthe (trick|catch|kicker|bottom line)( is| here is)?:|\bhere'?s the (thing|catch|kicker)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "virtue verdict",
        "Give the evidence for a virtue verdict on your own work, since the "
        "audience awards the word.",
        re.compile(r"\b(honestly|to be honest|frankly|candidly|genuine(ly)?)\b", re.IGNORECASE),
    ),
    (
        "hedge standing for a source",
        "Write a mark for a hedge that stands in for a missing source, since the "
        "hedge leaves the audience nothing to check.",
        re.compile(
            r"\b(as far as I (know|can tell|recall)|I believe|if I recall|IIRC)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "cushioning hedge",
        "Cut a hedge that cushions, since it spends attention before the point.",
        re.compile(
            r"\b((it'?s |it is )?worth (noting|mentioning|pointing out)"
            r"|it'?s important to (note|remember|mention)|it is important to (note|remember|mention)"
            r"|needless to say|as you can see)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "self-reference",
        "Give the content, or a link to where it sits, for a reference to the "
        "artifact itself, since the reference sends the audience away from the content.",
        re.compile(
            r"\b(this (document|section|paragraph)"
            r"|(mentioned|noted|described|discussed|outlined|explained|shown|listed) (above|below)"
            r"|see (above|below))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "strawman opener",
        "Draw a contrast against a consequence, a measurement, or a cited source, "
        "since a position nobody held spends attention on a claim nobody made.",
        re.compile(
            r"\b(than (you|one|people) might (think|expect|assume)|contrary to popular"
            r"|common misconception|you might (assume|expect)|counter-?intuitively)\b",
            re.IGNORECASE,
        ),
    ),
)

MENTION = re.compile(r"`[^`\n]*`|\"[^\"\n]*\"|“[^”\n]*”|https?://\S+")
BLOCKQUOTE = re.compile(r"^\s*>")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def mask_mentions(line):
    """The line with each mention replaced by spaces of equal length, so a
    match position on the masked line addresses the original."""
    return MENTION.sub(lambda span: " " * len(span.group(0)), line)


def sentence_around(line, position):
    start = 0
    for boundary in SENTENCE_END.finditer(line):
        if boundary.end() > position:
            return line[start : boundary.start()].strip()
        start = boundary.end()
    return line[start:].strip()


def flagged_sentences(blocks):
    """Sentences carrying a flagged string, keyed by rule index, in the order
    the rules are declared and each sentence listed once under a rule."""
    lines = []
    block_words = []
    for index, block in enumerate(blocks):
        block_words.append(len(block.split()))
        lines.extend((index, line) for line in block.splitlines())
    fenced = marks.fenced_line_numbers([line for _, line in lines])
    hits = {}
    for number, (block_index, line) in enumerate(lines):
        if number in fenced or BLOCKQUOTE.match(line):
            continue
        masked = mask_mentions(line)
        for rule_index, (key, _, pattern) in enumerate(RULES):
            if (
                key == "summary on a short message"
                and block_words[block_index] >= SHORT_MESSAGE_WORDS
            ):
                continue
            for match in pattern.finditer(masked):
                sentence = sentence_around(line, match.start())
                found = hits.setdefault(rule_index, [])
                if sentence not in found:
                    found.append(sentence)
    return hits


def build_reason(hits):
    listing = "\n\n".join(
        RULES[rule_index][1] + "\n" + "\n".join(f"- {sentence}" for sentence in sentences)
        for rule_index, sentences in sorted(hits.items())
    )
    return (
        "Your reply carries strings the prose rules cut, each listed under the "
        "rule line it fails:\n\n"
        f"{listing}\n\n"
        "Re-emit the reply with each string cut as its rule line says, and nothing "
        "else changed. Where a flagged string names the word itself, as a "
        "quotation or a term under discussion, put it in backticks or double "
        "quotation marks, which this pass skips."
    )


def build_notice(hits):
    listing = "\n".join(
        f"- {sentence} ({RULES[rule_index][0]})"
        for rule_index, sentences in sorted(hits.items())
        for sentence in sentences
    )
    return "These strings survived the pass and stand as written:\n" + listing


def run_stop(payload):
    blocks = [payload.get("last_assistant_message") or ""]
    transcript = payload.get("transcript_path", "")
    if transcript and Path(transcript).exists():
        blocks = marks.last_turn_text(transcript) + blocks
    hits = flagged_sentences(blocks)
    if not hits:
        sys.exit(0)
    if payload.get("stop_hook_active"):
        json.dump({"systemMessage": build_notice(hits)}, sys.stdout)
        sys.exit(0)
    json.dump({"decision": "block", "reason": build_reason(hits)}, sys.stdout)
    sys.exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    run_stop(payload)


if __name__ == "__main__":
    main()
