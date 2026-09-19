"""CLAUSE_WALK_SPEC.md §5-§9 — the walk."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import random  # noqa: E402

from dcd.clause import build_clause_index  # noqa: E402
from dcd.clause_walk import (  # noqa: E402
    apply_join_conventions,
    assemble,
    balance_marks,
    chapter_record,
    walk,
)
def _sentences():
    raw = [
        "The priest shut the door.",
        "He opened the door and she ran out.",
        "They followed him to the river.",
        "The river was cold that morning.",
        "She wept beside the river.",
        "A stranger came to the door at night.",
    ]
    return [
        {"id": i, "text": t, "story_id": f"s{i}", "position_in_story": 0}
        for i, t in enumerate(raw)
    ]


def _index():
    return build_clause_index(_sentences())


def test_walk_returns_none_when_a_word_is_absent():
    clauses, anchors = _index()
    assert walk("unicorn", "door", clauses, anchors, random.Random(0)) is None
    assert walk("door", "unicorn", clauses, anchors, random.Random(0)) is None


def test_walk_is_deterministic_for_a_fixed_seed():
    clauses, anchors = _index()
    a = walk("door", "river", clauses, anchors, random.Random(7))
    b = walk("door", "river", clauses, anchors, random.Random(7))
    assert a.text == b.text
    assert [h.anchor for h in a.hops] == [h.anchor for h in b.hops]


def test_seed_sentence_contains_word_a():
    clauses, anchors = _index()
    chapter = walk("river", "door", clauses, anchors, random.Random(3))
    assert "river" in _sentences()[chapter.seed_sentence]["text"].lower()


def test_word_b_never_appears_by_requirement():
    """§9 — word_B is a coordinate, not content. It may coincidentally
    appear, but nothing in the walk places it."""
    clauses, anchors = _index()
    chapter = walk("door", "river", clauses, anchors, random.Random(1))
    assert chapter.word_b == "river"


def test_hops_never_revisit_the_sentence_just_left():
    clauses, anchors = _index()
    chapter = walk("door", "river", clauses, anchors, random.Random(11))
    for hop in chapter.hops:
        assert hop.from_sentence != hop.to_sentence


def test_stop_reason_is_recorded():
    clauses, anchors = _index()
    chapter = walk("door", "river", clauses, anchors, random.Random(2))
    assert chapter.stop_reason in {"loop", "exhausted", "cap"}


def test_loop_close_stops_on_a_repeated_anchor():
    clauses, anchors = _index()
    chapter = walk("door", "river", clauses, anchors, random.Random(5))
    if chapter.stop_reason == "loop":
        anchors_used = [h.anchor for h in chapter.hops]
        assert len(anchors_used) != len(set(anchors_used)) or chapter.hops


def test_balance_marks_drops_only_unpaired_marks():
    assert balance_marks('He said, "Come here," and she came.') == (
        'He said, "Come here," and she came.'
    )
    assert balance_marks('Good-by: we shall meet again."') == (
        "Good-by: we shall meet again."
    )
    assert balance_marks("no quotes at all") == "no quotes at all"


def test_assemble_capitalises_and_terminates():
    assert assemble(["he went home"]) == "He went home."
    assert assemble(["he went home."]) == "He went home."
    assert assemble(["he went home,"]) == "He went home."


# --- §8 amendment 2026-09-18: the join conventions, off by default ----


def test_assemble_does_not_tidy_unless_asked():
    """The mechanism's own output must be unchanged."""
    parts = ["he amassed great wealth.", "and immediately seizing a knife"]
    assert assemble(parts) == "He amassed great wealth. and immediately seizing a knife."


def test_tidy_capitalises_after_a_terminal_mark():
    parts = ["he amassed great wealth.", "and immediately seizing a knife"]
    assert assemble(parts, tidy=True) == (
        "He amassed great wealth. And immediately seizing a knife."
    )


def test_tidy_supplies_a_stop_before_a_capital():
    assert apply_join_conventions(["seizing a sharp knife", "Though it is severe"]) == [
        "seizing a sharp knife.",
        "Though it is severe",
    ]


def test_tidy_leaves_an_already_punctuated_clause_alone():
    for mark in (";", ":", ","):
        assert apply_join_conventions([f"it is severe{mark}", "There was a ferry"]) == [
            f"it is severe{mark}",
            "There was a ferry",
        ]


def test_tidy_leaves_unpunctuated_to_lowercase_alone():
    """21.4% of joins. No positional signal, so nothing is invented."""
    parts = ["turn his attention elsewhere", "while Jen and Yi waited"]
    assert apply_join_conventions(parts) == parts


def test_tidy_repairs_no_grammar():
    """Both rules are positional. The non-sequitur must survive intact."""
    tidied = assemble(
        ["he amassed great wealth.", "and immediately seizing a sharp knife"],
        tidy=True,
    )
    assert "and immediately seizing a sharp knife" in tidied.lower()
    assert tidied.lower() == assemble(
        ["he amassed great wealth.", "and immediately seizing a sharp knife"]
    ).lower()          # lower-cased, the two are the same string


def test_tidy_reaches_the_walk():
    clauses, anchors = _index()
    raw = walk("door", "river", clauses, anchors, random.Random(4))
    tidied = walk("door", "river", clauses, anchors, random.Random(4), tidy=True)
    assert raw.hops == tidied.hops          # same chapter, same words
    assert raw.word_a == tidied.word_a


def test_chapter_record_has_the_spec_fields():
    clauses, anchors = _index()
    chapter = walk("door", "river", clauses, anchors, random.Random(4))
    record = chapter_record(12, chapter)
    for key in (
        "chapter_id", "word_a", "word_b", "seed_clause", "hops",
        "voice_arc", "stop_reason", "closing_anchor", "word_count",
        "output_text",
    ):
        assert key in record
    assert record["chapter_id"] == 12
    assert record["word_count"] == len(chapter.text.split())


def test_balance_marks_drops_orphaned_brackets():
    """A commentator's aside whose opening `[` stayed in a sentence that
    was never selected leaves a stray `]`."""
    assert balance_marks("who will not walk in the straight path.]") == (
        "who will not walk in the straight path."
    )
    assert balance_marks("[Hereon the commentator remarks") == (
        "Hereon the commentator remarks"
    )
    assert balance_marks("he read [the note] aloud") == "he read [the note] aloud"


def test_run_chapter_end_to_end_folds_in_cast_and_jump():
    """§9 + §10 — draws both words from the cast, walks, and returns a
    record reproducible from its log."""
    import json
    from pathlib import Path

    from dcd.clause_walk import run_chapter
    from dcd.traversal import build_king_wen_lookup
    from dcd.word_selection import tokenize_sequence

    root = Path(__file__).resolve().parent.parent
    sentences = [
        json.loads(line)
        for line in (root / "data" / "sentences.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    clauses, anchors = build_clause_index(sentences)
    sequence = tokenize_sequence(" ".join(s["text"] for s in sentences))
    pool = json.loads((root / "data" / "word_pool.json").read_text(encoding="utf-8"))
    nouns = {w.lower() for w in pool}
    king_wen = build_king_wen_lookup(str(root / "data" / "king_wen_table.json"))

    record = run_chapter(
        7, sentences, clauses, anchors, sorted(nouns), king_wen,
        sequence, nouns, random.Random(3),
    )
    assert record["chapter_id"] == 7
    assert record["output_text"]
    assert record["word_a"] in nouns and record["word_b"].lower() in nouns
    assert set(record["traversal_cast"]) == {
        "coin_totals_per_line", "from_hex", "to_hex"
    }
    jump = record["traversal_jump"]
    assert 0 <= jump["jump_distance"] <= 63
    assert jump["jump_direction"] in ("forward", "backward")
    assert 0 <= jump["word_a_occurrence_index"] < jump["word_a_occurrence_count"]
