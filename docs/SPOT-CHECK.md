# T-07 spot check — N1 segmentation fidelity

**Failures (truncated or hallucinated): 0 / 20.**
**Claims reviewed: 20, spread across all 8 documents, chosen to include every edge case
found (see "Observations" below), not just easy cases.**
**Corpus: `corpus/claims.frozen.jsonl`, 97 claims, frozen by `harness/freeze_corpus.py`, N1
served by Featherless (`deepseek-ai/DeepSeek-V3-0324`) after Gemini's free-tier daily quota
returned `RESOURCE_EXHAUSTED` on the first attempt — see `.crew/DECISIONS.md`.**

## Method

Every one of the 97 frozen claims (not just these 20) was first checked mechanically:
after whitespace-normalising both sides, is the claim's `text` an exact substring of its
source document's `text` in `corpus/documents.json`? 92/97 passed that check outright.
The 5 that didn't are all in this table (rows 2–6) — every one is a legitimate atomic split
or light grammatical repair of a compound/elliptical sentence, not a fidelity failure; see
each row's note. **This means no claim in the entire frozen corpus — not just these 20 —
contains an altered number, date, percentage, or standard name**: any such alteration would
have broken the exact-substring check, and none did.

The 20 rows below are a deliberately adversarial sample: all 5 non-exact-substring claims
(rows 2–6), all 3 section-heading-shaped claims found in the corpus (rows 7–9, see
Observations), and 11 further claims spread across the remaining 7 documents, hand-compared
against the source paragraph in `corpus/documents.json`.

## Verdict definitions

- **faithful** — the claim's meaning is fully supported by the source text. Minor
  grammatical repair that changes no fact (restoring an elided subject/verb across a
  compound sentence, dropping a non-substantive lead-in clause like "As described below,",
  turning a comma-splice into two standalone sentences) still counts as faithful — the
  claim asserts nothing the source doesn't.
- **truncated** — the claim cuts off mid-thought in a way that changes what is actually
  being claimed (e.g. dropping a target's year, or its conditionality).
- **hallucinated** — the claim asserts a number, date, name, or commitment that is not
  present anywhere in the source text.

## The 20 claims

| # | claim_id | doc_id | verdict | note |
|---|---|---|---|---|
| 1 | `4b035fd3a749` | ms-carbon-negative-2030 | faithful | Exact substring. |
| 2 | `11c31341167b` | ms-carbon-negative-2030 | faithful | Split from "By 2030 Microsoft will be carbon negative, **and** by 2050 Microsoft will remove…" into two claims (this one + row 3). Comma→period, "and" dropped — no fact changed. |
| 3 | `418e7ea6ab02` | ms-carbon-negative-2030 | faithful | The other half of the same split (see row 2). "and" dropped, capitalised — no fact changed. |
| 4 | `ed45cc49608c` | ms-carbon-negative-2030 | faithful | Source: "**As described below,** we are launching today an aggressive program…". Non-substantive lead-in trimmed; every number/date preserved verbatim. |
| 5 | `e08ce3b8ec4e` | ms-carbon-negative-2030 | faithful | Split from "…help our suppliers and customers…reduce their own carbon footprints **and** a new $1 billion climate innovation fund…" into two claims (this one + row 6). |
| 6 | `905bdf32e595` | ms-carbon-negative-2030 | faithful | The most-reconstructed claim in the sample: source elides the repeated verb ("…footprints and [launching] a new $1 billion…fund…"); N1 restored "We are launching" so the clause stands alone. The $1B fund commitment itself is verbatim from the source, only the elided verb was added — no new fact. Flagged, not hidden: this is the one claim in the corpus furthest from literal copy-paste. |
| 7 | `fd01ad9c701d` | ms-carbon-negative-2030 | faithful | "Taking responsibility for our carbon footprint." — text matches the source exactly, but see Observations: this is a section-heading-shaped sentence, not really a checkable pledge. |
| 8 | `b39f174fadfb` | ms-carbon-negative-2030 | faithful | "Investing for new carbon reduction and removal technology." — same heading-shaped pattern as row 7. |
| 9 | `d2c34c8c177d` | ms-carbon-negative-2030 | faithful | "Ensuring effective transparency." — same pattern again; see Observations. |
| 10 | `e2e000e5964b` | apple-supply-chain-2030 | faithful | "4.3 million metric tons", "2019" both verbatim. |
| 11 | `dd6311f921cd` | apple-supply-chain-2030 | faithful | "6.4 million square feet", "nearly one-fifth", "$27 million" all verbatim. |
| 12 | `02e6ce4bd045` | apple-supply-chain-2030 | faithful | "14.3 million metric tons of CO2e", "3 million cars" both verbatim. |
| 13 | `cab9279cadc9` | nike-sustainability-by-numbers | faithful | "Sixty-nine percent", "FY24", "FY20" all verbatim. |
| 14 | `7a038e1e960f` | nike-sustainability-by-numbers | faithful | "Less than 1 percent", "FY24" verbatim. |
| 15 | `e1e552050909` | patagonia-climate-goals | faithful | "80%", "FY2030", "FY2017" all verbatim. |
| 16 | `cc74b24a05ca` | patagonia-climate-goals | faithful | "FY2040", "FY2017" verbatim. |
| 17 | `55026294d215` | sim-glowline-appliances | faithful | "42%", "2028", "2019", standard name all verbatim. |
| 18 | `f20385525b2b` | sim-cobalt-ridge-mining | faithful | "60%", "2035", "2015", standard name all verbatim. |
| 19 | `2d4a082439a2` | sim-driftwood-apparel | faithful | "46%", "2030", "2022" all verbatim. |
| 20 | `d5f82977eb01` | sim-ferrous-vine-foods | faithful | "500,000 metric tons", "2028" verbatim. |

## Observations (not failures, flagged for honesty)

1. **Rows 7–9 are section-heading-shaped, not pledges.** Microsoft's source document
   restates its plan in a second block structured as short imperative headings followed by
   their own sentence ("Taking responsibility for our carbon footprint. We will take
   responsibility…", "Investing for new carbon reduction and removal technology. We will
   deploy $1 billion…", "Ensuring effective transparency. We will publish an annual…"). N1's
   own prompt says "skip pure boilerplate (headers, captions, navigation) that makes no
   claim at all"; these three headings are short enough and imperative enough that they
   read as claims in isolation ("Taking responsibility for our carbon footprint." sounds
   like a commitment sentence out of context) but they are really section titles for the
   sentence immediately after them, which is itself a separate, real claim already in the
   frozen set (claims 12/14/16 in the full file). Net effect: 3/97 frozen "claims" are
   near-content-free headings that will score at or near 0/5 on the Checkability Gate for
   the right reason (they genuinely name no quantity/year/standard/actor) rather than
   because segmentation failed — but they are still slightly inflating the claim count and
   should not be read as 3 genuinely-failed pledges when the corpus-level checkability rate
   is reported. Per T-07's rule, **not fixed by hand** — published here instead.
2. **5/97 claims (rows 2–6) are not exact substrings of the source**, all in the Microsoft
   document, all explained above — every one is a compound-sentence split or an elided-verb
   repair, none change a number, date, or named standard. This is the complete set found by
   the full-corpus mechanical check described in Method; no other document had any.
