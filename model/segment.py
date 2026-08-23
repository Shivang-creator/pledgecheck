"""model/segment.py — N1: document text -> JSON array of atomic claim sentences (T-06).

This is the function T-07 ("the freeze") calls exactly once, over each of the 8 corpus
documents, committing the combined output verbatim to `corpus/claims.frozen.jsonl`.
Nothing else in the repo may call this after that file exists — every arm and every rerun
reads the frozen file, per PLAN.md's architecture rule. This module is therefore never
imported by `harness/run_gate.py`.

Kill switch: if `model.provider.call` returns None (every provider's kill switch
engaged, or every provider genuinely failed — either way, already logged loudly by
`model/provider.py` and each provider module it tried), `segment_document` returns
None too, so T-07's own driver script fails loudly and falls back to the naive splitter
`harness/run_gate.py` already documents, rather than freezing a corpus nobody actually
generated with a model.
"""
from __future__ import annotations

import json
import sys

from model.provider import call

PROMPT_TEMPLATE = """You are extracting individual claim sentences from a corporate climate-pledge document for an auditability tool.

Split the document below into atomic claim sentences: each output item should be one self-contained sentence or clause that makes a single checkable-or-not assertion (a commitment, a target, a statistic, or a statement of intent). Do not merge multiple claims into one item. Do not summarise, paraphrase, or invent text — every item must be verbatim text copied from the document. Skip pure boilerplate (headers, captions, navigation) that makes no claim at all.

Respond with ONLY a JSON array of strings, no other text, no markdown code fences.

DOCUMENT:
{text}
"""


def segment_document(text: str, *, timeout: int = 60) -> list[str] | None:
    """Returns a list of verbatim claim-sentence strings extracted from `text`, or None
    on any model failure (kill switch or a real failure — model.gemini.call already
    logged the reason loudly; this function adds its own loud log only for failures that
    happen after a response came back, e.g. a response that isn't valid JSON)."""
    response = call(PROMPT_TEMPLATE.format(text=text), timeout=timeout)
    if response is None:
        return None

    cleaned = _strip_code_fence(response)

    try:
        claims = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"MODEL FALLBACK: N1 response was not valid JSON ({exc})", file=sys.stderr)
        return None

    if not isinstance(claims, list) or not all(isinstance(c, str) for c in claims):
        print("MODEL FALLBACK: N1 response was not a JSON array of strings", file=sys.stderr)
        return None

    return [c.strip() for c in claims if c.strip()]


def _strip_code_fence(response: str) -> str:
    """Models sometimes wrap JSON in ```json ... ``` even when told not to. Strip it if
    present; leave the text alone otherwise."""
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()
