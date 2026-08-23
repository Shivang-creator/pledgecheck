"""harness/run_baseline.py — Arm B (T-09): the steelmanned single-prompt baseline.

One model call per batch of 15 claims from the SAME frozen claim set every arm reads
(`corpus/claims.frozen.jsonl` — see `harness/freeze_corpus.py` / PLAN.md's architecture
rule: both arms, every rerun, and every table read this one file). No workflow, no code, no
rule pack: one prompt, asked once per batch, asking the model to do in a single shot
everything the Checkability Gate's five probes + rule pack do with code. This is Arm B in
the deliverable's comparison table.

The exact prompt text is regenerated into `docs/BASELINE-PROMPT.md` from the
`PROMPT_TEMPLATE` constant below every time this script runs (not hand-copied) — the two
can never drift, by construction, rather than by discipline.

Routes through `model.provider.call` (Gemini if it has quota, else Featherless, else
nothing) — not a single hardcoded provider — for the same reason `harness/run_gate.py`'s
N5 does: Gemini's free-tier daily quota is exhausted for the rest of tonight's build window
(`.crew/DECISIONS.md`, the T-06 amendment). The board's own row names "gemini-3.6-flash"
because it predates both that quota exhaustion and the Featherless provider added to route
around it; a literal single-provider reading of this task tonight would make Arm B
unrunnable, which is the opposite of "steelmanned."

Parse failures are recorded as `{"unparseable": true, "raw": <response, if any>}`, never
silently dropped — this IS Arm B's coverage number: a baseline that silently drops what it
can't parse would look more capable than it actually is, which is exactly the kind of
strawmanning this task explicitly forbids.

Run 3 times, `--run 1|2|3`, to `deliverables/runs/baseline.run{1,2,3}.json`. Unlike Arm A
(whose repeat-run identity check deliberately runs with the model OFF — see this task's
note in `.crew/DECISIONS.md` for why), Arm B's three runs are expected to genuinely differ
call to call: that variance, measured honestly, is part of the comparison the deliverable
makes (a single LLM call sampled independently three times vs. a deterministic rule
engine).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from model.provider import call  # noqa: E402

FROZEN_CLAIMS = ROOT / "corpus" / "claims.frozen.jsonl"
RUNS_DIR = ROOT / "deliverables" / "runs"
PROMPT_DOC = ROOT / "docs" / "BASELINE-PROMPT.md"
BATCH_SIZE = 15

PROMPT_TEMPLATE = """For each claim below, say whether it is checkable and which of these five elements it is missing: quantity, target year, baseline year, named standard, accountable party.

A claim is "checkable" only if it names all five: a specific quantity or amount, a specific target year to hit it by, a specific baseline year to measure the change against, a named external standard or framework, and a specific accountable party (a named role, team, or committee) responsible for delivering it.

Respond with ONLY a JSON object mapping each claim's id to an object of this exact shape, no other text, no markdown code fences:
{{"<claim_id>": {{"checkable": true or false, "missing": [zero or more of "quantity", "target_year", "baseline_year", "named_standard", "accountable_party"]}}}}

CLAIMS:
{claims_block}
"""


def _write_prompt_doc() -> None:
    PROMPT_DOC.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_DOC.write_text(
        "# Arm B baseline prompt (T-09)\n\n"
        "Regenerated verbatim from `PROMPT_TEMPLATE` in `harness/run_baseline.py` every "
        "time that script runs, so this document and the prompt actually sent can never "
        "drift apart. `{claims_block}` is the one substitution point: one JSON line per "
        'claim in the batch, `{"claim_id": ..., "text": ...}`, built by '
        "`_format_claims_block()` in the same file — nothing else about the text below "
        "changes between claims, batches, or runs.\n\n"
        "```\n" + PROMPT_TEMPLATE + "\n```\n"
    )


def _load_frozen_claims() -> list[dict]:
    if not FROZEN_CLAIMS.exists():
        print(
            f"error: {FROZEN_CLAIMS} does not exist yet — run harness/freeze_corpus.py "
            "first (T-07, the freeze). Arm B reads the identical frozen claim set Arm A "
            "does; there is no fallback claim source here on purpose.",
            file=sys.stderr,
        )
        sys.exit(1)
    claims = []
    for line in FROZEN_CLAIMS.read_text().splitlines():
        line = line.strip()
        if line:
            claims.append(json.loads(line))
    return claims


def _format_claims_block(claims: list[dict]) -> str:
    lines = [json.dumps({"claim_id": c["claim_id"], "text": c["text"]}) for c in claims]
    return "\n".join(lines)


def _strip_code_fence(response: str) -> str:
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()


def run_batch(claims: list[dict]) -> dict[str, dict]:
    """Returns {claim_id: {...}} for every input claim id: either the model's own
    checkable/missing verdict, or {"unparseable": true, "raw": ...} — every input claim_id
    is always a key in the result, coverage gaps are never a missing key."""
    prompt = PROMPT_TEMPLATE.format(claims_block=_format_claims_block(claims))
    response = call(prompt)
    if response is None:
        return {
            c["claim_id"]: {
                "unparseable": True,
                "raw": None,
                "reason": "model call failed (see MODEL FALLBACK log above)",
            }
            for c in claims
        }

    try:
        parsed = json.loads(_strip_code_fence(response))
    except json.JSONDecodeError as exc:
        print(f"BASELINE FALLBACK: batch response was not valid JSON ({exc})", file=sys.stderr)
        return {c["claim_id"]: {"unparseable": True, "raw": response} for c in claims}

    if not isinstance(parsed, dict):
        print("BASELINE FALLBACK: batch response was not a JSON object", file=sys.stderr)
        return {c["claim_id"]: {"unparseable": True, "raw": response} for c in claims}

    result: dict[str, dict] = {}
    for c in claims:
        value = parsed.get(c["claim_id"])
        if isinstance(value, dict) and "checkable" in value and "missing" in value:
            result[c["claim_id"]] = value
        else:
            result[c["claim_id"]] = {"unparseable": True, "raw": value}
    return result


def run_baseline_once(claims: list[dict]) -> dict:
    merged: dict[str, dict] = {}
    for start in range(0, len(claims), BATCH_SIZE):
        merged.update(run_batch(claims[start : start + BATCH_SIZE]))
    num_unparseable = sum(1 for v in merged.values() if v.get("unparseable"))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_claims": len(claims),
        "num_unparseable": num_unparseable,
        "coverage": (len(claims) - num_unparseable) / len(claims) if claims else 0.0,
        "results": merged,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run Arm B (the steelmanned single-prompt baseline).")
    parser.add_argument("--run", type=int, required=True, choices=(1, 2, 3), help="Which of the 3 repeat runs this is.")
    args = parser.parse_args(argv)

    _write_prompt_doc()

    claims = _load_frozen_claims()
    output = run_baseline_once(claims)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RUNS_DIR / f"baseline.run{args.run}.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    print(
        f"wrote {out_path} ({output['num_claims']} claims, "
        f"{output['num_unparseable']} unparseable, coverage={output['coverage']:.2%})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
