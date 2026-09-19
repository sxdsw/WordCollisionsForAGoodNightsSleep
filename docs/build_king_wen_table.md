# build_king_wen_table.py

This script writes `data/king_wen_table.json`, the lookup that turns six thrown lines
into a hexagram number.

It is a one-shot build, already run. Re-running it reproduces the file byte for byte.

```bash
python3 scripts/build_king_wen_table.py
```

## API

`build()` returns the table as a dict. Running the file writes it to
`data/king_wen_table.json`. Nothing imports this script — `traversal.py` reads the JSON.

An entry looks like this:

```json
"51": {"lines_bottom_to_top": [1,0,0,1,0,0], "binary_str": "100100", "decimal": 9}
```

Index 0 is the bottom line and `1` is yang, so the inner trigram sits in the low three
bits.

## How the table is built

1. Start from two hard-coded tables: the eight trigrams as bit triples, and all 64 King
   Wen numbers as their inner and outer trigram pair.
2. For each hexagram, join inner and outer into six lines, bottom first.
3. Record those lines three ways — as a list, as a binary string, as a decimal.
4. Check there are 64 entries and, more usefully, 64 *unique* patterns. A typo in the
   trigram table makes two hexagrams identical, and this is what catches it.
5. Spot-check six unambiguous hexagrams: 1 is `111111`, 2 is `000000`, 11 is `111000`,
   12 is `000111`, 63 is `101010`, 64 is `010101`.
6. Write the JSON.

`traversal.build_king_wen_lookup` reads the file back the other way round, as a map from
binary string to number.

## Example

Chapter 1's collision throw came out `1,0,0,1,0,0`. Looked up as `100100`, that is
hexagram 51. The succession throw came back as 38.

Both numbers are written to the chapter's log entry, and nothing reads them. The jump
distance is taken from the lines directly, not from the hexagram — this table records
which hexagram was thrown, it does not decide anything.

