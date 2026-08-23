"""Arm A entry point (T-04): run the deterministic Checkability Gate and write
deliverables/results.json.

Claim source, in priority order:
  1. corpus/claims.frozen.jsonl       — the real frozen claim set (T-07).
  2. corpus/documents.json            — naive sentence split, per T-04's spec, until T-07 lands.
  3. an embedded bring-up fixture     — so `./run.sh gate` is runnable tonight, before T-02/T-07
                                         land. Clearly tagged "Simulated" / doc_id "fallback-0",
                                         never confused with real corpus data.

This file is wiring, not domain logic: no rule-pack literal lives here, only the fallback
chain and the JSON shape. All real decisions are made by core/engine.py against
rules/*.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.engine import evaluate, load_pack  # noqa: E402
from core.scoring import claim_id as compute_claim_id  # noqa: E402
from core.scoring import corpus_rollup, per_document_rate  # noqa: E402
from model.explain import DISABLED_PLACEHOLDER, explain_claims  # noqa: E402
from model import provider as model_provider  # noqa: E402

FROZEN_CLAIMS = ROOT / "corpus" / "claims.frozen.jsonl"
DOCUMENTS = ROOT / "corpus" / "documents.json"
RESULTS = ROOT / "deliverables" / "results.json"
DEFAULT_PACK = ROOT / "rules" / "climate.v1.json"

# Tier 3 fallback: only used if neither the frozen claim set nor a fetched corpus exists
# yet tonight. Explicitly a fixture — provenance "Simulated", org names an invented company.
FALLBACK_DOCUMENTS = [
    {
        "doc_id": "fallback-0",
        "org": "Fixture Corp (T-04 bring-up fixture, not the real corpus)",
        "title": "Bring-up fixture",
        "source_url": None,
        "fetched_at_utc": None,
        "provenance": "Simulated",
        "text": (
            "We will cut Scope 1 and Scope 2 emissions by 50% by 2030, compared to a 2019 "
            "baseline, in line with the GHG Protocol, overseen by our Audit Committee. "
            "We are committed to a greener future for everyone. "
            "The Chief Sustainability Officer will oversee a 30% reduction in water use by "
            "2028 against a 2020 baseline. "
            "We aim to do better every year. "
            "Our target is to halve emissions by the end of the decade."
        ),
    }
]


def _naive_sentence_split(text: str) -> list[str]:
    """Regex sentence splitter used only as the tier-2/tier-3 fallback before N1 (T-06/T-07)
    lands. Not a substitute for real segmentation — it is intentionally crude."""
    pieces = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in pieces if p.strip()]


def _load_frozen_claims() -> list[dict] | None:
    if not FROZEN_CLAIMS.exists():
        return None
    claims = []
    for line in FROZEN_CLAIMS.read_text().splitlines():
        line = line.strip()
        if line:
            claims.append(json.loads(line))
    return claims or None


def _load_from_documents() -> list[dict] | None:
    if not DOCUMENTS.exists():
        return None
    docs = json.loads(DOCUMENTS.read_text())
    return _claims_from_documents(docs)


def _claims_from_documents(docs: list[dict]) -> list[dict]:
    claims = []
    for doc in docs:
        for sentence in _naive_sentence_split(doc["text"]):
            claims.append(
                {
                    "claim_id": compute_claim_id(sentence),
                    "doc_id": doc["doc_id"],
                    "org": doc.get("org"),
                    "provenance": doc.get("provenance"),
                    "text": sentence,
                }
            )
    return claims


def load_claims() -> tuple[list[dict], str]:
    """Returns (claims, source_tier) trying frozen -> documents -> embedded fallback."""
    claims = _load_frozen_claims()
    if claims is not None:
        return claims, "frozen"
    claims = _load_from_documents()
    if claims is not None:
        return claims, "documents.json"
    return _claims_from_documents(FALLBACK_DOCUMENTS), "embedded-fallback"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the Checkability Gate (Arm A).")
    parser.add_argument("--rules", default=str(DEFAULT_PACK), help="Path to a rule pack JSON.")
    parser.add_argument(
        "--out",
        default=str(RESULTS),
        help="Where to write the result JSON (default: deliverables/results.json). "
        "T-09 uses this to write the 3 repeat runs to deliverables/runs/gate.run{1,2,3}.json "
        "without disturbing the main deliverable.",
    )
    args = parser.parse_args(argv)
    out_path = Path(args.out)

    pack = load_pack(args.rules)
    claims, source_tier = load_claims()

    evaluated = []
    for claim in claims:
        result = evaluate(claim, pack)
        # carry provenance/document fields through so downstream tooling can group by doc
        for passthrough in ("doc_id", "org", "provenance"):
            if passthrough in claim:
                result[passthrough] = claim[passthrough]
        evaluated.append(result)

    documents: dict[str, list[dict]] = {}
    for c in evaluated:
        doc_id = c.get("doc_id", "unknown")
        documents.setdefault(doc_id, []).append(c)

    document_summaries = []
    for doc_id, doc_claims in documents.items():
        document_summaries.append(
            {
                "doc_id": doc_id,
                "org": doc_claims[0].get("org"),
                "provenance": doc_claims[0].get("provenance"),
                "num_claims": len(doc_claims),
                "checkability_rate": per_document_rate(doc_claims),
            }
        )

    # N5 (T-06/T-integrator): for every claim the Gate could not fully verify, ask the
    # model for the one-line rewrite that would make it checkable. explain_claims() owns
    # the entire kill-switch decision internally (PLEDGECHECK_NO_MODEL, every provider's
    # own key/config, and any real network/API failure from EVERY registered provider all
    # collapse to the same DISABLED_PLACEHOLDER, logged loudly by model/provider.py and
    # each provider it tried in turn) — nothing here re-implements or duplicates that
    # check. Scores and verdicts above this line are already final; nothing below it may
    # touch them. reset_providers_used() first so a previous run/test in this same
    # process (e.g. tests/test_killswitch.py calling run_gate.main() repeatedly) never
    # leaks provenance into this run's model_provider field.
    model_provider.reset_providers_used()
    failing_claims = [c for c in evaluated if c["score"] < c["max_score"]]
    explanations = explain_claims(failing_claims) if failing_claims else {}
    for c in evaluated:
        if c["claim_id"] in explanations:
            c["explanation"] = explanations[c["claim_id"]]

    # model_layer reports what actually happened this run, not merely what was configured:
    # "on" only if at least one explanation is real generated prose rather than the
    # disabled placeholder. A configured-but-failing key (bad key, network down, retired
    # model id) is honestly reported as "off", the same as an explicit kill switch — a
    # dead API must degrade the label, never claim success it didn't have.
    model_layer = "on" if any(v != DISABLED_PLACEHOLDER for v in explanations.values()) else "off"

    # model_provider names WHICH provider(s) actually served this run's explanations —
    # the fact a writeup needs to state truthfully. "none" covers the kill switch, an
    # absent/bad key on every provider, and every provider genuinely failing, all alike;
    # multiple names joined with "+" cover the (unlikely tonight, since Gemini's failure
    # mode is a uniform-for-the-process daily quota) case of different batches being
    # served by different providers within one run. See model/provider.py's docstring for
    # what this signal does and doesn't promise (call-level, not claim-level, attribution).
    served_by = sorted(model_provider.providers_used)
    model_provider_field = "+".join(served_by) if served_by else "none"

    output = {
        "pack_version": pack["version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_layer": model_layer,
        "model_provider": model_provider_field,
        "claim_source": source_tier,
        "claims": evaluated,
        "documents": document_summaries,
        "corpus": corpus_rollup(evaluated, pack),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {out_path} ({len(evaluated)} claims, source={source_tier})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
