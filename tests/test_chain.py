"""src/dcd/chain.py — the book-level chain from a single starting word."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import random  # noqa: E402

import pytest  # noqa: E402

from dcd.chain import MAX_CAST_REACH, STOP_REASON, run_chain  # noqa: E402
from dcd.clause import build_clause_index  # noqa: E402
from dcd.traversal import build_king_wen_lookup, scan_to_nearest_noun  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------
# scan_to_nearest_noun(skip=...) — the additive change to traversal.py
# ---------------------------------------------------------------------

SEQ = ["the", "door", "and", "the", "river", "of", "the", "priest"]
NOUNS = {"door", "river", "priest"}


def test_skip_is_scanned_past():
    assert scan_to_nearest_noun(0, SEQ, NOUNS).word == "door"
    assert scan_to_nearest_noun(0, SEQ, NOUNS, skip={"door"}).word == "river"
    assert scan_to_nearest_noun(0, SEQ, NOUNS, skip={"door", "river"}).word == "priest"


def test_skip_default_is_unchanged():
    """Every existing caller must be byte-identical."""
    for raw in range(len(SEQ)):
        assert scan_to_nearest_noun(raw, SEQ, NOUNS) == scan_to_nearest_noun(
            raw, SEQ, NOUNS, skip=None
        )


def test_skip_and_exclude_compose():
    got = scan_to_nearest_noun(0, SEQ, NOUNS, exclude="door", skip={"river"})
    assert got.word == "priest"


def test_skip_is_matched_lowercased():
    seq = ["a", "Priest", "and", "a", "River"]
    got = scan_to_nearest_noun(0, seq, NOUNS, skip={"priest"})
    assert got.word == "River"          # the corpus's own casing is preserved


def test_scan_distance_counts_skipped_words():
    got = scan_to_nearest_noun(0, SEQ, NOUNS, skip={"door", "river"})
    assert got.scan_distance == 7


# ---------------------------------------------------------------------
# the chain, against the real corpus
# ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def corpus():
    import json

    from dcd.word_selection import tokenize_sequence

    sentences = [
        json.loads(line)
        for line in (ROOT / "data" / "sentences.jsonl")
        .read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    pool = json.loads((ROOT / "data" / "word_pool.json").read_text(encoding="utf-8"))
    clauses, anchors = build_clause_index(sentences)
    return {
        "clauses": clauses,
        "anchors": anchors,
        "nouns": {w.lower() for w in pool},
        "sequence": tokenize_sequence(" ".join(s["text"] for s in sentences)),
        "king_wen": build_king_wen_lookup(str(ROOT / "data" / "king_wen_table.json")),
    }


def _run(corpus, seed, max_chapters=None, start="sleep", tidy=False):
    return list(
        run_chain(
            start, corpus["clauses"], corpus["anchors"], corpus["king_wen"],
            corpus["sequence"], corpus["nouns"], random.Random(seed),
            max_chapters=max_chapters, tidy=tidy,
        )
    )


def test_tidy_changes_only_the_joins(corpus):
    """Same seed, same chapters, same words, same casts — only the text
    of the joins differs (§8 amendment 2026-09-18).
    """
    raw = _run(corpus, 5, 20)
    tidied = _run(corpus, 5, 20, tidy=True)
    assert len(raw) == len(tidied)
    for a, b in zip(raw, tidied):
        for key in ("word_a", "word_b", "hops", "traversal_cast",
                    "succession_cast", "succession_word_a", "word_count"):
            assert a[key] == b[key]
        assert a["tidied"] is False and b["tidied"] is True
    assert [a["output_text"] for a in raw] != [b["output_text"] for b in tidied]


def test_tidy_is_off_by_default(corpus):
    assert _run(corpus, 5, 5) == _run(corpus, 5, 5, tidy=False)


def test_the_succession_throw_decides_the_next_word_a(corpus):
    chapters = [r for r in _run(corpus, 1, 30) if not r.get("terminal")]
    for previous, following in zip(chapters, chapters[1:]):
        assert following["word_a"] == previous["succession_word_a"].lower()


def test_word_b_is_a_coordinate_not_the_successor(corpus):
    """The whole reason for the second throw: word_B is printed and then
    discarded, never promoted into the next chapter's word_A.
    """
    chapters = [r for r in _run(corpus, 1, 60) if not r.get("terminal")]
    carried = sum(
        following["word_a"] == previous["word_b"].lower()
        for previous, following in zip(chapters, chapters[1:])
    )
    # Both land on pool nouns, so a coincidence is possible; a chain is not.
    assert carried <= 1


def test_each_chapter_records_two_distinct_throws(corpus):
    record = _run(corpus, 1, 1)[0]
    assert len(record["traversal_cast"]["coin_totals_per_line"]) == 6
    assert len(record["succession_cast"]["coin_totals_per_line"]) == 6
    assert record["traversal_jump"]["word_a_position"] != (
        record["succession_jump"]["word_a_position"]
    ) or record["traversal_cast"] != record["succession_cast"]


def test_the_collision_draw_skips_nothing(corpus):
    """Only the succession refuses used words. word_B may repeat across
    the book — the same word can be collided with from several
    directions, which is the point of it.
    """
    chapters = [r for r in _run(corpus, 1, 400) if not r.get("terminal")]
    seen_as_word_a = {r["word_a"] for r in chapters}
    assert any(r["word_b"].lower() in seen_as_word_a for r in chapters)


def test_starts_at_the_given_word(corpus):
    assert _run(corpus, 1, 3)[0]["word_a"] == "sleep"
    assert _run(corpus, 1, 3, start="dream")[0]["word_a"] == "dream"


def test_no_word_is_used_twice(corpus):
    chapters = [r for r in _run(corpus, 1, 200) if not r.get("terminal")]
    used = [r["word_a"] for r in chapters]
    assert len(used) == len(set(used))


def test_runs_to_its_own_stop_and_records_why(corpus):
    records = _run(corpus, 1)
    terminal = records[-1]
    assert terminal["terminal"] is True
    assert terminal["stop_reason"] == STOP_REASON
    assert terminal["scan_distance"] > MAX_CAST_REACH
    assert terminal["chapters_before_stop"] == len(records) - 1


def test_the_final_chapter_still_prints(corpus):
    """It is the succession that failed, not the chapter."""
    records = _run(corpus, 1)
    last_chapter, terminal = records[-2], records[-1]
    assert last_chapter["word_a"] == terminal["word_a"]
    assert last_chapter["chain"]["succession_scan_distance"] > MAX_CAST_REACH
    assert last_chapter["output_text"]


def test_every_printed_chapter_is_within_cast_reach(corpus):
    """The whole point of the stop rule: no chapter in the book was
    reached by a scan longer than any cast could jump.
    """
    chapters = [r for r in _run(corpus, 1) if not r.get("terminal")]
    for record in chapters[:-1]:        # the last one is where it stopped
        assert record["chain"]["succession_scan_distance"] <= MAX_CAST_REACH


def test_over_reaching_word_gets_no_chapter(corpus):
    records = _run(corpus, 1)
    terminal = records[-1]
    printed = {r["word_a"] for r in records if not r.get("terminal")}
    assert terminal["would_have_been"].lower() not in printed


def test_same_seed_same_book(corpus):
    assert _run(corpus, 4, 25) == _run(corpus, 4, 25)


def test_different_seeds_differ(corpus):
    assert _run(corpus, 1, 25) != _run(corpus, 2, 25)


def test_max_chapters_truncates_without_changing_the_chapters(corpus):
    short = _run(corpus, 3, 5)
    long = _run(corpus, 3, 12)
    assert len(short) == 5
    assert short == long[:5]


def test_start_word_must_occur_in_the_corpus(corpus):
    with pytest.raises(ValueError, match="does not occur"):
        _run(corpus, 1, 2, start="zzzznotaword")


def test_record_carries_the_full_audit_trail(corpus):
    record = _run(corpus, 1, 1)[0]
    assert record["chain"]["position"] == 1
    assert record["word_a"] == "sleep"
    for key in ("traversal_jump", "succession_jump"):
        assert 0 <= record[key]["jump_distance"] <= MAX_CAST_REACH
        assert record[key]["jump_direction"] in ("forward", "backward")
    assert record["output_text"]
    assert record["word_count"] > 0


# ---------------------------------------------------------------------
# the renderer
# ---------------------------------------------------------------------

def test_title_case_leaves_the_tail_alone():
    from render_dictionary import title_case

    assert title_case("sleep") == "Sleep"
    assert title_case("Ch'ang-ch'ing") == "Ch'ang-ch'ing"
    assert title_case("McGregor") == "McGregor"     # .capitalize() would break this
    assert title_case("") == ""


def test_chapter_html_escapes_and_heads():
    from render_dictionary import chapter_html

    got = chapter_html(
        {"word_a": "sleep", "word_b": "Chang", "output_text": "Tom & <b>Jerry</b>."}
    )
    assert "<h1>Sleep Chang</h1>" in got
    assert "Tom &amp; &lt;b&gt;Jerry&lt;/b&gt;." in got
    assert "<b>Jerry</b>" not in got
