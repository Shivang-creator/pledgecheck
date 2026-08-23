# FLOWCHART-SPEC — the poster that carries criterion 4

<!-- pc-designer, T-12, 2026-08-24 01:2x IST. Executable brief for T-13.
     Inputs: .crew/PLAN.md §2/§4, .crew/BOARD.md T-12/T-13, .crew/ANALYSIS.md §1/§3,
     .crew/DECISIONS.md (Featherless amendment), references/design-craft.md. -->

**This is the only picture in the entire submission packet.** The ML & Prompt Engineering track
requires no deployed app, so criterion 4 — *User Experience & Design: ease of use, aesthetic
appeal, accessibility*, 25% of the base score — is scored almost entirely off this one PNG. It is
judged as a poster, by design-sensitive eyes, at gallery size. Not a Mermaid dump. Not auto-layout.

Register per ANALYSIS §3: **hybrid tilted human.** No criterion names technical execution, so this
is not a systems diagram for engineers. It is an argument, drawn.

---

## 0. The six seconds a judge screenshots

**The middle of the workflow is one solid slab of ink; the two ends are dashed outlines that look
detachable.** Before a single word is read, the poster has already said *the machine is in the
middle and the model is bolted on at the ends*. Everything else on the page is evidence for that
one silhouette.

The colour system **is** the thesis, one-to-one, no exceptions:

| Ink (`#15191E`) | structure, type, the deterministic slab's fill |
| **Teal (`#0F5D53`)** | **computed by code** — the Gate, lit probe lamps, every verified number |
| **Amber (`#8F4513` / `#A9591F`)** | **written by a model** — N1, N5, `Generated` tags, dashed borders |

Nothing carries meaning by hue alone (design-craft §6): the code layer is **filled and solid-edged**,
the model layer is **unfilled and dash-edged**, a lit lamp is a **filled disc with a bar**, a dark
lamp is a **hollow ring**. Print the poster in greyscale and the thesis survives intact.

---

## 1. Canvas, render, and the acceptance command

- **Canvas: 2400 × 1600 CSS px, rendered 1:1** (`browse.js` screenshots the viewport at DPR 1, so
  CSS px = device px; vector text and SVG are natively sharp at that size).
- Single self-contained `deliverables/flowchart.html`. Inline SVG. **No external assets at all —
  no Google Fonts request**, because a font that arrives late renders the poster in a fallback face
  and nobody is awake to notice. macOS system faces only; the PNG bakes the result.
- `body { width: 2400px; height: 1600px; overflow: hidden }` — the render must not scroll.
- Wired as `./run.sh flowchart`, which must pass `2400 1600` (it currently passes `1200 800` — T-13
  fixes this and flags it).

```
node ~/Projects/pit-crew/bin/browse.js \
  file:///Users/shivang/Projects/reverie-2026/pledgecheck/deliverables/flowchart.html \
  /Users/shivang/Projects/reverie-2026/pledgecheck/deliverables/flowchart.png 2400 1600
```

---

## 2. Type — three faces, each with one job

| Role | Stack | Sizes |
|---|---|---|
| **Display / editorial voice** | `"Iowan Old Style", Charter, Georgia, serif` | question 56px/1.15 · footer thesis 30px italic |
| **Labels & body** | `"Avenir Next", "Helvetica Neue", Arial, sans-serif` | node title 34px 600 · panel heading 22px 600 tracking .1em uppercase · body 19px/1.45 · micro-label 14px tracking .14em uppercase |
| **Machine literal** | `"SF Mono", Menlo, monospace` | 16px — clause ids, file paths, env vars, sha256, `DIFF: IDENTICAL` |

The mono face is not decoration: **anything set in mono is a literal string the machine reads or
wrote.** Serif is the human argument. Sans is the apparatus.

**Half-size floor.** Devpost shows this at ~1200px wide. Everything that must survive halving:
question (56→28), node titles (34→17), layer-band labels (24→12 bold), probe names (24→12 bold),
footer thesis (30→15). Panel body copy is deliberately second-read.

---

## 3. Palette — concrete hex, contrast checked against the paper

| Token | Hex | Use | Contrast on `--paper` |
|---|---|---|---|
| `--paper` | `#F3F0E8` | page ground (warm, not white — this is a printed poster, not a web app) | — |
| `--panel` | `#EAE5D8` | panel/plinth tint | — |
| `--ink` | `#15191E` | primary type, the core slab fill | **16.3 : 1** |
| `--ink-2` | `#4A535E` | secondary type | **7.2 : 1** |
| `--rule` | `#CFC7B4` | hairlines only, never type | — |
| `--code` | `#0F5D53` | deterministic layer, lit lamps, verified numbers | **6.8 : 1** |
| `--code-tint` | `#DCE7E2` | Gate row banding | — |
| `--model` | `#8F4513` | model-layer type (small sizes) | **5.5 : 1** |
| `--model-line` | `#A9591F` | model-layer dashed strokes (≥3px graphics only) | **3.5 : 1**, above the 3:1 graphics floor |
| `--paper-on-ink` | `#F3F0E8` on `#15191E` | type inside the core slab | **16.3 : 1** |

Every type pairing on this poster is ≥ 5.5:1. Amber is never used for body copy on ink.
No text sits on a gradient, an image, or a colour it was not contrast-checked against.

---

## 4. Layout — 2400 × 1600, margins 96px, usable width 2208px

```
 0                                                                                2400
 ┌────────────────────────────────────────────────────────────────────────────────────┐
 │ 96  PLEDGECHECK ·······································  ┌──────────────────────┐  │
 │     Which of this company's climate promises              │ REVERIE HACKS 2026   │  │  masthead
 │     can anyone actually check?            (serif 56px)    │ ML & PROMPT ENG.     │  │  96–286
 │                                                           │ 5 nodes · 3 code     │  │
 │                                                           │ 67 tests green       │  │
 │ ──────────────────────────────────────────────────────────────────────────────── │  hairline 300
 │                                                                                    │
 │  MODEL LAYER            DETERMINISTIC CORE — no network, no model,     MODEL LAYER │  band labels
 │  ┌ ─ ─ ─ ─ ─ ┐   ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓   ┌ ─ ─ ─ ─ ─ ┐     │
 │  ╎ N1        ╎ → ┃ N2       │  N3  CHECKABILITY GATE  │ N4  ┃ → ╎ N5        ╎     │  spine
 │  ╎ SEGMENT   ╎   ┃ NORMALISE│  ● quantity      C1-QTY │ AGG ┃   ╎ EXPLAIN   ╎     │  320–950
 │  ╎ (dashed,  ╎   ┃  (ink    │  ● target year C2-TGTYR │ REG ┃   ╎ (dashed,  ╎     │
 │  ╎  unfilled)╎   ┃   slab,  │  ○ baseline yr C3-BASEYR│ ATE ┃   ╎  unfilled)╎     │
 │  └ ─ ─ ─ ─ ─ ┘   ┃   filled)│  ● named std     C4-STD │     ┃   └ ─ ─ ─ ─ ─ ┘     │
 │                  ┗━━━━━━━━━━━━━━━━━━━━━▲━━━━━━━━━━━━━━━━━━━┛                      │
 │                          ┌─────────────┴──────────────────┐                        │  plinth
 │                          │ rules/climate.v1.json  v1.0.0  │                        │  966–1086
 │                          │ GHG Protocol · SBTi · TCFD · ISSB IFRS S2               │
 │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐                    │  panels
 │  │ THE KILL SWITCH  │ │ ONE CLAIM        │ │ WHERE THE GATE   │                    │  1105–1365
 │  │ DIFF: IDENTICAL  │ │ ●●●●○  4/5       │ │ IS WRONG         │                    │
 │  └──────────────────┘ └──────────────────┘ └──────────────────┘                    │
 │  Observed ■  Rule ■  Simulated ▨  Generated ▨   (epistemic legend strip)            │  1385–1425
 │ ██████████████████████████████████████████████████████████████████████████████████ │  footer band
 │ █ Checkability is a property of a sentence — so the middle of this workflow is    █ │  1445–1600
 │ █ code, not a prompt. Switch the model off and not one verdict moves.            █ │  full bleed
 └────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Masthead (y 96–286)
- Wordmark `PLEDGECHECK`, sans 28px, weight 600, tracking `.28em`, `--code`.
- The question, serif 56px, `--ink`, max-width 1480px, two lines. **This is the 10-second read**
  (design-craft §7) — it states what the product is without a noun-phrase title.
- Right: a `--rule` 1px bordered meta block, sans 15px, `--ink-2`, four lines:
  `REVERIE HACKS 2026` / `TRACK · ML & PROMPT ENGINEERING` / `5 NODES · 3 CODE · 2 MODEL` /
  `67 TESTS GREEN · 97 FROZEN CLAIMS`.

### 4.2 The spine (y 320–950) — the whole argument
Widths, left to right, summing to 2208: **N1 330 · arrow 54 · CORE SLAB 1440 · arrow 54 · N5 330.**

**The core slab is ONE object, not three cards.** Fill `--ink`, radius 6px, 3px solid `--code`
border, containing three sections divided by 1px `--code` hairlines: `N2 NORMALISE` (340) ·
**`N3 CHECKABILITY GATE` (700, the dominant section)** · `N4 AGGREGATE` (340). Type inside is
`--paper-on-ink`. A chip at the slab's top-left reads
`DETERMINISTIC CORE · no network · no model · Python stdlib only` in sans 24px on `--code`.

**N1 and N5 are unfilled cards**: `--paper` ground, **3px dashed `--model-line` border**, radius 6px,
type in `--model`/`--ink`. A chip at each top-left reads `MODEL LAYER` in sans 24px.

Connectors: 54px gap crossed by a 3px `--ink` arrow with a solid triangular head. The two arrows
that cross a layer boundary carry a small mono label above them — `frozen claims` (N1→core) and
`scores, read-only` (core→N5). **The N5 arrow is drawn as a one-way stub with a blocked return**:
a short return arrow from N5 back toward the core, struck through with a 3px `--model-line` cross.
*The model cannot write back.* This is the second-most-important mark on the poster.

**Every node card carries the same five-line micro-grid** (sans 19px, labels in 14px micro-caps
`--ink-2` / `--code-tint`), which is exactly what the organiser asked a flowchart to show:

```
DOES        one sentence, plain
READS       what it is queried with / what it reads
MODEL       which model, named — or "none" in mono
RETURNS     what comes out
MODEL OFF   what happens under PLEDGECHECK_NO_MODEL=1
```

`MODEL OFF` must read **`identical`** on N2/N3/N4 and be set in `--code`; on N1 it reads
`reads the frozen file · no call`, on N5 `[model layer disabled]`.

**Which model — say it honestly.** The board row was written before Gemini's daily quota ran out.
The provider chain is real and must be printed as such:
`gemini-3.6-flash → featherless · DeepSeek-V3-0324`, with the mono footnote
`Gemini quota exhausted 23 Aug; every explanation in this build was served by Featherless.`
Both ids appear. Nothing on this poster claims a call that did not happen.

**N3's interior** is the five named probes, one row each, 54px tall, alternating `--code-tint` at 12%:

| lamp | probe | clause id (mono) | citation source | fired |
|---|---|---|---|---|
| ● | quantity | `C1-QTY` | GHG Protocol ch.9 | 26/97 |
| ● | target year | `C2-TGTYR` | SBTi Net-Zero v1.2 §4.2 | 24/97 |
| ● | baseline year | `C3-BASEYR` | GHG Protocol ch.5 | 13/97 |
| ● | named standard | `C4-STD` | TCFD 2017 | 21/97 |
| ● | accountable party | `C5-ACTOR` | ISSB IFRS S2 §6 | 11/97 |

Probe names sans 24px 600 `--paper-on-ink`; clause ids mono 16px `--code-tint`; citations sans 15px
`#9FB3AD`; fired-counts mono 16px right-aligned. Below the rows, one line in `--code-tint`:
`returns {present, span, clause_id} × 5 → score 0–5 → band`.

### 4.3 Human input — marked, not implied (y 966–1086)
The plinth sits directly under the slab, width 1440, centred, `--panel` fill, 1px `--rule` border,
with a 3px `--ink` arrow rising from its top edge into the Gate's bottom edge.

- Line 1, mono 18px: `rules/climate.v1.json · v1.0.0 · versioned data, not code`
- Line 2, four citation chips: `GHG Protocol` `SBTi Net-Zero v1.2` `TCFD 2017` `ISSB IFRS S2`
- Line 3, sans 18px: `Swap this file for rules/hiring.v1.json — five different probes, the same engine, the same flowchart.`

**Two `HUMAN INPUT` markers**, sans 14px micro-caps on a `--code` 2px left rule, are the only places
a person touches the pipeline, and the poster says so explicitly:
1. before N1 — `HUMAN INPUT · a person chooses the 8 documents`
2. under the plinth — `HUMAN INPUT · a person writes the clauses and their citations`
plus one line, sans 18px `--ink`: **`No human input anywhere in N2–N4. The Gate cannot be tuned at run time.`**

### 4.4 Three evidence panels (y 1105–1365, each 704 wide, 32px gutters)

**Panel 1 — THE KILL SWITCH.** Heading, then a two-column mini-diagram: `MODEL ON` / `MODEL OFF`
with N1 and N5 greyed to `--rule` in the OFF column while N2–N4 stay `--ink`. Then mono 16px:
`$ ./run.sh killswitch` → `8e5110de…  MODEL ON  (provider: featherless)` →
`8e5110de…  MODEL OFF (provider: none)` → **`DIFF: IDENTICAL`** in `--code` 22px 600.
Closing line, sans 18px: `93 explanations vanish. 0 verdicts change.`

**Panel 2 — ONE CLAIM THROUGH THE GATE.** The signature detail. Verbatim claim, serif 20px, with
the four matched spans underlined in `--code`:
> `By 2035, we aim to cut Scope 1 emissions from our processing facilities by 60%, using 2015 as
> our baseline year, in line with the GHG Protocol Corporate Standard.`

Then the five lamps in a row, four filled `--code`, the fifth a hollow `--model-line` ring labelled
`accountable party`. Then `4 / 5 · MOSTLY CHECKABLE` and, tagged `Generated`, N5's real rewrite:
`…, overseen by [Accountable Party].` One line under it, sans 17px `--ink-2`:
**`The rewrite is the model's. The 4/5 is not.`**
Source line, mono 14px: `Cobalt Ridge Mining Corp — invented company, Simulated`. **No real
company is scored anywhere on this poster** (PLAN §4 reputational guardrail).

**Panel 3 — WHERE THE GATE IS WRONG.** The visible failure (design-craft §4, playbook rule 8).
Heading in `--model`. Verbatim: `"…to halve embodied carbon in our products by the end of the
decade."` Then: `quantity → 0/5. "halve" is a word, not a numeral.` Then, mono 15px:
`known_miss_words in the rule pack · tests/test_probes.py::test_quantity_misses_word_numbers_like_halve`
Closing, sans 17px: `It is in the pack's own params and pinned by a passing test. We publish the miss.`

### 4.5 Epistemic legend strip (y 1385–1425)
One row, four chips, sans 17px, each `swatch + TAG + one-line meaning`, matching PLAN §4 exactly:

| Chip | Swatch | Meaning |
|---|---|---|
| **Observed** | solid `--ink` square | verbatim from a named public document, with URL + fetch time |
| **Rule** | solid `--code` square | computed by the engine from a named rule-pack clause |
| **Simulated** | `--rule` square, diagonal hatch | authored fixture, not a real company |
| **Generated** | `--model-line` dashed square | written by the model · never affects a score |

Right-aligned on the same strip, mono 15px: `corpus: 4 Observed · 4 Simulated · 97 claims frozen`.

### 4.6 Footer band (y 1445–1600, full bleed to all three edges)
`--ink` fill. Left, serif italic 30px `--paper`: **the thesis, one sentence** —

> *Checkability is a property of a sentence — so the middle of this workflow is code, not a prompt.
> Switch the model off and not one verdict moves.*

Right, mono 16px `#9FB3AD`, on two lines:
`67 tests green · 97 frozen claims · 93 model explanations · rule pack v1.0.0`
`self-agreement over 3 identical runs — single prompt 89/97 (91.8%) · this workflow 97/97 (100%)`

---

## 5. Accessibility floor (this is a design requirement, not a nicety)
1. **No meaning by colour alone.** Fill-vs-outline and solid-vs-dashed carry the layer distinction;
   filled disc vs hollow ring carries lamp state. Verify by rendering the PNG greyscale and
   confirming the thesis still reads.
2. **Contrast** as tabulated in §3 — every type pairing ≥ 5.5:1, every meaningful stroke ≥ 3:1.
3. **No emoji, no ambiguous pictograms** (design-craft §6, the EmoLens lesson). Lamps, arrows,
   and one struck-through return arrow are the entire icon set, and each is labelled in words.
4. **Reading order is left→right, top→bottom with no crossing connectors.** Nothing loops back;
   the one backward arrow exists only to be shown blocked.
5. Minimum type size anywhere on the poster: **14px** at 2400px canvas.

---

## 6. Do not — banned for this build
- **No Mermaid, no Graphviz, no draw.io, no auto-layout.** Hand-authored HTML/SVG only.
- **No external network request of any kind**, Google Fonts included.
- **No green-gradient eco imagery**, leaf icons, globes, or stock photography. The subject is
  auditing, not nature.
- **No emoji, no traffic lights, no thumbs.**
- **No real company scored, ranked, or named in a verdict.** Real text may be quoted verbatim with
  its provenance tag; the worked example uses a `Simulated` document precisely so a screenshot of
  this poster cannot be read as an accusation.
- **No number on this poster that was not produced by a command that ran tonight.** Specifically
  banned: any accuracy-vs-gold figure — T-08's gold labels have not landed, `COMPARISON.md` is
  still a stub, and a precision/recall number would be invented. Self-agreement (91.8% vs 100%)
  is measured and may appear; accuracy may not.
- **No "AI-powered" anywhere.** The poster's argument is the opposite.
- **No decorative drop shadows, glows, or 3D bevels.** Hairlines, fills, and dashes only.
- **No STUB string** anywhere in the file at ship time.

---

## 7. Acceptance (T-13 must pass all of these)
- `./run.sh flowchart` exits 0, prints `errors: none`, and writes a PNG **≥ 2400 × 1600**.
- `grep -c STUB deliverables/flowchart.html` → `0`.
- The PNG names **`gemini-3.6-flash`** *and* the Featherless/DeepSeek id actually used.
- All four epistemic tags appear with their swatches.
- N2/N3/N4 are visually one filled slab; N1/N5 are unfilled and dashed — **distinguishable in a
  greyscale conversion of the PNG**.
- The five probe names and their five clause ids all appear.
- The designer **opens the PNG and looks at it** before declaring done. Nothing overflows, no text
  is clipped, no element touches another's edge by accident.
