# Dream Collision Dictionary

A generative text system over Herbert Giles's 1880 translation of Pu
Songling's *Strange Stories from a Chinese Studio*. No language model, no
embeddings, no similarity scoring anywhere — every operation is exact
string matching, a random draw from a finite pool, or a table lookup.

`Word_Collision_Agent.md` (on the Desktop) is the authoritative spec.
`TECH_SPEC.md` describes the code as built. `CLAUSE_WALK_SPEC.md`
specifies the mechanism that produces the book. `NEEDS_INPUT.md` is the
working record of decisions and open questions.

## The two mechanisms

**The clause walk makes the book (decided 2026-09-16).** A chapter is a
chain of clauses from different stories, each linked to the next by its
final word. Every clause is real corpus text; the generative acts are
selection and sequencing. See `CLAUSE_WALK_SPEC.md`.

**The splice is kept but produces no output for reading.** A chapter is
two sentences cut at a shared word with their halves swapped. Its code,
tests and spec all stand and still run — it is simply not a route to the
page. See `TECH_SPEC.md` §1a.

Both draw `word_A` and `word_B` the same way: an I Ching cast supplies a
jump distance and direction, applied to a random occurrence of `word_A`
in the corpus's flat word sequence, then a forward scan to the nearest
pool noun.

## The book

**Step-by-step instructions, including what to install and how to read
the output: [`RUNNING.md`](RUNNING.md).** The short version:

```bash
python3 scripts/render_dictionary.py --word-a sleep --seed 1
```

One command, one PDF. `word_A` starts at **`sleep`**. Each chapter casts
twice, asking two different questions: *what does this word collide
with?* gives `word_B`, which the clause walk runs on; *where does the
book go next?* gives the following chapter's `word_A`. The cycle
continues until the mechanism exhausts itself.

`word_B` is a coordinate, not content — it is printed in the heading,
used to fix where the walk starts, and then discarded. It is never
promoted into the next chapter's `word_A`; that is what the second throw
is for. (An earlier version did promote it, and every word then appeared
twice in the headings — *Sleep Thick / Thick Kindness / Kindness Boat*.)

Writes `build/dictionary.pdf`, `build/dictionary.html` (the print source)
and `build/dictionary_log.jsonl` — a run record, then one audit record
per chapter with both throws, then a terminal record. From `sleep`, seed
1: **621 chapters, 68,552 words, 630 pages** with the title page,
introduction and colophon — opening *Sleep Thick* and closing *Knocking
Shame*. The whole run takes about 18 seconds.

**Every run is a new book unless you pass `--seed`.** The same seed gives
a byte-identical book forever; without one, the seed is drawn, printed
and recorded, so an unseeded book can still be reproduced afterwards.

### Title page, introduction and colophon

The book opens on its title — *Word Collisions for a Good Night’s Sleep*
— set in the chapter headings' own 34pt serif, on its own page. It is
also the PDF's document title. `--title` changes it for one render,
`BOOK_TITLE` in the script changes it for good, `--no-title-page` drops
the page.

Put your text in **`introduction.md`** at the project root and it is set
on its own page before chapter one, its heading in the same 34pt serif as
the chapters — *Introduction* by default, or whatever a leading `# Title`
line says. `--introduction FILE` points elsewhere.

The book closes with a **colophon** of one line — `621 chapters,
2026-09-18 21:40` — and nothing else. The seed, the starting word, where
the mechanism stopped, the corpus and the pool all live in the run record
on the first line of the log. `--no-colophon` omits the page.

`--max-chapters N` caps it for a test render, `--no-pdf` stops at the
HTML, `--chrome PATH` points at another Chrome.

### `--tidy` — the joins, optionally

```bash
python3 scripts/render_dictionary.py --word-a sleep --seed 1 --tidy
```

Writes `build/dictionary_tidy.*` **alongside** the untidied book, from
the same seed and the same chapters, so the two can be read side by side.

It applies two positional rules at the clause joins (the 2026-09-18 §8
amendment): capitalise after a `.`, `!` or `?`, and supply a full stop
where a clause ends unpunctuated before a capital. Across the seed-1 book
that is 1,088 letters and exactly 660 inserted full stops; 497 of 621
chapters differ. Word counts, hops and casts are identical — the audit
record carries `tidied` so every chapter says which convention made it.

This is **not** grammatical repair. *"...amassed great wealth. And
immediately seizing a sharp knife"* is exactly as much of a non-sequitur
capitalised as it was in lower case; what goes is the appearance of a
typo. The 1,013 joins where an unpunctuated clause meets a lower-case one
(21.4%) are left alone on purpose, so a tidied chapter still reads as
assembled. See `NEEDS_INPUT.md` item 16 for the measurements and the
alternatives that were declined.

### Where the book ends

The book stops **the first time the succession scan has to travel further
than 63 words** — the furthest any cast could ever jump, since the jump
is the six cast lines read as a binary number. That chapter still prints;
it is the succession, not the chapter, that failed.

Once several hundred words have had their chapter, the succession cast
starts landing on words already used. The cast is never re-thrown for
this (Constraint 4); instead the scan walks past used nouns, exactly as
it already walks past non-nouns and past `word_A` itself. But the scan
travels further as the pool empties — a median of 2 words over the first hundred
chapters, 46 by chapter 2,500, 356 over the last hundred if allowed to
run the pool dry. Past 63 the scan is reaching further than any cast
could, and the book has quietly stopped being cast-driven. So that is
where it ends: the moment the scan starts deciding instead of the coins.
In the seed-1 book the scan that ends it is 72 words long, at `knocking`.

**Constraint 5 is flagged, not resolved** — the chain carries the
current `word_A` and the set of used words across chapters, which is
memory in word selection. See `NEEDS_INPUT.md` item 15; it needs the
artist, not the code.

### The page

Specified, for once — measured off the two reference pages: A4, 30mm
margins, the two words as a 34pt serif heading in Title Case set as a
single block — one normal word space, chosen 2026-09-18 over the 14.2mm
gap the reference images carried, so the pair reads as one headword
rather than as two entries side by side — one
justified 12pt block beneath, a new page per chapter, overflow continuing
with no heading, no page numbers. Every measurement is a CSS custom
property at the top of the script's `STYLE` block. PDF conversion is
headless Chrome, which needs no install — there is no LaTeX here.

## The older book, unchained

A fixed number of chapters, each with an unrelated random `word_A`. Kept
and still working:

```bash
python3 scripts/attic/render_book.py --chapters 40 --seed 1
pdflatex -output-directory build build/book.tex
```

Writes `build/book.tex` and `build/book_log.jsonl` — one audit record per
chapter, so any chapter can be traced to its cast, jump, seed and hops.
Needs a LaTeX installation, which this machine does not have.

## Layout

```
dream_collision_dictionary/
├── data/
│   ├── pg43629.txt                  # §5.1 — Gutenberg source (Giles, 2 vols.)
│   ├── sentences.jsonl              # ingest() output — 4,553 records / 164 stories
│   ├── sentences_preview.txt        # same, human-readable
│   ├── king_wen_table.json          # §4, §6.1 — verified against the canonical sequence
│   ├── word_pool.json               # §5.3 — 4,516 nouns; static, do not regenerate per run
│   └── word_pool_wordnet_only.json  # the unfiltered 4,646, archived for reproducing old logs
├── src/dcd/
│   ├── corpus.py          # §5.1 ingestion + sentence segmentation
│   ├── word_selection.py  # §5.3 word pool, tokenisation, the three pool filters
│   ├── traversal.py       # §6 casting, King Wen lookup, the position jump
│   ├── clause.py          # CLAUSE_WALK_SPEC §4, §6a — clauses, anchors, pronouns
│   ├── clause_walk.py     # CLAUSE_WALK_SPEC §5–§10 — the walk
│   └── chain.py           # TECH_SPEC §6a — the book-level chain
├── RUNNING.md                  # how to run it, step by step
├── scripts/
│   ├── build_king_wen_table.py  # already run
│   ├── build_word_pool.py       # already run (needs nltk + wordnet)
│   ├── dump_sentences.py        # regenerate sentences.jsonl from the raw corpus
│   ├── attic/render_book.py           # chapters -> LaTeX + audit log
│   └── render_dictionary.py     # the chained book -> PDF + audit log
└── tests/                       # 7 modules, 110 tests
```

## Corpus and pool are rebuilt artefacts

`sentences.jsonl` and `word_pool.json` are committed static files, and
rebuilding either changes every chapter the system will ever produce.
Sentence ids are **not stable across rebuilds** — see §5.1 of the spec.
Keep the corpus build beside any log you intend to reproduce from.

## Build order status (§9)

| Step | Status |
|---|---|
| 1. Corpus ingestion + segmentation | **Done.** `ingest()` yields 4,553 records across 164 stories. Four deletions happen at ingest — footnote markers, italic delimiters, all bracketed matter, Roman-numeral sub-section markers. See spec §5.1. |
| 2. Word pool | **Done.** 4,516 tokens: 8,164 vocabulary -> 4,639 after the WordNet noun filter minus 113 curated exclusions -> 4,516 after 92 positional cuts and 31 complement-requiring cuts. Re-measured 2026-09-18; `build_word_pool.py` reproduces the committed file exactly. See spec §5.3. |
| 3. KWIC | **Done + verified** against the real corpus. |
| 4. Candidate selection + splice | **Done + verified.** |
| 5. Single-chapter generation, manual word pair | **Done + verified.** |
| 6. `cast_transition` | **Done + verified** — coin distribution matches the 3-coin method over 20k casts. |
| 7. King Wen table | **Done + verified** against the canonical sequence and Gait's worked example. But see the caveat below: nothing now reads its output. |
| 8. ~~Incremental Yilin population~~ | **Superseded 2026-08-28, code removed 2026-09-15.** §6.2 is the internal position jump; `derive_jump`, `position_of`, `jump_from_position` and `scan_to_nearest_noun` are built and tested. |
| 9. Full traversal flow, one chapter | **Done.** `pipeline.run_chapter` produces splice chapters; `clause_walk.run_chapter` produces clause-walk chapters. Previously raised on its first call. |
| 10. Multi-chapter run | **Done.** `scripts/render_dictionary.py` renders the chained book from `sleep` to a PDF (TECH_SPEC §6a); `scripts/attic/render_book.py` still renders the older unchained LaTeX book. |

## The King Wen table no longer affects output

`cast_transition` still computes `from_hex` and `to_hex`, and they are
still logged — but **nothing reads them**. Jump distance is the six
`from` lines read as a binary number, and direction is the bottom line's
polarity (spec §6.2, resolved 2026-09-15). The table, its lookup and its
build script exist to put two numbers in an audit record.

Whether to keep it is open. Keeping costs nothing and preserves a record
of what was cast; dropping it removes ~64 entries of data and its code.

## King Wen table caveat

`data/king_wen_table.json` was built by mapping each King Wen number to
its inner/outer trigram pair (sourced from "List of hexagrams of the I
Ching") and converting each trigram to its standard 3-bit binary pattern
(Qian=111 … Kun=000). Convention: line 1 = bottom, yang = 1, inner/lower
trigram in the low three bits.

**Verified (2026-08-28), NEEDS_INPUT.md item 2 closed:**

- All 64 entries match an independent transcription of the canonical
  King Wen sequence (`tests/test_king_wen_table.py`).
- The reading direction is confirmed against a worked example in
  Christopher Gait's own introduction: coin totals `7,6,7,6,7,6` give
  starting hexagram 63, changing lines 2/4/6, post-change hexagram 1 —
  all three reproduce from the table
  (`test_verified_against_gait_example`).

Hexagrams 63 and 1 are the two checked against Gait directly; the rest
rest on the canonical check plus the confirmed convention. `traversal.py`
already used this convention, so no code changed.

## What this does NOT do

- Does not fabricate corpus content. Every function that touches
  sentences takes them as a parameter — nothing is hardcoded.
- Does not guess the story-boundary regex (§5.1) — written against the
  actual `data/pg43629.txt` after hand inspection, with a runtime
  assertion that the 1..164 numbering stays clean.
- Does not repair grammar at any join, ever. The mismatch is the
  intended output (§5.5). `--tidy` capitalises after a full stop and
  supplies a missing one — two positional conventions, no grammar, off
  by default (CLAUSE_WALK_SPEC §8 amendment, 2026-09-18).
- Does not specify how a chapter looks on the page **for the splice or
  for `render_book.py`** — those remain working defaults, and that half
  of `NEEDS_INPUT.md` item 8 is still open. The chained book's page IS
  specified, from the artist's reference pages.
- Does not re-throw a cast, ever, including when it lands on a word that
  already had its chapter (Constraint 4).
