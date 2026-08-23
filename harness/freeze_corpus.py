"""harness/freeze_corpus.py — T-07: THE FREEZE.

Runs `model.segment.segment_document` (N1) exactly once over every document in
`corpus/documents.json` and commits the combined output verbatim to
`corpus/claims.frozen.jsonl` — one JSON object per line:
`{claim_id, doc_id, org, provenance, text}`. `claim_id` is `core.scoring.claim_id(text)`
(sha256 of the normalised text, first 12 hex chars) — the same function `core/engine.py`
uses, so a claim's id never depends on which script computed it.

After this file is committed, nothing in the repo may re-segment: `harness/run_gate.py`
already treats `corpus/claims.frozen.jsonl` as its tier-1 claim source (see
`load_claims()`), and this script refuses to run again if the file already exists — the
freeze happens exactly once, on purpose, per PLAN.md's architecture rule ("both arms,
every rerun, and every table read this file").

Per document, if N1 fails (kill switch, or every registered provider genuinely failing —
logged loudly by `model/provider.py` and whichever providers it tried), this falls back to
the same naive sentence splitter `harness/run_gate.py`'s tier-2 path already uses, rather
than leaving the corpus half-frozen or silently treating a whole document as one giant
"claim". Falls back per document, independently — one document's model failure does not
block another document's real segmentation, and the per-document report printed at the end
says which source (N1 vs naive-split) produced each document's claims.

Usage: `python3 harness/freeze_corpus.py` — no run.sh subcommand, deliberately: this is a
one-shot operation, not a repeatable pipeline step like gate/baseline/compare.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.scoring import claim_id as compute_claim_id  # noqa: E402
from harness.run_gate import _naive_sentence_split  # noqa: E402
from model.segment import segment_document  # noqa: E402

DOCUMENTS = ROOT / "corpus" / "documents.json"
FROZEN = ROOT / "corpus" / "claims.frozen.jsonl"


def freeze() -> tuple[list[dict], list[tuple[str, str, int]]]:
    docs = json.loads(DOCUMENTS.read_text())
    frozen: list[dict] = []
    seen_ids: set[str] = set()
    per_doc_report: list[tuple[str, str, int]] = []

    for doc in docs:
        sentences = segment_document(doc["text"])
        source = "N1"
        if sentences is None:
            print(
                f"FREEZE FALLBACK: N1 failed for {doc['doc_id']} — using the naive sentence "
                "splitter instead (see the MODEL FALLBACK line(s) above for why N1 failed)",
                file=sys.stderr,
            )
            sentences = _naive_sentence_split(doc["text"])
            source = "naive-split"

        added = 0
        for sentence in sentences:
            cid = compute_claim_id(sentence)
            if cid in seen_ids:
                # Same normalised text already frozen from an earlier document (or a
                # duplicate within this one) — dropped, not silently duplicated under the
                # same id, and logged so it shows up in the per-document counts below.
                print(
                    f"FREEZE DEDUP: dropping duplicate claim_id {cid} seen again in "
                    f"{doc['doc_id']} (identical normalised text already frozen)",
                    file=sys.stderr,
                )
                continue
            seen_ids.add(cid)
            frozen.append(
                {
                    "claim_id": cid,
                    "doc_id": doc["doc_id"],
                    "org": doc.get("org"),
                    "provenance": doc.get("provenance"),
                    "text": sentence,
                }
            )
            added += 1
        per_doc_report.append((doc["doc_id"], source, added))

    return frozen, per_doc_report


def main() -> int:
    if FROZEN.exists():
        print(
            f"REFUSING: {FROZEN} already exists — the freeze happens exactly once. "
            "Delete it by hand first if this is deliberate.",
            file=sys.stderr,
        )
        return 1

    frozen, report = freeze()
    with FROZEN.open("w") as f:
        for c in frozen:
            f.write(json.dumps(c) + "\n")

    print(f"wrote {FROZEN} ({len(frozen)} claims across {len(report)} documents)")
    for doc_id, source, n in report:
        print(f"  {doc_id}: {n} claims ({source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
