---
name: research-visuals
description: Produce and review publication-quality visuals (tables, charts, flowcharts, diagrams, pseudocode, listings) — code-driven, one shared style. Use when creating, fixing, or reviewing a figure/table, picking a tool, or auditing a PDF's figures.
---

# Research visuals

Figures and tables are how the work is judged on first glance — and the most common amateur tell is a paper whose visuals were built ad hoc in different tools and pasted in as bitmaps (mismatched fonts, blurry charts, overlapping labels, ugly tables). This skill makes every visual **code-driven, vector, and styled from one shared source**, and gives a way to **audit** what already exists.

Depth lives in the references; this file is the *what-to-use* and *when*:
- [references/visual-standards.md](references/visual-standards.md) — cross-cutting rules (typography/embedding, Okabe-Ito + viridis, vector-first, sizing, data-ink, the amateur-mistakes checklist).
- [references/by-type.md](references/by-type.md) — the tool + copy-paste template for each visual category, plus the figures-as-code Makefile.
- [references/audit.md](references/audit.md) — the two-layer evaluation (the `audit_visuals.py` mechanical pass + the visual-review pass) and the rubric.

## First principles (non-negotiable)

1. **One source of truth, generated from code/markup**, version-controlled — never a screenshot or a hand-pasted bitmap.
2. **Vector output** (PDF/SVG) for anything made of lines/text/marks; raster only for true photos at ≥300 dpi.
3. **One shared style** so the whole paper looks uniform — charts load `scripts/pub.mplstyle` (matplotlib route) or the studio's `theme.css` (browser route): one font, one size set, the colourblind-safe Okabe-Ito palette.
4. **Captions, numbering, and titles belong to the document** (the typesetter's float + `\caption` + `\label`), **never baked into the image** — no titles, footers, or provenance/debug strings inside a figure.
5. **Chart data is derived and asserted, never hand-typed.** Every series comes out of `runs/` artifacts through a prep script that **asserts** the derived numbers reproduce the paper's published tables within tolerance — a failed assert means figure and table have diverged. This is `research-provenance` made executable at the figure level.

## Decision matrix (visual type → tool → format)

| Visual | Build with | Format |
|---|---|---|
| **Table** | LaTeX `booktabs` + `siunitx` (generate body from `pandas`) | typeset (never an image) |
| **Statistical chart** | matplotlib + `pub.mplstyle` (or PGFPlots/TikZ for perfect font match); **figure studio** (ECharts/HTML → Chromium print) for layout-heavy or annotation-dense charts | vector PDF |
| **Flowchart / pipeline** | Graphviz `dot` or TikZ (final); Mermaid (draft) | vector PDF/SVG |
| **Architecture / org** | TikZ, Graphviz, or PlantUML-C4; **hand-written SVG** in the figure studio for dense bespoke layouts | vector PDF/SVG |
| **Pseudocode / algorithm** | LaTeX `algorithm2e` (or `algpseudocodex`) | typeset |
| **Code listing** | `minted` (or `listings`) | typeset |

Two chart pipelines are sanctioned — pick **one per paper** and put every figure through it: **matplotlib + `pub.mplstyle`** (default; zero extra deps) or the **figure studio** ([references/by-type.md](references/by-type.md) §7 — per-figure HTML/ECharts specs or hand-written SVG + shared `theme.css`, printed to mm-exact vector PDF via headless Chromium). The studio is production-proven on a full 14-figure submission (100% vector, zero Type-3) and covers charts *and* schematics in one pipeline; prefer it when figures need bespoke layout/annotation work or the paper mixes many diagram types.

## Toolchain

Primary typeset engine: **LaTeX via Tectonic** (single self-contained binary, auto-fetches packages; `tectonic file.tex`) — unlocks tables, pseudocode, code listings, TikZ/PGFPlots, and the final document. Charts (matplotlib, run under **uv** with a modern version) and diagrams (Graphviz now; Mermaid via `npx`) work without LaTeX. The audit uses **Poppler** (`pdffonts`/`pdfimages`/`pdftocairo`). Manual polish (Inkscape, or paid Illustrator/Lucidchart/draw.io) is allowed only when hand-layout is genuinely needed — keep the editable source in the repo. Install details + the availability table are in [references/by-type.md](references/by-type.md).

## Automation

Build figures as code via the Makefile template in `by-type.md`: sources in `figures/src/` → vector PDFs in `figures/out/` (run under uv); `make qa` runs the audit. Generated PDFs are regenerable build artifacts (gitignore them; commit the sources). This is the reproducible alternative to hand-made figures.

## The audit gate

Run when adding/finalizing figures, before submission, and to evaluate any existing PDF:

```bash
python .claude/skills/research-visuals/scripts/audit_visuals.py <file.pdf> [more.pdf ...]
```

It is a **two-layer** check (see [references/audit.md](references/audit.md)): the script extracts deterministic facts (font families, embedding, Type 3, raster DPI) and renders page previews — **fail-loud**, never a false "clean"; then a **two-phase VLM (vision) critic** reviews the rendered previews for the overlap, colour, spacing, caption-alignment, and aesthetics the script must not judge — so the *agent* catches figure defects and the user confirms a clean figure instead of hunting for them:

- **Phase A — during experiments:** a misleading or broken plot marks its `runs/` node buggy, so a bad figure is caught at generation rather than at submission.
- **Phase B — at write-up:** each figure is checked against its caption/claim, for legibility at print size, and for main-text-vs-appendix duplication.

Drive the VLM via the same CLI-panel mechanism as `research-mock-review` (no API keys; subscription cost). The script's tests live in the skill-**source** project (`tests/test_audit_visuals.py` there), per `research-code-review` — they are not shipped into paper installs.

Expect **3–5 audit → fix rounds** on a fresh figure set before it comes back clean (observed in production: canvas overflow, label collisions, legend clipping, bottom-edge clipping dominate). For dense schematics, pre-compute label fit instead of eyeballing: approximate text width ≈ 0.45–0.5 × font-size × character-count and compare it against the clear zone's actual geometry (for labels inside a ring of Bézier arcs, the arcs pass near the midpoint of the chord-midpoint and control-point radii — well inside the node radius); when a label overflows, split it onto two lines inside the clear zone rather than shrinking the font below the figure's type scale. After a fix, re-render via the studio but publish only the changed figure's PDF, and verify by reading the rendered page — not the source. This applies equally to TikZ/LaTeX-native diagrams inside a typeset document: **a clean compile log certifies nothing about layout** — zero errors and zero overfull-box warnings coexist with overlapping edge labels, arrows crossing node text, margin-touching tables, and wasteful whitespace from over-long connector arcs. Render the affected pages to images and inspect them before calling a diagram done. Budget for the loop; don't treat round 1 as final. For the user's review, pair each rendered figure with an editable **description that doubles as its regeneration spec** (data source, layout decisions, size) in one reviewable doc — the user edits descriptions, the agent folds them back into the specs.

## Cross-references

- **research-writing** — the Figures & tables step delegates here; the Phase-4 exit requires the visual audit to pass.
- **research-provenance** — principle 5 above is its executable form: figure prep scripts assert chart data against the published tables and the claims ledger.
- **research-mock-review** — bundles this figure audit into the one pre-submission packet; shares the CLI-driven VLM critic mechanism.
- **research-experiments** — figures generated from runs use this pipeline (vector, shared style, no baked-in chrome).
- **research-repo-hygiene** — figures-as-code layout + uv for the figure env.
- **research-code-review** — the test discipline this skill's audit script follows.
