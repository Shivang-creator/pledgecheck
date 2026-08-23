# Labelling rubric — gold checkability labels (T-08)

Written **blind**: before opening `deliverables/results.json`, `core/probes.py`, or
`rules/climate.v1.json`. These are independent operational definitions, derived from domain
knowledge of corporate climate-pledge disclosure practice (GHG Protocol / SBTi / TCFD / CDP
conventions), not from reading the Gate's implementation. Applied to the first 60 claims of
`corpus/claims.frozen.jsonl` in file order.

A claim is judged **sentence-by-sentence, in isolation** — exactly as a probe over one claim's
text would see it, with no context from neighbouring sentences in the same document. A claim that
reads as checkable only because a prior or following sentence supplies the missing piece is still
labelled on what *this* sentence alone states.

For every field: **TRUE** requires the specific value to be stated in the sentence's own text, in
a form precise enough that a third party could go and check it against a real record (an
emissions inventory, an annual report, a standard's published text). A generic or qualitative
gesture in the right direction (an adjective like "ambitious," "aggressive," "significant," or a
vague noun like "a plan," "our goals," "strong standards") is **FALSE** — vagueness is exactly
what these five fields exist to catch.

## 1. `quantity`

**TRUE** if the sentence states a specific numeric magnitude that quantifies the size, scope, or
degree of the action, target, or measured outcome being described: a percentage, an absolute
count, a monetary figure, a physical unit (tons, MWh, square feet, gigawatts), or a precise
proportional/multiplier **word** with an unambiguous numeric meaning ("half" = 50%, "double" =
2×, "triple" = 3×) used **literally**, not idiomatically ("double down on our work" is an idiom
for "intensify," not a literal 2× claim, and is FALSE).

A bare count of the *actors involved* (e.g. "thousands of suppliers," "millions of athletes") does
**not** count unless that number itself is the thing being pledged/measured — it describes scale
of the business, not a checkable magnitude of the climate commitment.

- **Worked example, TRUE** — claim 6 (`ed45cc49608c`, Microsoft): *"We are launching today an
  aggressive program to cut our carbon emissions by more than half by 2030..."* → TRUE. "more than
  half" is a specific, checkable proportion (≥50%) even though it is spelled as a word, not a
  digit — a human fact-checker can verify "was the cut actually ≥50%?" the same way as with "52%."
  (Note for T-10: a regex-only probe is likely to miss this one; that gap is the whole point of an
  independent gold label.)
- **Worked example, FALSE** — claim 5 (`5a897608855e`, Microsoft): *"We recognize that progress
  requires not just a bold goal but a detailed plan."* → FALSE. "bold" and "detailed" are
  qualitative; no number, proportion, or unit of any kind is present.

## 2. `target_year`

**TRUE** if the sentence states an explicit calendar or fiscal year (e.g. "2030," "FY2030") that
is the **future due date by which a commitment is to be achieved**. A year that is (a) historical
— when something already happened or began (a founding date, a policy's start date, a past
reporting year describing an *already-achieved* result) or (b) a relative/undated reference
("next year," "last year," "the past decade") with no explicit numeral in the sentence, is FALSE.
A publication/report title year (e.g. "our 2020 Environmental Progress Report") is also FALSE for
this field — it dates the document, not the target.

- **Worked example, TRUE** — claim 3 (`11c31341167b`, Microsoft): *"By 2030 Microsoft will be
  carbon negative."* → TRUE. 2030 is explicitly the future date the state is to be reached by.
- **Worked example, FALSE** — claim 7 (`280e8280df99`, Microsoft): *"We will fund this in part by
  expanding our internal carbon fee, in place since 2012 and increased last year..."* → FALSE.
  2012 is when the fee began (historical), not a due date for a commitment; "last year" carries no
  explicit numeral at all.

**Judgment call flagged for T-10**: a sentence reporting an *already-achieved* metric in a past
year (e.g. "...in FY24," "...in 2019") is labelled `target_year: FALSE` even though a year is
present, because the year is not a forward-looking due date. This affects several Nike and Apple
claims below (achieved-to-date reporting, not forward pledges) — see the per-claim notes.

## 3. `baseline_year`

**TRUE** if the sentence explicitly names a year used as the **reference/starting point against
which a stated change is measured** — the "from," "since," "versus," or "compared to" year in a
reduction or increase claim (e.g. "80% by FY2030 **from a FY2017 base year**," "**compared to a
FY20 baseline**"). A historical year that merely scopes *what counts* (e.g. "all carbon emitted
since it was founded in 1975") is FALSE unless it is tied to a stated quantified change relative to
that year. A duration with no explicit year ("over the past decade," "over the past 11 years") is
FALSE — it names a length of time, not a year.

- **Worked example, TRUE** — claim 32 (`cab9279cadc9`, Nike): *"Sixty-nine percent reduction of
  absolute Scope 1 and Scope 2 GHG emissions from Nike Operations in FY24, compared to a FY20
  baseline."* → TRUE. FY20 is explicitly named as the comparison point for the 69% figure.
- **Worked example, FALSE** — claim 4 (`418e7ea6ab02`, Microsoft): *"By 2050 Microsoft will remove
  from the environment all the carbon the company has emitted either directly or by electrical
  consumption since it was founded in 1975."* → FALSE. 1975 defines the cumulative scope of "all
  carbon ever emitted," not a base year for a percentage reduction — there is no stated rate of
  change relative to 1975, just a running total since then.

## 4. `named_standard`

**TRUE** if the sentence names a **specific, externally recognised** standard, protocol,
methodology, certifying/validating body, or accord by its proper name or well-known acronym — e.g.
GHG Protocol, Science Based Targets initiative / SBTi, Scope 1 / Scope 2 / Scope 3 (these are
defined categories of the GHG Protocol, not generic prose), TCFD, ISSB / IFRS S2, ISO 14064, CDP,
CSRD, the Paris Agreement. A generic reference to standards ("strong global reporting standards,"
"the latest science") without naming one is FALSE. A company's **own internal program name** (its
own supplier initiative, its own product-technology name) is FALSE — it is not an external,
third-party-auditable standard, no matter how official it sounds internally.

- **Worked example, TRUE** — claim 52 (`711fa04baf9f`, Patagonia): *"...in alignment with a set of
  standards provided by the Science Based Targets Initiative (SBTi)."* → TRUE. SBTi is named
  explicitly.
- **Worked example, FALSE** — claim 17 (`d0737a78d272`, Microsoft): *"We will publish an annual
  Environmental Sustainability Report that provides transparency on our progress, based on strong
  global reporting standards."* → FALSE. "strong global reporting standards" names no specific
  framework at all.

## 5. `accountable_party`

**TRUE** only if the sentence names a **specific organisational role, title, or governance body**
as responsible for the commitment or its oversight — e.g. "the board," "CEO," "chief
sustainability officer," "Audit Committee," "Executive Committee." The organisation's own name or
a bare "we"/"our company" as the grammatical subject of the pledge does **not** count — that is
true of nearly every sentence in a pledge document and would make the field meaningless if it
counted. The bar is a **named role or body distinguishable from the organisation as a whole**, not
just "the company will do X." A vague reference to a person without a title ("a senior executive
signed off") is also FALSE — there is no specific, checkable title to hold accountable.

- **Worked example, TRUE** — claim `e34f9c46c9dc` (index 66, outside the labelled 60, used here
  only because no claim within claims 1–60 contains a positive case — see note below): *"Our Chief
  Sustainability Officer will oversee a 15,000 MWh reduction in facility energy use by 2027,
  relative to a 2021 baseline..."* → TRUE. "Chief Sustainability Officer" is a specific,
  named accountable role.
- **Worked example, FALSE** — claim 51 (`a9b067c0f5e5`, Patagonia): *"We take responsibility for
  all of it."* → FALSE. The sentence explicitly invokes responsibility, which makes it a good
  contrast case, but the party taking responsibility is only "we" (Patagonia collectively) — no
  named role or governance body is given.

**Important finding, flagged loudly for T-10**: none of the first 60 claims (the four *Observed*
real-company documents — Microsoft, Apple, Nike, Patagonia) contain a positive
`accountable_party` case. Every occurrence of a named role/committee (Sustainability Committee,
Chief Sustainability Officer, Executive Committee, board of directors, CFO, Audit Committee, chief
executive officer) in the frozen corpus falls in claims 61–97, all from the four *Simulated*
fixture documents. This means, in the 60-claim gold set, `accountable_party` is TRUE for **zero**
claims — its precision/recall on this slice can only be computed on the trivial "always predict
FALSE" baseline. This is a real property of the corpus, not a labelling artefact; T-10 should
report it rather than silently produce a 0/0 or divide-by-zero figure for this one field.

## General notes applied throughout

- Section-heading-shaped fragments (e.g. "Taking responsibility for our carbon footprint.",
  "Investing for new carbon reduction and removal technology.", "Ensuring effective
  transparency.") are labelled on their own text like any other claim — they contain no checkable
  fields as standalone sentences, and are labelled FALSE across the board, consistent with
  `docs/SPOT-CHECK.md`'s observation that these are heading fragments, not full pledges.
- A number that quantifies something *other* than the pledge itself (a count of suppliers, a
  taxonomy of "three scopes," a report's title year) is not counted toward `quantity`,
  `target_year`, or `baseline_year` for that other thing — only the pledge's own magnitude/date
  counts.
- A specific degree threshold tied to a stated target ("1.5 degrees Celsius") **is** counted as
  `quantity: TRUE` even when it originates from an external accord (the Paris Agreement) rather
  than being the org's own original number — it is still a precise, checkable figure the org
  states it is committing to.
