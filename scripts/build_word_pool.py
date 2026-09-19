import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dcd.corpus import ingest  # noqa: E402
from dcd.word_selection import (  # noqa: E402
    build_word_pool,
    filter_by_position,
    noun_position_ratios,
    save_word_pool,
)

DEFAULT_CORPUS = ROOT / "data" / "pg43629.txt"
OUT_PATH = ROOT / "data" / "word_pool.json"


def main(corpus_path: str, positional: bool, out_path: Path) -> None:
    sentences = ingest(corpus_path)
    cleaned_text = "\n".join(s["text"] for s in sentences)
    pool = build_word_pool(cleaned_text)

    if positional:
        kept, cut = filter_by_position(pool, cleaned_text)
        ratios = noun_position_ratios(pool, cleaned_text)
        print(f"{len(sentences)} sentences -> {len(pool)} nouns from WordNet")
        print(f"positional filter: kept {len(kept)}, cut {len(cut)}\n")
        print(f"{'word':<16}{'occurs':>7}{'noun-pos':>10}")
        for word in sorted(cut, key=lambda w: -ratios[w.lower()][1]):
            head, total = ratios[word.lower()]
            print(f"{word:<16}{total:>7}{100 * head / total:>9.1f}%")
        pool = kept

    save_word_pool(pool, str(out_path))
    print(f"\n{len(pool)} noun tokens written to {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build data/word_pool.json (§5.3). Static file — run "
        "once and commit; do not regenerate per run."
    )
    parser.add_argument("corpus", nargs="?", default=str(DEFAULT_CORPUS))
    parser.add_argument(
        "--no-positional",
        dest="positional",
        action="store_false",
        help="skip the corpus-evidence noun filter and emit the raw "
        "WordNet pool (what data/word_pool_wordnet_only.json holds)",
    )
    parser.set_defaults(positional=True)
    parser.add_argument(
        "--out",
        default=None,
        help="output path; defaults to data/word_pool.json, or "
        "data/word_pool_positional.json with --positional, so the live "
        "pool is never overwritten by accident",
    )
    args = parser.parse_args()
    default_out = (
        ROOT / "data"
        / ("word_pool.json" if args.positional else "word_pool_wordnet_only.json")
    )
    main(args.corpus, args.positional, Path(args.out) if args.out else default_out)
