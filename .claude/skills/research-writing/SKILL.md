---
name: research-writing
description: Phase 4 (~20%) — write and revise the paper (sections, figures/tables, tone, citations, appendix), version the drafts, keep README/architecture/changelog current. Use when drafting or revising the manuscript after results exist (AI/Finance).
---

# Phase 4 — Writing the paper

Results don't speak for themselves — this phase turns evidence into a manuscript a reviewer will accept. The deliverable is a **complete, coherent draft** with figures, tables, references, and appendix, in the right voice for the venue.

## Drafts & versioning

Write under `drafts/` as **md + pdf pairs**: each `drafts/vNN-title.md` (the source of truth) has a compiled companion `drafts/vNN-title.pdf`, recompiled whenever the draft changes meaningfully so the pair stays in sync. Per the user's working agreement, when a chunk of effort exceeds **~5 agent-active hours**, start a **new** versioned draft (`drafts/v02-*.md` + `.pdf`) rather than editing the old one in place, so the trajectory is preserved; periodically untrack superseded drafts (move the whole set to `drafts/_archive/`, which is gitignored) — see `research-repo-hygiene`. The skeleton from Phase 1 is `v01`. The **main/arXiv draft** additionally carries a LaTeX source (`vNN-title.tex`) alongside the md+pdf — see the next section.

## Two versions: the main (arXiv) draft is the priority; the short version is venue-targeted

**Prioritize the main (full) draft.** It is the complete paper and the one posted to **arXiv**. A short version is derived from it *later*, and only once a target venue is chosen.

- **Main / full draft** — `vNN-title.md` is the working source of truth (every detail, all ablations, the full method). Maintain it in **three forms** so it is arXiv-ready: **Markdown** (`vNN-title.md`, author and edit here), **LaTeX** (`vNN-title.tex` — arXiv's expected submission form), and the compiled **PDF** (`vNN-title.pdf`, compiled from the canonical venue/arXiv source — see "Compiling drafts to PDF"). arXiv wants LaTeX source, so the `.tex` is a first-class deliverable, not an afterthought.
  - **The IP/vagueness decision lives with this version, because it's what goes public: mask the *recipe*, never the *evidence*.** You may abstract exact hyperparameters, proprietary data recipes, engineering tricks, and exact feature formulas (say so plainly) — but the **core mechanism** (critique-able by an expert), **honest complete results**, the **key ablation**, **named datasets/eval setup**, and **leakage/overfitting controls** must stay concrete. In finance you may withhold the strategy recipe but **never** the out-of-sample / multiple-testing / deflated-metric controls. Hiding the evidence (not just the recipe) reads as "marketing, not science" — see [references/short-version-guide.md](references/short-version-guide.md) for the safe-vs-concrete table and backfire warnings.
- **Short version** — `vNN-title-short.md`: a distillation built **for a specific target conference/journal**, conforming to *that venue's* page/column limit, template, formatting/syntax, required sections, and content/disclosure rules (e.g. double-blind anonymization, ethics/checklist, artifact policy). **Don't guess the requirements — research and confirm them first** via `research-venue-selection` (which finds the venue and its exact rules); the short version is not made until a venue is selected.

**The short version is a re-derivation around the one core message, not a truncation.** Naive deletion produces an incoherent, fragmented paper that loses the main draft's essence — that is the failure mode to avoid. Distill from the central "ping" outward, rewrite the joints, keep it self-contained, *then* fit it to the venue's limit. Full protocol, sourced from top-paper patterns, in [references/short-version-guide.md](references/short-version-guide.md). The essentials:

- **Emphasize** the main idea(s), headline results, and decisive ablation. Keep the primary setup, independent sample size, seed/run count, split, uncertainty method, and multiplicity rule in the main text; relocate exhaustive hyperparameters, logs, proofs, and secondary analyses to the appendix.
- **Coherent and self-contained** — one through-line (problem → idea → evidence), no fragmented or disconnected discussion. Re-sync the abstract + contributions list with the trimmed body; rewrite topic sentences and transitions around every cut (don't leave orphaned references).
- **Language** — elevate to a confident, technically precise, denser register, but **intuition-first so the big ideas don't confuse**; confidence from quantified claims, not adjectives.
- **Conform to the chosen venue exactly** — page/column limit, required section structure, anonymization, reference/citation style, and any ethics/artifact/checklist requirements are dictated by the target venue, not invented. This is why the venue (and its rules) must be confirmed *before* the short version is finalized.

## Writing discipline (compile-early, one coherent pass)

Two rules the strongest automated pipelines share, both cheap and both preventing whole classes of failure:

- **Compile-early hygiene.** Build the LaTeX/PDF skeleton *first* and keep it compiling on every meaningful edit. A draft that only gets compiled at the end can lose hours to a formatting break discovered too late; an always-green build never does.
- **Anti-disjoint single-pass write.** Parallelize the *research* (Phases 1–3), but **write the manuscript in one coherent pass** over all the notes/results, then do a dedicated revision pass — do **not** stitch together independently-authored sections. Naive concatenation reads as fragmented and is the top "it looks AI-written" tell. Structure the outline from the venue's required section-norms/TOC/length first, then write through it once.

## Revising a full draft (coherence → altitude → credibility → final QA)

A finished draft whose back half reads "confounded and shattered" usually has one root cause and a repeatable cure (production-earned on a 42-page TMLR submission).

**Audit before editing.** Fan out N parallel chapter auditors (per-section rubric: main point stated up front / coherent order / clear language / intro+takeaway scaffold / bold on claims / cut candidates with line numbers) plus **one whole-paper coherence reader** (argument spine with weak links; presumption ledger — stated / validated / neither; promise–payoff table vs abstract and contributions; terminology-drift list; redundancy map with one canonical home per item; limitations thread — raised inline vs collected). Auditors diagnose; **one writer applies every edit in a single coherent pass**.

- **Pass 1 — collapse re-telling (the #1 cause of "shattered").** The same finding told at three compression levels (up-front answers table → findings block → per-topic sections) makes every later section read as a repeat. Rule: **each finding gets exactly one full home; every other mention is headline-plus-pointer.** Repeated caveats get one canonical statement in methods plus one-line table-caption reminders. Results sections open answer-first — never on a table caption or operational logistics. Move any appendix walk-back of a body claim next to the claim it qualifies.
- **Pass 2 — altitude.** One purpose per paragraph; a detail survives only if it changes what the reader concludes *and* is not already carried by a table/figure (per-cell multipliers, per-attempt micro-counts, horizon-by-horizon re-reads, verbatim quotes → appendix with a pointer). Purge draft-history idiom from the body ("as of v1.1", "earlier drafts", "the pilot") — recast as present-tense design rationale; appendices are the designated revision-history home. Detect residue mechanically: a duplicated word-n-gram scan across the body catches near-verbatim twins the eye misses.
- **Pass 3 — credibility devices** (each cheap; each defuses a real reviewer objection): a falsifiability sentence for the research questions ("RQ1 fails if …" — present-tense logic, not a preregistration claim); a language-calibration commitment (unqualified language only for what was directly measured; never "first"/"proves"); a prescriptive N-check checklist for the field in the discussion; **one** coined flagship term planted at the finding's first appearance in the abstract; weakness disclosed at the point of maximum visibility, not only in the limitations dump. Echo prevailing terminology by *apposition*, never by renaming ("a survivorship artifact", "the agentic analogue of chain-of-thought unfaithfulness [cite]", "the agent's harness") — one echo per concept, each carrying its canonical citation when it implies a literature.
- **Pass 4 — adversarial final QA** (fresh-eyes agents, after all edits): (a) **semantic** cross-reference check — every §/Table/Figure/Appendix pointer's target must *contain what the citing sentence claims*, not merely exist; (b) stray-content sweep — orphaned "above/below", transitions into deleted text, unbalanced markup; (c) contradiction sweep across five categories — numbers (prose vs its own tables), claim strength, definitions, verdicts, scope — noting that **compression is the top contradiction source** (a cut qualifier quietly falsifies the sentence that remains); (d) reference truthfulness — cited↔listed both ways, entries spot-verified against live sources.

**Editing safety rails.** Snapshot the draft before the first edit and diff numeric tokens after every pass (a version-consistency guard: a revision may delete numbers, never introduce them; the only allowed additions are new references' bibliographic tokens, whitelisted by eye). Renumbering sections after a merge/delete: retarget references to the deleted section *first*, then ascending replace-all sweeps (`§7.9→§7.8`, then `§7.10→§7.9`, …), then grep-verify zero stale tokens — and re-check any text you pre-wrote in post-renumber terms, which the sweep will re-shift. Emphasis economy: bold marks *claims*, not machinery nouns — a skimming reviewer should reconstruct the argument from bold alone; keep run-in labels consistently styled within a sequence. The conclusion *advocates*: thesis first, contributions enumerated, a quotable closing stance — a fact-list conclusion reads like a diary.

## Compiling drafts to PDF (math, tables, typography)

The PDF is not an afterthought — it's how the paper is read and reviewed, and it must render the Markdown **faithfully**.

- **Working-draft toolchain: pandoc + a real LaTeX engine.** Pandoc is a convenient Markdown path, but the selected venue's official template and build instructions are canonical for submission. Use the engine required by that template; this XeLaTeX example is for a generic working draft:

  ```bash
  pandoc drafts/v01-title.md -o drafts/v01-title.pdf \
    --pdf-engine=xelatex --citeproc --bibliography=refs.bib \
    --number-sections -V geometry:margin=1in
  ```

  - **Math:** inline `$…$` and display `$$…$$` / `\begin{equation}` pass straight through to LaTeX — real typeset equations, not images.
  - **Tables:** Markdown pipe/grid tables render as proper tables; use `booktabs` styling (rules via `\toprule/\midrule/\bottomrule`, no vertical lines) for publication-quality output.
  - **Citations:** `--citeproc` resolves `[@key]` against the BibTeX that `research-references` verified — so only checked references appear.
- **Check the tool exists first.** If `pandoc` / a TeX distribution isn't installed, tell the user and offer to install it, or fall back to a **uv-managed** Python toolchain (`uv run`, per `research-repo-hygiene`) that supports LaTeX-quality math (KaTeX/MathJax) — but HTML→PDF converters often mangle equations, so this is a fallback, not the default.
- **Build the submission source locally and reproducibly.** Treat the venue-template LaTeX project as the canonical submission source; compile it with the matching engine and a TeX Live version compatible with the current venue/arXiv environment. Overleaf is optional collaboration/CI, not a correctness requirement. For arXiv, stage the exact source package, select the matching supported processor in the submission UI, inspect arXiv's compiled preview and log, and fix discrepancies there before submission.
- **Verify the render — never assume.** After compiling (locally or on Overleaf), open/inspect the PDF and confirm equations, tables, figures, and references actually came out right. A draft whose PDF silently dropped an equation or scrambled a table is not done. This check is part of the Phase-4 exit.

### Submission build & packaging (each lesson production-earned)

Turning the compiled draft into what a venue/arXiv actually accepts is its own step — script it (a `build_<target>.py` that post-processes the pandoc `.tex` into a submission-ready `main.tex` + zip), don't hand-edit the output:

- **Assert, don't eyeball, the package**: figure count in the staged build asserted against the source; page count checked against the venue's limit; the build re-runnable from the markdown master at any time. Presentation-only transforms — canonical content stays in the markdown.
- **Match arXiv's current processor.** arXiv supports pdfLaTeX and XeLaTeX; choose the processor that matches the source and current TeX Live environment. Do not add `\pdfoutput` to force a format. Remove generated branches only when they actually break the selected processor, and verify the uploaded source through arXiv's preview and compile log.
- **Encoding and glyph checks:** inspect the compile log for missing-character/font warnings. Under pdfLaTeX, map unsupported Unicode or use LaTeX commands; under XeLaTeX/LuaLaTeX, use embedded fonts with the needed glyphs. Avoid decorative box-drawing characters in verbatim unless the selected monospace font supports them.
- **Floats discipline**: wrap figures as `[tbp]` floats (not inline images) so LaTeX packs pages; cap widths to `\linewidth`; every float referenced in text (audit — orphan captions are a recurring real defect). Venue styles that own page geometry (e.g. `tmlr.sty`) usually do **not** set float fractions — re-inject `\floatpagefraction≈0.75` / `\topfraction≈0.92` in the build script, or a medium figure claims a lone, mostly-empty float page (LaTeX's default `floatpagefraction=0.5`). Detect under-filled pages mechanically — a per-page extracted-text-volume sweep (flag pages under ~1500 chars; the References tail before a fresh-page appendix is the one legitimate hit) — rather than paging through by eye.
- **PNG-free**: all figure references point at vector PDFs (see `research-visuals`); this also collapses the PDF size.
- **Assert staged assets by content hash.** Whether building locally or on a hosted editor, verify that every compiled figure matches the staged source; stale binary assets can silently survive a rebuild.
- **Multi-edition targets** (journal 30pp + conference 8pp + workshop): each edition is a separate build target from the same master with its own page budget asserted — plus a version-consistency check that shared numbers/claims match across editions before any is submitted.

### Typography & structure (follow SOTA, promote readability)

Match a **recognized template for the Phase-1 target venue** rather than inventing a style:
- **AI/ML:** use the official template for the exact venue and cycle; column count, font, page accounting, appendix, and checklist rules differ. For example, ICML, ACL, and AAAI use two-column submission formats, but the current author kit is the authority.
- **CS systems/HCI** (IEEE / ACM): two-column `IEEEtran` or ACM `acmart`.
- **Finance / economics** (Elsevier journals, AEA, etc.): `elsarticle` / AEA templates, single-column, often double-spaced for submission.

Readability essentials regardless of template: a clear numbered section hierarchy (Abstract → Intro → … → Conclusion), one idea per topic-sentence-led paragraph, consistent notation and terminology, generous but standard margins/line-spacing, `booktabs` tables, vector figures with captions (above tables, below figures), and figures/tables placed near first reference. Keep the body font serif and the type size in the venue's range — don't trade legibility for density.

## Section craft (match the chosen direction & venue)

- **Abstract & intro** — lead with the gap and the contribution; the first paragraph should make a reviewer want to keep reading. State claims precisely; don't over-claim.
- **Related work** — position against the prior art surfaced in Phase 1; make the gap unmissable. For a **survey/benchmark** (direction b), this and the taxonomy *are* much of the contribution — give them the most care.
- **Method** — precise enough to reproduce; notation consistent; a figure of the architecture/pipeline usually earns its space.
- **Experiments & ablations** — mirror the matrix from Phase 3. Every claim in the intro must have a table/figure backing it. Report variance (mean ± CI), and for finance report after-cost metrics (Sharpe, drawdown, turnover) and the out-of-sample/walk-forward protocol. **Reconcile theory-vs-measured numbers explicitly:** whenever a theoretical optimum and an observed value both appear, derive the bridge between them (which constraint — a cap, a prior, an approximation — moves theory to practice); an unexplained factor-2 gap is a defect a reviewer will find, and the reconciliation is usually a one-line calculation that strengthens the claim. **Close every hypothesis:** each Phase-1 research question must be visibly answered (confirmed/refuted) and every abstract claim must map to a reported result — the check `research-mock-review` enforces; write so it passes.
- **Limitations** — honest and specific; reviewers trust a paper more for naming its own weaknesses (and it preempts the obvious rejection reasons). Fold in the `research-mock-review` weaknesses tagged "preempt-in-Limitations."
- **Ethics / broader impact** — verify the exact cycle policy instead of assuming a universal section. Requirements differ: some venues require an impact statement, some require Limitations, and some make an ethics section conditional or optional. For AI×finance, address dual use, market impact, fairness, privacy, and regulatory considerations where relevant; follow the confirmed venue profile.
- **Conclusion** — what changed in the field's understanding, and the concrete next step.

## Figures & tables

**Build, fix, and audit every visual via `research-visuals`** — it owns the per-type tool choice (booktabs tables, matplotlib/TikZ charts, Graphviz/TikZ diagrams, algorithm2e pseudocode), the single shared style, and the quality audit (font consistency, vector, colourblind-safe, no baked-in chrome). The reminders below are the writing-side essentials:

- Tables: bold the best, mark significance, include baselines and the honest simple ones, state seeds/CIs in the caption.
- Figures: readable at print size, colorblind-safe palette, axes/units labeled, captions self-contained. Generate them reproducibly from `runs/` outputs (script the plots; don't hand-make them) and keep the plotting code in the repo.
- Every table/figure must be referenced in text and earn its place.

## Language, tone & references

- **Tone:** precise, measured, active voice; define terms on first use; consistent notation and terminology. Avoid hype; let the numbers carry the claim. Match the venue's register (ML conference vs finance journal differ).
- **References:** **every citation must pass `research-references` before it enters the bibliography**. Resolve the version of record, content-check the attached claim, and cover canonical origins plus current/contradictory evidence where relevant. Check corrections, supersession, and retractions; age alone is not a verdict. Keep resolved identifiers in BibTeX and do not pad.
- **Appendix:** full hyperparameters, dataset details and licensing, extra ablations, proofs, and a **reproducibility statement** (seeds, environment, data access, compute). Finance: state data vendor, point-in-time handling, and cost assumptions so results are checkable. Include an **AI-involvement disclosure** (which stages were AI-driven vs human-steered) — increasingly expected on arXiv/venue submissions and cheap to generate from the tracking record; keep it a short honest statement, not a heavyweight per-step ledger.

## Companion / teaching docs (explanation-grade material)

When the user asks for explanatory material about the method (a tutorial, lecture notes, a methodology walkthrough for their own study), it is a different genre from the manuscript, and revision rounds are predictable: readers escalate along the same four axes every time. Build them in on the first pass instead of waiting for the feedback loop:
1. **Derivations unpacked** — every theorem proved in named steps from a stated toolbox of prerequisites, each inequality justified in place (a manuscript-compact proof is "too dense" for a learning reader by default).
2. **Concept-level differentiation** — each key concept compared against its nearest siblings (what it beats, what it costs, where the tax lives); a bare definition doesn't let the reader see why *this* tool.
3. **Diagrams for structure** — architecture, flows, and decision routing drawn, not described; prose narration of a system reads as missing figures.
4. **Concrete scale** — worked estimates of what the system produces, how many, how fast, derived from the method's own math and labeled as design estimates; abstract structure without magnitudes feels unfinished.
5. **Semantic scaffolding** — for a reader not fluent in the underlying math field, formal correctness is not comprehension: pair every definition/lemma/theorem with a plain-language restatement of *what it says* and *what each proof step buys*, a domain dictionary mapping formal objects to the reader's home domain, a toy end-to-end example run before the real machinery, and "where beginners get stuck" callouts at the standard misconception points (all layered *around* the math, never replacing it — accessibility must not cost rigor).
Deliver bilingual if that is the user's stated need, and keep one file/PDF per artifact so revisions stay in place.

## Repo upkeep (do alongside writing)

- Keep `docs/changelogs.md` current as sections land.
- Update root `README.md` (quickstart: how to run the code/experiments and rebuild figures) and `architecture.md` (the design/workflow + project charter) — these are updated less often but should reflect the final state by submission.
- Back up significant outline/structure changes to `docs/plans/` and re-run `research-tracking` on the update.

## Exit criteria (Phase 4 → done)

Complete **main draft** as an in-sync **md + LaTeX + PDF** set whose PDF renders math, tables, figures, and citations correctly — the canonical LaTeX source compiled reproducibly and, for arXiv, verified against arXiv's own preview and compile log; all claims backed by figures/tables that **pass the `research-visuals` audit** (consistent embedded fonts, vector, colourblind-safe, no baked-in chrome), **a clean `research-references` citation audit** (every supporting reference VERIFIED or CANONICAL; no RETRACTED or UNVERIFIABLE source used as support, and corrected/superseded status handled explicitly), references and appendix in place, tests still passing, and README/architecture/changelog current. **When a target venue is selected** (`research-venue-selection`), additionally produce a coherent **short version** conforming to that venue's page limit, template, and content/disclosure rules — a distillation around the core message, not a truncation. A reflection pass (via `research-reflection`) before submission is worthwhile — a fresh adversarial read of the whole argument.

## Cross-references

- **research-paper** — orchestrator; routes here once results exist.
- **research-references** — the anti-hallucination citation gate every reference must pass before the bibliography is final.
- **research-provenance** — every reported number must resolve to a `runs/` artifact before the draft is final.
- **research-mock-review** — the pre-submission reviewer packet; its ranked weaknesses drive the final revision, its hypothesis-closure check gates the exit.
- **research-visuals** — builds and audits every figure/table (per-type tooling, shared style, quality audit).
- **research-venue-selection** — finds the target conference/journal and its exact requirements; the short version is built to the venue it confirms.
- **research-submission** — takes the built submission artifact through the portal, rebuttal, and camera-ready process (this skill owns the build; that one owns the process).
- **research-repo-hygiene** — draft rotation/untracking rules, changelog, README/architecture upkeep, commit conventions.
- **research-experiments** — source of the results, `runs/` outputs, and the plotting inputs.
- **research-reflection** — a pre-submission adversarial read of the full draft.
