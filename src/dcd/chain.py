"""The book-level chain — one continuous book from a single starting word.

Where `clause_walk.run_chapter` draws an unrelated `word_A` from the pool
for every chapter, this walks the book itself, starting from a word the
artist names (`sleep`).

**Two casts per chapter, asking two different questions** (decided
2026-09-18, revised the same day — see "Why two casts" below):

  1. *What does this word collide with?* -> `word_B`. Printed in the
     heading, used by `clause_walk.select_seed` to fix which occurrence
     of `word_A` the walk starts from, and then discarded.
  2. *Where does the book go next?* -> the next `word_A`, by the same
     jump-and-scan from a fresh occurrence of the current `word_A`.

Both are the ordinary §6.2/§6.4 draw: one cast, a jump of 0-63 words
from a random occurrence of `word_A`, a forward snap to a pool noun.

### Why two casts

The first version made chapter n's `word_B` into chapter n+1's `word_A`.
That contradicted the mechanism's own definition of `word_B`, written
into `clause_walk.select_seed`: "word_B never appears in the output: it
acts as a coordinate, consistent with how the cast derives it (a
position, not content)." Promoting it to the next chapter's `word_A` is
exactly what turns that coordinate into content, and it showed on the
page — every word appeared twice in the headings, Sleep Thick / Thick
Kindness / Kindness Boat. A separate throw for the succession puts
`word_B` back to being a coordinate and nothing else.

### Repeats

Only the succession draw refuses words that already had a chapter, and
it refuses them by scanning past, never by re-casting. This is the same
move as `exclude=word_A` in `traversal.scan_to_nearest_noun`, and rests
on the same reasoning: Constraint 4 forbids rejecting a draw *after*
seeing it; it does not forbid fixing beforehand what counts as a valid
landing. The collision draw skips nothing — the same word may be
collided with from several directions, which is the point of it.

### Termination

The succession scan travels further and further as the pool empties: a
median of 2 words over the first hundred chapters, 46 by chapter 2,500,
356 over the last hundred if allowed to run the pool dry. The jump is
only ever 0-63 words (six cast lines read as a binary number), so past 63
the scan is reaching further than any cast could and the book has quietly
stopped being cast-driven. **The book ends the first time the succession
scan exceeds `MAX_CAST_REACH`** — the moment the scan starts deciding
instead of the coins. That chapter still prints; it is the succession,
not the chapter, that failed.

Rejected: ending when the scan beats *this* cast's own distance. A jump
of 0 or 1 is common, so it fires at chapter 2-40 and there is no book.

### Constraint 5 is NOT resolved here — see NEEDS_INPUT item 15

The chain carries the current `word_A` and the set of used words across
chapters. Neither is derived by reading, parsing or scoring chapter n's
*output text*, which is what Constraint 5's body forbids — but its
heading is "no cross-chapter memory in word selection", and this is
memory. Flagged for the artist rather than settled here, per the spec's
own rule about constraint-adjacent choices.
"""

from typing import Iterator, NamedTuple

from dcd.clause import Clause
from dcd.clause_walk import chapter_record, walk
from dcd.traversal import (
    Occurrence,
    TraversalCast,
    cast_transition,
    derive_jump,
    jump_from_position,
    position_of,
    scan_to_nearest_noun,
)

# The largest jump any cast can produce: six lines read as a binary
# number, so 0-63 inclusive (traversal.derive_jump). A scan longer than
# this has outreached the oracle.
MAX_CAST_REACH = 63

STOP_REASON = "scan_exceeded_cast_reach"


class Link(NamedTuple):
    """One throw and where it landed.

    Used for both draws. `landing` is `word_B` on the collision draw and
    the next `word_A` on the succession draw — the procedure is
    identical, only the question differs.
    """
    word_a: str
    landing: str
    distance: int
    direction: str
    occurrence: Occurrence
    raw_position: int
    scan_distance: int
    cast: TraversalCast


def draw(
    word_a: str,
    king_wen_lookup: dict[str, int],
    corpus_word_sequence: list[str],
    noun_set: set[str],
    rng,
    skip: set[str] | None = None,
) -> Link:
    """Cast once, jump, snap forward to a pool noun (main spec §6.2, §6.4).

    `skip` is passed the used-word set on the succession draw and left
    None on the collision draw. One cast, thrown once, never re-thrown.
    """
    cast = cast_transition(rng, king_wen_lookup)
    distance, direction = derive_jump(cast["coin_totals_per_line"])
    occurrence = position_of(word_a, corpus_word_sequence, rng)
    raw_position = jump_from_position(
        occurrence.position, distance, direction, corpus_word_sequence
    )
    landing = scan_to_nearest_noun(
        raw_position, corpus_word_sequence, noun_set, exclude=word_a, skip=skip
    )
    return Link(
        word_a=word_a,
        landing=landing.word,
        distance=distance,
        direction=direction,
        occurrence=occurrence,
        raw_position=raw_position,
        scan_distance=landing.scan_distance,
        cast=cast,
    )


def _cast_fields(link: Link) -> dict:
    return {
        "coin_totals_per_line": link.cast["coin_totals_per_line"],
        "from_hex": link.cast["from_hex"],
        "to_hex": link.cast["to_hex"],
    }


def _jump_fields(link: Link) -> dict:
    return {
        "word_a_occurrence_index": link.occurrence.index,
        "word_a_occurrence_count": link.occurrence.count,
        "word_a_position": link.occurrence.position,
        "jump_distance": link.distance,
        "jump_direction": link.direction,
        "raw_landing_position": link.raw_position,
        "scan_distance_to_noun": link.scan_distance,
    }


def _record(
    chapter_id: int, collision: Link, succession: Link, chapter,
    used_count: int, tidy: bool,
) -> dict:
    """§10 audit record: the chapter, both throws, and the chain position,
    so any chapter is traceable to the coins that made it.
    """
    record = chapter_record(chapter_id, chapter)
    record["word_b"] = collision.landing          # the corpus's own casing
    # Which assembly convention produced output_text (§8 amendment
    # 2026-09-18). The words, the hops and both casts are identical
    # either way — only the joins differ.
    record["tidied"] = tidy
    record["traversal_cast"] = _cast_fields(collision)
    record["traversal_jump"] = _jump_fields(collision)
    record["succession_cast"] = _cast_fields(succession)
    record["succession_jump"] = _jump_fields(succession)
    record["succession_word_a"] = succession.landing
    record["chain"] = {
        "position": chapter_id,
        "used_count": used_count,
        "succession_scan_distance": succession.scan_distance,
        "max_cast_reach": MAX_CAST_REACH,
    }
    return record


def terminal_record(chapter_id: int, succession: Link, used_count: int) -> dict:
    """The record written where the book stops: the succession throw whose
    scan outreached every cast. `would_have_been` gets no chapter.
    """
    return {
        "chapter_id": None,
        "terminal": True,
        "stop_reason": STOP_REASON,
        "word_a": succession.word_a,
        "would_have_been": succession.landing,
        "scan_distance": succession.scan_distance,
        "jump_distance": succession.distance,
        "jump_direction": succession.direction,
        "max_cast_reach": MAX_CAST_REACH,
        "chapters_before_stop": chapter_id,
        "used_count": used_count,
        "traversal_cast": _cast_fields(succession),
    }


def run_chain(
    start_word: str,
    clauses: dict[int, list[Clause]],
    anchor_index: dict[str, set[int]],
    king_wen_lookup: dict[str, int],
    corpus_word_sequence: list[str],
    noun_set: set[str],
    rng,
    max_chapters: int | None = None,
    tidy: bool = False,
) -> Iterator[dict]:
    """Yields one §10 record per chapter, then a terminal record.

    Stops when the succession scan outreaches the cast — the chapter it
    was drawn for is yielded first, then the terminal record. Or after
    `max_chapters` chapters if given: the cap is for test renders and does
    not change the chapters it does emit.

    `tidy` applies the §8 join conventions (`clause_walk.assemble`). It
    changes only how clauses are joined into a chapter's text — the same
    seed yields the same chapters, the same words and the same casts
    either way.
    """
    word_a = start_word.lower()
    if not any(t.lower() == word_a for t in corpus_word_sequence):
        raise ValueError(f"{start_word!r} does not occur in the corpus word sequence")

    used = {word_a}
    chapter_id = 0
    while max_chapters is None or chapter_id < max_chapters:
        collision = draw(
            word_a, king_wen_lookup, corpus_word_sequence, noun_set, rng
        )
        chapter = walk(
            word_a, collision.landing, clauses, anchor_index, rng, tidy=tidy
        )
        if chapter is None:
            # Both words are corpus-sourced and anchor_index is keyed
            # under both tokenisations, so this cannot happen. Raise
            # rather than invent output or re-draw (Constraint 4).
            raise ValueError(
                f"no seed clause for word_a={word_a!r} / "
                f"word_b={collision.landing!r}; the clause index and the "
                "word pool have drifted apart"
            )
        succession = draw(
            word_a, king_wen_lookup, corpus_word_sequence, noun_set, rng, skip=used
        )

        chapter_id += 1
        yield _record(
            chapter_id, collision, succession, chapter, len(used), tidy
        )

        if succession.scan_distance > MAX_CAST_REACH:
            yield terminal_record(chapter_id, succession, len(used))
            return
        used.add(succession.landing.lower())
        word_a = succession.landing.lower()
