"""Rule-pack loader and gate evaluation (T-04).

The engine evaluates; the data (rules/*.json) decides. No model, no network. Allowed
imports in core/: re, json, hashlib, dataclasses, pathlib — nothing else, enforced by
tests/test_purity.py.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.probes import get_probe
from core.scoring import claim_id as _claim_id
from core.scoring import normalise


def load_pack(path: str | Path) -> dict:
    """Load and lightly validate a rule pack. Raises on missing required keys."""
    data = json.loads(Path(path).read_text())
    for key in ("pack_id", "version", "probes", "bands", "lexicons"):
        if key not in data:
            raise ValueError(f"rule pack {path} is missing required key {key!r}")
    if not data["probes"]:
        raise ValueError(f"rule pack {path} defines zero probes")
    seen_ids = set()
    for spec in data["probes"]:
        if spec["clause_id"] in seen_ids:
            raise ValueError(f"duplicate clause_id {spec['clause_id']!r} in {path}")
        seen_ids.add(spec["clause_id"])
        if not spec.get("citation", "").strip():
            raise ValueError(f"clause {spec['clause_id']!r} in {path} has no citation")
    return data


def evaluate(claim: dict, pack: dict) -> dict:
    """Run every probe in the pack, in pack order, against one claim.

    `claim` needs at least a `text` key; `claim_id` is computed from the text if absent.
    Returns {claim_id, text, score, max_score, verdicts, pack_version}. Verdict order
    always follows pack order, so two identical inputs give identical output.
    """
    text = claim["text"]
    cid = claim.get("claim_id") or _claim_id(text)

    verdicts = []
    score = 0
    max_score = 0
    for spec in pack["probes"]:
        fn = get_probe(spec["probe"])
        result = fn(text, spec.get("params", {}), pack["lexicons"])
        weight = spec.get("weight", 1)
        max_score += weight
        if result.present:
            score += weight
        verdicts.append(
            {
                "clause_id": spec["clause_id"],
                "probe": spec["probe"],
                "present": result.present,
                "span": list(result.span) if result.span else None,
                "matched": result.matched,
                "citation": spec["citation"],
            }
        )

    return {
        "claim_id": cid,
        "text": normalise(text),
        "score": score,
        "max_score": max_score,
        "verdicts": verdicts,
        "pack_version": pack["version"],
    }
