# Labelling rubric — Pledgecheck gold set v1

**Purpose.** This document defines, operationally, what each of the five checkability fields means
for a single extracted claim. It exists so that the gold labels in `corpus/gold.labels.json` are
reproducible by a second annotator who has never seen Pledgecheck's engine, and so that any
accuracy figure computed against those labels is a measurement rather than a restatement.

**Written and committed before a single label was assigned.** The commit timestamp of this file
precedes the commit timestamp of `corpus/gold.labels.json`; that ordering is the audit trail for
the blindness claim below.

---

## 0. Blindness protocol

The annotator (pc-red-team) labelled from the claim text and this rubric only. Before the labels
were written and committed, the annotator did not open, read, grep or otherwise inspect:

- `deliverables/results.json` or anything else under `deliverables/`
- `core/probes.py` or anything else under `core/`
- `rules/climate.v1.json` or anything else under `rules/`
- `docs/SPOT-CHECK.md` (excluded voluntarily: it may characterise probe behaviour)
- any `.crew/outbox/` note describing probe behaviour

The point is not ceremony. If the rubric is written by someone who already knows which claims the
engine gets right, the rubric silently deforms toward the engine and the resulting accuracy figure
measures nothing. A gold set is only worth the ignorance it was built under.

---

## 1. Two principles that govern every field

**Principle 1 — Semantic, not lexical.** These definitions describe what a careful human analyst
reads in the sentence. They are deliberately *not* written as pattern-matching rules. Where a
definition and a plausible regex diverge, the definition wins. This is what makes the gold set an
independent yardstick instead of a paraphrase of an implementation.

**Principle 2 — The claim text is the only evidence.** Each claim is labelled on its sentence
alone. The surrounding document, the neighbouring claims, and the record's own `org` and `doc_id`
metadata are **not** evidence and were not used. A claim reading "We will cut emissions in half"
does not get `accountable_party: true` because the JSON record happens to carry
`"org": "Microsoft Corporation"`. This is the single most consequential rule in the rubric: a
checkability gate exists to say whether *this sentence*, quoted on its own in front of a regulator
or a journalist, identifies who is on the hook. Reading in the metadata would make the field
almost always true and therefore useless.

**Disagreement is recorded, not resolved.** Where a claim is genuinely ambiguous under this
rubric, the label is still assigned by the rule, and the ambiguity is written into that claim's
`note` field. A documented ambiguity is data. A silent guess is noise.

---

## 2. `quantity`

**TRUE when** the claim states a specific numeric magnitude — an amount, rate, share, count,
duration or monetary sum — whether written in digits or spelled out in words.

Counts:
- Digits with or without a unit: `4.3 million metric tons`, `$1 billion`, `92`, `8 gigawatts`, `80%`
- Numbers spelled out as words: `Sixty-nine percent`, `One hundred percent`, `three`
- Word-expressed proportions naming a definite fraction: `more than half`, `nearly one-fifth`
- Bounded comparatives around a stated figure: `over 70 suppliers`, `less than 1 percent`
- Durations: `over the past 11 years`

Does **not** count:
- A calendar or fiscal year used as a date (`2030`, `FY24`, `since 1975`). A year is a point in
  time, not a magnitude. Years belong to `target_year` / `baseline_year` and are never quantities.
- Ordinal identifiers and labels that contain a digit but measure nothing: `Scope 1`, `Scope 2`,
  `Scope 3`, `IFRS S2`.
- Indefinite plurals with no figure: `thousands of suppliers`, `millions of athletes`.
- Vague magnitude language: `radically`, `ambitious`, `aggressive`, `significant`, `the bulk of`,
  `double down`, `at scale`.
- Goal-state terms that imply a number without stating one: `net zero`, `carbon neutral`,
  `carbon negative`. These name a destination, not a measured quantity.

> **Worked example — TRUE.** `cab9279cadc9` *"Sixty-nine percent reduction of absolute Scope 1 and Scope 2
> GHG emissions from Nike Operations in FY24, compared to a FY20 baseline."* → TRUE. The magnitude
> is spelled out rather than in digits; the rubric is semantic, so the spelling is irrelevant.
> Note that neither `FY24`, `FY20`, nor `Scope 1`/`Scope 2` contributes.
>
> **Worked example — FALSE.** `6b7e3bcfce48` *"We must radically reduce carbon emissions by transforming
> how we make our products."* → FALSE. `radically` is an intensifier, not a magnitude. Nothing
> here can be checked against a number.

---

## 3. `target_year`

**TRUE when** the claim names a specific calendar or fiscal year **by which a forward-looking
commitment is to be achieved**.

Counts:
- A year governed by a deadline preposition for a future commitment: `by 2030`, `by 2050`,
  `by FY2040`, `no later than 2035`
- A fiscal year used as a target label: `Near-Term, FY2030:`

Does **not** count:
- **The performance year of a result already achieved.** `in FY24`, `in 2019`, `last year`. A
  retrospective statement has no target year — the target field asks by when something *will* be
  done. This is the rubric's most consequential decision after Principle 2, because a large block
  of the corpus reports past performance, and a purely lexical reading would score those years as
  targets.
- A year inside a proper name or a document title: `the 2015 Paris Agreement`,
  `its 2020 Environmental Progress Report`.
- A year marking when something historically started: `in place since 2012`.
- The baseline year — that is a separate field, and no year is ever labelled as both on the same
  claim unless the claim genuinely states two distinct years in the two distinct roles.
- Relative or conditional deadlines with no year: `beginning next year`, `once completed`,
  `annually`, `each year`, `in the long run`.

> **Worked example — TRUE.** `d768f1626c96` *"Long-Term, FY2040: Reduce absolute Scope 1, 2, and 3 GHG
> emissions 90% by FY2040 from a FY2017 base year."* → TRUE. `FY2040` is the year by which the
> reduction is to be delivered. `FY2017` is not a target; it is the baseline, scored in §4.
>
> **Worked example — FALSE.** `e2e000e5964b` *"Apple decreased its carbon footprint by 4.3 million metric
> tons in 2019 through design and recycled content innovations in its products."* → FALSE. `2019`
> is the year the reported reduction happened, not a year by which anything is promised. The claim
> is an achievement, not a target.

---

## 4. `baseline_year`

**TRUE when** the claim names a specific calendar or fiscal year that serves as the **reference
point against which the change is measured**.

Counts:
- Explicitly labelled base years: `from a FY2017 base year`, `compared to a FY20 baseline`,
  `versus a FY20 baseline`
- A year naming the start of the accounting period for a cumulative total, where that year anchors
  the measurement (see the ambiguity flagged below)

Does **not** count:
- A year that appears only as history, with no comparative role in the measurement:
  `our internal carbon fee, in place since 2012` — 2012 dates a programme, it is not the reference
  point of any stated reduction.
- Relative spans with no named year: `over the past decade`, `over the past 11 years`.
- The target year.
- A year in a document title or proper name.

> **Worked example — TRUE.** `11e64368bcac` *"Thirty-six percent reduction of absolute Scope 3 GHG
> emissions from Nike's manufacturing and transportation in FY24, versus a FY20 baseline."* →
> TRUE. `FY20` is explicitly named as the baseline. (`FY24` is the performance year and is not a
> target year — see §3.)
>
> **Worked example — FALSE.** `280e8280df99` *"We will fund this in part by expanding our internal carbon
> fee, in place since 2012 and increased last year..."* → FALSE. `2012` is when a fee started. No
> reduction is being measured from it, so it is not a baseline.

**Flagged ambiguity, applied consistently.** A cumulative-since-founding claim
("remove all the carbon the company has emitted ... since it was founded in 1975") is labelled
`baseline_year: true`, on the ground that 1975 is the reference year anchoring the measurement.
A stricter reading — that a baseline year requires an explicit reduction-from comparison — would
label it false. Both are defensible; this rubric takes the anchoring reading, and every affected
claim carries the ambiguity in its `note`.

---

## 5. `named_standard`

**TRUE when** the claim invokes, **by name**, an external framework, standard, protocol,
methodology or international agreement.

Counts:
- `Science Based Targets Initiative`, `SBTi`, `Paris Agreement`, `GHG Protocol`, `TCFD`, `ISSB`,
  `IFRS S2`, `CDP`, `ISO 14001`, `RE100`
- The name is sufficient on its own; an accompanying abbreviation is not required.

Does **not** count:
- **Categories defined by a standard, where the standard itself is not named.** `Scope 1`,
  `Scope 2`, `Scope 3`. Scopes are defined by the GHG Protocol, but the sentence does not name the
  GHG Protocol, and a reader cannot cite what has not been named. This is a high-frequency
  decision in this corpus and is applied without exception.
- **First-party documents and internal programmes**, however official-sounding:
  `Environmental Sustainability Report`, `2020 Environmental Progress Report`,
  `Supplier Energy Efficiency Program`, `Climate Innovation Fund`. A standard the company wrote
  about itself is not an external standard.
- **Unnamed gestures at standards** — the paraphrase case: `based on strong global reporting
  standards`, `the latest science`, `robust target-setting`.
- Product and technology brands: `Dri-FIT`, `ReactX`.
- Goal-state terms: `net zero`, `carbon neutral`, `1.5 degrees Celsius`. A temperature threshold
  is a goal, not a named standard — unless the agreement that sets it is itself named.

> **Worked example — TRUE.** `711fa04baf9f` *"We have set ambitious goals ... in alignment with a set of
> standards provided by the Science Based Targets Initiative (SBTi)."* → TRUE. The standard-setter
> is named in full and abbreviated. A reader can go and check the register.
>
> **Worked example — FALSE.** `d0737a78d272` *"We will publish an annual Environmental Sustainability
> Report that provides transparency on our progress, based on strong global reporting standards."*
> → FALSE, twice over. The report is a first-party document, and `strong global reporting
> standards` names no standard at all. This sentence sounds maximally accountable and cites
> nothing — exactly the failure mode the field exists to catch.

---

## 6. `accountable_party`

**TRUE when** a **named** party can be identified from the claim text as the one bearing the
commitment, action or result that the claim asserts.

Counts:
- A named organisation as the agent: `Apple today unveiled its plan...`, `Nike is relentlessly
  innovating...`
- A possessive or attributive naming the same party the claim is about: `Microsoft's carbon
  footprint`, `every Apple device sold`, `Nike's global operations`
- A named role or governing body designated as responsible: `the Chief Sustainability Officer`,
  `the Board's Audit Committee`
- A named person

Does **not** count:
- **An unnamed pronoun or definite description as the only agent**: `we`, `our company`,
  `the company`, `our suppliers`, `those of us who can afford to`. Per Principle 2, the record's
  `org` metadata does not rescue these.
- Generic collectives: `government and industry`, `other companies`, `the world`.
- A named entity appearing only in a **subordinate role** — as a standard-setter, a citation, a
  beneficiary or a source — while the party actually doing the thing is unnamed. In *"We have set
  goals ... in alignment with standards provided by SBTi"*, SBTi is named but SBTi is not the
  party who set the goals; the agent is an unnamed `We`. FALSE.
- Imperative or headless target fragments with no subject: *"Reduce absolute Scope 3 GHG emissions
  ... 55% by FY2030 from a FY2017 base year."*

> **Worked example — TRUE.** `11c31341167b` *"By 2030 Microsoft will be carbon negative."* → TRUE.
> The main-clause subject is a named legal entity. Quoted alone in front of anyone, this sentence
> says who is on the hook.
>
> **Worked example — FALSE.** `ed45cc49608c` *"We are launching today an aggressive program to cut our
> carbon emissions by more than half by 2030, both for our direct emissions and for our entire
> supply and value chain."* → FALSE. The quantity is there and the target year is there, but the
> only agent is `we`. Lift this sentence out of its press release and it names nobody — which is
> precisely the information a checkability gate should surface.

**Flagged ambiguity, applied consistently.** Where a named third party is the *main-clause
subject* of a descriptive sentence (*"SBTi uses three scopes..."*), the field is TRUE: the action
the claim asserts is attributed to a named party. That party is not the pledging company, and a
reader wanting to know who is accountable for the *pledge* learns nothing. The rule is applied
mechanically for consistency, and every affected claim carries the caveat in its `note`.

---

## 7. Scope and coverage of the gold set

Labels cover the **first 60 claims** of `corpus/claims.frozen.jsonl` (of 97 frozen). Claims 61–97
are deliberately unlabelled and **must be excluded from every accuracy figure** — they are
reportable as coverage only.

One consequence must be stated plainly wherever these labels are used: the first 60 claims span
the four **real-company** documents only (Microsoft 17, Apple 13, Nike 13, Patagonia 17). The four
invented organisations sit entirely in the unlabelled tail. Accuracy computed on this gold set is
therefore accuracy **on verbatim real-world corporate climate language**, which is the harder and
more meaningful half — but it is not evidence about the synthetic documents, and no claim about
them may be supported by these numbers.
