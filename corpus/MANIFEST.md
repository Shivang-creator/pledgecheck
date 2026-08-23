# Corpus manifest — T-02

Built by pc-integrator, 23 Aug 2026 ~23:5x IST, using `~/Projects/pit-crew/bin/fc <url> md`
(the Firecrawl **MCP** is dead this session per BRIEF/PLAN — the `fc` helper reads the key
directly and works). Hard cap: 25 minutes of fetching, per the board.

## Counts

| provenance | count |
|---|---|
| Observed | 4 |
| Simulated | 4 |
| **Total** | **8** |

4 ≥ 3, so this corpus does **not** need to fall back to "every document Simulated."

## Observed documents (verbatim excerpts, source + fetch time attached)

| doc_id | org | source_url | fetched_at_utc |
|---|---|---|---|
| `ms-carbon-negative-2030` | Microsoft Corporation | https://blogs.microsoft.com/blog/2020/01/16/microsoft-will-be-carbon-negative-by-2030/ | 2026-08-23T17:50:00Z |
| `apple-supply-chain-2030` | Apple Inc. | https://www.apple.com/newsroom/2020/07/apple-commits-to-be-100-percent-carbon-neutral-for-its-supply-chain-and-products-by-2030/ | 2026-08-23T17:50:00Z |
| `nike-sustainability-by-numbers` | NIKE, Inc. | https://www.nike.com/sustainability | 2026-08-23T17:50:00Z |
| `patagonia-climate-goals` | Patagonia, Inc. | https://www.patagonia.com/climate-goals/ | 2026-08-23T17:50:00Z |

Each excerpt is verbatim text pulled from the fetched Markdown (image/nav/markdown-link
boilerplate stripped, no words changed or added), trimmed to the pledge-relevant paragraphs,
200-600 words per the board's spec. Each document text is quoted from a real, dated, publicly
published company statement — none of it is invented.

## Simulated documents (authored fixtures, obviously invented orgs)

| doc_id | org | source_url |
|---|---|---|
| `sim-glowline-appliances` | Glowline Appliances Inc. *(invented — not a real business)* | null |
| `sim-cobalt-ridge-mining` | Cobalt Ridge Mining Corp *(invented — not a real business)* | null |
| `sim-driftwood-apparel` | Driftwood Apparel Co. *(invented — not a real business)* | null |
| `sim-ferrous-vine-foods` | Ferrous & Vine Foods Group *(invented — not a real business)* | null |

Authored in the same register as real corporate pledge prose, deliberately mixing: fully
checkable claims (quantity + target year + baseline year + named standard + accountable
party all present), partially checkable claims, and the two documented known-miss patterns
from `rules/climate.v1.json`'s `known_miss_words` list — word-numbers ("halve", "triple",
"net-zero") and vague aspirational sentences with no auditable component at all ("we believe
every small step counts"). This is intentional corpus design, not sloppiness: the Gate's
honest miss on word-numbers needs real examples to demonstrate on, per PLAN.md §11 beat 4.

## URLs attempted and why they did not land as Observed documents

Every failure below is a fetch failure (404 / page-not-found / ad-blocker artifact / timeout)
against `fc`, not a content judgment call — the pages either don't exist at the guessed URL
any more, or Firecrawl's proxy hit a client-side block. None were abandoned for time; the
25-minute cap was not reached, but returns had flattened (5 real hits in 10 attempts, then 3
misses in a row) so the corpus was closed at 4 Observed + 4 Simulated to move on to T-06.

| URL tried | Result |
|---|---|
| https://www.aboutamazon.com/planet/climate-change | 404 — page not found (site restructured) |
| https://www.ikea.com/global/en/newsroom/corporate-news/ikea-shares-progress-on-becoming-climate-positive-by-2030-... | 404 — "Bear with us" error page |
| https://www.unilever.com/planet-and-society/climate-action/ | 404 — page not found |
| https://corporate.walmart.com/purpose/esgreport/environmental | 404 — "Out of Stock, but Not Out of Options" error page |
| https://blog.google/outreach-initiatives/sustainability/our-third-decade-climate-action-realizing-a-carbon-free-future/ | 404 — "This page doesn't exist" |
| https://news.starbucks.com/press-releases/starbucks-outlines-aspiration-to-become-resource-positive/ | Fetch timed out (backgrounded, then failed) |
| https://www.salesforce.com/news/stories/net-zero-cloud-climate-commitments/ | Returned mostly chat-widget/ad-blocker artifact markdown, no pledge content — rejected |
| https://www.gm.com/company/sustainability | 404 — page not found |
| https://ir.tesla.com/press-release/tesla-2023-impact-report | 404 — "I'm afraid I can't do that" error page |

## Guardrail check (PLAN.md §4)

No document, table, or downstream artifact ranks these four real companies against each
other. Each Observed document is quoted verbatim with its own source URL so a reader can
check the excerpt against the original page themselves; the product scores the
**checkability of the sentence**, never the sincerity of the company.
