"""Normalisation, claim ids, band lookup, and roll-ups (T-04).

Pure functions over data. No model, no network. Allowed imports in core/: re, json,
hashlib, dataclasses, pathlib — nothing else, enforced by tests/test_purity.py.
"""
from __future__ import annotations

import hashlib
import re


def normalise(text: str) -> str:
    """Trim and collapse internal whitespace. Deterministic, idempotent."""
    return re.sub(r"\s+", " ", text).strip()


def claim_id(text: str) -> str:
    """Stable id for a claim: sha256 of the (normalised) text, first 12 hex chars."""
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()[:12]


def band_for_score(score: int, pack: dict) -> dict:
    """Look up the band whose [min, max] contains score. Raises if the pack defines none."""
    for band in pack.get("bands", []):
        if band["min"] <= score <= band["max"]:
            return band
    raise ValueError(f"no band in pack {pack.get('pack_id')!r} covers score {score}")


def per_document_rate(claims: list[dict]) -> float:
    """Mean of (score / max_score) across the given claims. 0.0 for an empty document."""
    if not claims:
        return 0.0
    ratios = [c["score"] / c["max_score"] for c in claims if c.get("max_score")]
    if not ratios:
        return 0.0
    return sum(ratios) / len(ratios)


def corpus_rollup(claims: list[dict], pack: dict) -> dict:
    """Corpus-level checkability rate and band distribution."""
    n = len(claims)
    if n == 0:
        return {
            "num_claims": 0,
            "mean_score": 0.0,
            "checkability_rate": 0.0,
            "band_distribution": {},
        }
    mean_score = sum(c["score"] for c in claims) / n
    checkability_rate = per_document_rate(claims)
    distribution: dict[str, int] = {}
    for c in claims:
        band = band_for_score(c["score"], pack)
        label = band["label"]
        distribution[label] = distribution.get(label, 0) + 1
    return {
        "num_claims": n,
        "mean_score": mean_score,
        "checkability_rate": checkability_rate,
        "band_distribution": distribution,
    }
