# traversal.py

This script throws the coins and turns the throw into a word.

It is the oracle. Every random decision in the book that isn't a clause pick comes from
here.

## API

`cast_transition(rng, king_wen_lookup)` throws six lines and returns the coin totals plus
the hexagram thrown and the one it changes into.

`derive_jump(coin_totals)` turns those totals into a distance and a direction.
`from_lines(coin_totals)` is the yang/yin pattern behind them.

`position_of(word, sequence, rng)` picks one occurrence of a word at random and reports
which one it drew and how many there were.

`jump_from_position(position, distance, direction, sequence)` counts the distance out
from there, wrapping at either end of the corpus.

`scan_to_nearest_noun(position, sequence, noun_set, exclude=, skip=)` walks forward to
the first word in the pool and reports how far it had to go.

`build_king_wen_lookup(path)` and `king_wen_number(lines, lookup)` handle the hexagram
table.

## How a throw becomes a word

1. Throw three coins for each of six lines, bottom to top. Tails counts 2, heads 3, so a
   line totals between 6 and 9.
2. Read each line as yang or yin — odd is yang, even is yin.
3. Read the six of them as a binary number, bottom line as the 1s place. That is the
   **distance**, somewhere from 0 to 63.
4. The bottom line also gives the **direction**: yang forward, yin backward.
5. Pick one occurrence of `word_A` at random out of however many the corpus holds.
6. Count the distance from there, wrapping round if you run off either end.
7. Walk forward from where you land until you reach a word in the pool. That word is the
   answer.

Step 7 always walks forward, whichever way step 6 went.

## Example

Chapter 1 ran this twice.

**The collision throw.** The six lines came out `1,0,0,1,0,0`, which as a binary number
is 9, and the bottom line is yang, so: nine words forward. Starting from one of `sleep`'s
55 occurrences, it landed on `thick` — already a pool word, so there was nothing to walk.
That is `word_B`.

**The succession throw.** `1,1,0,1,0,1` = 43, forward again. This time it landed on
`the`, which is not in the pool, so it stepped once more and stopped on `sleeping` — the
next chapter's word.

Each throw is also looked up as a hexagram, 51 and 38. Both numbers go into the log and
nothing reads them.
