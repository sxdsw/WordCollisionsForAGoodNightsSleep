"""Render generated chapters to LaTeX, for a PDF.

    python scripts/render_book.py --chapters 40 --seed 1
    pdflatex -output-directory build build/book.tex

Renders the CLAUSE WALK only. The splice pipeline is kept and still
runs, but produces no output for reading (decided 2026-09-16,
TECH_SPEC §1) — so there is deliberately no way to render it from here.

Deliberately minimal — NEEDS_INPUT item 8 records that no reader-facing
chapter format is specified, so this is a working default, not a design.
It is the only place in the repo that decides how a chapter LOOKS; the
audit record (§7, §10) stays the source of truth for what it IS, and is
written alongside as JSONL.
"""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/attic/ -> project root
sys.path.insert(0, str(ROOT / "src"))

from dcd.clause import build_clause_index  # noqa: E402
from dcd.clause_walk import run_chapter as clause_chapter  # noqa: E402
from dcd.traversal import build_king_wen_lookup  # noqa: E402
from dcd.word_selection import tokenize_sequence  # noqa: E402

PREAMBLE = r"""\documentclass[11pt,a5paper]{book}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{microtype}
\usepackage[margin=2.2cm]{geometry}
\usepackage{fancyhdr}
\linespread{1.15}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.8em}
\pagestyle{fancy}\fancyhf{}\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}
\title{The Dream Collision Dictionary}
\author{}\date{}
\begin{document}
\maketitle
\thispagestyle{empty}
\clearpage
"""

# LaTeX-significant characters. The corpus is Victorian English plus
# transliteration, so this is short; & and % do occur.
_ESCAPES = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}


def latex_escape(text: str) -> str:
    return "".join(_ESCAPES.get(ch, ch) for ch in text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", type=int, default=20)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", default=str(ROOT / "build"))
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    sentences = [
        json.loads(line)
        for line in (ROOT / "data" / "sentences.jsonl")
        .read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    pool = json.loads((ROOT / "data" / "word_pool.json").read_text(encoding="utf-8"))
    nouns = {w.lower() for w in pool}
    sequence = tokenize_sequence(" ".join(s["text"] for s in sentences))
    king_wen = build_king_wen_lookup(str(ROOT / "data" / "king_wen_table.json"))
    rng = random.Random(args.seed)

    clauses, anchors = build_clause_index(sentences)

    body, records = [], []
    for chapter_id in range(1, args.chapters + 1):
        record = clause_chapter(
            chapter_id, sentences, clauses, anchors, sorted(nouns),
            king_wen, sequence, nouns, rng,
        )
        text = record["output_text"]
        records.append(record)
        body.append(
            "\\chapter*{\\normalfont\\Large "
            f"{chapter_id}"
            "}\n"
            f"{latex_escape(text)}\n\\clearpage\n"
        )

    tex_path = out_dir / "book.tex"
    tex_path.write_text(PREAMBLE + "\n".join(body) + "\n\\end{document}\n",
                        encoding="utf-8")
    log_path = out_dir / "book_log.jsonl"
    with log_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"{args.chapters} clause-walk chapters")
    print(f"wrote {tex_path}")
    print(f"wrote {log_path}   (§7/§10 audit record, one line per chapter)")
    print(f"\n  pdflatex -output-directory {out_dir} {tex_path}")


if __name__ == "__main__":
    main()
