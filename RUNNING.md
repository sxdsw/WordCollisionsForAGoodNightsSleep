# GUide on how to run the dream machine

Everything below was run on this machine, in this order, and the output
shown is what it actually printed. If you only want one thing, it is
step 2.

---

## 0. What you need

| | why | check |
|---|---|---|
| **Python 3** | the generator — **standard library only**, nothing to install | `python3 -V` (tested on 3.13.5) |
| **Google Chrome** | prints the PDF. There is no LaTeX on this machine and none is needed | it lives at `/Applications/Google Chrome.app` |
| `pytest` | only for step 6, the tests | `python3 -m pytest --version` |
| `jq` | only for step 5, reading the log — a Python one-liner does the same | `which jq` |
| `nltk` | **only** if you ever rebuild the word pool (step 8). Not needed to make a book | — |

Chrome may already be running with your own windows open; that is fine.
The script starts its own private copy with a throwaway profile and
never touches your session.

---

## 1. Go to the project and check the data is there

```bash
cd ~/Downloads/dream_collision_dictionary
ls data/
```

You should see `pg43629.txt`, `sentences.jsonl`, `word_pool.json` and
`king_wen_table.json`. These are **committed static files, not build
artefacts** — you do not generate them, and rebuilding them changes
every chapter the system will ever produce (step 8).

---

## 2. Make the book

```bash
python3 scripts/render_dictionary.py --word-a sleep --seed 1
```

About 20 seconds — 4 for the text, the rest is Chrome printing 627
pages. You will see:

```
621 chapters, 68,552 words
  opens  Sleep Thick
  closes Knocking Shame
  stopped: scan of 72 words exceeded the 63-word cast reach at 'knocking' (would have been 'wallet')
wrote .../build/dictionary.html
wrote .../build/dictionary_log.jsonl   (§7/§10 audit record, one line per chapter)

printing 621 chapters to PDF ...
wrote .../build/dictionary.pdf   (1.5 MB)
```

That is the whole thing. **`build/dictionary.pdf` is the book.**

The command works from any directory — the script finds the project from
its own location, so `python3 ~/Downloads/dream_collision_dictionary/scripts/render_dictionary.py`
works from anywhere too.

---

## 3. What you just made

| file | what it is |
|---|---|
| `build/dictionary.pdf` | **the book.** Title page, introduction, 621 chapters, colophon — 630 pages |
| `build/dictionary.html` | what Chrome printed from. Every layout measurement lives in its `<style>` block |
| `build/dictionary_log.jsonl` | the audit record — a run record on the first line, then one JSON line per chapter, then a terminal record. This is the source of truth for what each chapter *is*; the PDF is only how it looks |

**On repeat runs.** With the same `--seed` you get a byte-identical book,
every time. **Drop `--seed` and every run is a completely new book** —
different chapters, different length, different ending. The seed it drew
is printed and written into the log either way, so an unseeded book can
still be made again afterwards:

```
  seed   230162027   (drawn for this run — pass --seed to make this book again)
```

---

## 4. The variations

**Tidied joins** — capitalises after a full stop and supplies one where a
clause ends unpunctuated before a capital:

```bash
python3 scripts/render_dictionary.py --word-a sleep --seed 1 --tidy
```

Writes `dictionary_tidy.*` **alongside** the untidied book, from the same
seed and the same chapters, so you can read both. See `NEEDS_INPUT.md`
item 16 for what it changes and what it deliberately leaves alone.

**A quick sample**, when you are testing a layout change and do not want
to wait for 621 chapters:

```bash
python3 scripts/render_dictionary.py --max-chapters 8 --seed 1
```

Writes `dictionary_sample8.*`, so a capped run can never overwrite a full
render's files.

**Start somewhere else:**

```bash
python3 scripts/render_dictionary.py --word-a dream --seed 1
```

Any word that occurs in the corpus works. A word that does not gets a
plain refusal rather than a traceback:

```
'zzzz' does not occur in the corpus — pick another starting word.
```

**Skip the PDF** and stop at the HTML — useful when you only want the log:

```bash
python3 scripts/render_dictionary.py --seed 1 --no-pdf
```

**Everything else:**

```bash
python3 scripts/render_dictionary.py --help
```

---

## 4a. The title page

The book opens on its title, set in the same 34pt serif as the chapter
headings, on its own page. The title is also the PDF's document title, so
it is what a reader's PDF viewer shows in its window and tab.

It defaults to *Word Collisions for a Good Night’s Sleep*. To change it
for one render:

```bash
python3 scripts/render_dictionary.py --title "Another Title" --seed 1
```

To change it for good, edit `BOOK_TITLE` at the top of
`scripts/render_dictionary.py`. `--no-title-page` drops the page while
keeping the title on the PDF itself.

## 4b. Adding an introduction

Write your text in a file called **`introduction.md`** in the project
root and it is picked up automatically — no flag needed. (`preface.md`
also works, for older projects.)

```bash
cat > introduction.md <<'EOF'
# On Falling Asleep

Your first paragraph. Blank lines separate paragraphs, and nothing in
the file is interpreted: the text is set exactly as you wrote it.

Your second paragraph.
EOF

python3 scripts/render_dictionary.py --word-a sleep --seed 1
```

The run tells you it found it:

```
  intro   introduction.md — 'On Falling Asleep', 3 paragraphs
```

It is set on its own page before chapter one, with its heading in the
same 34pt serif as the chapter headings. A leading `# Title` line becomes
that heading; leave it out and the heading is simply *Introduction*.

Keep it somewhere else, or keep several:

```bash
python3 scripts/render_dictionary.py --introduction drafts/intro-v2.md --seed 1
```

## 4c. The colophon

The last page carries one line, and nothing else:

```
621 chapters, 2026-09-18 21:40
```

Everything else about the run — the seed, the starting word, where the
mechanism stopped, the corpus and pool — is in the run record on the
first line of the log (step 5). It was cut from the page, not from the
record.

Omit the page with `--no-colophon`.

---

## 5. Reading the audit log

Any chapter can be traced back to the coins that made it.

```bash
# the first three headings
jq -r 'select(.chapter_id) | "\(.word_a) \(.word_b)"' build/dictionary_log.jsonl | head -3
```
```
sleep thick
sleeping release
landlord ounces
```

```bash
# why the book stopped
jq -r 'select(.terminal == true) | "stopped at \(.word_a): scan \(.scan_distance) > \(.max_cast_reach), would have been \(.would_have_been)"' build/dictionary_log.jsonl
```
```
stopped at knocking: scan 72 > 63, would have been wallet
```

```bash
# the longest chapters
jq -r 'select(.chapter_id) | "\(.word_count)\t\(.word_a) \(.word_b)"' build/dictionary_log.jsonl | sort -rn | head -3
```
```
702     virtue soul
586     rivers days
577     throne palace
```

```bash
# totals
jq -r 'select(.run) | "\(.chapters) chapters, \(.words) words, seed \(.seed)"' build/dictionary_log.jsonl
```
```
621 chapters, 68552 words, seed 1
```

Without `jq`, the same in Python:

```bash
python3 -c "
import json
r=[json.loads(l) for l in open('build/dictionary_log.jsonl') if l.strip()]
c=[x for x in r if x.get('chapter_id')]
print(len(c),'chapters,',sum(x['word_count'] for x in c),'words')"
```

Each chapter record carries both throws — `traversal_cast` and
`traversal_jump` for the collision that gave `word_B`, `succession_cast`
and `succession_jump` for the throw that chose the next `word_A` — plus
every hop the clause walk made.

---

## 6. Running the tests

```bash
python3 -m pytest tests/ -q
```

110 tests, about 75 seconds (most of it is building the clause index
from the real corpus, which several tests need).

A single file, if you are working on one part:

```bash
python3 -m pytest tests/test_chain.py -q
```

---

## 7. Changing how the page looks

Everything is a CSS custom property at the top of `STYLE` in
`scripts/render_dictionary.py`:

```
--page-margin: 30mm
--body-size: 12pt
--body-leading: 1.5
--heading-size: 34pt
--heading-word-gap: 0        /* 0.95em restores the reference images' wide gap */
--space-above-heading: 25mm
--space-below-heading: 27mm
```

Change one, then re-render a sample to look at it:

```bash
python3 scripts/render_dictionary.py --max-chapters 8 --seed 1
open build/dictionary_sample8.pdf
```

---

## 8. Rebuilding the corpus or the word pool — read first

**You almost certainly do not want to do this.** `sentences.jsonl` and
`word_pool.json` are committed static files. Rebuilding either changes
every chapter the system will ever produce, and **sentence ids are not
stable across rebuilds**, so every existing log stops resolving against
the corpus it was written from. Keep the corpus build beside any log you
intend to reproduce from.

If you still need to:

```bash
python3 scripts/dump_sentences.py                     # rebuilds sentences.jsonl
pip install -r requirements.txt                       # nltk, for the pool only
python3 -c "import nltk; nltk.download('wordnet')"    # once
cp data/word_pool.json /tmp/word_pool_before.json     # keep the old one to compare against
python3 scripts/build_word_pool.py                    # rebuilds word_pool.json
```

To see what the rebuild changed:

```bash
python3 -c "
import json
before = set(json.load(open('/tmp/word_pool_before.json')))
after  = set(json.load(open('data/word_pool.json')))
print(len(before), '->', len(after))
print('gone: ', sorted(before - after))
print('new:  ', sorted(after - before))
"
```

---

## 9. The older, unchained book

`scripts/render_book.py` renders a fixed number of chapters, each with an
unrelated random `word_A` — the design before the chain. It is kept and
still works, but it outputs LaTeX:

```bash
python3 scripts/render_book.py --chapters 40 --seed 1
pdflatex -output-directory build build/book.tex     # needs LaTeX — NOT installed here
```

The first command works; the second will not, unless you install a LaTeX
distribution. The chained book (step 2) needs no LaTeX at all.

---

## 10. If something goes wrong

**`Chrome not found at ...`** — pass the real path, or stop at the HTML:

```bash
python3 scripts/render_dictionary.py --seed 1 --chrome "/path/to/Google Chrome"
python3 scripts/render_dictionary.py --seed 1 --no-pdf
```

**The PDF step seems to hang.** It should not — the script launches
Chrome, watches the PDF file until it stops growing, then stops the
process, because Chrome 153's headless mode never exits on its own after
`--print-to-pdf`. If a very large render does time out, raise the limit:

```bash
python3 scripts/render_dictionary.py --seed 1 --pdf-timeout 1800
```

**`'x' does not occur in the corpus`** — the starting word must appear in
Giles's text. Try another.

**A different number of chapters than you expected.** Without `--seed`
every run is a new book; 621 chapters is specific to `--seed 1` starting
from `sleep`. The length is set by where the mechanism exhausts itself,
which differs per seed.

**The book stopped much sooner than expected.** That is the stop rule
working — see "Where the book ends" in `README.md`.

---

## Where the reasoning lives

| document | what it holds |
|---|---|
| `README.md` | what the project is, the chain, where the book ends |
| `TECH_SPEC.md` | the code as built, §-by-§ |
| `CLAUSE_WALK_SPEC.md` | the clause walk, and the §8 assembly rules |
| `NEEDS_INPUT.md` | every open question and every decision, with its reasoning |
