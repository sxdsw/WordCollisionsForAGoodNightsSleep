"""
Run the script for a full render that is consistent:
    python3 scripts/render_dictionary.py --word-a sleep --seed 1

word_A starts at `sleep`. The cast selects word_B, the clause walk runs
until it stops, the chapter is written out, and that word_B becomes the
next chapter's word_A. The cycle continues until the mechanism exhausts
itself — the first time the landing scan has to travel further than any
cast could jump.

the .pdf is formated on A4, 30mm margins. Each Chapter is the result of two 
word interactions. The chapter heading are the two words, and the body 
is the text genereated by the dream machine.
"""

import argparse
import html
import json
import random
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dcd.chain import run_chain  
from dcd.clause import build_clause_index  
from dcd.traversal import build_king_wen_lookup  
from dcd.word_selection import tokenize_sequence 

CHROME_DEFAULT = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

BOOK_TITLE = "Word Collisions for a Good Night’s Sleep"

STYLE = """
:root {
  --page-size: A4;
  --page-margin: 30mm;        /* text block: 150mm wide, as measured */
  --body-face: "Times New Roman", Times, "Liberation Serif", serif;
  --body-size: 12pt;
  --body-leading: 1.5;
  --heading-size: 34pt;
  --heading-word-gap: 0;      /* EXTRA space between the two words, on top
                                 of the normal one. 0 = a single space, so
                                 the pair reads as one block (chosen
                                 2026-09-18). The reference images had a
                                 14.2mm gap, which read as two separate
                                 entries; 0.95em restores it. */
  --space-above-heading: 25mm;
  --space-below-heading: 27mm;
}

@page {
  size: var(--page-size);
  margin: var(--page-margin);
  /* no page numbers, no running heads — the reference pages carry none */
}

html, body { margin: 0; padding: 0; background: #fff; color: #000; }

body {
  font-family: var(--body-face);
  font-size: var(--body-size);
  line-height: var(--body-leading);
  text-align: justify;
  text-justify: inter-word;
  hyphens: none;
  -webkit-hyphens: none;
  orphans: 2;
  widows: 2;
}

.chapter { break-before: page; page-break-before: always; }
.chapter:first-of-type { break-before: auto; page-break-before: auto; }

.chapter h1 {
  font-family: var(--body-face);
  font-size: var(--heading-size);
  font-weight: normal;
  line-height: 1.1;
  text-align: left;
  /* padding, not margin: a top margin collapses at the start of a page box */
  padding-top: var(--space-above-heading);
  margin: 0 0 var(--space-below-heading) 0;
  word-spacing: var(--heading-word-gap);
  break-after: avoid;
  page-break-after: avoid;
}

/* The chapter is one continuous block of clauses, never broken into
   paragraphs — overflow simply continues on the next page with no
   heading, as in the second reference image. */
.chapter p { margin: 0; text-indent: 0; }

/* Front and back matter. Both take the chapter's heading, so they sit
   inside the book's own visual system rather than beside it. The
   preface, unlike a chapter, is ordinary prose and keeps its
   paragraphs. */
.front p + p { margin-top: 0.9em; }
/* The title page is the heading and nothing else. */
.titlepage h1 { margin-bottom: 0; }
/* The closing page carries two facts and no heading, so its single line
   sits where a chapter's body would begin — on the same grid as every
   other page rather than floating. */
.colophon { text-align: left; }
.colophon p { padding-top: calc(var(--space-above-heading)
                                + var(--space-below-heading)); }
"""

DOCUMENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{style}</style>
</head>
<body>
{body}</body>
</html>
"""


def title_case(word: str) -> str:
    """Upper-case the first letter and leave the rest alone.

    NOT str.capitalize(), which lower-cases the tail: the corpus supplies
    tokens like `Chang` and `Ch'ang-ch'ing` and they must survive intact.
    """
    return word[:1].upper() + word[1:]


def title_page_html(title: str) -> str:
    """The title page — the title alone, in the chapter heading's own
    type and position, so the book opens inside its own visual system
    rather than beside it. Same reasoning as the preface heading.
    """
    return (
        '<section class="chapter titlepage">\n'
        f"<h1>{html.escape(title)}</h1>\n</section>\n"
    )


def load_preface(path: Path) -> tuple[str, list[str]]:
    """Read a preface file: paragraphs separated by blank lines.

    If the first line is a Markdown-style `# Heading`, it becomes the
    heading and is dropped from the body; otherwise the heading is
    "Introduction" (renamed from "Preface" 2026-09-18). Nothing else is
    interpreted — this is the artist's own text and it is set exactly as
    written.
    """
    raw = path.read_text(encoding="utf-8").strip()
    title = "Introduction"
    if raw.startswith("# "):
        first, _, rest = raw.partition("\n")
        title, raw = first[2:].strip(), rest.strip()
    paragraphs = [" ".join(block.split()) for block in raw.split("\n\n")]
    return title, [p for p in paragraphs if p]


def preface_html(title: str, paragraphs: list[str]) -> str:
    body = "\n".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    return (
        '<section class="chapter front">\n'
        f"<h1>{html.escape(title)}</h1>\n{body}\n</section>\n"
    )


def colophon_html(run: dict, terminal: dict | None, chapters: list[dict]) -> str:
    """The closing page: the chapter count and the timestamp, and nothing
    else (set by the artist 2026-09-18).

    An earlier version printed the seed, the corpus, where the mechanism
    stopped and the command that reproduces the book. All of that is
    still written to the run record on the first line of the log — it was
    cut from the page, not from the record.
    """
    stamp = datetime.fromisoformat(run["generated_at"]).strftime("%Y-%m-%d %H:%M")
    line = f"{run['chapters']:,} chapters, {stamp}"
    return (
        '<section class="chapter colophon">\n'
        f'<p>{html.escape(line)}</p>\n</section>\n'
    )


def chapter_html(record: dict) -> str:
    heading = "{} {}".format(
        html.escape(title_case(record["word_a"])),
        html.escape(title_case(record["word_b"])),
    )
    return (
        '<section class="chapter">\n'
        f"<h1>{heading}</h1>\n"
        f"<p>{html.escape(record['output_text'])}</p>\n"
        "</section>\n"
    )


def to_pdf(chrome: str, html_path: Path, pdf_path: Path, timeout: int) -> None:
    """Print the HTML to PDF with headless Chrome.

    Chrome 153 has no old headless mode left, and the new one does not
    exit after --print-to-pdf: the PDF is written and the process simply
    stays up. Nor can its output be captured through a pipe — its helper
    processes inherit the pipe and hold it open, so the parent waits on
    an EOF that never comes.

    So: launch it, watch the PDF file until it stops growing, then stop
    the process. A throwaway --user-data-dir keeps all of this out of the
    way of any Chrome the artist already has running.
    """
    pdf_path.unlink(missing_ok=True)   # never mistake a stale PDF for this run
    with tempfile.TemporaryDirectory(prefix="dcd-chrome-") as profile:
        log = Path(profile) / "chrome.log"
        with log.open("wb") as sink:
            proc = subprocess.Popen(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions",
                    f"--user-data-dir={profile}",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}",
                    html_path.as_uri(),
                ],
                stdout=sink,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )
            try:
                _wait_for_pdf(proc, pdf_path, timeout)
            finally:
                _stop(proc)
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            tail = log.read_text(encoding="utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"Chrome wrote no PDF.\n{tail}")


def _wait_for_pdf(proc, pdf_path: Path, timeout: int) -> None:
    """Return once the PDF has stopped growing, or Chrome has exited."""
    deadline = time.monotonic() + timeout
    last, stable = -1, 0
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return                       # exited by itself: nothing to wait for
        size = pdf_path.stat().st_size if pdf_path.exists() else -1
        if size > 0 and size == last:
            stable += 1
            if stable >= 4:              # ~2s unchanged — the write is finished
                return
        else:
            stable = 0
        last = size
        time.sleep(0.5)
    raise TimeoutError(
        f"Chrome did not finish the PDF within {timeout}s "
        f"(--pdf-timeout raises it)"
    )


def _stop(proc) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--word-a", default="sleep",
                        help="the word the book starts from (default: sleep). "
                             "It must occur in the corpus.")
    parser.add_argument("--seed", type=int, default=None,
                        help="fixes the casts, so the same seed always yields "
                             "the same book. Omit for a different book every run.")
    parser.add_argument("--out", default=str(ROOT / "build"),
                        help="output directory (default: build/)")
    parser.add_argument("--max-chapters", type=int, default=0,
                        help="0 = run until the mechanism stops; a positive "
                             "number caps it for a test render, which writes "
                             "dictionary_sampleN.* so a full render's files "
                             "are never overwritten")
    parser.add_argument("--tidy", action="store_true",
                        help="apply the §8 join conventions — capitalise after "
                             "a full stop, and supply one where a clause ends "
                             "unpunctuated before a capital. Off by default; "
                             "writes dictionary_tidy.* so both books survive "
                             "side by side.")
    parser.add_argument("--title", default=BOOK_TITLE,
                        help=f"the book's title, set on a title page and used "
                             f"as the PDF's document title "
                             f"(default: {BOOK_TITLE!r})")
    parser.add_argument("--no-title-page", action="store_true",
                        help="omit the title page (the title is still the "
                             "PDF's document title)")
    parser.add_argument("--introduction", "--preface", dest="preface",
                        default=None,
                        help="a text file to set before chapter one. If "
                             "omitted, introduction.md/.txt or preface.md/.txt "
                             "in the project root is used when it exists. A "
                             "leading '# Title' line becomes the heading, "
                             "otherwise it is 'Introduction'; blank lines "
                             "separate paragraphs.")
    parser.add_argument("--no-colophon", action="store_true",
                        help="omit the closing page that records the seed, "
                             "the counts and where the book stopped")
    parser.add_argument("--no-pdf", action="store_true",
                        help="write the HTML and the log, skip Chrome")
    parser.add_argument("--chrome", default=CHROME_DEFAULT,
                        help="path to Chrome, if it is not in the usual place")
    parser.add_argument("--pdf-timeout", type=int, default=900,
                        help="seconds to wait for Chrome to finish the PDF "
                             "(default: 900)")
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
    clauses, anchors = build_clause_index(sentences)

    # An unseeded run used to be unreproducible: random.Random(None) takes
    # its seed from the OS and never says what it was, so the book could
    # not be made again. Draw one explicitly instead, and record it. The
    # audit log is the source of truth for what a chapter IS (§7), and a
    # book it cannot regenerate is not a record of anything.
    seed = random.randrange(2**32) if args.seed is None else args.seed
    rng = random.Random(seed)

    # run_chain raises for this too, but a bare traceback is a poor
    # answer to a typo. Its own guard stays as the library-level check.
    if not any(t.lower() == args.word_a.lower() for t in sequence):
        sys.exit(f"{args.word_a!r} does not occur in the corpus — "
                 "pick another starting word.")

    # A capped run is a sample, not the book, and must never overwrite a
    # full render's files — that is easy to do by accident and costs the
    # log the book was audited from.
    stem = "dictionary" + ("_tidy" if args.tidy else "")
    if args.max_chapters:
        stem += f"_sample{args.max_chapters}"
    body, records, words = [], [], 0
    terminal = None
    for record in run_chain(
        args.word_a, clauses, anchors, king_wen, sequence, nouns, rng,
        max_chapters=args.max_chapters or None, tidy=args.tidy,
    ):
        records.append(record)
        if record.get("terminal"):
            terminal = record
            continue
        body.append(chapter_html(record))
        words += record["word_count"]

    chapters = [r for r in records if not r.get("terminal")]

    run = {
        "run": True,
        "seed": seed,
        "start_word": args.word_a,
        "tidied": args.tidy,
        "chapters": len(chapters),
        "words": words,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "corpus": "data/pg43629.txt",
        "sentences": len(sentences),
        "word_pool": len(pool),
    }

    front = []
    if not args.no_title_page:
        front.append(title_page_html(args.title))

    preface_path = Path(args.preface) if args.preface else next(
        (c for c in (ROOT / "introduction.md", ROOT / "introduction.txt",
                     ROOT / "preface.md", ROOT / "preface.txt") if c.exists()),
        None,
    )
    preface_note = "none"
    if preface_path is not None:
        if not preface_path.exists():
            sys.exit(f"no preface file at {preface_path}")
        title, paragraphs = load_preface(preface_path)
        if paragraphs:
            front.append(preface_html(title, paragraphs))
            preface_note = (f"{preface_path.name} \u2014 {title!r}, "
                            f"{len(paragraphs)} paragraph"
                            f"{'s' if len(paragraphs) != 1 else ''}")
    body[:0] = front
    if not args.no_colophon:
        body.append(colophon_html(run, terminal, chapters))
        run["colophon"] = True
    run["title"] = args.title

    html_path = out_dir / f"{stem}.html"
    html_path.write_text(
        DOCUMENT.format(
            title=args.title,
            style=STYLE,
            body="".join(body),
        ),
        encoding="utf-8",
    )
    log_path = out_dir / f"{stem}_log.jsonl"
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(run, ensure_ascii=False) + "\n")
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"{len(chapters)} chapters, {words:,} words"
          + ("   [--tidy: §8 join conventions applied]" if args.tidy else ""))
    print(f"  seed   {seed}"
          + ("" if args.seed is not None else "   (drawn for this run — "
             "pass --seed to make this book again)"))
    if chapters:
        first, last = chapters[0], chapters[-1]
        print(f"  opens  {title_case(first['word_a'])} {title_case(first['word_b'])}")
        print(f"  closes {title_case(last['word_a'])} {title_case(last['word_b'])}")
    if terminal:
        print(f"  stopped: scan of {terminal['scan_distance']} words exceeded the "
              f"{terminal['max_cast_reach']}-word cast reach at "
              f"{terminal['word_a']!r} (would have been "
              f"{terminal['would_have_been']!r})")
    else:
        print(f"  stopped: --max-chapters {args.max_chapters} reached")
    print(f"  title   {args.title!r}"
          + ("" if not args.no_title_page else "   (no title page)"))
    print(f"  intro   {preface_note}")
    print(f"wrote {html_path}")
    print(f"wrote {log_path}   (§7/§10 audit record, one line per chapter)")

    pdf_path = out_dir / f"{stem}.pdf"

    if args.no_pdf:
        print(f"\n  --no-pdf: print it yourself with\n"
              f"  '{args.chrome}' --headless=new --print-to-pdf="
              f"{pdf_path} {html_path.as_uri()}")
        return

    if not Path(args.chrome).exists() and not shutil.which(args.chrome):
        sys.exit(f"Chrome not found at {args.chrome!r} — pass --chrome PATH, "
                 f"or --no-pdf to stop at the HTML.")
    print(f"\nprinting {len(chapters)} chapters to PDF ...")
    to_pdf(args.chrome, html_path, pdf_path, args.pdf_timeout)
    size = pdf_path.stat().st_size
    print(f"wrote {pdf_path}   ({size / 1_048_576:.1f} MB)")


if __name__ == "__main__":
    main()
