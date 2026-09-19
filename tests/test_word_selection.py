import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dcd.word_selection import (  # noqa: E402
    _CURATED_EXCLUSIONS,
    _vocabulary,
    load_word_pool,
    select_word_a,
)

POOL_FILE = Path(__file__).resolve().parent.parent / "data" / "word_pool.json"


# --- tokenisation (pure, no nltk) ------------------------------------------


def test_vocabulary_splits_hyphenated_compounds():
    assert _vocabulary("a fox-girl appeared") >= {"fox", "girl", "appeared"}


def test_vocabulary_drops_possessive_s():
    vocab = _vocabulary("the dog's bone and the foxes' den")
    assert "dog" in vocab
    assert "dogs" not in vocab and "dog's" not in vocab


def test_vocabulary_drops_single_letters_and_accented_fragments():
    vocab = _vocabulary("Mr. J. Hsü met Ch‘ang-ngan at M.A. level")
    assert "j" not in vocab
    assert "hs" not in vocab and "hsü" not in vocab
    assert "ch" not in vocab and "ngan" in vocab  # plain-ascii piece survives


def test_vocabulary_is_lowercased_and_deduped():
    assert _vocabulary("Dream dream DREAM") == {"dream"}


# --- selection ------------------------------------------------------------


def test_select_word_a_is_uniform_draw_from_pool():
    pool = ["alpha", "beta", "gamma"]
    rng = random.Random(0)
    picks = {select_word_a(pool, rng) for _ in range(50)}
    assert picks <= set(pool)


def test_select_word_a_is_deterministic_under_seed():
    pool = ["alpha", "beta", "gamma", "delta"]
    assert select_word_a(pool, random.Random(42)) == select_word_a(
        pool, random.Random(42)
    )


# --- the committed static pool ------------------------------------------


built_pool = pytest.mark.skipif(
    not POOL_FILE.exists() or POOL_FILE.read_text().strip() in ("", "[]"),
    reason="data/word_pool.json not built yet (run scripts/build_word_pool.py)",
)


@built_pool
def test_committed_pool_is_sane():
    pool = load_word_pool(str(POOL_FILE))
    assert len(pool) > 3000
    assert pool == sorted(pool)
    assert len(pool) == len(set(pool))
    assert all(w == w.lower() for w in pool)
    assert all(len(w) >= 2 for w in pool)
    # common story nouns are present
    for w in ("dream", "fox", "priest", "ghost", "sword", "wine"):
        assert w in pool


@built_pool
def test_committed_pool_has_no_curated_exclusions():
    pool = set(load_word_pool(str(POOL_FILE)))
    assert not (pool & _CURATED_EXCLUSIONS)
    # spot-check a few from each exclusion group
    for w in ("he", "was", "nothing", "li", "wu", "mr", "mrs", "ii"):
        assert w not in pool
    # second pass (2026-09-01): stopwords and tokenizer debris that
    # matter now word_B lands on pool members by walking the corpus
    for w in ("then", "there", "have", "back", "well", "shan", "re", "won"):
        assert w not in pool


# ---------------------------------------------------------------------
# Positional noun filter (opt-in; not applied to the live pool)
# ---------------------------------------------------------------------

_POS_TEXT = (
    "He opened the door, and the old man went in. "
    "A great dream was upon him. He had found the door open. "
    "She took the old lamp from the door, and the dream was gone. "
    "The man was young, and the young man found a dream in the lamp. "
) * 24     # every test word must clear MIN_EVIDENCE (20 occurrences)


def test_filter_keeps_nouns_and_cuts_adjectives_and_verbs():
    from dcd.word_selection import filter_by_position
    pool = ["door", "dream", "lamp", "old", "young", "great", "found"]
    kept, cut = filter_by_position(pool, _POS_TEXT)
    assert {"door", "dream", "lamp"} <= set(kept)
    assert {"old", "young", "great", "found"} <= set(cut)


def test_filter_spares_words_with_too_little_evidence():
    """Below MIN_EVIDENCE a word keeps WordNet's benefit of the doubt."""
    from dcd.word_selection import MIN_EVIDENCE, filter_by_position
    rare = "skiff " + _POS_TEXT
    kept, cut = filter_by_position(["skiff"], rare)
    assert kept == ["skiff"] and cut == []
    assert MIN_EVIDENCE == 20


def test_keep_list_survives_a_zero_score():
    from dcd.word_selection import POSITIONAL_KEEP, filter_by_position
    assert "orders" in POSITIONAL_KEEP
    text = "He gave orders that day. " * 30
    kept, cut = filter_by_position(["orders"], text)
    assert kept == ["orders"] and cut == []


def test_noun_position_ratios_counts_head_and_total():
    from dcd.word_selection import noun_position_ratios
    ratios = noun_position_ratios(["door"], "He opened the door, then the door was shut.")
    head, total = ratios["door"]
    assert total == 2
    assert head == 2          # "the door," and "the door was"


def test_filter_does_not_touch_tokenize_sequence():
    """The positional tokeniser keeps punctuation; tokenize_sequence,
    which defines corpus positions for §6.2, must be unaffected."""
    from dcd.word_selection import tokenize_sequence
    assert tokenize_sequence("the door, and the man.") == [
        "the", "door", "and", "the", "man"
    ]


def test_complement_requiring_words_are_always_cut():
    """Numerals and quantifiers are unfinished on their own, so whatever
    follows them at a splice seam reads as a typo. Excluded by class."""
    from dcd.word_selection import filter_by_position
    kept, cut = filter_by_position(["fifteen", "hundred", "half", "door"], _POS_TEXT)
    assert set(cut) == {"fifteen", "hundred", "half"}
    assert kept == ["door"]


def test_complement_exclusion_beats_the_keep_list():
    from dcd.word_selection import POSITIONAL_KEEP, _COMPLEMENT_REQUIRING
    assert not (POSITIONAL_KEEP & _COMPLEMENT_REQUIRING)
