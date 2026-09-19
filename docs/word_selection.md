# word_selection.py

The script defines what counts as a word of the corpus, which words are eligible, and the uniform `word_A`
draw.

## API

`tokenize_sequence(text)` is the important one: it is *the* definition of a word of the
corpus, shared by the word pool and by the positional traversal, which have to agree or a
jump counted in one would not line up with the nouns built by the other. It splits on
whitespace and hyphens, strips surrounding punctuation and a trailing `'s`, and keeps
everything else in order and in its original case — transliteration fragments included,
because a jump of nine words has to count them. They simply never match the noun set.

`build_word_pool(corpus_text)` takes the vocabulary, keeps what WordNet gives a noun
sense, and drops the curated exclusions; it needs `nltk`, and is build-time only.
`filter_by_position(pool, text)` applies the positional test and returns the kept and cut
lists, with `noun_position_ratios` exposing the counts behind it. `select_word_a(pool,
rng)` is `rng.choice` with no weighting, and `load_word_pool` / `save_word_pool` are
JSON.


## How the pool was narrowed

The corpus contains 8,164 different words. The pool keeps 4,516 of them. Three cuts get
from one number to the other.


1. It uses WordNet Lists to check if the word has a noun sense.
2. Names, Prepositions and translistd names are cut.
3. Checks the corpus directly by grammar structure. It asks if the word is a noun if it sits after an article such as 'the' or 'of', or if it sits before a comma/verb.


The pool is built from the cleaned corpus rather than the raw file, so every word in it
is guaranteed to occur at least once, and re-running `scripts/build_word_pool.py`
reproduces the committed file exactly.



