# Pledgecheck

> Which of this company's climate promises can anyone actually check?

Not "is this greenwashing" — that's a sentiment question a single prompt already answers badly
and differently every time you ask. **Checkability is a property of a sentence**, and a property
can be tested by code.

Pledgecheck runs a five-node workflow over corporate climate-pledge text. A model node splits the
text into atomic claims; a **deterministic Checkability Gate** — five pure-function probes over
versioned rule-pack data — decides whether each claim names a quantity, a target year, a baseline
year, a named standard, and an accountable party. The gate never asks a model anything. Turn the
model off entirely and every score, verdict and band stays byte-identical.

**Status:** complete. `./run.sh test` prints **81**. The three track deliverables are
`deliverables/flowchart.png` (the workflow poster), `deliverables/COMPARISON.md` (this workflow vs
a single-prompt baseline over the same 97 frozen claims, run three times each) and
`deliverables/NODES.md` (the reasoning behind each node). `deliverables/HONESTY.md` says what is
real and what is authored.

## Requirements

- Python **3.14** (stdlib only — no `pip install`, no venv, no `requirements.txt`)
- Node (for rendering the flowchart PNG via headless Chromium — see below)
- Optionally, a model provider key — only needed for the model layer; everything else runs
  with `PLEDGECHECK_NO_MODEL=1` or no key at all. Two providers are wired in, tried in order
  (`model/provider.py`): `GEMINI_API_KEY` in `/Users/shivang/Projects/common-ground/.env.local`,
  else `FEATHERLESS_API_KEY`/`FEATHERLESS_BASE_URL`/`FEATHERLESS_MODEL` in
  `/Users/shivang/Projects/deadline-agent/.env.local`. Neither is required; the deterministic
  Gate runs the same either way.

## Run it

```sh
cd pledgecheck
./run.sh test        # python3 -m unittest discover -s tests -v
./run.sh gate         # Arm A: run the Checkability Gate over the frozen claim set
./run.sh baseline     # Arm B: the steelmanned single-prompt baseline
./run.sh compare      # score both arms against gold labels -> deliverables/COMPARISON.md
./run.sh killswitch   # run the pipeline model-on and model-off, diff by sha256
./run.sh flowchart    # render deliverables/flowchart.html -> flowchart.png (headless Chromium)
./run.sh all          # the above, in order
```

## The kill switch

```sh
PLEDGECHECK_NO_MODEL=1 ./run.sh gate
```

produces a `deliverables/results.json` that is byte-identical (modulo `generated_at` and the
`explanation` field) to a run with the model on. `./run.sh killswitch` proves this in one command
and prints both sha256 hashes plus `DIFF: IDENTICAL`.

## Layout

```
core/        deterministic Checkability Gate — no model, no network, no framework.
             Allowed imports: re, json, hashlib, dataclasses, pathlib. Enforced by
             tests/test_purity.py (an AST scan that fails the build on a forbidden import).
rules/       versioned rule-pack data (climate.v1.json). Every clause carries a citation.
             core/ contains no domain literal — swap the pack, not the code.
model/       the only place in the repo that opens a socket. provider.py is the one public
             entry point (a registry of interchangeable providers — gemini.py, then
             featherless.py, then the deterministic fallback). Segments claims (N1) and
             writes the post-hoc rewrite (N5). Reads the score; can never change it.
corpus/      source documents and the frozen claim set (corpus/claims.frozen.jsonl).
harness/     run_gate (Arm A), run_baseline (Arm B), compare (pure arithmetic scoring
             of both arms against gold labels).
tests/       unittest suite. `./run.sh test` runs it.
deliverables/ the three artifacts this track requires: flowchart.png, COMPARISON.md,
             NODES.md — plus results.json and HONESTY.md.
docs/        spot-check, labelling rubric, flowchart spec, baseline prompt — the receipts.
```

## Secrets

Never committed. `.env*` is gitignored. `GEMINI_API_KEY` and the `FEATHERLESS_*` triplet are
each read from their `.env.local` file at call time, never hardcoded, never printed. Each
provider owns its own key resolution (`model/gemini.py`, `model/featherless.py`); nothing
outside `model/` ever sees a key.
