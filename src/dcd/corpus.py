"""§5.1 — Corpus Ingestion & Sentence Segmentation.

Hard constraint reminder (Constraint 1): no statistical sentence-boundary
model, ever. This module is rule-based string processing only.
"""

import re
from typing import TypedDict

# Fixed abbreviation list (§5.1 step 3) — do not split a sentence on a
# period that's part of one of these.
ABBREVIATIONS = {"Mr.", "Mrs.", "Dr.", "St."}
# Single capital letter + period (initials) is handled structurally in
# _is_abbreviation_period, not via this set.

GUTENBERG_START_RE = re.compile(r"\*\*\*\s*START OF.*?\*\*\*", re.IGNORECASE | re.DOTALL)
GUTENBERG_END_RE = re.compile(r"\*\*\*\s*END OF.*?\*\*\*", re.IGNORECASE | re.DOTALL)

# Sentence boundary: '.', '!', or '?' followed by whitespace and an
# uppercase letter, or followed by end of text.
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


class Sentence(TypedDict):
    id: int
    text: str
    story_id: str
    position_in_story: int


def strip_gutenberg_boilerplate(raw_text: str) -> str:
    """Removes the standard Gutenberg license header/footer.

    Delimited by '*** START OF...' / '*** END OF...' markers, per §5.1
    step 1.
    """
    start_match = GUTENBERG_START_RE.search(raw_text)
    end_match = GUTENBERG_END_RE.search(raw_text)
    start = start_match.end() if start_match else 0
    end = end_match.start() if end_match else len(raw_text)
    return raw_text[start:end].strip()


# --- §5.1 step 2: story splitting -------------------------------------------
#
# Written against the ACTUAL downloaded file (Project Gutenberg #43629,
# "Strange Stories from a Chinese Studio", Giles tr., 2 vols. in one
# ebook), inspected by hand. What the real file looks like:
#
#   * Front matter: two title pages, a dedication, a full CONTENTS list
#     (every story title, alphabetised, with page numbers), and a long
#     INTRODUCTION with its own numbered footnotes. None of this is story
#     content.
#   * Each story begins with a Roman-numeral line on its own -- "I.",
#     "II.", ... running 1..164 straight through BOTH volumes (Vol. II
#     opens at "LXIII.") -- then a blank line, then the TITLE IN FULL
#     CAPS on its own line (sometimes with a trailing "[36]" footnote
#     ref). The story number line is always preceded by a blank line.
#   * A story's editorial apparatus ("FOOTNOTES:" / "FOOTNOTE:" followed
#     by "[n] ..." entries) sits at the END of that story's text.
#   * Between Vol. I and Vol. II the file has a "END OF VOL. I." line and
#     a reprinted title page, wedged after story LXII's footnotes.
#   * Back matter: "APPENDIX A.", "APPENDIX B." (Giles' own essays) and
#     "INDEX TO THE NOTES." -- not story content.
#
# The TOC is what a naive "line in caps" pattern false-matches. Two
# things rule it out here: (a) TOC entries are mixed-case with trailing
# page numbers, not full caps, and (b) they are not preceded by a bare
# Roman-numeral line. The one other false positive -- a footnote reading
# "... See the _Hsi-yu-chi_, Section\nXI." -- is excluded by requiring
# the Roman-numeral line to be preceded by a blank line AND followed by
# an all-caps title line. With both guards, exactly 164 headers are
# found and they number 1..164 with no gaps (asserted below -- if that
# ever fails, the format changed and this must be re-inspected, not
# patched over).

_STORY_NUMBER_RE = re.compile(r"^[IVXLC]+\.$")
_BACK_MATTER_RE = re.compile(r"^(APPENDIX\s+[A-Z]|INDEX TO THE NOTES|GLOSSARY)\.?$")
_APPARATUS_RE = re.compile(r"^(FOOTNOTES?:|END OF VOL\b.*)$")
_BRACKET_REF_RE = re.compile(r"\[\d+\]")
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _roman_to_int(roman: str) -> int:
    total = 0
    prev = 0
    for ch in reversed(roman):
        value = _ROMAN_VALUES[ch]
        total += -value if value < prev else value
        prev = max(prev, value)
    return total


def _looks_like_title(line: str) -> bool:
    """A story title line: has letters, and every letter is uppercase.
    (Trailing "[36]" refs and punctuation are fine.)
    """
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


# Bracketed matter, stripped at ingest. Two kinds, both removed as of
# 2026-09-16:
#
#   * Commentator asides — the Chinese commentator's notes and the
#     translator's remarks ABOUT a story ("[Hereon the commentator, I
#     Shih-shih, makes the following remark:--...]"). Not story text; the
#     same category as the front/back matter §5.1 already excludes. Two
#     of the six span sentence boundaries, so removing them deleted three
#     sentence records and renumbered the corpus after them (decided
#     2026-09-16; see NEEDS_INPUT item 13 for the cost to logged ids).
#
#   * Stage directions and glosses — "[Leopard]", "[Night]", "[to the
#     woman]", "[Here she burst into tears and implored the magistrate's
#     pity.]". Giles narrating inside a scene rather than commenting on
#     it, so these were initially KEPT. Removed 2026-09-16 after seeing
#     one land mid-chapter with its surrounding dialogue gone ("How [to
#     the woman] What old man and woman can have entertained you
#     there?"): a stage direction addressed to a speaker who is no longer
#     present reads as an intrusion, and neither mechanism can supply the
#     context that made it legible.
#
# All bracketed spans now go. This is deletion of editorial apparatus,
# the same judgement as the "[36]" footnote markers — but it is a larger
# one, and it removes authored words, so it is recorded here rather than
# left implicit.
_BRACKETED_SPAN_RE = re.compile(r"\[[^\[\]]*\]", re.DOTALL)

# Numbered sub-section markers inside a story: "I.--A certain village
# butcher...", "II.--A butcher, while travelling...". A few stories are
# split into parts this way. The marker is transcription structure, not
# authored text, and without stripping it the numeral glues onto the
# first sentence of the part — "ii" reached the word pool and had to be
# hand-excluded. Same family as the "[36]" footnote markers above.
# Anchored to a numeral followed by a period and a dash run, so it cannot
# match the pronoun "I" in ordinary prose.
_SECTION_MARKER_RE = re.compile(r"\b[IVXLC]{1,5}\.-{1,2}\s*")


def _strip_bracketed_matter(text: str) -> str:
    """Removes every bracketed span — commentary and stage directions
    alike. Runs on whole story text, before sentence segmentation,
    because two of the commentator asides span sentence boundaries.
    """
    return _BRACKETED_SPAN_RE.sub(" ", text)


def _clean_markup(text: str) -> str:
    """Strip transcription markup that isn't authored text, so it can't
    get glued onto a word when the corpus is searched or tokenised.

    Two things, both introduced by the Project Gutenberg transcription
    rather than by Giles:
      * "[36]"-style inline footnote reference markers.
      * Numbered sub-section markers ("I.--", "II.--") inside a story.
      * Paired "_..._" underscores marking italics. "_" is a regex word
        character, so "_yamên_" would defeat a \\b-anchored search
        for "yamên"; and a literal splice would leave a stray "_" in the
        output. Every "_" in this file is an italic delimiter (there is
        no authored underscore in a Victorian English translation), so
        all of them are removed.

    This is deletion of mechanical markers, not spelling/grammar repair
    (which §5.1 forbids). It is a judgement call beyond the literal spec
    and is flagged in NEEDS_INPUT.md.
    """
    text = _BRACKET_REF_RE.sub("", text)
    text = text.replace("_", "")
    text = _strip_bracketed_matter(text)
    text = _SECTION_MARKER_RE.sub("", text)
    # Deleting a span mid-sentence leaves a doubled space, and one that
    # sat before punctuation leaves " ,". Collapse both — spacing repair
    # for a deletion this module made, not repair of Giles.
    text = re.sub(r"[ \t]{2,}", " ", text)
    return re.sub(r" +([,.;:!?])", r"\1", text)


def _story_id_from_title(number: int, title: str) -> str:
    slug = _BRACKET_REF_RE.sub("", title).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return f"{number:03d}-{slug}"


def split_into_stories(cleaned_text: str) -> list[tuple[str, str]]:
    """Splits corpus text into (story_id, story_text) pairs.

    `cleaned_text` is the output of strip_gutenberg_boilerplate (Gutenberg
    license header/footer already gone; front/back matter still present).

    `story_id` is metadata only. Nothing downstream may use
    it to constrain matching -- it exists so a spliced line can be traced
    back to where it came from, nothing more.
    """
    lines = cleaned_text.split("\n")

    # Locate real story headers (see notes above for why these two guards).
    headers: list[tuple[int, int, int]] = []  # (number_line, title_line, number)
    for i, line in enumerate(lines):
        if not _STORY_NUMBER_RE.match(line.strip()):
            continue
        if i > 0 and lines[i - 1].strip() != "":
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines) or not _looks_like_title(lines[j].strip()):
            continue
        headers.append((i, j, _roman_to_int(line.strip()[:-1])))

    if not headers:
        raise RuntimeError(
            "No story headers found in corpus. The file format is not what "
            "split_into_stories() was written against (#43629). Re-inspect."
        )

    numbers = [h[2] for h in headers]
    if numbers != list(range(1, len(numbers) + 1)):
        raise RuntimeError(
            f"Story numbers are not a clean 1..N sequence: {numbers}. "
            "This means a header was missed or a false one matched. "
            "Re-inspect the file rather than papering over it."
        )

    # Hard stop for the last story: first back-matter heading after it.
    end_of_stories = len(lines)
    for i in range(headers[-1][0], len(lines)):
        if _BACK_MATTER_RE.match(lines[i].strip()):
            end_of_stories = i
            break

    stories: list[tuple[str, str]] = []
    for k, (_, title_line, number) in enumerate(headers):
        title = lines[title_line].strip()
        body_start = title_line + 1
        body_end = headers[k + 1][0] if k + 1 < len(headers) else end_of_stories
        body_lines = lines[body_start:body_end]

        # Drop trailing editorial apparatus (footnotes block, and the
        # inter-volume printer matter that trails story LXII).
        for idx, bl in enumerate(body_lines):
            if _APPARATUS_RE.match(bl.strip()):
                body_lines = body_lines[:idx]
                break

        story_text = _clean_markup("\n".join(body_lines)).strip()
        stories.append((_story_id_from_title(number, title), story_text))

    return stories


def _is_abbreviation_period(text: str, period_index: int) -> bool:
    """True if the '.' at period_index is part of a fixed abbreviation
    or a single-capital-letter initial, and should NOT be treated as a
    sentence boundary.
    """
    # Fixed abbreviation list, e.g. "Mr.", "Dr.", "St."
    for abbr in ABBREVIATIONS:
        if text[: period_index + 1].endswith(abbr):
            return True
    # Single capital letter + period (initials), e.g. "J. Smith"
    if period_index >= 1 and text[period_index - 1].isupper():
        # Must be preceded by whitespace or start-of-string, so we don't
        # false-match the last letter of an ordinary capitalized word.
        if period_index == 1 or text[period_index - 2] in " \t\n":
            return True
    return False


def tokenize_sentences(text: str) -> list[str]:
    """Rule-based sentence splitter, §5.1 step 3.

    Splits on '.', '!', or '?' followed by whitespace and an uppercase
    letter, or end of text. Does not split on periods that are part of
    ABBREVIATIONS or single-capital-letter initials.

    This is explicitly not expected to be perfect (spec: "Spot-check
    ~50 sentences manually after implementation and accept the
    result.") — do not iterate this toward a statistical model.
    """
    # First pass: naive split on the boundary regex.
    rough_pieces = _SENTENCE_BOUNDARY_RE.split(text)

    # Second pass: stitch back together any split that occurred on an
    # abbreviation/initial period, by re-scanning original text offsets.
    sentences: list[str] = []
    buf = ""
    cursor = 0
    for piece in rough_pieces:
        piece_start = text.index(piece, cursor)
        cursor = piece_start + len(piece)
        if buf:
            # Check whether the period ending `buf` is an abbreviation.
            stripped = buf.rstrip()
            if stripped and stripped[-1] in ".!?" and _is_abbreviation_period(
                stripped, len(stripped) - 1
            ):
                buf = buf + " " + piece
                continue
            sentences.append(buf.strip())
            buf = piece
        else:
            buf = piece
    if buf:
        sentences.append(buf.strip())
    return [s for s in sentences if s]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_sentence_records(
    stories: list[tuple[str, str]]
) -> list[Sentence]:
    """Runs tokenize_sentences per story and assembles the record schema
    from §5.1 step 4. `stories` is a list of (story_id, story_text).
    """
    records: list[Sentence] = []
    next_id = 0
    for story_id, story_text in stories:
        for position, raw_sentence in enumerate(tokenize_sentences(story_text)):
            records.append(
                Sentence(
                    id=next_id,
                    text=normalize_whitespace(raw_sentence),
                    story_id=story_id,
                    position_in_story=position,
                )
            )
            next_id += 1
    return records


def ingest(corpus_file_path: str) -> list[Sentence]:
    """Top-level entry point for §5.1: raw file -> sentence records.

    Boilerplate strip -> story split -> markup clean -> segmentation.
    Yields 4,553 records across 164 stories for data/pg43629.txt.
    """
    with open(corpus_file_path, encoding="utf-8") as f:
        raw_text = f.read()
    cleaned = strip_gutenberg_boilerplate(raw_text)
    stories = split_into_stories(cleaned)
    return build_sentence_records(stories)
