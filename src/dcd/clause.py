"""CLAUSE_WALK_SPEC.md §4 — Clause segmentation, and §6a pronoun tagging.

A second layer beneath §5.1's sentence records: each sentence is cut into
clauses, and each clause carries the anchor (§5) the walk hops on and the
pronoun classes (§6a) it contains.

Hard constraint reminder (Constraint 1): rule-based string processing
only. The word lists below are closed-set lookups, on the same footing as
corpus.ABBREVIATIONS — not grammatical analysis, and not a classification
judgment about which clauses are worth using. Nothing here filters.
"""

import re
from typing import NamedTuple

from dcd.corpus import ABBREVIATIONS, Sentence
from dcd.word_selection import tokenize_sequence

# --- §4 closed word lists -------------------------------------------------

# Subordinators: safe as a clause boundary on their own after a comma.
_SUB = (
    r"(?:when|while|whilst|who|whom|whose|which|that|after|before|until|till"
    r"|unless|though|although|because|since|whereupon|wherein|whereat|if"
    r"|where|whither|whence)"
)
# Pronouns leading a new clause after a comma.
_PRON = r"(?:he|she|they|it|we|I|you|his|her|their|its|there|this|these|those)"
# Coordinators are NOT a boundary on their own — they must lead a subject,
# or the list "Hsiao, Chung, and Hsin" breaks at "and Hsin".
_COORD = r"(?:and|but|or|so|for|yet|nor)"
_DET = (
    r"(?:the|a|an|his|her|their|its|my|our|your|this|that|these|those"
    r"|all|some|no)"
)
# Words ending in -ing that are not participles. Without this, "his two
# sons, Ming and Chêng" breaks at "Ming".
_NOT_ING = (
    r"(?!king|thing|evening|morning|nothing|something|anything|everything"
    r"|during|spring|being|ring|wing|sing|bring)"
)

# The optional closing-quote class after .!? and ;: is required: without
# it a closing quote defeats the lookbehind and the split silently fails.
# Both straight and curly marks must be listed — the corpus uses curly.
_CLOSE_Q = "[\"'\u201d\u2019]?"

# A sentence-final period is NOT a clause boundary when it belongs to an
# abbreviation. Built from corpus.ABBREVIATIONS so the clause splitter
# and the sentence splitter (§5.1) cannot drift apart: the sentence
# splitter already declines to split on these, and without the same
# guard here "To-morrow Mr. Chang came" breaks after "Mr.", leaving a
# clause whose anchor is "mr". That affected 350 clauses and made "mr"
# the second most common clause-final word in the corpus.
# `(?<![A-Z]\.)` additionally covers single-capital initials, which
# corpus.py handles structurally rather than by list.
_NOT_ABBREV = "".join(
    f"(?<!{abbrev.replace('.', chr(92) + '.')})" for abbrev in sorted(ABBREVIATIONS)
) + r"(?<![A-Z]\.)"
SPLIT_RE = re.compile(
    "|".join(
        [
            r"(?<=[;:])" + _CLOSE_Q + r"\s+",
            r"\s+--+\s*",
            _NOT_ABBREV + r"(?<=[.!?])" + _CLOSE_Q + r"\s+",
            r",\s+(?=" + _SUB + r"\s)",
            r",\s+(?=" + _PRON + r"\s)",
            r",\s+(?=" + _COORD + r"\s+(?:" + _PRON + "|" + _DET + r")\s)",
            r",\s+(?=" + _NOT_ING + r"[a-z]{4,}ing\s)",
        ]
    )
)

COORDINATORS = {"and", "but", "or", "so", "for", "yet", "nor"}

MIN_CLAUSE_TOKENS = 3

_WORD_RE = re.compile(
    r"['’]?[^\W\d_]+(?:['‘’‐-―-][^\W\d_]+)*['’]?",
    re.UNICODE,
)

# --- §6a pronoun classes --------------------------------------------------

PRONOUN_CLASS = {
    "he": "M", "him": "M", "his": "M", "himself": "M",
    "she": "F", "her": "F", "hers": "F", "herself": "F",
    "they": "P", "them": "P", "their": "P", "themselves": "P",
    "i": "1", "me": "1", "my": "1", "myself": "1", "mine": "1",
}


class Clause(NamedTuple):
    sentence_id: int
    index: int          # position within the sentence, 0-based
    text: str           # verbatim, whitespace-normalised
    anchor: str         # lowercased final word token (§5)
    pronoun: frozenset  # pronoun classes present (§6a); empty if none


def words(text: str) -> list[str]:
    """Word tokens of a clause. Local to this module: the walk counts
    words for the anchor and for reporting, not for corpus positions —
    word_selection.tokenize_sequence remains the definition of "a word of
    the corpus" for §5.3/§6.2.
    """
    return _WORD_RE.findall(text)


def _strip_stranded_coordinator(text: str, toks: list[str]) -> tuple[str, list[str]]:
    """§4 — drop a trailing `and`/`but`/`or`... and re-derive the anchor.

    Caused by the interrupted-coordinator construction "..., and, when ...":
    the first comma correctly declines to split (the coordinator is not
    leading a subject), then the subordinator splits at the second comma
    and strands the coordinator at the end of the previous clause.
    An `and` anchor is not an association — `and` occurs in 3,834 of 4,553
    sentences, so the hop becomes a random jump across 84% of the corpus.
    """
    while toks and toks[-1].lower() in COORDINATORS:
        stripped = re.sub(
            r"[\s,;:]*" + re.escape(toks[-1]) + r"\s*$", "", text
        ).rstrip(" ,;:")
        if stripped == text:
            # The coordinator is not at the literal end of the string
            # (trailing punctuation the pattern does not cover). Nothing
            # to strip; stop rather than spin.
            break
        text = stripped
        toks = words(text)
    return text, toks


def pronoun_classes(toks: list[str]) -> frozenset:
    """§6a — the SET of pronoun classes a clause uses.

    A set, not a string: 12.6% of clauses carry two classes ("he told
    her"), and the set is what lets containment matching keep them usable
    instead of treating them as dead ends.
    """
    return frozenset(
        PRONOUN_CLASS[t.lower()] for t in toks if t.lower() in PRONOUN_CLASS
    )


def segment(sentence: Sentence) -> list[Clause]:
    """Cuts one sentence record into clauses (§4)."""
    clauses: list[Clause] = []
    for part in SPLIT_RE.split(sentence["text"]):
        part = part.strip() if part else ""
        if not part:
            continue
        toks = words(part)
        if toks and toks[-1].lower() in COORDINATORS:
            part, toks = _strip_stranded_coordinator(part, toks)
        if len(toks) < MIN_CLAUSE_TOKENS:
            continue
        clauses.append(
            Clause(
                sentence_id=sentence["id"],
                index=len(clauses),
                text=part,
                anchor=toks[-1].lower(),
                pronoun=pronoun_classes(toks),
            )
        )
    return clauses


def build_clause_index(
    sentences: list[Sentence],
) -> tuple[dict[int, list[Clause]], dict[str, set[int]]]:
    """Returns (clauses_by_sentence_id, anchor_index).

    `anchor_index` maps every lowercased word in a sentence — not only
    clause-final ones — to the ids of sentences containing it. The anchor
    must be findable anywhere in a target sentence, not just at its edges.

    It is keyed under BOTH tokenisations, because two different ones are
    in play and they disagree about hyphens:

      * `words()` keeps "fox-girl" whole. Clause anchors come from here,
        so "fox-girl" must be a key or a hop on it finds nothing.
      * `word_selection.tokenize_sequence()` splits it into "fox" and
        "girl". The word pool is built from that, so `word_A` may BE
        "girl" — and without indexing the split form, 116 pool words
        (ant, aspen, bishop, bullock, captain, citron...) occur only
        inside compounds, are absent from the index, and cannot seed a
        walk at all. That raised AttributeError on 2.55% of chapters.

    Indexing both is the fix; narrowing either tokeniser would cost
    real words (see the note in word_selection._CURATED_EXCLUSIONS).
    """
    clauses: dict[int, list[Clause]] = {}
    anchor_index: dict[str, set[int]] = {}
    for sentence in sentences:
        segmented = segment(sentence)
        if segmented:
            clauses[sentence["id"]] = segmented
        forms = {t.lower() for t in words(sentence["text"])}
        forms |= {t.lower() for t in tokenize_sequence(sentence["text"])}
        for token in forms:
            anchor_index.setdefault(token, set()).add(sentence["id"])
    return clauses, anchor_index
