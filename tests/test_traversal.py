import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dcd.traversal import (  # noqa: E402
    cast_transition,
    king_wen_number,
)


class FakeRng:
    """Returns coin values from a fixed queue, ignoring the `choices`
    argument. Lets us test the coin-total -> line mapping without any
    real randomness, and without any King Wen table data (§9 step 6).
    """

    def __init__(self, queue):
        self._queue = list(queue)

    def choice(self, _options):
        return self._queue.pop(0)


def make_trivial_king_wen_lookup():
    """A synthetic 64-entry lookup, deliberately NOT derived from
    data/king_wen_table.json, so this test stays independent of that
    (possibly-wrong-until-verified) table per §9 step 6.
    """
    lookup = {}
    for i in range(64):
        bits = format(i, "06b")[::-1]  # arbitrary but unique per pattern
        lookup[bits] = i + 1
    assert len(lookup) == 64
    return lookup


def test_coin_total_six_is_old_yin_changing_0_to_1():
    # every line totals 6 (2+2+2) -> every line is an old-yin changing line
    rng = FakeRng([2, 2, 2] * 6)
    lookup = make_trivial_king_wen_lookup()
    cast = cast_transition(rng, lookup)
    assert cast["coin_totals_per_line"] == [6, 6, 6, 6, 6, 6]
    # old yin: from=0 (yin), to=1 (yang) on every line -> from_lines are
    # all-zero, to_lines are all-one, so the two hexagrams must differ
    assert cast["from_hex"] != cast["to_hex"]


def test_coin_total_nine_is_old_yang_changing_1_to_0():
    rng = FakeRng([3, 3, 3] * 6)  # every line totals 9
    lookup = make_trivial_king_wen_lookup()
    cast = cast_transition(rng, lookup)
    assert cast["coin_totals_per_line"] == [9, 9, 9, 9, 9, 9]


def test_coin_total_seven_is_young_yang_stable():
    rng = FakeRng([2, 2, 3] * 6)  # sums to 7 each line
    lookup = make_trivial_king_wen_lookup()
    cast = cast_transition(rng, lookup)
    assert cast["coin_totals_per_line"] == [7, 7, 7, 7, 7, 7]
    # stable line: from_hex should equal to_hex (no changing lines)
    assert cast["from_hex"] == cast["to_hex"]


def test_coin_total_eight_is_young_yin_stable():
    rng = FakeRng([2, 3, 3] * 6)  # sums to 8 each line
    lookup = make_trivial_king_wen_lookup()
    cast = cast_transition(rng, lookup)
    assert cast["coin_totals_per_line"] == [8, 8, 8, 8, 8, 8]
    assert cast["from_hex"] == cast["to_hex"]


def test_king_wen_number_lookup_roundtrip():
    lookup = make_trivial_king_wen_lookup()
    lines = [1, 0, 1, 0, 1, 0]
    binary_str = "".join(str(b) for b in lines)
    assert king_wen_number(lines, lookup) == lookup[binary_str]


# ---------------------------------------------------------------------
# §6.2 derive_jump — resolved 2026-09-15
# ---------------------------------------------------------------------

def test_from_lines_maps_coin_totals_to_yin_yang():
    from dcd.traversal import from_lines
    # 6 old yin, 7 young yang, 8 young yin, 9 old yang
    assert from_lines([6, 7, 8, 9, 7, 8]) == [0, 1, 0, 1, 1, 0]


def test_from_lines_rejects_an_impossible_total():
    import pytest
    from dcd.traversal import from_lines
    with pytest.raises(AssertionError):
        from_lines([5, 7, 8, 9, 7, 8])


def test_derive_jump_reads_lines_as_binary_bottom_first():
    from dcd.traversal import derive_jump
    # bottom line is the 1s place
    assert derive_jump([7, 8, 8, 8, 8, 8])[0] == 1
    assert derive_jump([8, 7, 8, 8, 8, 8])[0] == 2
    assert derive_jump([8, 8, 8, 8, 8, 7])[0] == 32
    assert derive_jump([7, 7, 7, 7, 7, 7])[0] == 63
    assert derive_jump([8, 8, 8, 8, 8, 8])[0] == 0


def test_derive_jump_direction_is_the_bottom_line():
    from dcd.traversal import derive_jump
    assert derive_jump([7, 8, 8, 8, 8, 8])[1] == "forward"   # bottom yang
    assert derive_jump([8, 7, 7, 7, 7, 7])[1] == "backward"  # bottom yin


def test_derive_jump_identity_casts_are_not_all_backward():
    """The superseded `from_hex < to_hex` rule sent all 18% of identity
    casts backward. The bottom line is fair on every cast."""
    import random
    from dcd.traversal import derive_jump
    rng = random.Random(4)
    directions = set()
    for _ in range(200):
        totals = [rng.choice([7, 8]) for _ in range(6)]  # no changing lines
        directions.add(derive_jump(totals)[1])
    assert directions == {"forward", "backward"}


def test_derive_jump_distance_is_flat_not_centre_weighted():
    """All 64 values must occur, none dominating — the summed-totals
    formula put 76% of casts in 7-11."""
    import random
    from collections import Counter
    from dcd.traversal import derive_jump
    rng = random.Random(9)
    seen = Counter()
    n = 40000
    for _ in range(n):
        totals = [sum(rng.choice([2, 3]) for _ in range(3)) for _ in range(6)]
        seen[derive_jump(totals)[0]] += 1
    assert len(seen) == 64
    assert max(seen.values()) / n < 0.025      # flat is 1.56%
    assert min(seen.values()) / n > 0.008


# ---------------------------------------------------------------------
# §6.2/§6.4 position_of, jump_from_position, scan_to_nearest_noun
# ---------------------------------------------------------------------

_SEQ = ["The", "fox", "sat", "by", "the", "well", "and", "the", "fox", "slept"]
_NOUNS = {"fox", "well"}


def test_position_of_reports_index_and_count():
    import random
    from dcd.traversal import position_of
    occ = position_of("fox", _SEQ, random.Random(0))
    assert occ.count == 2
    assert occ.position in (1, 8)
    assert occ.index in (0, 1)


def test_position_of_is_case_insensitive():
    import random
    from dcd.traversal import position_of
    assert position_of("THE", _SEQ, random.Random(0)).count == 3


def test_position_of_draws_more_than_one_occurrence_over_many_rolls():
    """§6.4 resolved to a RANDOM occurrence, not always the first."""
    import random
    from dcd.traversal import position_of
    rng = random.Random(2)
    drawn = {position_of("fox", _SEQ, rng).position for _ in range(40)}
    assert drawn == {1, 8}


def test_position_of_raises_when_absent():
    import pytest, random
    from dcd.traversal import position_of
    with pytest.raises(ValueError):
        position_of("dragon", _SEQ, random.Random(0))


def test_jump_from_position_offsets_both_ways():
    from dcd.traversal import jump_from_position
    assert jump_from_position(4, 3, "forward", _SEQ) == 7
    assert jump_from_position(4, 3, "backward", _SEQ) == 1


def test_jump_from_position_wraps_at_both_ends():
    from dcd.traversal import jump_from_position
    assert jump_from_position(8, 5, "forward", _SEQ) == 3     # past the end
    assert jump_from_position(1, 5, "backward", _SEQ) == 6    # past the start


def test_jump_from_position_rejects_a_bad_direction():
    import pytest
    from dcd.traversal import jump_from_position
    with pytest.raises(ValueError):
        jump_from_position(0, 1, "sideways", _SEQ)


def test_scan_to_nearest_noun_reports_distance():
    from dcd.traversal import scan_to_nearest_noun
    assert scan_to_nearest_noun(1, _SEQ, _NOUNS) == ("fox", 0)   # already on one
    assert scan_to_nearest_noun(2, _SEQ, _NOUNS) == ("well", 3)


def test_scan_to_nearest_noun_scans_forward_and_wraps():
    from dcd.traversal import scan_to_nearest_noun
    # from the last token, the only way on is round the end
    assert scan_to_nearest_noun(9, _SEQ, _NOUNS) == ("fox", 2)


def test_scan_to_nearest_noun_raises_when_no_token_qualifies():
    import pytest
    from dcd.traversal import scan_to_nearest_noun
    with pytest.raises(ValueError):
        scan_to_nearest_noun(0, _SEQ, {"unicorn"})


def test_scan_excludes_word_a_so_the_two_words_always_differ():
    """word_B == word_A on 3.4% of casts without this: a short backward
    jump plus the forward snap returns to the starting word. Reversed
    2026-09-16. Not a re-draw — the cast stands, the scan walks on."""
    from dcd.traversal import scan_to_nearest_noun
    seq = ["the", "fox", "sat", "by", "the", "fox"]
    assert scan_to_nearest_noun(1, seq, {"fox", "sat"}) == ("fox", 0)
    assert scan_to_nearest_noun(1, seq, {"fox", "sat"}, exclude="fox") == ("sat", 1)


def test_scan_exclude_is_case_insensitive():
    from dcd.traversal import scan_to_nearest_noun
    seq = ["Fox", "sat"]
    assert scan_to_nearest_noun(0, seq, {"fox", "sat"}, exclude="FOX") == ("sat", 1)
