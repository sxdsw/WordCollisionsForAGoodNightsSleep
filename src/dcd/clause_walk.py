"""The clause walk — one chapter.

A chapter is a chain of clauses linked by their final word: the anchor.
Every clause is verbatim corpus text; the generative act is selection and
sequencing only. See TECH_SPEC.md for a worked example.
"""

import bisect
import re
from typing import NamedTuple

from dcd.clause import Clause, words
from dcd.corpus import Sentence
from dcd.traversal import (
    cast_transition,
    derive_jump,
    jump_from_position,
    position_of,
    scan_to_nearest_noun,
)
from dcd.word_selection import select_word_a

# §7 — safety cap only. The observed maximum over 3,000 runs was 40 hops;
# this should never be reached.
MAX_HOPS = 200

_TERMINAL_RE = re.compile("[.!?][\"'\u201d\u2019]?$")
# A clause ending in ; : or , is already punctuated and needs nothing.
_MID_RE = re.compile("[;:,][\"'\u201d\u2019]?$")


class Hop(NamedTuple):
    anchor: str
    from_sentence: int
    to_sentence: int
    clause_index: int
    candidate_count: int
    voice: str | None
    voice_changed: bool


class Chapter(NamedTuple):
    text: str
    word_a: str
    word_b: str
    seed_sentence: int
    seed_clause_index: int
    hops: list[Hop]
    voice_arc: list[str | None]
    stop_reason: str            # "loop" | "exhausted" | "cap"


def select_seed(
    word_a: str,
    word_b: str,
    clauses: dict[int, list[Clause]],
    anchor_index: dict[str, set[int]],
    rng,
) -> Clause | None:
    """§9 — word_A supplies the opening clause; word_B decides which
    occurrence of word_A you start from.

    Of all the sentences containing word_A, begin at the one lying
    nearest a word_B occurrence in corpus order. word_B never appears in
    the output: it acts as a coordinate, consistent with how the cast
    derives it (a position, not content).

    This is not curation (Constraint 2): the seed is not ranked by
    length, quality or fit, it is fixed by an external procedural
    signal, on the same footing as the coin-parity output selection at
    §5.5 of the main spec.
    """
    a_sents = [s for s in anchor_index.get(word_a.lower(), ()) if clauses.get(s)]
    b_sents = [s for s in anchor_index.get(word_b.lower(), ()) if clauses.get(s)]
    if not a_sents or not b_sents:
        return None
    # Sentence ids are assigned in corpus order (§5.1), so the id is the
    # position; no separate position table is needed. Binary search keeps
    # this O(|A| log |B|) — a linear scan is a million comparisons per
    # chapter when both words are common.
    b_sorted = sorted(b_sents)

    def gap(sentence_id: int) -> int:
        i = bisect.bisect_left(b_sorted, sentence_id)
        best = len(b_sorted) * 0 + float("inf")
        if i < len(b_sorted):
            best = b_sorted[i] - sentence_id
        if i > 0:
            best = min(best, sentence_id - b_sorted[i - 1])
        return int(best)

    best = min(gap(s) for s in a_sents)
    seed_sentence = rng.choice(sorted(s for s in a_sents if gap(s) == best))
    return rng.choice(clauses[seed_sentence])


def _initial_voice(clause: Clause) -> str | None:
    """§6a — the voice starts unset unless the opening clause carries
    exactly one pronoun class. An unset voice leaves the walk
    unconstrained; it is NOT a voice in its own right.
    """
    return next(iter(clause.pronoun)) if len(clause.pronoun) == 1 else None


def _compatible(clause: Clause, voice: str | None) -> bool:
    """§6a — compatibility is containment, not equality. "he told her"
    continues a `he` chapter, because he is in it.
    """
    return not clause.pronoun or voice in clause.pronoun


def walk(
    word_a: str,
    word_b: str,
    clauses: dict[int, list[Clause]],
    anchor_index: dict[str, set[int]],
    rng,
    tidy: bool = False,
) -> Chapter | None:
    """Runs one chapter. Returns None if word_a or word_b is not in the
    corpus at all.

    Loop: take the anchor (§5), find every sentence containing it, choose
    one uniformly (§6), choose a clause from it uniformly, preferring
    pronoun-compatible clauses (§6a), append, and stop when the new
    anchor is one already used (§7).
    """
    seed = select_seed(word_a, word_b, clauses, anchor_index, rng)
    if seed is None:
        return None

    parts = [seed.text]
    anchor = seed.anchor
    current_sentence = seed.sentence_id
    voice = _initial_voice(seed)
    used_anchors = {anchor}
    voice_arc: list[str | None] = [voice]
    hops: list[Hop] = []
    stop_reason = "cap"

    while len(hops) < MAX_HOPS:
        candidate_sentences = [
            s
            for s in anchor_index.get(anchor, ())
            if s != current_sentence and clauses.get(s)
        ]
        if not candidate_sentences:
            stop_reason = "exhausted"
            break

        pool = [(s, c) for s in candidate_sentences for c in clauses[s]]
        if voice is not None:
            matching = [p for p in pool if _compatible(p[1], voice)]
            # preference, not a filter: full pool remains the fallback
            pool = matching or pool

        next_sentence, chosen = rng.choice(pool)

        changed = False
        if voice is None:
            if len(chosen.pronoun) == 1:
                voice = next(iter(chosen.pronoun))
        elif chosen.pronoun and voice not in chosen.pronoun:
            voice = (
                next(iter(chosen.pronoun))
                if len(chosen.pronoun) == 1
                else rng.choice(sorted(chosen.pronoun))
            )
            changed = True

        hops.append(
            Hop(
                anchor=anchor,
                from_sentence=current_sentence,
                to_sentence=next_sentence,
                clause_index=chosen.index,
                candidate_count=len(candidate_sentences),
                voice=voice,
                voice_changed=changed,
            )
        )
        parts.append(chosen.text)
        voice_arc.append(voice)
        current_sentence = next_sentence
        anchor = chosen.anchor

        if anchor in used_anchors:
            stop_reason = "loop"
            break
        used_anchors.add(anchor)

    return Chapter(
        text=assemble(parts, tidy=tidy),
        word_a=word_a,
        word_b=word_b,
        seed_sentence=seed.sentence_id,
        seed_clause_index=seed.index,
        hops=hops,
        voice_arc=voice_arc,
        stop_reason=stop_reason,
    )


def balance_marks(text: str) -> str:
    """§8 — delete unpaired quote marks and brackets from the ASSEMBLED
    chapter.

    Clause splitting cuts inside quotations and bracketed asides more
    often than sentence splitting did, so without this a chapter
    routinely carries orphaned marks — three or four quote marks, or the
    closing half of a commentator's bracket whose opening `[` stayed in
    a sentence that was never selected.

    Quote marks are classified by context: an opener is preceded by
    start-of-string, whitespace or `([{—-` and followed by an
    alphanumeric or apostrophe; anything else is a closer. Curly marks
    say which they are outright. Brackets need no classification.

    The deletion is lossy — speech whose closing mark lived in another
    sentence becomes unmarked narration — and that is accepted. No other
    character is touched.
    """
    drop: set[int] = set()

    # quotes
    marks = [m.start() for m in re.finditer("[\"\u201c\u201d]", text)]
    open_stack: list[int] = []
    for i in marks:
        if text[i] == "\u201c":
            is_open = True
        elif text[i] == "\u201d":
            is_open = False
        else:
            before = text[i - 1] if i > 0 else ""
            after = text[i + 1] if i + 1 < len(text) else ""
            is_open = (
                before == "" or before.isspace() or before in "([{\u2014-"
            ) and (after.isalnum() or after in "\u2018'")
        if is_open:
            open_stack.append(i)
        elif open_stack:
            open_stack.pop()
        else:
            drop.add(i)
    drop |= set(open_stack)

    # brackets — unambiguous, no classification needed
    bracket_stack: list[int] = []
    for i, char in enumerate(text):
        if char == "[":
            bracket_stack.append(i)
        elif char == "]":
            if bracket_stack:
                bracket_stack.pop()
            else:
                drop.add(i)
    drop |= set(bracket_stack)

    if not drop:
        return text
    kept = "".join(c for j, c in enumerate(text) if j not in drop)
    return re.sub(r"\s{2,}", " ", kept).strip()


def apply_join_conventions(parts: list[str]) -> list[str]:
    """§8 AMENDMENT 2026-09-18 — the two sentence conventions, applied at
    the interior joins instead of only at the chapter's edges.

    Off by default; reached by `assemble(parts, tidy=True)` and by the
    renderer's `--tidy`. The book still prints untidied unless asked.

    Two rules, both purely positional — neither reads a word, and neither
    knows what any word means:

      1. after a clause ending in `.`, `!` or `?`, upper-case the next
         clause's first letter        (1,088 joins in the seed-1 book)
      2. where a clause ends with no punctuation at all and the next
         begins with a capital, append a full stop to the first
                                      (660 joins in the seed-1 book)

    **This is NOT grammatical repair, and it is not permitted to become
    any.** The collision survives both rules completely: "...amassed
    great wealth. And immediately seizing a sharp knife" is exactly as
    much of a non-sequitur as it was in lower case. What the rules remove
    is the appearance of a *typo* — a reader currently takes that
    lower-case `a` for a mistake rather than for a seam. §8 already
    applies these same two conventions at the chapter's first and last
    character; this extends them inward. Nothing is smoothed, no clause
    is fitted to its neighbour, and the 1,013 joins where an unpunctuated
    clause meets a lower-case one (21.4%) are deliberately left alone —
    there is no positional signal there to act on, and inventing one
    would be the repair this rule exists to forbid.

    Decided by the artist 2026-09-18, after seeing the measurements and
    six rendered alternatives. See NEEDS_INPUT item 16.
    """
    out = [parts[0]]
    for right in parts[1:]:
        left = out[-1].rstrip()
        if not left or not right:
            out.append(right)
            continue
        if _TERMINAL_RE.search(left):
            if right[:1].islower():
                right = right[:1].upper() + right[1:]
        elif not _MID_RE.search(left) and right[:1].isupper():
            out[-1] = left + "."
        out.append(right)
    return out


def assemble(parts: list[str], tidy: bool = False) -> str:
    """§8 — join, balance quotes, capitalise, terminate.

    No grammatical repair at any join, ever — the mismatch is the output,
    not a bug (same rule as the splice, §5.5 of the main spec).

    `tidy=True` additionally applies the two sentence conventions of the
    2026-09-18 §8 amendment at the interior joins. See
    `apply_join_conventions` for why that is not the repair this docstring
    forbids. Default False: the mechanism's own output is unchanged.
    """
    if tidy:
        parts = apply_join_conventions(parts)
    text = balance_marks(" ".join(parts))
    if not text:
        return text
    text = text[0].upper() + text[1:]
    if not _TERMINAL_RE.search(text.strip()):
        text = text.rstrip(",;: ") + "."
    return text


def chapter_record(chapter_id: int, chapter: Chapter) -> dict:
    """§10 — full audit record, independent of what a reader sees."""
    return {
        "chapter_id": chapter_id,
        "word_a": chapter.word_a,
        "word_b": chapter.word_b,
        "seed_clause": {
            "sentence_id": chapter.seed_sentence,
            "clause_index": chapter.seed_clause_index,
        },
        "hops": [h._asdict() for h in chapter.hops],
        "voice_arc": chapter.voice_arc,
        "stop_reason": chapter.stop_reason,
        "closing_anchor": chapter.hops[-1].anchor if chapter.hops else None,
        "word_count": len(words(chapter.text)),
        "output_text": chapter.text,
    }


def run_chapter(
    chapter_id: int,
    sentences: list[Sentence],
    clauses: dict[int, list[Clause]],
    anchor_index: dict[str, set[int]],
    word_pool: list[str],
    king_wen_lookup: dict[str, int],
    corpus_word_sequence: list[str],
    noun_set: set[str],
    rng,
) -> dict:
    """§9 + §10 — one clause-walk chapter, end to end.

    Draws `word_A` and `word_B` exactly as the splice pipeline does: the
    cast supplies a jump distance and direction, which are applied to a
    random occurrence of `word_A` in the corpus's flat word sequence, and
    the scan snaps forward to the nearest pool noun (main spec §6.2,
    §6.4). Then walks.

    Returns the §10 record with the cast and jump folded in, so a chapter
    is reproducible from its log. Both words are corpus-sourced, so the
    walk always seeds; it can still stop at zero hops when the opening
    anchor occurs in no other sentence (§7, ~8% of chapters).
    """
    cast = cast_transition(rng, king_wen_lookup)
    distance, direction = derive_jump(cast["coin_totals_per_line"])
    word_a = select_word_a(word_pool, rng)
    occurrence = position_of(word_a, corpus_word_sequence, rng)
    raw_position = jump_from_position(
        occurrence.position, distance, direction, corpus_word_sequence
    )
    landing = scan_to_nearest_noun(
        raw_position, corpus_word_sequence, noun_set, exclude=word_a
    )

    chapter = walk(word_a, landing.word, clauses, anchor_index, rng)
    if chapter is None:
        # Both words are corpus-sourced, and anchor_index is keyed under
        # both tokenisations (dcd.clause.build_clause_index), so a seed
        # should always exist. Raise loudly rather than inventing output
        # or re-drawing (Constraint 4).
        raise ValueError(
            f"no seed clause for word_a={word_a!r} / word_b={landing.word!r}; "
            "the clause index and the word pool have drifted apart"
        )
    record = chapter_record(chapter_id, chapter)
    record["traversal_cast"] = {
        "coin_totals_per_line": cast["coin_totals_per_line"],
        "from_hex": cast["from_hex"],
        "to_hex": cast["to_hex"],
    }
    record["traversal_jump"] = {
        "word_a_occurrence_index": occurrence.index,
        "word_a_occurrence_count": occurrence.count,
        "word_a_position": occurrence.position,
        "jump_distance": distance,
        "jump_direction": direction,
        "raw_landing_position": raw_position,
        "scan_distance_to_noun": landing.scan_distance,
    }
    return record
