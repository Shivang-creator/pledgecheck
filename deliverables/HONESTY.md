# HONESTY — the epistemic legend, and what is real

Every value anywhere in this packet that could be mistaken for something it is not carries exactly
one of four tags. This file says what each tag means and where it is used, and then says plainly
what was measured for real and what was authored.

## Legend

| Tag | Meaning | Where it appears |
|---|---|---|
| **Observed** | Verbatim text from a named public document, with its source URL. | 4 of the 8 corpus documents (Microsoft, Apple, Nike, Patagonia) and the 60 claims taken from them. |
| **Rule** | Computed by the deterministic engine from a named rule-pack clause. The clause id and its citation travel with the number. | Every probe verdict, score and band in `results.json`; every Arm A figure in `COMPARISON.md`. |
| **Simulated** | An authored fixture written to resemble pledge language. Not from any real company. | 4 of the 8 corpus documents (Glowline, Cobalt Ridge, Driftwood, Ferrous & Vine) and the 37 claims taken from them, including the worked example on the flowchart. |
| **Generated** | Written by a model. Never affects a score. | The `explanation` field only — 93 of the 97 claims in the shipped `results.json`, all served by Featherless (`DeepSeek-V3-0324`). |

## Mocked vs real

| Thing | Status | The honest sentence |
|---|---|---|
| Corpus documents | **Mixed, tagged per document.** 8 documents: 4 `Observed`, 4 `Simulated`. | The four real ones are verbatim excerpts from public pages with their source URLs in `corpus/documents.json`. The four invented ones are labelled as invented everywhere they appear, including on the poster. |
| Claim extraction (N1) | **Real model output, frozen once.** | One recorded run over the 8 documents, output committed to `corpus/claims.frozen.jsonl` (97 claims) and never re-segmented. `harness/freeze_corpus.py` exits 1 if the file already exists. All 97 were mechanically checked as whitespace-normalised substrings of their source document; 92 passed outright and the 5 that did not are written up one by one in `docs/SPOT-CHECK.md`, along with 3 section-heading-shaped claims left in the set rather than edited out. |
| The Gate (N2/N3/N4) | **Real deterministic code. No mocks anywhere.** | 81 tests, an AST purity test that fails the build if anything under `core/` imports outside `re, json, hashlib, dataclasses, pathlib`, and a kill-switch proof by sha256. |
| Gold labels | **Real, blind, and limited.** 60 of the 97 claims. | Labelled from the claim text alone against a rubric committed 134 seconds earlier (`docs/LABELLING-RUBRIC.md`, commit `dcd981f`; labels `8f60d5d`). That ordering is auditable in git. "The annotator had not read `results.json`, `core/probes.py` or `rules/climate.v1.json`" is attested by the annotator, not provable from this repository. Claims 61-97 are reported as coverage only and are excluded from every accuracy figure. |
| A second label set | **Present, disclosed, and unused.** | `corpus/gold.labels.A.json` is a second *reading*, not a second *independent* one — its author read the first annotator's committed file while diagnosing a file collision, and said so unprompted. No number in this packet is derived from it, and **no inter-annotator agreement figure is reported anywhere, on any field.** |
| Baseline arm (Arm B) | **Real model calls, 3 independent runs.** | Same 97 frozen claims, one prompt, no workflow, no code. The exact prompt is in `docs/BASELINE-PROMPT.md`, generated from the same string the code sends. Raw responses committed per run in `deliverables/runs/`. |
| The "one command" kill switch | **Real.** | `./run.sh killswitch` runs the whole pipeline model-on and model-off, hashes both, and prints `DIFF: IDENTICAL`. |
| Model providers | **Real, and one of them failed for real.** | Gemini (`gemini-3.6-flash`) is tried first and hit its free-tier daily cap of 20 requests during the freeze; Featherless (`DeepSeek-V3-0324`) served every model call in the shipped artifacts. `model_layer` reports what actually happened, not what was configured: a key that is present but failing reports `"off"`, exactly like an explicit kill switch. |
| Anything else | **Nothing is a placeholder at ship time.** | Every watermark the build started with has been replaced by a real value; the completeness grep over `deliverables/` comes back empty. |

## What is not shown

One rule pack (`climate.v1.json`), one domain, 60 gold labels, one annotator whose blindness is
attested rather than provable, and no evidence at all about the four invented documents beyond
coverage. Three open probe defects are disclosed in `COMPARISON.md` and on the poster rather than
fixed quietly: `Scope 1/2/3` matched as a named standard (R-01), `quantity` blind to plain digit
magnitudes such as "$1 billion" (R-02), and `baseline_year` blind to two-digit fiscal years such as
`FY20` (R-04). The word-number miss ("halve") is deliberate and is pinned by a passing test.
