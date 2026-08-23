# COMPARISON — Arm A (the Checkability Gate) vs Arm B (single-prompt baseline)

Both arms read the identical frozen claim set, `corpus/claims.frozen.jsonl` (97 claims, frozen once by T-07 and never re-segmented). An imperfect claim extractor would still make this comparison fair, because whatever it got wrong is wrong for both arms equally — the one thing that would NOT be fair is either arm seeing a claim set the other didn't. Every number below is reproducible by `./run.sh compare`; see the command list at the bottom.

**Scope of every accuracy figure in this file:** gold labels (`corpus/gold.labels.json`, T-08) cover only the first 60 of the 97 frozen claims, and only those 60 are used below. Claims 61-97 are reported as coverage only. The labelled 60 span the four **real, verbatim, real-company** documents (Microsoft, Apple, Nike, Patagonia) — the four invented/"Simulated" documents sit entirely in the unlabelled tail. So every accuracy number below is accuracy on **real corporate climate language**, which is the harder and more meaningful half, but it is not evidence about the synthetic documents, and no sentence in this file claims otherwise.

**A limit this file cannot repair:** the gold set is attested blind — its rubric (`docs/LABELLING-RUBRIC.md`) is committed 134 seconds before the labels, which is auditable in git — but "the annotator did not read `deliverables/results.json`, `core/probes.py` or `rules/climate.v1.json` before labelling" is a claim the annotator makes about themselves, not something this repository can prove. Stated here rather than left for a hostile reader to find first.

---

## Where the single prompt beats us

Across the 60 gold-labelled claims, the honest total is **14 field-level checks the single-prompt baseline gets right and the Gate gets wrong**: **11 misses** (gold says present, the Gate says absent, the baseline correctly says present) plus **3 over-fires** (gold says absent, the Gate says present, the baseline correctly says absent). Both halves are counted the same way and both exclude `accountable_party` (that field's disagreement is a definitional conflict between two rubrics, not a Gate defect — see below). Not counted, in either direction: cases where the baseline is ALSO wrong on the same field — that is a shared miss, not the single prompt beating us. Every one of the 11 misses is `quantity` or `baseline_year`; two of the three over-fires are the `named_standard`/Scope bug documented below (**R-01**), the third is a new `baseline_year` false positive — the probe matches any nearby year, not necessarily the one attached to a reduction target. Five misses, quoted in full:

- **`ed45cc49608c` — `quantity` missed.** "We are launching today an aggressive program to cut our carbon emissions by more than half by 2030, both for our direct emissions and for our entire supply and value chain." — "more than half" is a word-number, same failure family as the documented `halve` miss.
- **`cab9279cadc9` — `quantity` missed.** "Sixty-nine percent reduction of absolute Scope 1 and Scope 2 GHG emissions from Nike Operations in FY24, compared to a FY20 baseline." — "Sixty-nine percent" is spelled out, not digits, and this claim also misses `baseline_year` — "FY20" is a two-digit fiscal year the year regex never matches (R-04, see below).
- **`905bdf32e595` — `quantity` missed.** "We are launching a new $1 billion climate innovation fund to accelerate the global development of carbon reduction, capture, and removal technologies." — "$1 billion" is digits, not a word-number — a new gap (R-02), not the documented one.
- **`3972fd81a5ae` — `quantity` missed.** "The number of facilities participating in Apple's Supplier Energy Efficiency Program grew to 92 in 2019; these facilities avoided over 779,000 annualized metric tons of supply chain carbon emissions." — a bare digit count ("92") with no unit token the pattern recognises (R-02).
- **`11e64368bcac` — `baseline_year` missed.** "Thirty-six percent reduction of absolute Scope 3 GHG emissions from Nike's manufacturing and transportation in FY24, versus a FY20 baseline." — a second, confirming case of the "FY20" two-digit-fiscal-year miss (R-04) — not a one-off.

And all three over-fires, quoted in full:

- **`cab9279cadc9` — `named_standard` over-fired.** "Sixty-nine percent reduction of absolute Scope 1 and Scope 2 GHG emissions from Nike Operations in FY24, compared to a FY20 baseline." — "Scope 1" is matched as a named standard, but a bare Scope mention names no standard by itself — the disclosed `named_standard` false-positive bug (**R-01**).
- **`11e64368bcac` — `named_standard` over-fired.** "Thirty-six percent reduction of absolute Scope 3 GHG emissions from Nike's manufacturing and transportation in FY24, versus a FY20 baseline." — a second, confirming case of the same Scope false positive (**R-01**).
- **`280e8280df99` — `baseline_year` over-fired.** "We will fund this in part by expanding our internal carbon fee, in place since 2012 and increased last year, to start charging not only our direct emissions, but those from our supply and value chains." — "2012" is matched as a baseline year, but it is the year an internal carbon fee started, not a stated baseline for a reduction target — the probe fires on any nearby year, not specifically one attached to a target. A new, previously undisclosed gap, found while fixing R-08.

All nine `quantity` misses split into two distinct, disclosed failure modes, neither of them the one the rule pack already documents (`params.known_miss_words` on `C1-QTY` pins `halve`/`double`/`triple`/`net-zero`, and `tests/test_probes.py::test_quantity_misses_word_numbers_like_halve` asserts it as a known miss, not a passing case):

1. **Spelled-out word-numbers the documented miss doesn't literally cover** — "more than half", "Sixty-nine percent", "Thirty-six percent", "Ninety-six percent" — the same failure family as `halve`, just a different word.
2. **Digit magnitudes with no unit token the regex recognises** — "$1 billion", a bare "92" facility count. This is a new, previously undisclosed gap (filed as **R-02**, `.crew/BOARD.md`), not the word-number miss.

The two `baseline_year` misses (`cab9279cadc9`, `11e64368bcac`) are a third, distinct, newly-found gap: **`FY20`, a two-digit fiscal-year shorthand, never matches the probe's year regex**, which requires four digits (`(?:19|20)\d{2}`) — the same rule that correctly parses `FY2040`/`FY2017` elsewhere in this corpus fails silently on `FY20`. Filed as **R-04** for the same reason R-01/R-02 were: a hostile reader will find it if we don't say it first.

These are tests, not just narrative: `tests/test_probes.py` already pins the documented word-number miss as a **passing assertion that the verdict is False** (a miss that stops being asserted the moment someone "fixes" it without noticing they changed what the Gate promises); R-01/R-02/R-04 are filed on `.crew/BOARD.md` for the same treatment, not hidden as narrative color.

---

## Per-field precision / recall / F1

Arm A is the Gate, computed fresh from `core/engine.py` against the frozen claims (`Rule`, deterministic, no model). Arm B is baseline run 1 of 3 (`Generated`, one real Featherless-served call per batch of 15 claims, no workflow, no code) — see the self-agreement section below for why "run 1" is not the whole story for Arm B.

**Arm A — the Gate (`Rule`)**

| Field | Precision | Recall | F1 | Accuracy | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|
| `quantity` | 100.0% | 52.0% | 68.4% | 80.0% | 13 | 0 | 12 | 35 |
| `target_year` | 100.0% | 100.0% | 100.0% | 100.0% | 11 | 0 | 0 | 49 |
| `baseline_year` | 80.0% | 57.1% | 66.7% | 93.3% | 4 | 1 | 3 | 52 |
| `named_standard` | 37.5% | 100.0% | 54.5% | 91.7% | 3 | 5 | 0 | 52 |
| `accountable_party` | n/a | 0.0% | n/a | 51.7% | 0 | 0 | 29 | 31 |

**Arm B — single-prompt baseline, run 1/3 (`Generated`)**

| Field | Precision | Recall | F1 | Accuracy | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|
| `quantity` | 95.7% | 88.0% | 91.7% | 93.3% | 22 | 1 | 3 | 34 |
| `target_year` | 64.7% | 100.0% | 78.6% | 90.0% | 11 | 6 | 0 | 43 |
| `baseline_year` | 42.9% | 85.7% | 57.1% | 85.0% | 6 | 8 | 1 | 45 |
| `named_standard` | 25.0% | 66.7% | 36.4% | 88.3% | 2 | 6 | 1 | 51 |
| `accountable_party` | n/a | 0.0% | n/a | 51.7% | 0 | 0 | 29 | 31 |

Overall field-decision accuracy across all five fields (300 decisions on 60 claims): Arm A **83.3%**, Arm B run 1 **81.7%**. Restricted to the four fields with no definitional conflict (`quantity`, `target_year`, `baseline_year`, `named_standard` — 240 decisions): Arm A **91.2%**, Arm B run 1 **89.2%**.

**`target_year` is 60/60 (100%) for the Gate against a blind gold set** — the strongest single verifiable number in this file, and it holds on the hard cases: `d768f1626c96` states a target year (`FY2040`) and a baseline year (`FY2017`) in one sentence and the Gate splits them correctly, and every retrospective performance year in the corpus ("in FY24", "in 2019") is correctly declined as a target.

**`named_standard` has a disclosed false-positive bug**: `Scope 1`/`Scope 2`/`Scope 3` are matched as a named standard, which is why Arm A's precision on that field is only 37.5% despite perfect recall. Scopes are *defined by* the GHG Protocol, but a sentence that only says "Scope 1" names no standard — filed as **R-01**.

### The `accountable_party` definitional conflict

Two rubrics, both committed to git before either annotator saw the other's file, define this field **oppositely**:

- **Canonical gold rubric** (`docs/LABELLING-RUBRIC.md`, used for every number above): a **named organisation** counts as the accountable party — "By 2030 Microsoft will be carbon negative" → TRUE. Under this construct, **29/60** of the gold-labelled claims are positive.
- **The Gate's own construct** (`rules/climate.v1.json`'s `actors` lexicon: `board`, `CEO`, `chief sustainability officer`, and other named roles/governance bodies — never the company's own name): under this construct the Gate fires on **0/60** of the same claims.

That single choice of definition moves **29 of the 60 claims**. Neither construct is wrong; they measure different things, and averaging them would misreport a definitional disagreement as a defect. The sentence worth keeping from this: **under the Gate's own role-based reading, not one of the 60 verbatim claims from Microsoft, Apple, Nike or Patagonia names a governance body or officer accountable for the pledge** — every positive case in the whole 97-claim corpus is in the invented documents, outside the labelled range. Worth noting, not over-claimed: the single-prompt baseline lands close to the Gate's reading, not the gold rubric's — 0/60 positive on run 1, the same order of magnitude as the Gate's 0, not the gold set's 29.

No inter-annotator-agreement figure is computed anywhere in this file, on any field. A second labelling pass exists in this repo (`corpus/gold.labels.A.json`) but its author read the canonical annotator's already-committed file before finishing their own — a disclosed, second *reading*, not a second *independent* one — so it is not used for any number above, and no agreement statistic is derived from it.

---

## Exact-match rate (5-bit vector)

A claim counts as an exact match only if all five fields agree with gold simultaneously — the strictest number in this file, and the one most distorted by the `accountable_party` conflict (below it, restricted to the four non-conflicted fields, for comparison).

| | 5-field exact match | 4-field exact match (excl. `accountable_party`) |
|---|---|---|
| Arm A (Gate) | 23/60 (38.3%) | 43/60 (71.7%) |
| Arm B run 1 | 26/60 (43.3%) | 40/60 (66.7%) |
| Arm B run 2 | 25/60 (41.7%) | 36/60 (60.0%) |
| Arm B run 3 | 25/60 (41.7%) | 40/60 (66.7%) |

---

## Coverage

Parseable per-claim verdicts returned, out of all 97 frozen claims (not just the 60 gold-labelled ones — coverage is measured over the whole corpus, accuracy only over the labelled slice).

| Arm | Parseable | Total | Coverage |
|---|---|---|---|
| Arm A (Gate) | 97 | 97 | 100.0% |
| Arm B run 1 | 97 | 97 | 100.0% |
| Arm B run 2 | 97 | 97 | 100.0% |
| Arm B run 3 | 97 | 97 | 100.0% |

Coverage alone does not distinguish the arms tonight — both reached 100% on all runs. It is reported because a baseline that silently drops what it can't parse would look more capable than it is; this run's baseline never had to.

---

## Self-agreement across 3 identical runs — the headline

**Arm A is 3/3 identical by construction.** The Gate is a pure function of the claim text and the rule pack; `deliverables/runs/gate.run{1,2,3}.json` are three separate invocations, model layer off, and their scoring-relevant fields (`claim_id, text, score, max_score, verdicts, pack_version`) hash **identically** — sha256 `c6f13fcc07548cfa3b524f811fd7c39b40b88c03b88e491672ef9d4fda62640f` — all three times.

**Arm B is not.** Three independent, real, model-on calls against the identical prompt and the identical 97 claims: the checkable-or-not verdict changed between runs on **8 of 97 claims** (8.2% contradiction rate; 89/97 = 91.8% agreement). At the finer-grained level — all five fields, not just the checkable summary bit — agreement is worse: only 78/97 (80.4%) of claims got the identical 5-field verdict all three times; 19 claims flipped at least one field.

Same prompt, same model, same 97 claims, three calls: the deterministic core never moves and the single prompt disagrees with itself on roughly 1 in 12 claims even on the summary bit, and roughly 1 in 5 claims at field granularity.

---

## Epistemic tags

| Tag | Meaning | Applies to |
|---|---|---|
| `Rule` | Computed by the deterministic engine from a named rule-pack clause. | Every Arm A number in this file. |
| `Generated` | Written by the model (`gemini-3.6-flash` if quota allows, else Featherless — see `model/provider.py`). Never affects a score. | Every Arm B number in this file. |

---

## What this comparison does not show

60 gold labels, one rule pack version (`climate.v1.json`), one domain (corporate climate pledges), one model family served across two providers, and — for everything but `target_year` — a single annotator whose blindness is attested, not provable from the repo. It does not show performance on the four invented documents (unlabelled, coverage only), it does not show what a differently-tuned single-prompt baseline could do with more examples or a stricter schema, and it does not show anything about domains outside corporate climate pledges — `rules/hiring.v1.json`, if it exists, is a separate claim with its own evidence. What it does show, without qualification: on the same 97 claims, run three times each, one arm never moved and the other did.

---

## Reproduce every number above

```
./run.sh compare
```
reads only committed inputs (`corpus/claims.frozen.jsonl`, `corpus/gold.labels.json`, `rules/climate.v1.json`, `deliverables/runs/*.json`) and rewrites this file. Deleting `deliverables/COMPARISON.md` and re-running the command above regenerates it byte-for-byte, because nothing in it is derived from wall-clock time.

