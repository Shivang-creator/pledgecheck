# Arm B baseline prompt (T-09)

Regenerated verbatim from `PROMPT_TEMPLATE` in `harness/run_baseline.py` every time that script runs, so this document and the prompt actually sent can never drift apart. `{claims_block}` is the one substitution point: one JSON line per claim in the batch, `{"claim_id": ..., "text": ...}`, built by `_format_claims_block()` in the same file — nothing else about the text below changes between claims, batches, or runs.

```
For each claim below, say whether it is checkable and which of these five elements it is missing: quantity, target year, baseline year, named standard, accountable party.

A claim is "checkable" only if it names all five: a specific quantity or amount, a specific target year to hit it by, a specific baseline year to measure the change against, a named external standard or framework, and a specific accountable party (a named role, team, or committee) responsible for delivering it.

Respond with ONLY a JSON object mapping each claim's id to an object of this exact shape, no other text, no markdown code fences:
{{"<claim_id>": {{"checkable": true or false, "missing": [zero or more of "quantity", "target_year", "baseline_year", "named_standard", "accountable_party"]}}}}

CLAIMS:
{claims_block}

```
