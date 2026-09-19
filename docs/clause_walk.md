# clause_walk.py

Makes one chapter. Give it two words and it hands back a block of prose: a chain of
clauses, each one lifted from a different sentence, each linked to the next by a shared
word.

## API

`walk(word_a, word_b, clauses, anchor_index, rng, tidy=False)` builds the chapter and
returns it, along with the hops it made and why it stopped.

`select_seed(word_a, word_b, clauses, anchor_index, rng)` picks the clause it opens from.

`assemble(parts, tidy=False)` joins the clauses into the finished text, with
`balance_marks(text)` doing the quote-mark cleanup.

`chapter_record(chapter_id, chapter)` is the audit record written to the log.

`run_chapter(...)` is a side door — see the note at the end.

## How a chapter gets built

1. `word_A` is the seed to identify all possible sentences to start.
2.Of all the sentences containing `word_A`, take the one nearest a sentence containing `word_B`. 
Chapter 1's words were `sleep` and `thick`, and one sentence happens to contain both, so it won outright:

   > That night they did not attempt to sleep, spending the interval in padding their
   > knees with thick felt concealed beneath their clothes; and then they got into
   > chairs and were carried off to the hills.

3. It takes a clause at random. 
Here it was the middle one, ending on
   `clothes`. A clause's last word is its **anchor**, and from here on the anchor is the
   only thing the walk pays attention to. `word_B` has done its job and is dropped.

4. Look up the other sentences containing the anchor.
  `clothes` is in 83 of them.

5. Pick one sentence, take a clause from it, add it to the chapter. That clause's last word is the new anchor — then go back to step 4 and repeat.

6. The clausal walk stops when the anchor leads no where.

   Chapter 1 ran `clothes` → `wealth` (11 sentences to choose from) → `knife` (24) → `effected` (1), and that last clause ended
   on `lao-lung`, a word in no other sentence in the corpus. Four hops, five clauses, five unrelated stories, 60 words.

7. Join the clauses together with single spaces, delete quote marks whose
   partner was left behind in a sentence that never got used, capitalise the first letter and put a full stop on the end. That is all. `wealth. and immediately` keeps its lower-case `a`, because smoothing that over is not this program's job.

In the script code: steps 2–3 are `select_seed()`, steps 4–6 are `walk()`, step 7 is `assemble()`.

## A chapter ends if it is: 

`exhausted` — no other sentence contains the anchor.

`loop` — the new anchor is one this chapter has already hopped on.

`cap` — 200 hops.

## Pronoun Alignment for Associative Coherence

The walk prefers clauses whose pronouns match the ones already in play — if a chapter is
running on *they*, a *they* clause is chosen over a *she* clause.

When no clause matches, the full set is used, so a voice can never dead-end a
walk.

Every pick is uniform except the seed, and even that is fixed by `word_B`'s position, not
by anything about the text.

`tidy=True` capitalises after a full stop and supplies a stop where a clause ends
unpunctuated before a capital. It never touches grammar, and it is off unless the
renderer is run with `--tidy`.

This module also has a `run_chapter()` that throws the coins itself and draws an unrelated word from the pool each time.


