import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dcd.corpus import ingest

CORPUS = ROOT / "data" / "pg43629.txt"
JSONL = ROOT / "data" / "sentences.jsonl"
PREVIEW = ROOT / "data" / "sentences_preview.txt"


def main() -> None:
    records = ingest(str(CORPUS))

    with JSONL.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with PREVIEW.open("w", encoding="utf-8") as f:
        current = None
        for r in records:
            if r["story_id"] != current:
                current = r["story_id"]
                f.write(f"\n\n===== {current} =====\n\n")
            f.write(f"[{r['id']:>4}] {r['text']}\n")

    stories = {r["story_id"] for r in records}
    print(f"{len(records)} sentences across {len(stories)} stories")
    print(f"wrote {JSONL.relative_to(ROOT)}")
    print(f"wrote {PREVIEW.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
