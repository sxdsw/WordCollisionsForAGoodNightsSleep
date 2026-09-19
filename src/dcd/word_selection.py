"""§5.3 — Word Selection Per Chapter.

word_a: uniform random draw from a fixed word pool (corpus vocabulary,
filtered to tokens WordNet lists as having a noun sense). This is an
eligibility filter, not a ranking — every noun that passes has equal
chance of being drawn (does not conflict with Constraint 1).

word_b: not drawn here, but constrained by the same pool. Under the
revised §6.2 it is *found* rather than drawn — the hexagram cast gives a
jump distance/direction from word_a's corpus position, and the scan then
runs forward to the first token whose lowercased form is in this pool.
So every word_b is a pool member too; it just arrives by walking the
corpus instead of by rng.choice(). Consequence: word_a is uniform over
pool *types*, word_b is effectively weighted by corpus frequency.
"""

import json
import re
import string
from pathlib import Path


# Tokenisation for the vocabulary scan (rule-based only, Constraint 1):
#   * split on whitespace AND hyphens/dashes, so "fox-girl" -> fox, girl
#     and the transliterated names ("Ch'ang-ngan", "Sung-ling") break
#     into pieces that then fail the checks below;
#   * strip surrounding punctuation and a trailing possessive "'s";
#   * keep a token only if what remains is >= 2 plain ASCII letters.
#     This drops single-letter debris (initials, "M.A.") and every
#     transliteration fragment (they carry an apostrophe-aspirate or an
#     accented vowel: "ch'ang", "hsü", "chün"), without needing a name
#     list.
_SPLIT_RE = re.compile(r"[\s\-‐-―]+")
_POSSESSIVE_RE = re.compile(r"['’]s$")
_PLAIN_WORD_RE = re.compile(r"[a-z]{2,}$")
_STRIP_CHARS = string.punctuation + "‘’“”—…"


# Curated exclusions — reviewed token-by-token in sentence context and
# removed by the project owner (NEEDS_INPUT.md item 6c). WordNet gives
# each a noun sense; in THIS corpus none is a content noun a "collision"
# cut should land on. A hand-built list, a deliberate step outside the
# spec's "WordNet is the only filter" rule, affecting ~2.4% of the
# pre-filter pool.
#
# MEASURED 2026-09-16 — the list is two unlike things, and an earlier
# version of this comment described them wrongly. It claimed the debris
# came from contractions ("you're", "won't"). It does not: a contraction
# keeps its apostrophe, so it fails _PLAIN_WORD_RE and never reaches the
# vocabulary at all. And "won" is not debris — it is the ordinary past
# tense of "win", excluded as a judgement like the other function words.
#
#   * 23 entries are FRAGMENTS OF HYPHENATED TRANSLITERATIONS, produced
#     by _SPLIT_RE breaking "Ch'ang-shan" into "ch'ang" + "shan" or
#     "Ta-nan" into "ta" + "nan". These are tokenizer artefacts.
#     NOT fixed by changing the tokenizer: keeping hyphenated words whole
#     would cost 116 real pool words that occur ONLY inside compounds
#     (ant, aspen, bishop, bullock, captain, citron, couplet, elm,
#     driver, eater...), and would shift every corpus position by
#     dropping ~2,328 tokens from the flat sequence. Five real nouns lost
#     per fragment removed; the hand-list is the cheaper fix.
#
#   * 90 entries are STANDALONE WORDS — English function words WordNet
#     gives a noun sense ("he", "was", "in", "be", "do", "one", "two"),
#     and transliterated names that stand on their own ("han", "lao",
#     "li", "ma", "tai", "wu"). These are judgements, not artefacts, and
#     no tokenizer change touches them.
#
# Why a hand list rather than a rule: WordNet's noun check asks whether a
# word has ANY noun sense, not whether it is a noun here, and no
# automated substitute is clean. A frequency threshold over WordNet's
# tagged data was tested and rejected — it cuts real nouns that are
# commoner as verbs ("colour", "pepper", "lock") while keeping "while"
# (100% noun in tagged data, a conjunction throughout this corpus) and
# having no data at all for "does"/"won"/"re"/"shan". Deciding it per
# sentence would need a POS tagger, which Constraint 1 rules out.
#
# The two groups are kept as separate frozensets so the distinction
# survives; _CURATED_EXCLUSIONS is their union and is what the build
# uses.
_HYPHEN_FRAGMENTS = frozenset({
    "ai", "ang", "chi", "de", "ex", "fo", "hao", "ii", "ko", "min", "nan",
    "ngo", "ni", "pei", "pi", "po", "pu", "re", "sa", "shan", "si", "ta",
    "wan",
})

_STANDALONE_EXCLUSIONS = frozenset({
    "above", "am", "an", "are", "as", "at", "back", "be", "being", "can",
    "do", "does", "down", "enough", "even", "fa", "far", "few", "get",
    "go", "han", "has", "have", "he", "here", "ho", "hua", "hun", "in",
    "it", "its", "lan", "lao", "lay", "lbs", "let", "li", "lin", "longer",
    "looking", "lu", "ma", "mao", "may", "me", "mi", "more", "mr", "mrs",
    "much", "na", "no", "nobody", "nothing", "now", "one", "or", "out",
    "over", "pa", "put", "same", "saw", "say", "see", "seeing", "set",
    "so", "somebody", "still", "tai", "tan", "tao", "then", "there",
    "ti", "two", "us", "was", "wei", "well", "while", "who", "why",
    "will", "won", "wu", "yen", "yes", "yi",
})

_CURATED_EXCLUSIONS = _HYPHEN_FRAGMENTS | _STANDALONE_EXCLUSIONS



def tokenize_sequence(text: str) -> list[str]:
    """Order-preserving word tokenisation, same rules as the vocabulary
    scan above: split on whitespace and hyphens/dashes, strip surrounding
    punctuation, drop a trailing possessive "'s".

    Unlike `_vocabulary`, this keeps EVERY non-empty token, in order, in
    its original case. It is the single definition of "a word of the
    corpus" shared by the word pool (§5.3) and the positional traversal
    (§6.2) -- they must agree, or a jump distance counted in one would
    not line up with the noun set built by the other.

    Tokens that fail `_PLAIN_WORD_RE` (transliteration fragments like
    "ch'ang"/"hsü", single letters) are KEPT here: they are words in
    the text and a jump of N words must count them. They simply never
    match `noun_set`, so `scan_to_nearest_noun` walks past them.
    Tokens that strip to nothing (bare "--", stray brackets) are not
    words and are dropped.
    """
    tokens: list[str] = []
    for raw in _SPLIT_RE.split(text):
        tok = _POSSESSIVE_RE.sub("", raw.strip(_STRIP_CHARS))
        if tok:
            tokens.append(tok)
    return tokens


def _vocabulary(corpus_text: str) -> set[str]:
    return {
        tok
        for tok in tokenize_sequence(corpus_text.lower())
        if _PLAIN_WORD_RE.match(tok)
    }


def build_word_pool(corpus_text: str) -> list[str]:
    """Extracts unique vocabulary tokens from the CLEANED corpus text
    (corpus.ingest() output joined together, not the raw Gutenberg file),
    keeps only tokens WordNet lists as having a noun sense, then drops the
    hand-curated _CURATED_EXCLUSIONS.

    This is an eligibility filter, not a ranking (§5.3). Build once and
    store as data/word_pool.json via scripts/build_word_pool.py -- do
    not regenerate per run.

    Requires `nltk` with the WordNet corpus downloaded.
    """
    try:
        from nltk.corpus import wordnet  # local import: optional dependency
    except ImportError as e:
        raise ImportError(
            "nltk is required for build_word_pool(). Install with "
            "`pip install nltk --break-system-packages` and run "
            "nltk.download('wordnet') before calling this."
        ) from e

    tokens = _vocabulary(corpus_text)
    nouns = sorted(
        t
        for t in tokens
        if t not in _CURATED_EXCLUSIONS and wordnet.synsets(t, pos=wordnet.NOUN)
    )
    return nouns


def save_word_pool(pool: list[str], path: str) -> None:
    Path(path).write_text(json.dumps(pool, indent=2), encoding="utf-8")


def load_word_pool(path: str) -> list[str]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select_word_a(pool: list[str], rng) -> str:
    """Uniform random choice from the static word pool. No weighting."""
    return rng.choice(pool)


# ---------------------------------------------------------------------
# Positional noun filter (optional; off by default)
# ---------------------------------------------------------------------
#
# WordNet's check asks whether a word has ANY noun sense in English, not
# whether it is a noun in THIS corpus. That is why "old", "found",
# "take" and "three" are in the pool. This filter asks the corpus
# instead: does the word ever occupy a position only a noun occupies?
#
#     the door,        <- determiner + word + phrase-closer   = noun
#     of silver was    <- preposition + word + phrase-closer   = noun
#     the old man      <- followed by "man", not a closer      = NOT counted
#
# Real nouns score 45-90%; adjectives and verbs score 0-1%.
#
# Constraint 1: two closed word lists and counting. No tagger, no model,
# no similarity. Same technique as the clause-splitting rules in
# CLAUSE_WALK_SPEC.md §4.
#
# This is a larger act of curation than _CURATED_EXCLUSIONS. ADOPTED
# 2026-09-16: data/word_pool.json is now the filtered pool (4,547 words);
# the unfiltered WordNet pool is kept at data/word_pool_wordnet_only.json
# (4,646) so chapters logged before the switch stay reproducible.
# build_word_pool.py applies it by default; --no-positional emits the
# raw pool.
#
# Known imprecision at the boundary. The 5% threshold is not a clean
# line: "three" (5.4%), "ten" (7.3%), "hundred" (9.7%), "thousand"
# (18.2%) and "fifty" (15.8%) survive while "four", "five", "six",
# "seven", "eight" and "twenty" are cut, because numerals score as nouns
# when used nominally ("a thousand of them"). "nine" survives only for
# having 19 occurrences, one under MIN_EVIDENCE. Other marginal
# survivors at 5-8%: white, small, little, lady, know, buy, going,
# thinking, asking, round, begging, chang, chou. Tighten by raising
# MIN_NOUN_RATIO if this matters; each step up also cuts real nouns.

_LEFT_CONTEXT = frozenset({
    # determiners
    "the", "a", "an", "this", "that", "these", "those",
    "his", "her", "their", "its", "my", "our", "your", "some", "no",
    # quantifiers — without these, "for three years" and "a few moments"
    # look like non-noun positions and "years"/"moments"/"ounces"/"times"
    # are cut wrongly
    "few", "several", "many", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten", "twenty", "thirty", "forty", "fifty",
    "hundred", "thousand", "other", "another", "every", "each", "all",
    "both", "any", "more", "most", "such", "own",
    # prepositions — "to heaven,", "in purgatory,", "of silver"
    "to", "of", "in", "on", "at", "by", "with", "from", "into", "upon",
    "for", "through", "towards", "toward", "without", "within", "under",
    "over", "after", "before", "beside", "against", "among", "about",
})

_PHRASE_CLOSER = frozenset(
    list(".,;:!?")
    + ["of", "in", "on", "to", "at", "by", "with", "from", "was", "were",
       "is", "are", "had", "has", "who", "which", "and", "but", "for",
       "into", "upon", "said", "then", "when", "so"]
)

# Words the rule cannot see, kept by name. Reviewed 2026-09-16.
#   orders   — always "gave orders", object of a verb, nothing qualifying
#              in front of it; scores 0.0%
#   degree   — 2.9%, fellow 4.4%, creature 4.5%: real nouns sitting just
#              under the threshold. Lowering the threshold to reach them
#              readmits 25 adjectives and verbs (might, dead, poor, bad,
#              ill, black, cold, born, rose, burst...), so they are named
#              instead.
POSITIONAL_KEEP = frozenset({"orders", "degree", "fellow", "creature"})

# Below this many occurrences there is not enough evidence to judge, so
# the word keeps WordNet's benefit of the doubt. Two-thirds of the pool
# occurs four times or fewer; without this, rare real nouns (cassia,
# skiff, turtles, wisps) are cut for lack of examples.
MIN_EVIDENCE = 20
MIN_NOUN_RATIO = 0.05

# Local to this filter: unlike _SPLIT_RE it KEEPS punctuation, because
# the phrase-closer test needs it. tokenize_sequence() remains the
# single definition of "a word of the corpus" for §5.3/§6.2 — this does
# not touch it.
_POSITIONAL_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*|[.,;:!?]")


# Words that syntactically REQUIRE a complement — a numeral or quantifier
# is unfinished on its own, so whatever follows it at a splice seam looks
# wrong whatever it is. "...and about fifteen" + " husband." reads as a
# typo rather than as a collision. ADDED 2026-09-16.
#
# This is a grammatical-class lookup, not a judgment about output
# quality: these words are excluded for what they are, not for how the
# result reads. Prepositions and articles are already absent — the
# positional filter and _CURATED_EXCLUSIONS removed them.
#
# Effect measured over the corpus: 25 words, 0.4% of running tokens.
# word_A is one of them on 0.5% of draws; the word_B scan stops on one on
# 1.9% of landings, and thereafter walks to the next pool member (the
# scan lands on "pears" instead of "hundred" in "several hundred pears").
#
# Cost: no chapter can ever be seeded by a number. "a thousand", "a
# hundred" and "three" are lost as openings.
_COMPLEMENT_REQUIRING = frozenset({
    # numerals
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty",
    "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand",
    "million", "dozen", "score",
    # quantifiers
    "few", "several", "many", "much", "more", "most", "less", "least",
    "both", "either", "neither", "every", "each", "another", "other",
    "such", "own", "half", "whole", "certain", "various", "numerous",
})


def noun_position_ratios(pool: list[str], corpus_text: str) -> dict[str, tuple[int, int]]:
    """For each pool word, (times in noun position, total occurrences)."""
    members = {w.lower() for w in pool}
    tokens = [t.lower() for t in _POSITIONAL_TOKEN_RE.findall(corpus_text)]
    counts: dict[str, list[int]] = {w: [0, 0] for w in members}
    for i, token in enumerate(tokens):
        if token not in members:
            continue
        counts[token][1] += 1
        left = tokens[i - 1] if i else ""
        right = tokens[i + 1] if i + 1 < len(tokens) else ""
        if left in _LEFT_CONTEXT and right in _PHRASE_CLOSER:
            counts[token][0] += 1
    return {w: (h, t) for w, (h, t) in counts.items()}


def filter_by_position(
    pool: list[str], corpus_text: str
) -> tuple[list[str], list[str]]:
    """Returns (kept, cut). Cut = occurs >= MIN_EVIDENCE times, scores
    below MIN_NOUN_RATIO, and is not in POSITIONAL_KEEP.
    """
    ratios = noun_position_ratios(pool, corpus_text)
    kept, cut = [], []
    for word in pool:
        head, total = ratios[word.lower()]
        if word.lower() in _COMPLEMENT_REQUIRING:
            cut.append(word)
            continue
        drop = (
            total >= MIN_EVIDENCE
            and (head / total) < MIN_NOUN_RATIO
            and word.lower() not in POSITIONAL_KEEP
        )
        (cut if drop else kept).append(word)
    return kept, cut
