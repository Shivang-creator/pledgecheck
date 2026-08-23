# NODES — the reasoning behind each node in the workflow

*Deliverable 3 of 3 for the ML & Prompt Engineering track. Deliverable 1 is
`deliverables/flowchart.png`; Deliverable 2 is `deliverables/COMPARISON.md`.*

---

"We will halve embodied carbon in our products by the end of the decade."

We wrote that one. It comes from one of the four pledge documents in this corpus that are
invented, and it is invented deliberately: the worked example that ends up in a screenshot should
not have a real company's name on it. It is written in the register of the four real reports
sitting beside it and you would not pick it out of a line-up with them. Read it as a person and it
sounds like a commitment. Read it as an auditor and there is nothing in it to hold. No figure you
could measure against, no year you could arrive at, no baseline the reduction runs from, no
standard that defines what "embodied carbon" counts, and nobody named who answers for it if it
does not happen. It scores zero out of five here.

**Checkability is a property of a sentence, not an opinion about a company.** That one line placed
every node in this workflow. A property of a sentence can be decided by code, and the moment you
decide it by code you owe the reader a reason, a rule, and a citation for the rule. An opinion can
only be asked for, and it comes back different every time you ask.

So the workflow has five nodes and one rule about where they sit: **a model may read the text and
write the prose, but only code may produce a verdict.** N1 and N5 are model nodes at the two ends.
N2, N3 and N4 are the middle, and the middle never opens a socket. Below, each node answers the
same six questions in the same order, and the second question is the one that actually matters.

Every number quoted here was produced by a command that ran on the night of 23–24 August 2026.
`./run.sh test` prints **67**, and every test named below exists in `tests/`.

---

## N1 — SEGMENT · model layer

**What it does.** Takes one document's raw text and returns a list of atomic claim sentences, each
copied verbatim from the source. Nothing is summarised, paraphrased or invented; the prompt in
`model/segment.py` says so in those words, and we checked afterwards rather than trusting it.

**Why it sits on the model side.** Splitting a corporate sustainability report into claims is not a
punctuation problem. These documents are full of bullet fragments with no terminal period, headings
that read like pledges, and sentences carrying two separate commitments joined by "and". A regex
splitter gets those wrong in ways that quietly change what is being scored. We kept a crude regex
splitter in the repo anyway (`harness/run_gate.py::_naive_sentence_split`) so you can see exactly
what the model is being asked to beat, and so there is somewhere to fall back to. Reading language
without a rule that decides it in advance is the thing a model is genuinely good at.

**And why it runs exactly once.** N1 is also the node where a model's variability would do the most
damage, because everything downstream inherits it. So it ran one time, over eight documents, and
its output was committed to `corpus/claims.frozen.jsonl`. Every rerun, both comparison arms, the
kill switch and every table in this packet read that file. `harness/freeze_corpus.py` exits with
status 1 if the file already exists, so the freeze is enforced in code rather than left as a
convention someone could break by pressing up-arrow and enter.

This is what makes the rest of the packet mean anything. If N1 ran on every invocation, the
model-on and model-off runs would not be scoring the same claims, and a matching hash would prove
nothing at all. The same goes for the comparison: both arms answer the same 97 frozen claims, so
the only variable between them is the workflow. It also means imperfect extraction does not
invalidate the comparison. Both arms get the same imperfect claims.

**What it reads.** `corpus/documents.json` — eight documents, four real ones held verbatim with
their source URL and fetch timestamp, four openly invented and tagged `Simulated`.

**What it returns.** A JSON array of strings per document, written out as 97 lines of
`{claim_id, doc_id, org, provenance, text}`.

**When it fails, and when the model is off.** `segment_document` returns `None` on a kill switch, a
dead provider, or a response that is not a JSON array of strings, and the freeze falls back to the
naive splitter for that document alone. The end-of-run report says which source produced each
document's claims, so a fallback can never be mistaken for real segmentation. In normal operation
with `PLEDGECHECK_NO_MODEL=1`, N1 is not called at all: the pipeline reads the frozen file.

**What we found and published rather than fixed.** All 97 claims were mechanically checked for
being exact whitespace-normalised substrings of their source document, which is a stronger
guarantee than reading twenty of them by hand: no figure, date or standard name could have been
altered anywhere without breaking the match. 92 passed outright. The five that did not are all
legitimate compound-sentence splits, written up one by one in `docs/SPOT-CHECK.md`. Three claims
are section headings that read as pledges in isolation. They are still in the frozen set, flagged,
because editing the frozen file to make our own numbers nicer is exactly the move this
architecture exists to make impossible.

**Pinned by.** `tests/test_corpus.py::test_claim_ids_are_stable_hashes_of_the_normalised_text` ·
`test_no_duplicate_claim_ids` · `test_claim_count_matches_the_manifest_once_the_corpus_is_frozen`.

---

## N2 — NORMALISE · deterministic core

**What it does.** Collapses whitespace, assigns each claim a stable id, and carries the document's
provenance tag through untouched.

**Why it sits on the code side.** An id has to survive. `core/scoring.claim_id` is the first twelve
hex characters of the sha256 of the normalised text, which means the same sentence gets the same id
on a different machine, in a different month, with no API key present. That is not a convenience.
The blind gold labels are keyed by claim id, so if ids drifted between runs the labels would stop
pointing at the claims they were written against, and every accuracy figure in the comparison would
silently become meaningless. Beyond that, normalisation is a fully specified operation. There is
nothing here to judge, and a node with nothing to judge has no business calling a model.

**What it reads.** One line of `corpus/claims.frozen.jsonl`.

**What it returns.** The normalised text, its `claim_id`, and the `doc_id` / `org` / `provenance`
fields passed through to the output so results can be grouped by document later.

**When it fails, and when the model is off.** Identical, always. It is a pure function of a string,
so it has no failure mode involving the outside world. The one failure that would matter is a
duplicate id, which would mean two claims collapsing into one row.

**Pinned by.** `tests/test_corpus.py::test_every_claim_carries_a_provenance_tag` ·
`test_every_provenance_tag_is_in_the_legal_set` ·
`tests/test_engine.py::test_two_identical_inputs_give_identical_output`.

---

## N3 — CHECKABILITY GATE · deterministic core

**What it does.** Runs five probes against the claim text and returns a verdict for each:
`quantity` (C1-QTY), `target year` (C2-TGTYR), `baseline year` (C3-BASEYR), `named standard`
(C4-STD), `accountable party` (C5-ACTOR). Each verdict carries whether the element is present, the
exact character span that matched, the rule-pack clause id, and that clause's citation. Five
verdicts make a score out of five and a band.

**Why it sits on the code side. This is the whole argument.** N3 is the node almost everyone would
build as a prompt, and there are three reasons it is not one here.

*The question is closed.* "Is there a year in this sentence a reader would take as the target date"
has an answer that does not change when you ask it a second time. Our single-prompt control arm was
given the identical claims and the identical question three times, and it changed its
checkable-or-not answer on 8 of the 97 claims depending only on which of three calls happened to
answer it. The Gate returned the same verdicts all three times, because it cannot do anything else.
The numbers and the method are in `deliverables/COMPARISON.md`.

*A verdict has to come with something you can argue with.* When C4-STD fires, the output says which
characters of the sentence it matched and which clause of the rule pack it fired under. You can
read that and tell us we are wrong, and sometimes you would be right (see below). "The model
assessed this claim as checkable" gives you nothing to push against.

*The decision has to be editable by someone who does not write Python.* Every literal that decides
a verdict lives in `rules/climate.v1.json`: the regexes, the year ranges, both lexicons, the band
thresholds, and the citation text for each clause. `core/probes.py` contains no climate vocabulary
at all. This is also where the domain expertise formally enters the pipeline, and it is the only
place it does. Each clause cites the standard that says the element is required: GHG Protocol ch.9
for a quantified amount, SBTi Corporate Net-Zero v1.2 §4.2 for a target year, GHG Protocol ch.5 for
a baseline, TCFD 2017 for naming the standard, ISSB IFRS S2 §6 for the accountable body. A person
wrote those clauses and cited them, once, before the run. Nobody can tune the Gate while it is
running.

**What it reads.** The claim text, plus this clause's `params` and the pack's shared `lexicons`.
Nothing else. It does not know which document the claim came from, which company wrote it, or what
any other claim scored.

**What it returns.** `{present, span, matched, clause_id, citation}` for each of the five probes in
pack order, a score, a max score, and the pack version stamped into the output. Across the 97
frozen claims the probes fire 26, 24, 13, 21 and 11 times respectively, which is itself the finding:
most of these sentences are missing most of what would make them checkable.

**When it fails, and when the model is off.** Identical with the model off, byte for byte. Its
failure modes are all about the rule pack, and they are all loud. A pack naming a probe the engine
does not implement raises rather than scoring that clause absent. A clause with an empty citation
refuses to load at all. A Gate that quietly scores a claim zero because its own rules were broken
is worse than a Gate that stops.

**Where the Gate is wrong, on the record.** `quantity` misses word numbers such as "halve" and
"double", which is a deliberate narrowness with a passing test asserting the miss. It also misses
plain digit magnitudes like "$1 billion", because the regexes cover percentages, mass and energy
units and nothing else. That one is not deliberate, it is a gap, and it is open. And
`named_standard` fires on "Scope 1" and "Scope 3", which are defined by the GHG Protocol but are
not themselves a named standard. That is five false positives on the labelled slice and it is open
too. Both are written up in `deliverables/COMPARISON.md` rather than fixed quietly at 3am.

**Pinned by.** `tests/test_probes.py`, thirty tests, six per probe: present, absent, boundary,
negation, unicode and typography, and the known weakness asserted as a miss rather than papered
over. Specifically `test_quantity_misses_word_numbers_like_halve` and
`test_named_standard_misses_paraphrased_standard_language`. Also
`tests/test_engine.py::test_verdict_ordering_always_follows_pack_order`,
`test_unknown_probe_name_raises`, and
`tests/test_purity.py::test_core_never_contains_http_substring`.

---

## N4 — AGGREGATE · deterministic core

**What it does.** Rolls the per-claim scores up into a per-document checkability rate, a band for
each claim from the pack's thresholds, and a corpus-level rate with its band distribution.

**Why it sits on the code side.** The arithmetic is trivial, so the interesting question is why we
did not ask a model to write the summary. Because the summary is the part that gets quoted. It is
the sentence that ends up in a headline, a slide or a screenshot, and it is therefore the last
place in the pipeline you want a number nobody can rederive. Every figure in this packet can be
recomputed from `deliverables/results.json` with a few lines of Python. The bands live in the rule
pack too, so "what counts as Mostly Checkable" is a cited, editable decision rather than a
threshold buried three functions deep.

**What it reads.** The scored claims and the pack's `bands`.

**What it returns.** Per-document rates, a corpus rate, and a count of claims in each band.

**When it fails, and when the model is off.** Identical with the model off. `band_for_score` raises
if no band in the pack covers a score, instead of inventing a label like "unknown". A pack with a
hole in its bands is a broken pack and should say so on the first claim, not the hundredth.

**What the roll-up actually found.** Under this rule pack's definition of an accountable party (a
named role or governance body, not merely the company's own name), the probe fires on **none of the
60 verbatim claims** taken from the four real reports. All eleven of its hits sit in the four
documents we invented ourselves. Sixty real sentences, and not one names a role or a body that
answers for the promise inside it.

That is a statement about sentences, not about sincerity, and it comes with one caveat. A second
careful reader, working blind from the same claims, wrote a rubric counting a named organisation as
the accountable agent, and under that reading the finding changes on 29 of 60 claims. Both
rubrics are in git with timestamps, written before either reader saw the other's file. We report
both definitions rather than picking the one that flatters us, and the disagreement is honestly the
more interesting result: two careful people read the same corporate pledges and did not agree on
what "accountable" means.

**Pinned by.** `tests/test_engine.py::test_band_thresholds_from_the_real_pack_cover_every_reachable_score` ·
`test_score_arithmetic_counts_one_point_per_present_probe` ·
`test_rule_pack_version_is_asserted_in_output`.

---

## N5 — EXPLAIN · model layer

**What it does.** For every claim the Gate could not fully verify, writes one sentence rewriting it
to add only the missing elements, with a placeholder in square brackets for anything the original
did not contain. A 4-out-of-5 claim missing its accountable party comes back as the same sentence
with ", overseen by [Accountable Party]" attached, in the register of the original.

**Why it sits on the model side.** This is the one job in the workflow with no right answer. There
is no rule that produces a good rewrite, only a hundred acceptable ones, and picking a phrasing
that sits naturally in someone else's sentence is a language task through and through. It is also
the node with the most obvious commercial pull toward letting the model do more, which is why the
constraint is structural rather than a policy we promise to keep. `explain_claims` is called in
`harness/run_gate.py` after `evaluate` has already returned. It receives claim dictionaries and
returns a `{claim_id: string}` map. It has no way to return a number, a verdict or a band, and the
only thing it can put in the deliverable is a string in a field called `explanation`, tagged
`Generated`. The rewrite is the model's. The score is not.

**What it reads.** The claim text and the list of clause ids the Gate marked absent, batched fifteen
claims per call.

**What it returns.** One rewrite per claim. In the shipped `results.json`, 93 of the 97 claims carry
a real one, all served by Featherless (`DeepSeek-V3-0324`) after Gemini's free tier hit its daily
cap on the first call of the freeze. Both provider ids appear on the poster; nothing in this packet
claims a call that did not happen.

**When it fails, and when the model is off.** Every claim in a failed batch gets the literal string
`[model layer disabled]`, and the provider that failed has already written the reason to stderr. The
`model_layer` field in `results.json` reports what actually happened rather than what was
configured: a key that is present but returns errors reports `"off"`, exactly like an explicit kill
switch, because an API that is quietly dead must never be able to look like a success.

**The proof, in one command.** `./run.sh killswitch` runs the whole pipeline twice, once with the
model on and once with `PLEDGECHECK_NO_MODEL=1`, and hashes both results. It prints
`DIFF: IDENTICAL`. 93 explanations vanish and not one verdict moves.

**Pinned by.** `tests/test_killswitch.py::test_scores_identical_with_model_on_and_off` ·
`test_results_json_sha256_matches_model_on_and_off` ·
`test_verdicts_identical_across_gemini_featherless_and_off` ·
`test_model_layer_is_off_when_kill_switched_or_the_model_fails` ·
`test_model_fallback_path_logs_loudly_to_stderr`.

---

## The boundary, file by file

The line is not a diagram. It is a list, and a test that enforces it.

```
DETERMINISTIC — no network, no model, Python stdlib only
  core/probes.py              the five probes
  core/engine.py              rule-pack loader and gate evaluation
  core/scoring.py             normalisation, ids, bands, roll-ups
  rules/climate.v1.json       versioned data; every clause carries a citation
  harness/compare.py          scoring both arms against gold; arithmetic only

MODEL — the only place a socket is opened
  model/provider.py           the registry and the single kill-switch check
  model/gemini.py             provider
  model/featherless.py        provider
  model/segment.py            N1
  model/explain.py            N5
```

`tests/test_purity.py` walks every file under `core/` with Python's `ast` module, collects every
import statement, and fails the build if anything appears outside the allowlist of `re`, `json`,
`hashlib`, `dataclasses` and `pathlib`. Two more tests in the same file assert that nothing in
`core/` reads `os.environ` and that no file under `core/` contains the substring `http`. That test
file is worth more than this paragraph describing it, because it is the version of this claim that
keeps being true after everyone goes to bed.

The boundary got tested for real tonight, by accident. Gemini's daily quota ran out on the first
call of the freeze, so a second provider had to be added mid-build. That took one new module
(`model/featherless.py`, the same `call(prompt, *, timeout=60) -> str | None` shape as the first
provider), one line added to the `PROVIDERS` tuple in `model/provider.py`, and a one-line import
change in each of `model/segment.py` and `model/explain.py`. Nothing in `core/` changed. The purity
test passed unmodified, which we verified by running it rather than by assuming it. If swapping the
model backend had required touching the Checkability Gate, that would have been the signal the
boundary was drawn in the wrong place. It didn't.

The same property is what makes the domain swap real rather than aspirational. Replace
`rules/climate.v1.json` with a rule pack for hiring pledges and you get five different probes with
five different citations, the same engine, and the same flowchart.

---

## What we would change with another day

**Fix the two open probe defects instead of only disclosing them.** "Scope 1" and "Scope 3" should
come out of the standards lexicon and get a probe of their own, because scope coverage genuinely is
an auditability element, just not a named standard. The `quantity` regexes should cover currency
amounts and bare magnitudes. The word-number miss ("halve", "double") we would leave exactly where
it is, pinned by its passing test, because that one is a real judgement call about what counts as
quantified and it deserves to stay visible.

**Agree the `accountable_party` rubric before labelling, not after.** Two blind readers wrote
opposite definitions of "accountable" and that choice moves 29 of 60 claims. Fixing it properly
needs a rubric settled in advance and a labeller who has not read anything else in the repo, and
there was no uncontaminated reader left before the deadline. So both constructs are reported side
by side, which is the honest option available tonight but not the one we would choose with time.

**Make provider attribution per claim instead of per call.** `providers_used` records which backend
answered a call, not which backend wrote a given sentence. N5 batches fifteen claims per call, so if
a batch's JSON failed to parse after a provider answered, that provider would still be recorded
while every claim in the batch fell back to the placeholder. Tonight one provider served every
call, so the coarser signal is accurate. It is exactly the kind of shortcut that stays honest right
up until the day it doesn't.

---

The sentence we started with still scores zero out of five, and part of that zero is our fault
rather than the sentence's: "halve" is a quantity to any reader, and this Gate cannot see it. The
test that says so is green, the miss is on the poster, and the rewrite our model suggests for it
does not move the score by a single point. That is the arrangement. The model reads the report and
writes the prose. The code says what can actually be checked, names the clause it checked against,
and shows you the characters it matched, whether or not the model is switched on at all.
