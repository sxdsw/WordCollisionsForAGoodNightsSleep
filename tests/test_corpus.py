import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dcd.corpus import (  # noqa: E402
    build_sentence_records,
    ingest,
    split_into_stories,
    strip_gutenberg_boilerplate,
)

CORPUS_FILE = Path(__file__).resolve().parent.parent / "data" / "pg43629.txt"


# --- split_into_stories: pure-logic tests (synthetic input) -----------------

SYNTHETIC = """\
CONTENTS.

  Talking Pupils, The                            5         --
  Painted Wall, The                              9         --


INTRODUCTION.

I.--PERSONAL.--Some introduction prose that mentions section
XI.
of another work, which must not be read as a story header.


STRANGE STORIES




I.

THE FIRST STORY.


Body of the first story. It has two sentences here.

FOOTNOTES:

[1] A footnote that should be dropped.




II.

THE SECOND STORY.[99]


Body of the second story, with an inline ref[99] and an _italic_ word.


APPENDIX A.

Not a story.
"""


def test_split_finds_only_real_headers():
    stories = split_into_stories(SYNTHETIC)
    ids = [sid for sid, _ in stories]
    assert ids == ["001-the-first-story", "002-the-second-story"]


def test_split_drops_footnotes_block():
    stories = dict(split_into_stories(SYNTHETIC))
    assert "footnote that should be dropped" not in stories["001-the-first-story"]


def test_split_strips_inline_markup():
    stories = dict(split_into_stories(SYNTHETIC))
    text = stories["002-the-second-story"]
    assert "[99]" not in text
    assert "_" not in text
    assert "italic word" in text


def test_split_excludes_back_matter():
    stories = dict(split_into_stories(SYNTHETIC))
    assert all("Not a story" not in t for t in stories.values())


def test_split_raises_when_numbering_not_sequential():
    broken = "\n\nI.\n\nTHE FIRST.\n\nx\n\n\nIII.\n\nTHE THIRD.\n\ny\n"
    with pytest.raises(RuntimeError):
        split_into_stories(broken)


def test_story_id_is_metadata_only_not_used_for_grouping():
    # Two stories, distinct ids; records carry story_id through unchanged.
    records = build_sentence_records(split_into_stories(SYNTHETIC))
    assert {r["story_id"] for r in records} == {
        "001-the-first-story",
        "002-the-second-story",
    }


# --- ingest: end-to-end against the real downloaded file --------------------

real_corpus = pytest.mark.skipif(
    not CORPUS_FILE.exists(), reason="corpus file data/pg43629.txt not downloaded"
)


@real_corpus
def test_ingest_real_file_shape():
    records = ingest(str(CORPUS_FILE))
    # 164 stories in Giles' 1880 two-volume edition.
    assert len({r["story_id"] for r in records}) == 164
    # ids are a contiguous 0..N-1 run.
    assert [r["id"] for r in records] == list(range(len(records)))
    # schema per §5.1 step 4.
    assert all(
        set(r.keys()) == {"id", "text", "story_id", "position_in_story"}
        for r in records
    )


@real_corpus
def test_ingest_real_file_has_no_apparatus_leakage():
    records = ingest(str(CORPUS_FILE))
    blob = "\n".join(r["text"] for r in records)
    for marker in ("FOOTNOTES:", "END OF VOL", "APPENDIX A", "PROJECT GUTENBERG"):
        assert marker not in blob
    assert "_" not in blob
    assert "[1]" not in blob and "[36]" not in blob


@real_corpus
def test_strip_boilerplate_removes_license_wrapper():
    raw = CORPUS_FILE.read_text(encoding="utf-8")
    cleaned = strip_gutenberg_boilerplate(raw)
    assert len(cleaned) < len(raw)
    assert "*** START OF" not in cleaned and "*** END OF" not in cleaned
    assert "Project Gutenberg License" not in cleaned
