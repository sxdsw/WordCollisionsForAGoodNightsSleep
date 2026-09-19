"""§6 — Traversal Word Mechanism.

The traversal word (word_b) comes from an independently cast I Ching
hexagram transition, applied to the corpus as a jump distance and
direction (§6.2).

The Jiaoshi Yilin lookup that used to supply word_b was dropped
2026-08-28 and its code removed 2026-09-15: load_yilin_table,
save_yilin_table, add_yilin_entry, get_verse, extract_traversal_word and
YilinNotYetTranscribed are gone, along with data/yilin_table.json. The
table would have needed 4,096 verses transcribed by hand and never was. It is never
derived from chapter n's text (Constraint 5). Casting itself must never
read chapter n's own text or output either — cast_transition() below
takes only an rng, nothing corpus-derived.
"""

import json
from pathlib import Path
from typing import NamedTuple, TypedDict


class TraversalCast(TypedDict):
    coin_totals_per_line: list[int]  # 6 values, each 6-9
    from_hex: int
    to_hex: int


# ---------------------------------------------------------------------
# §6.1 Hexagram Casting
# ---------------------------------------------------------------------

def cast_transition(rng, king_wen_lookup: dict[str, int]) -> TraversalCast:
    """Simulated traditional three-coin method, six lines, bottom to top.

    king_wen_lookup maps a 6-char binary string (index 0 = bottom line,
    '1' = yang, '0' = yin) to its King Wen number 1-64. Build this with
    build_king_wen_lookup() from data/king_wen_table.json.

    If no lines change, from_hex == to_hex. This is valid and needs no
    special-casing: §6.2 takes direction from the bottom line, not from
    comparing the two hexagrams, so identity casts are not all sent one
    way.
    """
    from_lines: list[int] = []
    to_lines: list[int] = []
    coin_totals: list[int] = []
    for _ in range(6):
        total = sum(rng.choice([2, 3]) for _ in range(3))  # tails=2, heads=3
        coin_totals.append(total)
        if total == 6:  # old yin — changing
            from_lines.append(0)
            to_lines.append(1)
        elif total == 7:  # young yang — stable
            from_lines.append(1)
            to_lines.append(1)
        elif total == 8:  # young yin — stable
            from_lines.append(0)
            to_lines.append(0)
        elif total == 9:  # old yang — changing
            from_lines.append(1)
            to_lines.append(0)
        else:
            raise AssertionError(f"impossible coin total: {total}")

    from_hex = king_wen_number(from_lines, king_wen_lookup)
    to_hex = king_wen_number(to_lines, king_wen_lookup)
    return TraversalCast(coin_totals_per_line=coin_totals, from_hex=from_hex, to_hex=to_hex)


def king_wen_number(lines: list[int], king_wen_lookup: dict[str, int]) -> int:
    """Looks up a 6-bit pattern (index 0 = bottom line) against the King
    Wen table. `king_wen_lookup` is binary_str -> King Wen number, built
    by build_king_wen_lookup().
    """
    binary_str = "".join(str(b) for b in lines)
    return king_wen_lookup[binary_str]


def build_king_wen_lookup(king_wen_table_path: str) -> dict[str, int]:
    """Loads data/king_wen_table.json and inverts it into
    binary_str -> King Wen number.

    Verified 2026-08-28, twice: every entry against an independent
    transcription of the canonical sequence (tests/test_king_wen_table.py),
    and the reading direction against the worked example in Gait's own
    introduction (totals 7,6,7,6,7,6 -> hex 63, changing lines 2/4/6,
    hex 1), which confirms first-toss-as-bottom-line.
    """
    raw = json.loads(Path(king_wen_table_path).read_text(encoding="utf-8"))
    lookup: dict[str, int] = {}
    for kw_str, entry in raw.items():
        lookup[entry["binary_str"]] = int(kw_str)
    if len(lookup) != 64:
        raise ValueError(
            f"expected 64 unique line-patterns in King Wen table, got {len(lookup)}"
        )
    return lookup


# ---------------------------------------------------------------------
# §6.2 Traversal target — internal, position-based
# ---------------------------------------------------------------------

def from_lines(coin_totals_per_line: list[int]) -> list[int]:
    """The `from` hexagram's six lines, bottom first, 1 = yang.

    Recovered from the coin totals rather than passed separately:
    6 (old yin) and 8 (young yin) are yin; 7 (young yang) and 9 (old
    yang) are yang.
    """
    lines = []
    for total in coin_totals_per_line:
        if total not in (6, 7, 8, 9):
            raise AssertionError(f"impossible coin total: {total}")
        lines.append(1 if total in (7, 9) else 0)
    return lines


def derive_jump(coin_totals_per_line: list[int]) -> tuple[int, str]:
    """§6.2 — returns (distance, direction). RESOLVED 2026-09-15.

    distance: the six `from` lines read as a binary number, bottom line
              as the 1s place. Flat over 0-63.

              Do NOT use sum(coin_totals_per_line) - 36. That is a bell
              curve, not a range: 76% of casts land 7-11 words away and
              the ends are unreachable (0 or 18 at under 0.01%). Six
              totals summed always do this. Read as bits the same throws
              are flat, because each line is a fair coin — old yin and
              young yang together are exactly half.

    direction: forward if the bottom line is yang, else backward.

              Do NOT use `from_hex < to_hex`. 18% of casts have no
              changing lines, so from_hex == to_hex, and that rule sends
              every one of them backward — nearly a fifth of chapters
              jumping backward for a reason unconnected to the cast. The
              bottom line is fair and is defined on every cast.

    from_hex/to_hex are deliberately not parameters: neither is needed
    any more, and accepting them would invite the superseded rule back.
    """
    lines = from_lines(coin_totals_per_line)
    distance = sum(bit << i for i, bit in enumerate(lines))
    direction = "forward" if lines[0] == 1 else "backward"
    return distance, direction


class Occurrence(NamedTuple):
    """Where in the flat word sequence a draw of word_A landed."""
    position: int       # index into corpus_word_sequence
    index: int          # which occurrence was drawn, 0-based
    count: int          # how many there were to draw from


class NounScan(NamedTuple):
    """Result of snapping a raw landing position to the nearest noun."""
    word: str
    scan_distance: int  # how far the snap moved from raw_position


def position_of(word: str, corpus_word_sequence: list[str], rng) -> Occurrence:
    """§6.4 — picks the occurrence of `word` the jump starts from.

    RESOLVED 2026-09-15: a **random** occurrence, drawn uniformly from
    all of them, not the first. The variation is wanted. The cost is that
    the chapter is no longer reproducible from word_A and the cast alone,
    so `index` and `count` are returned for §7 to log
    (`word_a_occurrence_index`, `word_a_occurrence_count`).

    Matching is on the lowercased form, since the word pool is lowercased
    and the sequence keeps original case.
    """
    target = word.lower()
    positions = [i for i, tok in enumerate(corpus_word_sequence) if tok.lower() == target]
    if not positions:
        raise ValueError(f"{word!r} does not occur in the corpus word sequence")
    index = rng.randrange(len(positions))
    return Occurrence(position=positions[index], index=index, count=len(positions))


def jump_from_position(
    word_a_position: int,
    distance: int,
    direction: str,
    corpus_word_sequence: list[str],
) -> int:
    """§6.2 — offsets `word_a_position` by `distance` in `direction`.

    If the offset runs past either end, wrap around to the opposite end:
    the corpus is circular for this purpose only, and nowhere else in the
    pipeline.
    """
    if direction not in ("forward", "backward"):
        raise ValueError(f"direction must be 'forward' or 'backward', got {direction!r}")
    length = len(corpus_word_sequence)
    if length == 0:
        raise ValueError("corpus word sequence is empty")
    offset = distance if direction == "forward" else -distance
    return (word_a_position + offset) % length


def scan_to_nearest_noun(
    raw_position: int,
    corpus_word_sequence: list[str],
    noun_set: set[str],
    exclude: str | None = None,
    skip: set[str] | None = None,
) -> NounScan:
    """§6.2 — from `raw_position`, scan FORWARD (wrapping at the end)
    until a token whose lowercased form is in `noun_set`.

    Always forward, whichever way the jump itself went — the direction
    belongs to the jump, not the snap.

    DEVIATION from the spec signature, which returns `str`: §7 requires
    `scan_distance_to_noun`, and that is underivable from the word alone,
    so a NounScan is returned instead.

    `exclude` names a word the landing may not be, and is passed word_A.
    Without it, a short backward jump followed by the forward snap
    returns to the starting word: word_B == word_A on 3.4% of casts.
    Accepted 2026-09-15, REVERSED 2026-09-16 — when the two words
    coincide there is only one word, so nothing collides. The splice
    cuts both sentences at the same word, and in the clause walk word_B
    goes inert, since every occurrence of word_A is then zero distance
    from an occurrence of word_B and the seed falls back to a uniform
    draw.

    This is NOT a re-draw (Constraint 4). The cast stands as thrown;
    only what counts as a valid landing has changed, and the scan walks
    on to the next one.

    `skip` names a SET of words the landing may not be, and is scanned
    past on exactly the same footing as `exclude`. Added 2026-09-18 for
    the book-level chain (dcd.chain), which may not re-use a word that
    has already had its chapter. It is the same move as `exclude` and
    rests on the same reasoning: the rule for what counts as a valid
    landing is fixed BEFORE the coins are thrown, so no cast is ever
    rejected after the fact. Default None leaves every existing caller
    byte-identical.

    No upper bound on scan distance is needed — noun_set is built from
    this corpus, so at least one match exists and the scan terminates.
    """
    length = len(corpus_word_sequence)
    if length == 0:
        raise ValueError("corpus word sequence is empty")
    excluded = exclude.lower() if exclude else None
    skipped = skip or frozenset()
    for steps in range(length):
        i = (raw_position + steps) % length
        token = corpus_word_sequence[i]
        lowered = token.lower()
        if lowered in noun_set and lowered != excluded and lowered not in skipped:
            return NounScan(word=token, scan_distance=steps)
    raise ValueError("no token of the corpus is in noun_set")
