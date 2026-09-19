import json
from pathlib import Path

TRIGRAM = {
    "qian": (1, 1, 1),  # heaven
    "kun": (0, 0, 0),  # earth
    "zhen": (1, 0, 0),  # thunder
    "kan": (0, 1, 0),  # water
    "gen": (0, 0, 1),  # mountain
    "xun": (0, 1, 1),  # wind
    "li": (1, 0, 1),  # fire
    "dui": (1, 1, 0),  # lake/swamp
}

KING_WEN_TRIGRAMS = {
    1: ("qian", "qian"), 2: ("kun", "kun"), 3: ("zhen", "kan"), 4: ("kan", "gen"),
    5: ("qian", "kan"), 6: ("kan", "qian"), 7: ("kan", "kun"), 8: ("kun", "kan"),
    9: ("qian", "xun"), 10: ("dui", "qian"), 11: ("qian", "kun"), 12: ("kun", "qian"),
    13: ("li", "qian"), 14: ("qian", "li"), 15: ("gen", "kun"), 16: ("kun", "zhen"),
    17: ("zhen", "dui"), 18: ("xun", "gen"), 19: ("dui", "kun"), 20: ("kun", "xun"),
    21: ("zhen", "li"), 22: ("li", "gen"), 23: ("kun", "gen"), 24: ("zhen", "kun"),
    25: ("zhen", "qian"), 26: ("qian", "gen"), 27: ("zhen", "gen"), 28: ("xun", "dui"),
    29: ("kan", "kan"), 30: ("li", "li"), 31: ("gen", "dui"), 32: ("xun", "zhen"),
    33: ("gen", "qian"), 34: ("qian", "zhen"), 35: ("kun", "li"), 36: ("li", "kun"),
    37: ("li", "xun"), 38: ("dui", "li"), 39: ("gen", "kan"), 40: ("kan", "zhen"),
    41: ("dui", "gen"), 42: ("zhen", "xun"), 43: ("qian", "dui"), 44: ("xun", "qian"),
    45: ("kun", "dui"), 46: ("xun", "kun"), 47: ("kan", "dui"), 48: ("xun", "kan"),
    49: ("li", "dui"), 50: ("xun", "li"), 51: ("zhen", "zhen"), 52: ("gen", "gen"),
    53: ("gen", "xun"), 54: ("dui", "zhen"), 55: ("li", "zhen"), 56: ("gen", "li"),
    57: ("xun", "xun"), 58: ("dui", "dui"), 59: ("kan", "xun"), 60: ("dui", "kan"),
    61: ("dui", "xun"), 62: ("gen", "zhen"), 63: ("li", "kan"), 64: ("kan", "li"),
}


def build() -> dict:
    assert len(KING_WEN_TRIGRAMS) == 64
    table = {}
    for kw, (inner, outer) in KING_WEN_TRIGRAMS.items():
        lines = TRIGRAM[inner] + TRIGRAM[outer]  
        bits_str = "".join(str(b) for b in lines)
        decimal = sum(b << i for i, b in enumerate(lines)) 
        table[kw] = {"lines_bottom_to_top": list(lines), "binary_str": bits_str, "decimal": decimal}

    patterns = {t["binary_str"] for t in table.values()}
    assert len(patterns) == 64, f"only {len(patterns)} unique patterns -- error in trigram table"

    # Spot checks against unambiguous named hexagrams.
    assert table[1]["binary_str"] == "111111"
    assert table[2]["binary_str"] == "000000"
    assert table[11]["binary_str"] == "111000"  
    assert table[12]["binary_str"] == "000111"  
    assert table[63]["binary_str"] == "101010" 
    assert table[64]["binary_str"] == "010101" 
    return table


if __name__ == "__main__":
    out_path = Path(__file__).resolve().parent.parent / "data" / "king_wen_table.json"
    table = build()
    out_path.write_text(json.dumps(table, indent=2), encoding="utf-8")
    print(f"wrote {out_path} — 64 unique patterns, spot checks passed")
