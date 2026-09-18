# Dream Collision Dictionary — how it works

The code, explained by following one chapter through it. Every number below is measured
from the committed data and `build/dictionary_log.jsonl` at seed 1.

---

## What it makes

```bash
python3 scripts/render_dictionary.py --word-a sleep --seed 1
```

~18s → `build/dictionary.pdf` (630 pages), `dictionary.html`, `dictionary_log.jsonl`.
From `sleep`, seed 1: **621 chapters, 68,552 words**, closing on *Knocking Shame*.

A chapter is a heading of two words and one block of prose. The prose is a chain of
clauses lifted verbatim from *Strange Stories from a Chinese Studio* (Giles, Gutenberg
#43629), each linked to the next by its final word. No text is written or repaired; the
generative acts are selection and sequencing. Python 3.13, standard library only at
runtime. No network, no database, no model.

---

## Chapter 1, end to end

### 1. The collision cast — what does `sleep` collide with?

Three coins, six lines, bottom to top. Tails 2, heads 3, so a line totals 6–9; odd is
yang, even is yin.

| line | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| total | 7 | 8 | 8 | 7 | 8 | 8 |
| | yang | yin | yin | yang | yin | yin |
| bit | 1 | 0 | 0 | 1 | 0 | 0 |

Read as binary with line 1 as the 1s place: **distance 9**. Line 1 is yang: **forward**.

### 2. The jump

`sleep` occurs 55 times in the flat corpus word sequence (170,540 tokens). One occurrence
is drawn at random — the 37th, position 117147. Jump +9 → 117156. Then scan forward to
the first word in the noun pool; here the landing word already is one, so the scan
distance is 0:

```
… did not attempt to [sleep] spending the interval in padding their knees with [thick] felt …
                     117147                                                     117156
```

**word_B = `thick`.** It goes in the heading and is then discarded — it is a coordinate,
not content, and never appears in the chapter. (Here it happens to be visible in the
text, because the jump was short enough to land inside the sentence the walk then seeds
from. Coincidence.)

Heading: **Sleep Thick**

### 3. The seed clause

Of every sentence containing `sleep`, take the one lying nearest a sentence containing
`thick`, measured in sentence ids. Sentence 3217 contains both, so its gap is 0:

> That night they did not attempt to sleep, spending the interval in padding their knees
> with thick felt concealed beneath their clothes; and then they got into chairs and were
> carried off to the hills.

One of that sentence's clauses is then taken **uniformly at random** — clause 1. Its last
word is the first **anchor**.

> spending the interval in padding their knees with thick felt concealed beneath their
> clothes; → anchor `clothes`

### 4. The walk

Take the anchor, find every *other* sentence containing it, pick one uniformly, pick one
of its clauses uniformly (preferring clauses whose pronoun matches the voice in play),
append it. The appended clause's last word is the next anchor. Repeat.

| hop | anchor | candidate sentences | → | clause appended | new anchor |
|---|---|---|---|---|---|
| 1 | `clothes` | 83 | 3073 | they took Niu’s clothes and buried them, and after that Chung continued his father’s business and soon amassed great wealth. | `wealth` |
| 2 | `wealth` | 11 | 4162 | and immediately seizing a sharp knife | `knife` |
| 3 | `knife` | 24 | 263 | Though it is severe, a cure can be effected; | `effected` |
| 4 | `effected` | 1 | 4508 | there was actually a ferry known as the Old Dragon (Lao-lung); | `lao-lung` |

`lao-lung` occurs in no sentence but 4508, so there is nowhere to hop: **`exhausted`**.
The other two stops are `loop` (the new anchor has already been used) and `cap`
(`MAX_HOPS = 200`, never reached — the observed maximum is 40).

### 5. What prints

Clauses joined with one space, quote marks and brackets balanced, first letter
capitalised, a full stop added if the last clause lacks one. Nothing else is touched —
the tense and pronoun mismatches at the seams are the output, not a defect. 60 words:

> **Spending** the interval in padding their knees with thick felt concealed beneath their
> **clothes;** they took Niu’s clothes and buried them, and after that Chung continued his
> father’s business and soon amassed great **wealth.** and immediately seizing a sharp
> **knife** Though it is severe, a cure can be **effected;** there was actually a ferry known
> as the Old Dragon (Lao-lung).

(`--tidy` writes a second book alongside it with the joins capitalised and stopped where
there is a positional signal for it: 1,088 letters and 660 stops across the book. Same
seed, same chapters, joins only.)

### 6. The succession cast — where does the book go next?

A second, independent cast, same procedure, different question:

| line | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| total | 7 | 7 | 8 | 7 | 8 | 7 |
| bit | 1 | 1 | 0 | 1 | 0 | 1 |

Distance **43**, forward, from occurrence 40 of `sleep` at 120819 → 120862, which is
`the` — not a pool noun, so scan forward 1 → **`sleeping`**. That is chapter 2's word_A.

The two throws stay separate on purpose: word_B is never promoted to the next word_A. An
earlier version did that, and every word then appeared twice in the headings (*Sleep
Thick / Thick Kindness / Kindness Boat*), which made word_B content.

---

## The rest of the mechanism

**One draw** (`chain.draw`) = one cast → jump → forward snap to a pool noun. Both
questions use it unchanged. The succession draw passes `skip=used` so a word that has
already had its chapter is scanned past; the collision draw skips nothing, and the same
word_B may be arrived at from several directions (621 chapters, 425 distinct word_B).

**No cast is ever re-thrown.** The rules for what counts as a valid landing are fixed
before the coins are thrown; nothing is rejected after the fact.

**The book stops** the first time a *succession* scan has to travel further than
`MAX_CAST_REACH = 63` — the furthest any cast can jump. Past that the scan is reaching
further than the coins ever could, and the book has quietly become "the next unused word
in reading order". The chapter it was drawn for still prints; the over-reached word gets
none. At seed 1 that is chapter 621, a 72-word scan. (The scan's median is 2 words over
the first hundred chapters and 356 over the last hundred if allowed to run the pool dry.)

**Determinism.** Everything random goes through one injected `rng`. An omitted `--seed`
is drawn explicitly and written to the log, so every book is reproducible.

---

## Four things that look like bugs

- **The jump is the cast lines read as bits, not `sum(totals) - 36`.** Six summed totals
  are a bell curve — 76% land 7–11 and the ends never occur. As bits they are flat over
  0–63. (`from_hex` and `to_hex` are deliberately *not* parameters to `derive_jump`.)
- **Direction is the bottom line's parity, not `from_hex < to_hex`.** 18% of casts have
  no changing lines, so `from_hex == to_hex`, and that rule sends every one of them
  backward.
- **The noun scan always runs forward**, whichever way the jump went. The direction
  belongs to the jump, not to the snap.
- **`exclude=word_A` on the scan.** Without it, a short backward jump plus the forward
  snap returns to the starting word on 3.4% of casts — and with both words identical
  there is nothing to collide and word_B goes inert.

---

## Data

| File | What |
|---|---|
| `data/pg43629.txt` | raw Gutenberg #43629, Giles, 2 vols (gitignored) |
| `data/sentences.jsonl` | 4,553 sentences / 164 stories from `corpus.ingest()` (gitignored; `scripts/dump_sentences.py` regenerates it) |
| `data/word_pool.json` | 4,516 nouns |
| `data/king_wen_table.json` | 64 hexagrams → 6-bit pattern |
| clause index | built in memory at load: 12,901 clauses, mean 12.9 words, 9,412 anchor keys |

**Ingestion** strips the Gutenberg boilerplate, splits on story headers (a bare Roman
numeral preceded by a blank line *and* followed by an ALL-CAPS title — both guards are
needed to reject the contents page and a wrapped footnote), drops appendices, footnote
blocks and printer matter, deletes transcription apparatus (footnote refs, bracketed
matter, `_italic_` delimiters, sub-section markers), then segments sentences on `.!?` +
whitespace + uppercase with abbreviations stitched back. The 1..164 story numbering is
asserted at runtime: if it breaks, `split_into_stories` raises rather than guesses.

**Pool** (`scripts/build_word_pool.py`, needs `nltk` + WordNet; build time only):
8,164 vocabulary → 4,639 kept by the WordNet noun filter minus 113 curated exclusions →
**4,516** after `filter_by_position` (92 positional cuts, 31 complement-requiring). Built
from the *cleaned* corpus, so every pool word is guaranteed a corpus hit. Re-running the
script reproduces the committed file exactly.

**Anchor index** is keyed under both tokenisations — `clause.words()`, which keeps
`fox-girl` whole, and `word_selection.tokenize_sequence()`, which splits it. With only
one, 116 pool words exist solely inside compounds and 2.55% of chapters raise.

**King Wen table** is verified twice (against an independent transcription of the
canonical sequence, and against the worked example in Gait's introduction: totals
`7,6,7,6,7,6` → hex 63, changing lines 2/4/6, hex 1). Nothing reads its output —
`from_hex`/`to_hex` are computed, logged, and used by nothing.

---

## Modules

```
src/dcd/
  corpus.py          ingestion, story split, markup cleaning, sentence segmentation
  word_selection.py  tokenisation, pool build + filters, uniform word_A draw
  traversal.py       cast_transition, derive_jump, position_of, jump, noun scan
  clause.py          clause segmentation, anchor + pronoun tagging, anchor index
  clause_walk.py     select_seed, walk, assemble, chapter record
  chain.py           the book — two draws per chapter, used set, stop rule
scripts/
  render_dictionary.py     the book → PDF/HTML/log
  build_word_pool.py       one-shot (needs nltk)
  build_king_wen_table.py  one-shot
  dump_sentences.py        regenerate data/sentences.jsonl
  attic/render_book.py     the older unchained LaTeX book, kept, needs pdflatex
tests/                     7 modules, 110 tests
docs/                      one .md per module, each tracing Chapter 1
```

---

## Invariants

1. **No statistical models.** No POS tagger, no sentence-boundary model, no stemming, no
   fuzzy matching, no embeddings. WordNet is permitted as a dictionary lookup; the closed
   word lists in `clause.py` and `corpus.ABBREVIATIONS` on the same footing.
2. **No content-based selection.** Candidate choice is uniform. The one non-random pick
   is the seed, fixed by word_B's position — an external procedural signal, not a
   judgment about the text.
3. **No grammatical repair at the seam.** The mismatch is the output.
4. **No re-casting.** A cast that produces an unproductive word stands.
5. **The cast never reads chapter text.** `cast_transition` takes only an `rng`.
6. **No cross-chapter memory in chapter generation** — nothing special-cases chapter 1
   and the walk never sees another chapter. The chain's used-word set is the single
   exception and is still open, below.
7. **Static data is not rebuilt per run.**

There is no silence state: both words are read out of the corpus, so no pool can come
back empty and every chapter produces text. The two loud failures — `position_of` raising
on a word absent from the sequence, `run_chapter` raising when no seed clause exists —
both mean the committed data files have drifted apart, and belong fixed at the data.

---

## Running it

```bash
python3 -m pytest -q                              # 110 tests
python3 scripts/render_dictionary.py --word-a sleep --seed 1
```

Flags that matter: `--seed`, `--word-a`, `--tidy`, `--max-chapters N` (test render; writes
`dictionary_sampleN.*` so it can't clobber a full run), `--no-pdf`, `--title`,
`--introduction FILE` (defaults to `introduction.md`, set verbatim), `--no-colophon`.
The PDF is printed by headless Chrome — there is no LaTeX on this machine.

The log is line 1 = run record (seed, counts, corpus, timestamp), then one record per
chapter, then a terminal record. So `jq` recipes filter on `select(.chapter_id)`.

One chapter from Python:

```python
import json, random, sys; sys.path.insert(0, "src")
from dcd.clause import build_clause_index
from dcd.clause_walk import run_chapter, walk
from dcd.traversal import build_king_wen_lookup
from dcd.word_selection import tokenize_sequence

sentences = [json.loads(l) for l in open("data/sentences.jsonl")]
pool = json.load(open("data/word_pool.json"))
nouns = {w.lower() for w in pool}
sequence = tokenize_sequence(" ".join(s["text"] for s in sentences))
king_wen = build_king_wen_lookup("data/king_wen_table.json")
clauses, anchors = build_clause_index(sentences)

record = run_chapter(1, sentences, clauses, anchors, sorted(nouns),
                     king_wen, sequence, nouns, random.Random(1))
print(record["output_text"])

# or walk a pair you choose, skipping the cast entirely:
print(walk("dream", "moon", clauses, anchors, random.Random(0)).text)
```
