import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dcd.traversal import build_king_wen_lookup  # noqa: E402

TABLE_PATH = Path(__file__).resolve().parent.parent / "data" / "king_wen_table.json"


def load_raw_table():
    return json.loads(TABLE_PATH.read_text(encoding="utf-8"))


def test_table_has_64_entries():
    table = load_raw_table()
    assert len(table) == 64
    assert set(int(k) for k in table.keys()) == set(range(1, 65))


def test_all_line_patterns_are_unique():
    # A hard requirement: King Wen order is a bijection over the space
    # of 64 possible hexagrams, so no two King Wen numbers can share a
    # line pattern.
    table = load_raw_table()
    patterns = [entry["binary_str"] for entry in table.values()]
    assert len(set(patterns)) == 64


def test_spot_check_unambiguous_hexagrams():
    table = load_raw_table()
    assert table["1"]["binary_str"] == "111111"  # Qian, all yang
    assert table["2"]["binary_str"] == "000000"  # Kun, all yin
    assert table["11"]["binary_str"] == "111000"  # Tai/Peace
    assert table["12"]["binary_str"] == "000111"  # Pi/Standstill
    assert table["63"]["binary_str"] == "101010"  # Ji Ji/After Completion
    assert table["64"]["binary_str"] == "010101"  # Wei Ji/Before Completion


# Full King Wen sequence, lines read bottom->top as bits (yang=1, yin=0),
# i.e. inner/lower trigram in bits 0-2, outer/upper in bits 3-5. This is
# an independent transcription of the standard sequence, used to check
# every entry rather than a handful (NEEDS_INPUT.md item 2, part 1).
#
# NOTE: this pins the table to the *standard* convention. The reading
# direction (first toss = bottom line = low bit) is separately confirmed
# against Gait's own worked example -- see
# test_verified_against_gait_example below.
_CANONICAL_KING_WEN = {
    1: "111111", 2: "000000", 3: "100010", 4: "010001", 5: "111010",
    6: "010111", 7: "010000", 8: "000010", 9: "111011", 10: "110111",
    11: "111000", 12: "000111", 13: "101111", 14: "111101", 15: "001000",
    16: "000100", 17: "100110", 18: "011001", 19: "110000", 20: "000011",
    21: "100101", 22: "101001", 23: "000001", 24: "100000", 25: "100111",
    26: "111001", 27: "100001", 28: "011110", 29: "010010", 30: "101101",
    31: "001110", 32: "011100", 33: "001111", 34: "111100", 35: "000101",
    36: "101000", 37: "101011", 38: "110101", 39: "001010", 40: "010100",
    41: "110001", 42: "100011", 43: "111110", 44: "011111", 45: "000110",
    46: "011000", 47: "010110", 48: "011010", 49: "101110", 50: "011101",
    51: "100100", 52: "001001", 53: "001011", 54: "110100", 55: "101100",
    56: "001101", 57: "011011", 58: "110110", 59: "010011", 60: "110010",
    61: "110011", 62: "001100", 63: "101010", 64: "010101",
}


def test_all_64_entries_match_canonical_king_wen_sequence():
    table = load_raw_table()
    for kw in range(1, 65):
        assert table[str(kw)]["binary_str"] == _CANONICAL_KING_WEN[kw], (
            f"KW {kw}: table has {table[str(kw)]['binary_str']}, "
            f"canonical is {_CANONICAL_KING_WEN[kw]}"
        )


def test_build_king_wen_lookup_inverts_cleanly():
    lookup = build_king_wen_lookup(str(TABLE_PATH))
    assert len(lookup) == 64
    assert lookup["111111"] == 1
    assert lookup["000000"] == 2


def test_verified_against_gait_example():
    """Spot-check against a worked example in Christopher Gait's own
    introduction to his 2015 Jiaoshi Yilin ("Notes on Divination", the
    Nanjing-method example). Closes NEEDS_INPUT.md item 2.

    Only the data points are encoded here (his prose is in copyright):
      - coin totals, in casting order: 7, 6, 7, 6, 7, 6
      - Gait states the starting hexagram is 63
      - Gait states the changing lines are positions 2, 4, 6
      - Gait states the post-change hexagram is 1

    Reading first-toss = bottom line (the convention cast_transition()
    and king_wen_number() already use), all three reproduce from
    data/king_wen_table.json. If build_king_wen_table.py's bit
    convention is ever changed, this test breaks loudly.
    """
    lookup = build_king_wen_lookup(str(TABLE_PATH))
    coin_totals = [7, 6, 7, 6, 7, 6]
    before = {6: 0, 7: 1, 8: 0, 9: 1}
    changes = {6, 9}

    from_lines = [before[t] for t in coin_totals]
    changing = [i + 1 for i, t in enumerate(coin_totals) if t in changes]
    to_lines = [
        (1 - b) if t in changes else b
        for t, b in zip(coin_totals, from_lines)
    ]

    assert "".join(map(str, from_lines)) == "101010"
    assert lookup["101010"] == 63          # Gait: starting hexagram 63
    assert changing == [2, 4, 6]           # Gait: changing lines 2, 4, 6
    assert lookup["".join(map(str, to_lines))] == 1  # Gait: post-change hexagram 1
