# corpus.py

This script turns the raw Gutenberg file into numbered sentence records.

Everything else in the project works on those records. Nothing reopens the file.

## API

`ingest(path)` does the whole job and is the only function anything else calls. It
returns the list of sentence records.

`strip_gutenberg_boilerplate(raw)` cuts everything outside the `*** START OF ***` and
`*** END OF ***` markers.

`split_into_stories(text)` returns 164 `(story_id, text)` pairs, and raises if the
numbering is not a clean 1 to 164.

`tokenize_sentences(text)` splits a story into sentences.

`build_sentence_records(stories)` numbers them and assembles the records.

A `Sentence` holds an `id`, the `text`, a `story_id` and a `position_in_story`. The id
runs in reading order across the whole corpus, which is what later lets clause_walk.py
treat an id as a position. The story id is metadata only — nothing is allowed to filter
on it.

## How the file becomes sentences

1. Cut away everything outside the Gutenberg start and end markers.
2. Find the story headers. A header is a bare Roman-numeral line with a blank line before
   it and an all-caps title after it. Both guards are needed: one alone matches the
   contents page and a footnote that happens to wrap as `Section` / `XI.`
3. Drop what is not story text — front matter, the appendices, the index, each story's
   footnote block, and the printer's matter wedged between the two volumes.
4. Delete the transcription markup: `[36]` footnote refs, bracketed asides, the `_`
   marking italics, and `I.--` sub-section markers. Then collapse the doubled spaces and
   stray ` ,` those deletions leave behind.
5. Split into sentences at `.` `!` `?` followed by a space and a capital letter.
6. Stitch back anything that split on `Mr.`, `Mrs.`, `Dr.`, `St.` or an initial.
7. Number them from 0, normalise the whitespace, and note which story each came from.

That gives 4,553 sentences across 164 stories.

## Example

Chapter 1 opens from record 3217:

> That night they did not attempt to sleep, spending the interval in padding their knees
> with thick felt concealed beneath their clothes; and then they got into chairs and were
> carried off to the hills.

That is this script's entire contribution to the chapter: one clean string with a number
on it. The `_` italics, the footnote markers and the editorial brackets that surrounded
it in the Gutenberg file are gone, and everything downstream can point at the sentence by
saying 3217.

## If the numbering breaks

Step 2 counts the headers and checks they run 1 to 164 with no gaps. If they don't, the
function raises instead of carrying on with what it found.

It has to be loud, because the failure is silent otherwise: a missed header shifts every
sentence id after it, and every id ever written to a log then points at the wrong
sentence.
