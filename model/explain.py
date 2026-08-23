"""model/explain.py — N5: batches of failing claims -> one-line rewrites (T-06).

N5 receives each claim's already-computed score and verdicts (to know which clauses are
missing) and may NEVER return a score, verdict, band, or count — it only writes prose.
Its output is merged into `deliverables/results.json` as a separate `explanation` field
on each claim, tagged `Generated`, attached by `harness/run_gate.py` strictly AFTER
`core/engine.py` has already scored the claim — never before, and never by anything this
module returns (this module has no way to influence a score even if it wanted to; it only
ever reads `claim["verdicts"]`, never writes to a claim dict itself).

Kill switch: if `model.provider.call` returns None for a batch (kill switch engaged, or
every registered provider genuinely failed — already logged loudly by `model/provider.py`
and each provider it tried), every claim in that batch gets the literal placeholder
`DISABLED_PLACEHOLDER` as its explanation. The same placeholder is used regardless of
*why* the call failed: from the explanation field's point of view, a kill-switched call
and a genuinely failed call are equally absent output. WHY it failed is preserved by each
provider's own loud stderr log, never dropped, just not duplicated into the deliverable
itself.
"""
from __future__ import annotations

import json
import sys

from model.provider import call

DISABLED_PLACEHOLDER = "[model layer disabled]"
BATCH_SIZE = 15

PROMPT_TEMPLATE = """You are helping a company make its climate pledges independently checkable.

For each claim below, its Checkability Gate verdict named which auditable elements are missing (quantity, target year, baseline year, named standard, or accountable party — identified by clause id). Write ONE short sentence per claim that rewrites it to add ONLY the missing element(s) — invent a plausible placeholder value in [square brackets] for anything not already in the claim text, and change nothing else about the claim. Do not judge the company, do not comment on sincerity, do not add caveats.

Respond with ONLY a JSON object mapping each claim_id to its one-line rewrite string, no other text, no markdown code fences.

CLAIMS:
{claims_block}
"""


def _missing_clauses(claim: dict) -> list[str]:
    return [v["clause_id"] for v in claim["verdicts"] if not v["present"]]


def _format_claims_block(claims: list[dict]) -> str:
    lines = [
        json.dumps({"claim_id": c["claim_id"], "text": c["text"], "missing": _missing_clauses(c)})
        for c in claims
    ]
    return "\n".join(lines)


def _strip_code_fence(response: str) -> str:
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()


def explain_batch(claims: list[dict], *, timeout: int = 60) -> dict[str, str]:
    """`claims`: already-scored claim dicts (score/verdicts already computed — this
    function only reads them, never mutates or returns them). Returns
    {claim_id: explanation_text}, one entry per input claim: DISABLED_PLACEHOLDER for
    every claim in the batch if the model call fails for any reason, so a caller never
    has to distinguish "no entry" from "disabled" — every input claim_id is always a key
    in the result."""
    if not claims:
        return {}

    response = call(PROMPT_TEMPLATE.format(claims_block=_format_claims_block(claims)), timeout=timeout)
    if response is None:
        return {c["claim_id"]: DISABLED_PLACEHOLDER for c in claims}

    try:
        parsed = json.loads(_strip_code_fence(response))
    except json.JSONDecodeError as exc:
        print(f"MODEL FALLBACK: N5 response was not valid JSON ({exc})", file=sys.stderr)
        return {c["claim_id"]: DISABLED_PLACEHOLDER for c in claims}

    if not isinstance(parsed, dict):
        print("MODEL FALLBACK: N5 response was not a JSON object", file=sys.stderr)
        return {c["claim_id"]: DISABLED_PLACEHOLDER for c in claims}

    result: dict[str, str] = {}
    for c in claims:
        value = parsed.get(c["claim_id"])
        result[c["claim_id"]] = value.strip() if isinstance(value, str) and value.strip() else DISABLED_PLACEHOLDER
    return result


def explain_claims(claims: list[dict], *, batch_size: int = BATCH_SIZE) -> dict[str, str]:
    """Batches `claims` (already-scored, already-filtered to failing ones by the caller)
    into groups of `batch_size` and calls `explain_batch` on each in turn. Returns the
    merged {claim_id: explanation_text} map across every batch."""
    merged: dict[str, str] = {}
    for start in range(0, len(claims), batch_size):
        merged.update(explain_batch(claims[start : start + batch_size]))
    return merged
