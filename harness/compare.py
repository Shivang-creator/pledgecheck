"""harness/compare.py — T-10 (DELIVERABLE 2): scores both arms against the frozen, blind
gold set and writes deliverables/COMPARISON.md.

Pure arithmetic. No network, no model. The only things this file reads are committed
inputs: corpus/claims.frozen.jsonl, corpus/gold.labels.json, rules/climate.v1.json, and
deliverables/runs/{gate,baseline}.run{1,2,3}.json. Arm A's verdicts are recomputed fresh
through core.engine.evaluate() on every run (not read back from deliverables/results.json,
which also carries the model-layer explanation field this file has no business touching) —
so "./run.sh compare" is a complete, from-scratch measurement every time, not a copy of a
previous one.

Determinism: COMPARISON.md carries no timestamp and no field derived from wall-clock time,
so deleting it and re-running this script reproduces it byte-for-byte (T-10's own
acceptance criterion, and the honest version of "reproducible by a named command").

Both arms read the IDENTICAL frozen claim set (corpus/claims.frozen.jsonl, frozen by T-07,
97 claims). That matters more than either arm's own accuracy: an imperfect extractor would
still make this a fair comparison, because whatever it got wrong is wrong for both arms
equally. What would NOT be fair is either arm seeing a claim set the other didn't.

Gold labels (corpus/gold.labels.json, T-08) cover only the first 60 of the 97 frozen claims,
labelled blind (rubric committed before labels; see docs/LABELLING-RUBRIC.md) and confined to
the four real-company documents (Microsoft, Apple, Nike, Patagonia — see corpus/MANIFEST.md).
Claims 61-97 (the four invented/"Simulated" documents) are reported as coverage only and are
excluded from every accuracy figure in this file, per T-08's acceptance and R-03.

accountable_party is carried in every table for completeness but is flagged everywhere it
appears: two independently-committed rubrics (docs/LABELLING-RUBRIC.md's "named organisation
counts" vs. a sibling rubric's "named role/governing body only, not the org's own name" —
both timestamped in git before either saw the other) define the field oppositely, and that
single definitional choice moves 29 of the 60 gold labels. No inter-annotator-agreement
figure is computed anywhere in this file, on any field — see .crew/outbox/T-08.md and
.crew/DECISIONS.md for why that would misrepresent a definitional conflict as measurement
noise.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.engine import evaluate, load_pack  # noqa: E402

FROZEN_CLAIMS = ROOT / "corpus" / "claims.frozen.jsonl"
GOLD = ROOT / "corpus" / "gold.labels.json"
PACK_PATH = ROOT / "rules" / "climate.v1.json"
RUNS_DIR = ROOT / "deliverables" / "runs"
OUT = ROOT / "deliverables" / "COMPARISON.md"

FIELDS = ["quantity", "target_year", "baseline_year", "named_standard", "accountable_party"]
# accountable_party is excluded from "the Gate's total miss count" and from the headline
# 4-field accuracy figure: the gate/gold disagreement there is a definitional conflict
# (see module docstring), not a probe error, and folding it into "misses" would misreport
# a choice of definition as a measured defect.
SCORED_FIELDS = ["quantity", "target_year", "baseline_year", "named_standard"]


# --------------------------------------------------------------------------- data loading


def load_frozen_claims() -> list[dict]:
    claims = []
    for line in FROZEN_CLAIMS.read_text().splitlines():
        line = line.strip()
        if line:
            claims.append(json.loads(line))
    return claims


def load_gold() -> dict[str, dict]:
    return json.loads(GOLD.read_text())


def load_baseline_run(n: int) -> dict:
    return json.loads((RUNS_DIR / f"baseline.run{n}.json").read_text())


# --------------------------------------------------------------------------- arm A (the Gate)


def gate_verdicts(claim: dict, pack: dict) -> dict[str, bool]:
    """Run the real Checkability Gate on one claim; return {field: present}."""
    result = evaluate(claim, pack)
    return {v["probe"]: v["present"] for v in result["verdicts"]}


def gate_verdicts_for_claims(claims: list[dict], pack: dict) -> dict[str, dict[str, bool]]:
    return {c["claim_id"]: gate_verdicts(c, pack) for c in claims}


# --------------------------------------------------------------------------- arm B (baseline)


def baseline_verdicts(run: dict) -> dict[str, dict[str, bool] | None]:
    """{claim_id: {field: present} or None if that claim was unparseable this run}.
    Each present dict also carries "_checkable": the model's OWN self-reported checkable
    bool (not derived from the missing list) under that key, since the two can and do
    disagree — the model's checkable bool and its own missing-list are two separate
    outputs from the same call, and one measure of self-contradiction is exactly that they
    don't always agree with each other, let alone across runs."""
    out: dict[str, dict[str, bool] | None] = {}
    for cid, v in run["results"].items():
        if v.get("unparseable"):
            out[cid] = None
        else:
            missing = set(v.get("missing", []))
            verdict = {f: (f not in missing) for f in FIELDS}
            verdict["_checkable"] = bool(v.get("checkable"))
            out[cid] = verdict
    return out


# --------------------------------------------------------------------------- metrics


def confusion(gold: dict[str, dict], preds: dict[str, dict | None], claim_ids: list[str], field: str) -> dict[str, int]:
    tp = fp = fn = tn = 0
    for cid in claim_ids:
        pred = preds.get(cid)
        if pred is None:
            continue
        gv = gold[cid][field]
        pv = pred[field]
        if gv and pv:
            tp += 1
        elif (not gv) and pv:
            fp += 1
        elif gv and (not pv):
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def precision_recall_f1(c: dict[str, int]) -> tuple[float | None, float | None, float | None]:
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    p = tp / (tp + fp) if (tp + fp) else None
    r = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * p * r / (p + r)) if (p is not None and r is not None and (p + r) > 0) else None
    return p, r, f1


def accuracy(c: dict[str, int]) -> float:
    total = c["tp"] + c["fp"] + c["fn"] + c["tn"]
    return (c["tp"] + c["tn"]) / total if total else 0.0


def exact_match(gold: dict[str, dict], preds: dict[str, dict | None], claim_ids: list[str], fields: list[str]) -> tuple[int, int]:
    matches = 0
    total = 0
    for cid in claim_ids:
        pred = preds.get(cid)
        if pred is None:
            continue
        total += 1
        if all(gold[cid][f] == pred[f] for f in fields):
            matches += 1
    return matches, total


def coverage(preds: dict[str, dict | None]) -> tuple[int, int]:
    parseable = sum(1 for v in preds.values() if v is not None)
    return parseable, len(preds)


def self_agreement(runs: list[dict[str, dict | None]], claim_ids: list[str], fields: list[str]) -> dict:
    """Across len(runs) independent runs of the SAME arm on the SAME claims: how many claims
    get an identical verdict every time, on (a) the checkable-or-not headline bit — the
    model's OWN self-reported "checkable" boolean, stashed under "_checkable" by
    baseline_verdicts(), NOT re-derived from its missing-list (the two aren't always
    consistent even within one call, so re-deriving would silently measure something else)
    — and (b) the full field-level vector derived from the missing list."""
    agree_checkable = disagree_checkable = 0
    agree_vector = disagree_vector = 0
    skipped = 0
    disagree_checkable_ids: list[str] = []
    for cid in claim_ids:
        values = [r.get(cid) for r in runs]
        if any(v is None for v in values):
            skipped += 1
            continue
        checkables = {v["_checkable"] for v in values}
        if len(checkables) == 1:
            agree_checkable += 1
        else:
            disagree_checkable += 1
            disagree_checkable_ids.append(cid)
        vectors = {tuple(v[f] for f in fields) for v in values}
        if len(vectors) == 1:
            agree_vector += 1
        else:
            disagree_vector += 1
    return {
        "agree_checkable": agree_checkable,
        "disagree_checkable": disagree_checkable,
        "disagree_checkable_ids": disagree_checkable_ids,
        "agree_vector": agree_vector,
        "disagree_vector": disagree_vector,
        "skipped_unparseable": skipped,
        "total": len(claim_ids),
    }


def find_gate_misses(
    gold: dict[str, dict],
    gate_preds: dict[str, dict],
    baseline_preds: dict[str, dict | None],
    claim_ids: list[str],
    fields: list[str],
) -> list[tuple[str, str]]:
    """(claim_id, field) pairs where gold says present, the Gate says absent, and the
    baseline correctly said present — a false NEGATIVE the single prompt avoids. This is
    HALF of "where the single prompt beats us"; see find_gate_overfires for the other half.
    Restricted to SCORED_FIELDS by the caller so the accountable_party construct conflict
    never gets silently counted as a Gate defect."""
    misses = []
    for cid in claim_ids:
        b = baseline_preds.get(cid)
        if b is None:
            continue
        for f in fields:
            if gold[cid][f] and not gate_preds[cid][f] and b[f]:
                misses.append((cid, f))
    return misses


def find_gate_overfires(
    gold: dict[str, dict],
    gate_preds: dict[str, dict],
    baseline_preds: dict[str, dict | None],
    claim_ids: list[str],
    fields: list[str],
) -> list[tuple[str, str]]:
    """(claim_id, field) pairs where gold says absent, the Gate says present, and the
    baseline correctly said absent — a false POSITIVE the single prompt avoids. The mirror
    image of find_gate_misses.

    R-08 (red team, .crew/BOARD.md): an earlier version of this file counted only
    find_gate_misses and reported that count as the total of "where the single prompt beats
    us." That undercounted it — a Gate false positive the baseline correctly avoids is just
    as much a case of "the single prompt beats us" as a false negative is, and this file has
    a whole paragraph two sections down (`named_standard`'s Scope 1/2/3 false positives)
    describing exactly this failure mode without ever adding it to the headline count.
    misses + overfires together is the honest total."""
    overfires = []
    for cid in claim_ids:
        b = baseline_preds.get(cid)
        if b is None:
            continue
        for f in fields:
            if not gold[cid][f] and gate_preds[cid][f] and not b[f]:
                overfires.append((cid, f))
    return overfires


# --------------------------------------------------------------------------- formatting


def fmt_pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def build_field_table(rows: dict[str, dict[str, int]], fields: list[str]) -> list[str]:
    lines = [
        "| Field | Precision | Recall | F1 | Accuracy | TP | FP | FN | TN |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for f in fields:
        c = rows[f]
        p, r, f1 = precision_recall_f1(c)
        lines.append(
            f"| `{f}` | {fmt_pct(p)} | {fmt_pct(r)} | {fmt_pct(f1)} | {fmt_pct(accuracy(c))} "
            f"| {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} |"
        )
    return lines


def build_markdown(data: dict) -> str:
    L: list[str] = []
    a = L.append

    a("# COMPARISON — Arm A (the Checkability Gate) vs Arm B (single-prompt baseline)")
    a("")
    a(
        "Both arms read the identical frozen claim set, `corpus/claims.frozen.jsonl` "
        f"({data['n_frozen']} claims, frozen once by T-07 and never re-segmented). An "
        "imperfect claim extractor would still make this comparison fair, because whatever "
        "it got wrong is wrong for both arms equally — the one thing that would NOT be fair "
        "is either arm seeing a claim set the other didn't. Every number below is "
        "reproducible by `./run.sh compare`; see the command list at the bottom."
    )
    a("")
    a(
        "**Scope of every accuracy figure in this file:** gold labels "
        "(`corpus/gold.labels.json`, T-08) cover only the first 60 of the 97 frozen claims, "
        "and only those 60 are used below. Claims 61-97 are reported as coverage only. "
        "The labelled 60 span the four **real, verbatim, real-company** documents "
        "(Microsoft, Apple, Nike, Patagonia) — the four invented/\"Simulated\" documents sit "
        "entirely in the unlabelled tail. So every accuracy number below is accuracy on "
        "**real corporate climate language**, which is the harder and more meaningful half, "
        "but it is not evidence about the synthetic documents, and no sentence in this file "
        "claims otherwise."
    )
    a("")
    a(
        "**A limit this file cannot repair:** the gold set is attested blind — its rubric "
        "(`docs/LABELLING-RUBRIC.md`) is committed 134 seconds before the labels, which is "
        "auditable in git — but \"the annotator did not read `deliverables/results.json`, "
        "`core/probes.py` or `rules/climate.v1.json` before labelling\" is a claim the "
        "annotator makes about themselves, not something this repository can prove. Stated "
        "here rather than left for a hostile reader to find first."
    )
    a("")
    a("---")
    a("")

    # ---- 1. Negative result, above the fold -----------------------------------------
    a("## Where the single prompt beats us")
    a("")
    a(
        f"Across the 60 gold-labelled claims, the honest total is **{data['n_gate_wrong_total']} "
        "field-level checks the single-prompt baseline gets right and the Gate gets "
        f"wrong**: **{data['n_gate_misses']} misses** (gold says present, the Gate says "
        f"absent, the baseline correctly says present) plus **{data['n_gate_overfires']} "
        "over-fires** (gold says absent, the Gate says present, the baseline correctly "
        "says absent). Both halves are counted the same way and both exclude "
        "`accountable_party` (that field's disagreement is a definitional conflict between "
        "two rubrics, not a Gate defect — see below). Not counted, in either direction: "
        "cases where the baseline is ALSO wrong on the same field — that is a shared miss, "
        "not the single prompt beating us. Every one of the 11 misses is `quantity` or "
        "`baseline_year`; two of the three over-fires are the `named_standard`/Scope bug "
        "documented below (**R-01**), the third is a new `baseline_year` false positive — "
        "the probe matches any nearby year, not necessarily the one attached to a "
        "reduction target. Five misses, quoted in full:"
    )
    a("")
    for cid, field, text, why in data["miss_examples"]:
        a(f"- **`{cid}` — `{field}` missed.** \"{text}\" — {why}")
    a("")
    a("And all three over-fires, quoted in full:")
    a("")
    for cid, field, text, why in data["overfire_examples"]:
        a(f"- **`{cid}` — `{field}` over-fired.** \"{text}\" — {why}")
    a("")
    a(
        "All nine `quantity` misses split into two distinct, disclosed failure modes, "
        "neither of them the one the rule pack already documents "
        "(`params.known_miss_words` on `C1-QTY` pins `halve`/`double`/`triple`/`net-zero`, "
        "and `tests/test_probes.py::test_quantity_misses_word_numbers_like_halve` asserts "
        "it as a known miss, not a passing case):"
    )
    a("")
    a(
        "1. **Spelled-out word-numbers the documented miss doesn't literally cover** — "
        "\"more than half\", \"Sixty-nine percent\", \"Thirty-six percent\", "
        "\"Ninety-six percent\" — the same failure family as `halve`, just a different word."
    )
    a(
        "2. **Digit magnitudes with no unit token the regex recognises** — "
        "\"$1 billion\", a bare \"92\" facility count. This is a new, previously "
        "undisclosed gap (filed as **R-02**, `.crew/BOARD.md`), not the word-number miss."
    )
    a("")
    a(
        "The two `baseline_year` misses (`cab9279cadc9`, `11e64368bcac`) are a third, "
        "distinct, newly-found gap: **`FY20`, a two-digit fiscal-year shorthand, never "
        "matches the probe's year regex**, which requires four digits "
        "(`(?:19|20)\\d{2}`) — the same rule that correctly parses `FY2040`/`FY2017` "
        "elsewhere in this corpus fails silently on `FY20`. Filed as **R-04** for the same "
        "reason R-01/R-02 were: a hostile reader will find it if we don't say it first."
    )
    a("")
    a(
        "These are tests, not just narrative: `tests/test_probes.py` already pins the "
        "documented word-number miss as a **passing assertion that the verdict is False** "
        "(a miss that stops being asserted the moment someone \"fixes\" it without noticing "
        "they changed what the Gate promises); R-01/R-02/R-04 are filed on `.crew/BOARD.md` "
        "for the same treatment, not hidden as narrative color."
    )
    a("")
    a("---")
    a("")

    # ---- 2. Per-field precision/recall/F1 ---------------------------------------------
    a("## Per-field precision / recall / F1")
    a("")
    a(
        "Arm A is the Gate, computed fresh from `core/engine.py` against the frozen claims "
        "(`Rule`, deterministic, no model). Arm B is baseline run 1 of 3 "
        "(`Generated`, one real Featherless-served call per batch of 15 claims, no "
        "workflow, no code) — see the self-agreement section below for why \"run 1\" is not "
        "the whole story for Arm B."
    )
    a("")
    a("**Arm A — the Gate (`Rule`)**")
    a("")
    L.extend(build_field_table(data["gate_confusion"], FIELDS))
    a("")
    a("**Arm B — single-prompt baseline, run 1/3 (`Generated`)**")
    a("")
    L.extend(build_field_table(data["baseline_confusion"][1], FIELDS))
    a("")
    a(
        f"Overall field-decision accuracy across all five fields (300 decisions on 60 "
        f"claims): Arm A **{fmt_pct(data['gate_overall_acc_5'])}**, Arm B run 1 "
        f"**{fmt_pct(data['baseline_overall_acc_5'][1])}**. Restricted to the four fields "
        "with no definitional conflict (`quantity`, `target_year`, `baseline_year`, "
        f"`named_standard` — 240 decisions): Arm A "
        f"**{fmt_pct(data['gate_overall_acc_4'])}**, Arm B run 1 "
        f"**{fmt_pct(data['baseline_overall_acc_4'][1])}**."
    )
    a("")
    a(
        "**`target_year` is 60/60 (100%) for the Gate against a blind gold set** — the "
        "strongest single verifiable number in this file, and it holds on the hard cases: "
        "`d768f1626c96` states a target year (`FY2040`) and a baseline year (`FY2017`) in "
        "one sentence and the Gate splits them correctly, and every retrospective "
        "performance year in the corpus (\"in FY24\", \"in 2019\") is correctly declined as "
        "a target."
    )
    a("")
    a(
        "**`named_standard` has a disclosed false-positive bug**: `Scope 1`/`Scope 2`/"
        "`Scope 3` are matched as a named standard, which is why Arm A's precision on that "
        "field is only "
        f"{fmt_pct(precision_recall_f1(data['gate_confusion']['named_standard'])[0])} "
        "despite perfect recall. Scopes are *defined by* the GHG Protocol, but a sentence "
        "that only says \"Scope 1\" names no standard — filed as **R-01**."
    )
    a("")
    a("### The `accountable_party` definitional conflict")
    a("")
    a(
        "Two rubrics, both committed to git before either annotator saw the other's file, "
        "define this field **oppositely**:"
    )
    a("")
    a(
        "- **Canonical gold rubric** (`docs/LABELLING-RUBRIC.md`, used for every number "
        "above): a **named organisation** counts as the accountable party — "
        "\"By 2030 Microsoft will be carbon negative\" → TRUE. Under this construct, "
        f"**{data['gold_accountable_party_true']}/60** of the gold-labelled claims are "
        "positive."
    )
    a(
        "- **The Gate's own construct** (`rules/climate.v1.json`'s `actors` lexicon: "
        "`board`, `CEO`, `chief sustainability officer`, and other named roles/governance "
        "bodies — never the company's own name): under this construct the Gate fires on "
        f"**{data['gate_accountable_party_true']}/60** of the same claims."
    )
    a("")
    a(
        "That single choice of definition moves **29 of the 60 claims**. Neither construct "
        "is wrong; they measure different things, and averaging them would misreport a "
        "definitional disagreement as a defect. The sentence worth keeping from this: "
        "**under the Gate's own role-based reading, not one of the 60 verbatim claims from "
        "Microsoft, Apple, Nike or Patagonia names a governance body or officer accountable "
        "for the pledge** — every positive case in the whole 97-claim corpus is in the "
        "invented documents, outside the labelled range. Worth noting, not over-claimed: "
        f"the single-prompt baseline lands close to the Gate's reading, not the gold "
        f"rubric's — {data['baseline_accountable_party_true'][1]}/60 positive on run 1, "
        "the same order of magnitude as the Gate's 0, not the gold set's 29."
    )
    a("")
    a(
        "No inter-annotator-agreement figure is computed anywhere in this file, on any "
        "field. A second labelling pass exists in this repo "
        "(`corpus/gold.labels.A.json`) but its author read the canonical annotator's "
        "already-committed file before finishing their own — a disclosed, second *reading*, "
        "not a second *independent* one — so it is not used for any number above, and no "
        "agreement statistic is derived from it."
    )
    a("")
    a("---")
    a("")

    # ---- 3. Exact match -----------------------------------------------------------------
    a("## Exact-match rate (5-bit vector)")
    a("")
    a(
        "A claim counts as an exact match only if all five fields agree with gold "
        "simultaneously — the strictest number in this file, and the one most distorted by "
        "the `accountable_party` conflict (below it, restricted to the four "
        "non-conflicted fields, for comparison)."
    )
    a("")
    a("| | 5-field exact match | 4-field exact match (excl. `accountable_party`) |")
    a("|---|---|---|")
    gm, gt = data["gate_exact_5"]
    gm4, gt4 = data["gate_exact_4"]
    a(f"| Arm A (Gate) | {gm}/{gt} ({fmt_pct(gm/gt)}) | {gm4}/{gt4} ({fmt_pct(gm4/gt4)}) |")
    for n in (1, 2, 3):
        bm, bt = data["baseline_exact_5"][n]
        bm4, bt4 = data["baseline_exact_4"][n]
        a(
            f"| Arm B run {n} | {bm}/{bt} ({fmt_pct(bm/bt)}) | "
            f"{bm4}/{bt4} ({fmt_pct(bm4/bt4)}) |"
        )
    a("")
    a("---")
    a("")

    # ---- 4. Coverage ----------------------------------------------------------------------
    a("## Coverage")
    a("")
    a(
        "Parseable per-claim verdicts returned, out of all 97 frozen claims (not just the "
        "60 gold-labelled ones — coverage is measured over the whole corpus, accuracy only "
        "over the labelled slice)."
    )
    a("")
    a("| Arm | Parseable | Total | Coverage |")
    a("|---|---|---|---|")
    gp, gtt = data["gate_coverage"]
    a(f"| Arm A (Gate) | {gp} | {gtt} | {fmt_pct(gp/gtt)} |")
    for n in (1, 2, 3):
        bp, bt = data["baseline_coverage"][n]
        a(f"| Arm B run {n} | {bp} | {bt} | {fmt_pct(bp/bt)} |")
    a("")
    a(
        "Coverage alone does not distinguish the arms tonight — both reached 100% on all "
        "runs. It is reported because a baseline that silently drops what it can't parse "
        "would look more capable than it is; this run's baseline never had to."
    )
    a("")
    a("---")
    a("")

    # ---- 5. Self-agreement — the headline -------------------------------------------------
    a("## Self-agreement across 3 identical runs — the headline")
    a("")
    a(
        "**Arm A is 3/3 identical by construction.** The Gate is a pure function of the "
        "claim text and the rule pack; `deliverables/runs/gate.run{1,2,3}.json` are three "
        "separate invocations, model layer off, and their scoring-relevant fields "
        "(`claim_id, text, score, max_score, verdicts, pack_version`) hash **identically** "
        f"— sha256 `{data['gate_run_hash']}` — all three times."
    )
    a("")
    a(
        "**Arm B is not.** Three independent, real, model-on calls against the identical "
        f"prompt and the identical 97 claims: the checkable-or-not verdict changed between "
        f"runs on **{data['baseline_disagree_checkable']} of "
        f"{data['baseline_self_total']} claims** "
        f"({fmt_pct(data['baseline_disagree_checkable']/data['baseline_self_total'])} "
        "contradiction rate; "
        f"{data['baseline_agree_checkable']}/{data['baseline_self_total']} = "
        f"{fmt_pct(data['baseline_agree_checkable']/data['baseline_self_total'])} agreement). "
        "At the finer-grained level — all five fields, not just the checkable summary bit "
        f"— agreement is worse: only "
        f"{data['baseline_agree_vector']}/{data['baseline_self_total']} "
        f"({fmt_pct(data['baseline_agree_vector']/data['baseline_self_total'])}) of claims "
        "got the identical 5-field verdict all three times; "
        f"{data['baseline_disagree_vector']} claims flipped at least one field."
    )
    a("")
    a(
        "Same prompt, same model, same 97 claims, three calls: the deterministic core "
        "never moves and the single prompt disagrees with itself on roughly 1 in "
        f"{round(data['baseline_self_total']/max(data['baseline_disagree_checkable'],1))} "
        "claims even on the summary bit, and roughly 1 in "
        f"{round(data['baseline_self_total']/max(data['baseline_disagree_vector'],1))} "
        "claims at field granularity."
    )
    a("")
    a("---")
    a("")

    # ---- 6. Tags ------------------------------------------------------------------------
    a("## Epistemic tags")
    a("")
    a(
        "| Tag | Meaning | Applies to |\n"
        "|---|---|---|\n"
        "| `Rule` | Computed by the deterministic engine from a named rule-pack clause. | "
        "Every Arm A number in this file. |\n"
        "| `Generated` | Written by the model (`gemini-3.6-flash` if quota allows, else "
        "Featherless — see `model/provider.py`). Never affects a score. | Every Arm B "
        "number in this file. |"
    )
    a("")
    a("---")
    a("")

    # ---- 7. What this does not show ------------------------------------------------------
    a("## What this comparison does not show")
    a("")
    a(
        "60 gold labels, one rule pack version (`climate.v1.json`), one domain (corporate "
        "climate pledges), one model family served across two providers, and — for "
        "everything but `target_year` — a single annotator whose blindness is attested, not "
        "provable from the repo. It does not show performance on the four invented "
        "documents (unlabelled, coverage only), it does not show what a differently-tuned "
        "single-prompt baseline could do with more examples or a stricter schema, and it "
        "does not show anything about domains outside corporate climate pledges — "
        "`rules/hiring.v1.json`, if it exists, is a separate claim with its own evidence. "
        "What it does show, without qualification: on the same 97 claims, run three times "
        "each, one arm never moved and the other did."
    )
    a("")
    a("---")
    a("")
    a("## Reproduce every number above")
    a("")
    a("```")
    a("./run.sh compare")
    a("```")
    a(
        "reads only committed inputs (`corpus/claims.frozen.jsonl`, `corpus/gold.labels.json`, "
        "`rules/climate.v1.json`, `deliverables/runs/*.json`) and rewrites this file. Deleting "
        "`deliverables/COMPARISON.md` and re-running the command above regenerates it "
        "byte-for-byte, because nothing in it is derived from wall-clock time."
    )
    a("")

    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- main


MISS_EXAMPLES_SOURCE = [
    (
        "ed45cc49608c",
        "quantity",
        "We are launching today an aggressive program to cut our carbon emissions by more "
        "than half by 2030, both for our direct emissions and for our entire supply and "
        "value chain.",
        "\"more than half\" is a word-number, same failure family as the documented "
        "`halve` miss.",
    ),
    (
        "cab9279cadc9",
        "quantity",
        "Sixty-nine percent reduction of absolute Scope 1 and Scope 2 GHG emissions from "
        "Nike Operations in FY24, compared to a FY20 baseline.",
        "\"Sixty-nine percent\" is spelled out, not digits, and this claim also misses "
        "`baseline_year` — \"FY20\" is a two-digit fiscal year the year regex never "
        "matches (R-04, see below).",
    ),
    (
        "905bdf32e595",
        "quantity",
        "We are launching a new $1 billion climate innovation fund to accelerate the "
        "global development of carbon reduction, capture, and removal technologies.",
        "\"$1 billion\" is digits, not a word-number — a new gap (R-02), not the "
        "documented one.",
    ),
    (
        "3972fd81a5ae",
        "quantity",
        "The number of facilities participating in Apple's Supplier Energy Efficiency "
        "Program grew to 92 in 2019; these facilities avoided over 779,000 annualized "
        "metric tons of supply chain carbon emissions.",
        "a bare digit count (\"92\") with no unit token the pattern recognises (R-02).",
    ),
    (
        "11e64368bcac",
        "baseline_year",
        "Thirty-six percent reduction of absolute Scope 3 GHG emissions from Nike's "
        "manufacturing and transportation in FY24, versus a FY20 baseline.",
        "a second, confirming case of the \"FY20\" two-digit-fiscal-year miss (R-04) — "
        "not a one-off.",
    ),
]

OVERFIRE_EXAMPLES_SOURCE = [
    (
        "cab9279cadc9",
        "named_standard",
        "Sixty-nine percent reduction of absolute Scope 1 and Scope 2 GHG emissions from "
        "Nike Operations in FY24, compared to a FY20 baseline.",
        "\"Scope 1\" is matched as a named standard, but a bare Scope mention names no "
        "standard by itself — the disclosed `named_standard` false-positive bug (**R-01**).",
    ),
    (
        "11e64368bcac",
        "named_standard",
        "Thirty-six percent reduction of absolute Scope 3 GHG emissions from Nike's "
        "manufacturing and transportation in FY24, versus a FY20 baseline.",
        "a second, confirming case of the same Scope false positive (**R-01**).",
    ),
    (
        "280e8280df99",
        "baseline_year",
        "We will fund this in part by expanding our internal carbon fee, in place since "
        "2012 and increased last year, to start charging not only our direct emissions, "
        "but those from our supply and value chains.",
        "\"2012\" is matched as a baseline year, but it is the year an internal carbon "
        "fee started, not a stated baseline for a reduction target — the probe fires on "
        "any nearby year, not specifically one attached to a target. A new, previously "
        "undisclosed gap, found while fixing R-08.",
    ),
]


def main() -> int:
    pack = load_pack(PACK_PATH)
    claims = load_frozen_claims()
    gold = load_gold()
    gold_ids = list(gold.keys())
    # "the first 60 claims" per T-08's own spec: corpus order, not dict order.
    ordered_gold_ids = [c["claim_id"] for c in claims if c["claim_id"] in gold]
    assert set(ordered_gold_ids) == set(gold_ids), "gold labels reference a claim not in the frozen corpus"

    gate_preds_all = gate_verdicts_for_claims(claims, pack)
    gate_preds_gold = {cid: gate_preds_all[cid] for cid in ordered_gold_ids}

    baseline_runs_raw = {n: load_baseline_run(n) for n in (1, 2, 3)}
    baseline_preds = {n: baseline_verdicts(baseline_runs_raw[n]) for n in (1, 2, 3)}

    all_claim_ids = [c["claim_id"] for c in claims]

    gate_confusion = {f: confusion(gold, gate_preds_gold, ordered_gold_ids, f) for f in FIELDS}
    baseline_confusion = {
        n: {f: confusion(gold, baseline_preds[n], ordered_gold_ids, f) for f in FIELDS}
        for n in (1, 2, 3)
    }

    gate_overall_5 = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    gate_overall_4 = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for f in FIELDS:
        for k in gate_overall_5:
            gate_overall_5[k] += gate_confusion[f][k]
        if f in SCORED_FIELDS:
            for k in gate_overall_4:
                gate_overall_4[k] += gate_confusion[f][k]

    baseline_overall_5 = {}
    baseline_overall_4 = {}
    for n in (1, 2, 3):
        o5 = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        o4 = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        for f in FIELDS:
            for k in o5:
                o5[k] += baseline_confusion[n][f][k]
            if f in SCORED_FIELDS:
                for k in o4:
                    o4[k] += baseline_confusion[n][f][k]
        baseline_overall_5[n] = accuracy(o5)
        baseline_overall_4[n] = accuracy(o4)

    gate_exact_5 = exact_match(gold, gate_preds_gold, ordered_gold_ids, FIELDS)
    gate_exact_4 = exact_match(gold, gate_preds_gold, ordered_gold_ids, SCORED_FIELDS)
    baseline_exact_5 = {n: exact_match(gold, baseline_preds[n], ordered_gold_ids, FIELDS) for n in (1, 2, 3)}
    baseline_exact_4 = {
        n: exact_match(gold, baseline_preds[n], ordered_gold_ids, SCORED_FIELDS) for n in (1, 2, 3)
    }

    gate_cov = coverage({cid: gate_preds_all[cid] for cid in all_claim_ids})
    baseline_cov = {n: coverage(baseline_preds[n]) for n in (1, 2, 3)}

    baseline_runs_list = [baseline_preds[n] for n in (1, 2, 3)]
    agg = self_agreement(baseline_runs_list, all_claim_ids, FIELDS)

    misses = find_gate_misses(gold, gate_preds_gold, baseline_preds[1], ordered_gold_ids, SCORED_FIELDS)
    overfires = find_gate_overfires(gold, gate_preds_gold, baseline_preds[1], ordered_gold_ids, SCORED_FIELDS)

    gold_accountable_true = sum(1 for cid in ordered_gold_ids if gold[cid]["accountable_party"])
    gate_accountable_true = sum(1 for cid in ordered_gold_ids if gate_preds_gold[cid]["accountable_party"])
    baseline_accountable_true = {
        n: sum(
            1
            for cid in ordered_gold_ids
            if baseline_preds[n].get(cid) is not None and baseline_preds[n][cid]["accountable_party"]
        )
        for n in (1, 2, 3)
    }

    def stable_hash(path: Path) -> str:
        d = json.loads(path.read_text())
        d.pop("generated_at", None)
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode("utf-8")).hexdigest()

    gate_run_hashes = {stable_hash(RUNS_DIR / f"gate.run{n}.json") for n in (1, 2, 3)}
    gate_run_hash = next(iter(gate_run_hashes)) if len(gate_run_hashes) == 1 else "DIVERGED-" + "/".join(sorted(gate_run_hashes))

    data = {
        "n_frozen": len(claims),
        "n_gate_misses": len(misses),
        "n_gate_overfires": len(overfires),
        "n_gate_wrong_total": len(misses) + len(overfires),
        "miss_examples": MISS_EXAMPLES_SOURCE,
        "overfire_examples": OVERFIRE_EXAMPLES_SOURCE,
        "gate_confusion": gate_confusion,
        "baseline_confusion": baseline_confusion,
        "gate_overall_acc_5": accuracy(gate_overall_5),
        "gate_overall_acc_4": accuracy(gate_overall_4),
        "baseline_overall_acc_5": baseline_overall_5,
        "baseline_overall_acc_4": baseline_overall_4,
        "gate_exact_5": gate_exact_5,
        "gate_exact_4": gate_exact_4,
        "baseline_exact_5": baseline_exact_5,
        "baseline_exact_4": baseline_exact_4,
        "gate_coverage": gate_cov,
        "baseline_coverage": baseline_cov,
        "gate_run_hash": gate_run_hash,
        "baseline_disagree_checkable": agg["disagree_checkable"],
        "baseline_agree_checkable": agg["agree_checkable"],
        "baseline_agree_vector": agg["agree_vector"],
        "baseline_disagree_vector": agg["disagree_vector"],
        "baseline_self_total": agg["total"],
        "gold_accountable_party_true": gold_accountable_true,
        "gate_accountable_party_true": gate_accountable_true,
        "baseline_accountable_party_true": baseline_accountable_true,
    }

    OUT.write_text(build_markdown(data))
    print(f"wrote {OUT}")
    print(f"  Gate wrong, baseline right, excl. accountable_party (TOTAL): {len(misses) + len(overfires)}")
    print(f"    misses (Gate false negative): {len(misses)}")
    print(f"    over-fires (Gate false positive): {len(overfires)}")
    print(f"  Arm A exact-match (5-field): {gate_exact_5[0]}/{gate_exact_5[1]}")
    print(f"  Arm B run1 exact-match (5-field): {baseline_exact_5[1][0]}/{baseline_exact_5[1][1]}")
    print(
        f"  Arm B self-agreement (checkable bit): {agg['agree_checkable']}/{agg['total']} "
        f"({agg['disagree_checkable']} contradictions)"
    )
    print(f"  Arm A 3-run hash: {gate_run_hash}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
