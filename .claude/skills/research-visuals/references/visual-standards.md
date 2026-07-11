# Visual standards (cross-cutting)

The rules that apply to **every** visual in the paper, regardless of type. `research-visuals` SKILL.md points here; read this before producing or fixing any figure/table.

## The one principle: a single, code-driven, vector source of truth

Every visual is **generated from version-controlled source** (code or markup), exported as **vector**, and styled from **one shared style** so the whole paper looks like it came from one hand. The opposite — figures built ad hoc in different tools and pasted as bitmaps — is what produces font chaos, blur, and overlap.

- **Captions and numbering belong to the document, not the image.** Use the typesetter's float + `\caption{}` + `\label{}` (LaTeX) so numbering is automatic and correct. **Never** bake a title, caption, footer, watermark, provenance string (`generated …`, `scripts/…`, `fig:…`), or page-ref into the figure image.
- **No baked-in chrome.** A figure image contains only the data graphic. Everything else is the document's job.

## Typography & embedding

- **Match the paper's body font** in figures. Easiest guarantees: TikZ/PGFPlots (inherit the document font automatically), matplotlib with the shared `pub.mplstyle` (serif + STIX math), or **vendoring the exact face into the figure pipeline** (the studio's `fonts/` + `@font-face` — a sans companion of the body serif, e.g. Biolinum for Libertine, also reads well).
- **Embed fonts as vector.** matplotlib: `pdf.fonttype=42` / `ps.fonttype=42` (in `pub.mplstyle`). **Never ship Type 3 (bitmap) fonts** — forbidden by NeurIPS/IEEE. Browser-print pipelines: vendor the font as **TTF** — Chromium's print-to-PDF embeds OTF as Type 3; the TTF conversion of the same face embeds cleanly.
- **At most ~2 type families + 1 monospace** across all figures (e.g. body serif + math + mono for code). More than that reads as inconsistent.
- **Consistent sizes**: figure text at ~8–10 pt at final print size. Do **not** scale a figure after export (it rescales the fonts non-uniformly). Set the figure to its final column width *in the source*.

## Vector vs raster

- **Vector (PDF/SVG/EPS) for everything that is lines/text/marks** — charts, diagrams, tables, plots. Stays crisp at any size; fonts embed.
- **Raster only for true photographs / bitmap content**, at **≥300 dpi** (halftone) or **≥600 dpi** (line art). A chart exported as PNG is a defect, not a fallback.

## Colour & accessibility

- **Categorical → Okabe-Ito** (colourblind-safe). Hex: `#0072B2` blue · `#D55E00` vermillion · `#009E73` green · `#CC79A7` purple · `#E69F00` orange · `#56B4E9` sky · `#F0E442` yellow · `#000000` black. (This is the default cycle in `pub.mplstyle`.)
- **Fix the categorical order and validate it.** Pick ≤5 categorical colours in a **fixed assignment order** and verify adjacent pairs under CVD simulation (target ΔE ≥ 12 between adjacent assigned colours under deutan/protan; the proven 5-set `#0072B2 #E69F00 #009E73 #CC79A7 #56B4E9` measures worst-adjacent ΔE 17.9 deutan). Keep **one accent colour outside the categorical set** (e.g. vermillion `#D55E00`) reserved for status/highlight marks so an annotation can never be misread as a series.
- **Semantic colour constancy across the whole paper.** The same entity/condition keeps the same colour in *every* figure (e.g. condition A = blue, condition B = orange, everywhere). A reader who learns the mapping once must never relearn it.
- **Ink discipline:** all figure text — labels, value annotations, axis names — uses the ink scale (primary/secondary/muted), **never a series colour**; gridlines stay recessive (light, behind the data). Diverging scales are blue↔vermillion (or another CVD-safe pair), **never red↔green**.
- **Sequential/continuous → viridis or cividis** (perceptually uniform, grayscale-robust; cividis is best for deuteranopia). Never `jet`/rainbow.
- **Never encode by colour alone.** Add a second channel — marker shape, line style, hatching, or direct labels — so the figure survives grayscale printing and colour-blind readers. Avoid red/green as the sole distinction.
- **Test:** simulate colour-blindness (DaltonLens / Coblis / Color Oracle) and convert to grayscale; all series must stay distinguishable.

## Sizing for the venue

Set the figure width to the target column width and let height follow (golden ratio is a good default):

| Venue | 1-column | 2-column (full width) |
|---|---|---|
| Nature | 89 mm (3.5 in) | 183 mm (7.2 in) |
| IEEE | 3.5 in | 7.16 in |
| NeurIPS / ACL / ICML | ~3.25 in (col) | ~6.75 in (text width) |

`pub.mplstyle` defaults to 3.5 in (single column). Override per figure for full-width.

## Data-ink & honesty (charts)

- Maximize data-ink; drop chartjunk (3-D effects, heavy gridlines, boxed legends, redundant borders).
- **Avoid** 3-D charts, dual-axis charts (scale-distorting), and pie charts with >5 slices — use 2-D bars / small multiples instead.
- **Direct-label** series at the line end where it fits; reserve legends for when direct labels would crowd. Put exact values on top of bars when there are few enough to read.
- **Error bars / bands are mandatory where there's uncertainty**, and the caption must state what they are (SD, SEM, 95% CI). Report seeds/repeats as mean ± interval, not a single run. With few runs per condition, **mean-dot + full run-range whiskers** is more honest than a fake CI.
- **An outlier that would crush the scale gets excluded to a text annotation**, not plotted: clip the axis to where the data lives, state the outlier's value in an ink-coloured note ("cost-high: −3.32, off scale"). Same for axis ranges generally — clip to the informative range with explicit tick intervals rather than defaulting to zero when zero is uninformative (say so in the caption if the baseline matters).
- **Small matrices beat colorbars.** For a matrix of ≤ ~8×8 values, print the numbers in the cells (neutral fill for the zero/NA cell) instead of a heatmap-plus-colorbar — the colorbar spends space to make values *less* readable.

## Paper integration

- **Every figure and table is referenced from the text at least once.** Audit this explicitly before submission — floats that exist only as captions are a real, recurring defect (a production audit found 6 tables and 7 figures uncited in one draft). `research-writing` owns the prose side; the audit here flags the orphans.
- **The final paper is PNG-free.** Every chart/diagram/table reference points at a vector PDF or is typeset; replacing legacy PNGs with the vector rebuilds cut one production paper's PDF from 2.6 MB to 0.77 MB.
- **Figure data provenance is executable.** The prep step that turns run artifacts into chart data *asserts* the derived series reproduce the published table values (see SKILL.md principle 5 and `research-provenance`) — run it on every data refresh, before re-rendering.

## Amateur-mistakes checklist (reject any figure that does these)

- [ ] Many typefaces / sizes across figures (built in different tools) — the #1 tell.
- [ ] Type 3 (bitmap) fonts; non-embedded fonts.
- [ ] A chart pasted as a low-res raster (blurry; < 300 dpi).
- [ ] Title / caption / provenance / debug text **baked into** the image.
- [ ] A redundant in-image caption duplicated by the document's `\caption`.
- [ ] Overlapping elements (label over legend, annotation over data).
- [ ] Colour-only encoding; red/green; rainbow colormap.
- [ ] Figures numbered out of order (placed as manual images, not floats).
- [ ] A table rendered as an image, or with vertical rules and uneven row heights.

## Cross-references

- **by-type.md** — the per-category tool + template to actually build each visual.
- **audit.md** — how to evaluate an existing/finished PDF against these standards (the `audit_visuals.py` first pass + the visual-review layer).
