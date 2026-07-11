# Evaluating visuals in an existing PDF

How to assess the figures/tables in any finished or draft PDF against `visual-standards.md`. The evaluation is **two layers** — neither alone is trusted:

1. **Mechanical (deterministic, scripted):** `scripts/audit_visuals.py` extracts facts Poppler reports authoritatively (font families, embedding, Type 3, raster DPI) and renders page previews. It is **fail-loud**: if a tool is missing or output can't be parsed, it says "needs review", never a false "clean".
2. **Visual (judgment, by a human or vision-model):** open the rendered previews and inspect for the things no script should judge — overlap, alignment, colour choice, spacing, clutter, legibility at print size.

## Run the mechanical pass

```bash
python .claude/skills/research-visuals/scripts/audit_visuals.py paper.pdf
# or audit every built figure:
python .claude/skills/research-visuals/scripts/audit_visuals.py figures/out/*.pdf
```
It prints, per PDF: family count, non-embedded/Type 3 fonts, image count + min DPI + how many below the floor, and where the page previews were written. Exit code is non-zero if anything is flagged **or** any check couldn't run. (The script's tests live in the skill-source project under `tests/`; they are not shipped into paper installs.)

## Then the visual pass

Open the `qa_previews/*.png` and check each figure/table against the rubric below. A vision-capable agent can read the PNGs directly.

**What the visual pass actually catches** (production frequency order — a real 12-figure set took **five** audit→fix rounds): canvas overflow (a label or panel poking past the figure edge), label collisions (annotation over a value label, adjacent tick labels merging), legend clipping at the figure boundary, and bottom-edge clipping. Look for these four first; plan for several rounds, not one.

## Audit rubric

| Category | Check | How | Pass |
|---|---|---|---|
| Typography | font consistency | `audit_visuals.py` font count | ≤ ~3 families, all embedded, **no Type 3** |
| Resolution | raster DPI | `audit_visuals.py` | photos ≥300 dpi, line-art ≥600; **charts should be vector, not raster at all** |
| Vector | charts are vector | image count vs # of charts | charts contribute ~no embedded bitmaps |
| Colour | colourblind-safe | simulate (DaltonLens/Coblis) + grayscale | all series distinguishable without colour; no red/green-only; no rainbow |
| Layout | no overlap/misalignment | visual review of previews | labels/legends/annotations clear of data and each other; panels aligned |
| Tables | clean typeset table | visual review | booktabs rules, even row spacing, no vertical rules, decimal-aligned, not an image |
| Captions | in document, not image | visual review | caption/number from the float; **no baked-in title/caption/provenance text** |
| Numbering | floats in order | scan figure numbers | Figure/Table N appear in ascending order |
| Consistency | one look across all figures | visual review across pages | same font, palette, sizing, marker styles everywhere |

## Anatomy of a bad figure (what failure looks like)

A poor academic figure typically shows several of these at once — treat any as a defect to fix:

- **Font chaos:** many typefaces/sizes across figures (e.g. eight families in one document), often with **Type 3 (bitmap) fonts** — the signature of charts/tables built in different tools and pasted in.
- **Raster-only charts:** every chart is an embedded bitmap; several render **below 300 dpi** and look blurry in print.
- **Baked-in chrome:** titles, captions, footers, watermarks, or debug/provenance strings (`generated …`, `scripts/…`, `fig:…`) burned into the image.
- **Redundant captions:** an in-image caption duplicated by the document's real `\caption`.
- **Overlap:** a data label sitting on top of the legend; trend annotations crossing the lines.
- **Colour-only encoding** with a **red/green** pair (invisible to ~8% of male readers) or a rainbow/`jet` colormap.
- **Scrambled numbering:** figures appearing out of order because they were placed as manual images rather than numbered floats.
- **Image-tables:** tables rendered as screenshots, or HTML-style tables with vertical rules and uneven row heights.

Root cause is almost always structural: figures emitted with baked-in chrome and embedded as bitmaps into an HTML→browser-print pipeline. The fix is not cosmetic tweaking — it is moving to the **code-driven, vector, single-shared-style** pipeline in `by-type.md` feeding a typeset document.

## Colour / contrast tooling

- Colour-blindness simulation: **DaltonLens**, **Coblis**, **Color Oracle** (upload a preview PNG; check all CVD types).
- Contrast: WCAG checkers (WebAIM) — figure/label text should meet ≥ 4.5:1 against its background.
- Grayscale test: convert a preview to grayscale (`convert in.png -colorspace Gray out.png`) and confirm series stay distinct.

## Cross-references

- **visual-standards.md** — the standards this rubric checks against.
- **by-type.md** — how to rebuild a failing visual correctly.
