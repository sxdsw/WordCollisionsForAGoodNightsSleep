# clause.py

This script cuts every sentence into clauses, and builds an index of which sentences
contain which words.

clause_walk.py uses both: the clauses are what a chapter is made of, and the index is how
it finds the next one.

## API

`segment(sentence)` cuts one sentence record into clauses.

`build_clause_index(sentences)` runs that across the corpus and returns two things: the
clauses, keyed by sentence id, and the anchor index. Both are built in memory when the
book starts; neither is written to disk.

`words(text)` is the tokenisation used inside a clause. It keeps `fox-girl` whole.

`pronoun_classes(tokens)` tags a clause with the pronouns it uses — male, female, plural,
first person.

A `Clause` holds its sentence id, its position in that sentence, its text, its anchor and its pronoun set. The anchor is its last word, lowercased, and it is the only part the walk hops on. 

## How a sentence is cut into clauses

1. Split at `;` and `:`, at `.` `!` `?`, and at runs of em-dashes.
2. Also split at a comma — but only when a subordinator, a pronoun, a coordinator leading
   a subject, or a participial `-ing` follows it. A bare comma is never enough on its
   own, or "Hsiao, Chung, and Hsin" comes apart into pieces.
3. Don't split on the full stop of `Mr.`, `Mrs.`, `Dr.`, `St.` or an initial. That list comes from corpus.py, so the clause splitter and the sentence splitter cannot drift apart.
4. Throw away any piece under three words.
5. If a piece was left ending on `and`, `but`, `or` and so on, strip it off.
6. Take the last word, lowercase it: that is the anchor.
7. Tag whatever pronouns the clause contains.

## How the index is built

For every sentence, record every word it contains — not just the clause-final ones, since
an anchor has to be findable anywhere in a target sentence. The result maps a word to the
set of sentences holding it, so "which sentences contain this word?" is a lookup, not a
search.

Hyphenated words are indexed twice over: `fox-girl` files its sentence under the whole
word and under each half. An anchor may be the whole thing; a pool word may be just
`girl`. Whichever way the word arrives, the lookup finds it.

This matters more than it sounds: 116 pool words never appear on their own anywhere in
the book, only inside a hyphenated one, and before both forms were indexed a chapter
opening on any of them had no sentence to start from — 2.55 per cent of chapters.

## Example

Sentence 3217 is cut into three clauses:

```
0  That night they did not attempt to sleep                         → sleep
1  spending the interval in padding their knees with thick felt
   concealed beneath their clothes;                                 → clothes
2  and then they got into chairs and were carried off to the hills. → hills
```

Chapter 1 took the middle one, so its first anchor was `clothes`. The index says
`clothes` is in 84 sentences; the walk drops the one it is standing in, leaving the 83
choices its log records for that hop. Four hops later the anchor is `lao-lung`, which the
index has in one sentence only — the one it is already in — so the chapter ends.

