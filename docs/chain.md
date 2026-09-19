# chain.py

This script decides 'word_A' and 'word_B' for a chapter, sends this pair to 'clause_walk.py' and decides what is the next pair of words for the next chapter.

This continues until no more chapters are produced, compiling a log of chapters.  

## API

`run_chain(start_word, clauses, anchor_index, king_wen_lookup, sequence, noun_set, rng,
max_chapters=None, tidy=False)` yields one audit record per chapter and then a terminal
record. 

`draw(word_a, ..., skip=None)` is one cast, one jump and one forward snap,
returning a `Link` that holds the landing word together with the throw that produced it.


`terminal_record` writes the record where the book stops. `MAX_CAST_REACH` is 63.

## How word_A and word_B are chosen in a chapter

Word_A has been selected.
1. The algorithm selects word_B
2. It prints word_B beside word_A. 
3. clause_walk.py is called. To select the starting clause, take every sentence containing word_A, keep the one nearest a sentence containing word_B, and draw one of its clauses at random. That clause's last word is the first anchor.
4. Looks the anchor up, take a clause from some other sentence containing it, add it, and use its last word as the next anchor. Repeat until the anchor leads nowhere. Then join the clauses, tidy the stray quote marks, capitalise the start and end with a full stop.
5. When clause_walk.py is finished building a chapter, it runs the algorithm to select the next word_A, skipping a word that has been used.
6. Repeats 1-5



## Example
run_chain() is the outer loop — one iteration per chapter, 621 of them. It carries two pieces of state: word_a, the current word, and used, the set of words that have already had a chapter.
```
draw(word_a)             → "thick"      cast, jump, forward scan  = word_B
walk(word_a, "thick")    → 60 words     the chapter
draw(word_a, skip=used)  → "sleeping"   same draw, unused words only
yield record; used.add("sleeping"); word_a = "sleeping"
```
The used set now holds `sleep`, so no later succession can land back on it. The second
throw only had to step one word past its landing to find something unused — it is when
that step grows past 63 that the book ends.

## Condition for the book to stop.

The book ends the first time a succession scan travels further than 63 words, which is
the furthest any cast can jump. 


