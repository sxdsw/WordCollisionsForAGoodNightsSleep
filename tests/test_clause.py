"""CLAUSE_WALK_SPEC.md §4 (segmentation) and §6a (pronoun tagging)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dcd.clause import Clause, pronoun_classes, segment, words  # noqa: E402
def _s(text: str, sentence_id: int = 1):
    return {"id": sentence_id, "text": text, "story_id": "x", "position_in_story": 0}


def test_splits_on_semicolon_and_subordinator():
    out = segment(_s("He went home; and when the sun rose, he was gone."))
    assert len(out) == 3
    assert out[0].text == "He went home;"


def test_coordinator_alone_does_not_split_a_list():
    """`Hsiao, Chung, and Hsin` must not break at `and Hsin` — a
    coordinator is a boundary only when it leads a subject."""
    out = segment(_s("He had three sons, Hsiao, Chung, and Hsin."))
    assert len(out) == 1


def test_coordinator_leading_a_subject_does_split():
    out = segment(_s("He shut the door, and the servant ran away."))
    assert len(out) == 2


def test_proper_noun_ending_in_ing_is_not_a_participle():
    """`his two sons, Ming and Cheng` must not break at `Ming`."""
    out = segment(_s("In three years' time his two sons, Ming and Cheng, came out high."))
    assert len(out) == 1


def test_participle_after_comma_does_split():
    out = segment(_s("He put down the cup, turning towards the window."))
    assert len(out) == 2


def test_stranded_coordinator_is_stripped_and_anchor_rederived():
    """The interrupted-coordinator case `..., and, when ...`."""
    out = segment(_s("He heard the lady call out to her maid, and, when she came, say to her."))
    assert out[0].text.rstrip().endswith("maid")
    assert out[0].anchor == "maid"


def test_anchor_is_last_word_lowercased_unfiltered():
    """§5 — no filtering; a common last word is still the anchor."""
    out = segment(_s("Sung sat down alongside of him."))
    assert out[0].anchor == "him"


def test_chunks_under_three_tokens_are_discarded():
    """`He ran;` is two tokens, so only the second chunk survives."""
    out = segment(_s("He ran; and so did she."))
    assert [c.text for c in out] == ["and so did she."]
    assert len(segment(_s("No."))) == 0


def test_closing_curly_quote_does_not_defeat_the_split():
    out = segment(_s("“Let me go,” he said. She did not move."))
    assert len(out) == 2


def test_pronoun_classes_is_a_set_and_holds_both():
    assert pronoun_classes(words("he told her to wait")) == frozenset({"M", "F"})
    assert pronoun_classes(words("the door was shut")) == frozenset()
    assert pronoun_classes(words("I saw my own face")) == frozenset({"1"})


def test_clause_records_index_within_sentence():
    out = segment(_s("He went home; she stayed behind; the door was shut."))
    assert [c.index for c in out] == [0, 1, 2]
    assert all(isinstance(c, Clause) for c in out)


def test_abbreviation_period_is_not_a_clause_boundary():
    """`Mr.` must not split. corpus.py's sentence splitter already
    declines to; without the same guard here 350 clauses ended on "mr",
    making it the second most common clause-final word in the corpus."""
    out = segment(_s("To-morrow Mr. Chang will come. He saw Mrs. Wang at the door."))
    assert [c.text for c in out] == [
        "To-morrow Mr. Chang will come.",
        "He saw Mrs. Wang at the door.",
    ]
    assert [c.anchor for c in out] == ["come", "door"]


def test_single_capital_initial_is_not_a_clause_boundary():
    out = segment(_s("He wrote to A. Chang about the matter that night."))
    assert len(out) == 1


def test_anchor_index_is_keyed_under_both_tokenisations():
    """`words()` keeps "fox-girl" whole (clause anchors come from it);
    tokenize_sequence splits it (the word pool comes from that). Both
    must be keys, or a pool word occurring only inside a compound cannot
    seed a walk — that broke 2.55% of chapters."""
    from dcd.clause import build_clause_index
    sentences = [_s("He saw the fox-girl standing by the well.", 1)]
    _, anchors = build_clause_index(sentences)
    assert "fox-girl" in anchors      # clause anchor form
    assert "fox" in anchors           # word-pool form
    assert "girl" in anchors
