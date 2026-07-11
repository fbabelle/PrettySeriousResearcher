# Short-version & paper-language guide

Reference for `research-writing`. Two parts: (1) **language/structure patterns** distilled from top CS/AI and finance papers (apply to *any* draft), and (2) the **short-version protocol** — how to distill the main draft into a **venue-targeted** short version that stays coherent and meets the chosen conference/journal's requirements. The **IP/disclosure rule** (mask the recipe, never the evidence) is in Part 2 but governs the *publicly posted* version — i.e. the main arXiv draft — not just the short one. Confirm the target venue and its rules via `research-venue-selection` before finalizing the short version.

Sources (verify via `research-references` if citing): Peyton Jones "How to Write a Great Research Paper"; Widom (Stanford InfoLab) "Tips for Writing Technical Papers"; Swales CARS model; CVPR/NeurIPS author guides + NeurIPS Paper Checklist & Code Policy; Cochrane "Writing Tips for PhD Students"; Head "Introduction Formula"; Harvey–Liu–Zhu (2016) & Harvey (2017) on t>3 / multiple testing; Gu–Kelly–Xiu (2020); Bailey–López de Prado (Deflated Sharpe, backtest overfitting); GPT-4 Technical Report & Model Cards (disclosure boundary); Lipton–Steinhardt "Troubling Trends in ML Scholarship".

---

## Part 1 — Language & structure patterns of top papers

### Abstract
- **4–5 beat formula:** problem → why it matters → what we do → what we find (quantified) → what follows. ~150 words (CS/AI); ≤100 words at JF/JFE/RFS. Write it **last**; don't copy sentences verbatim from the body.
- **State concrete results, not intentions** — the headline number goes here ("improves X by N", "net Sharpe of Y after costs"), not "achieves strong performance." No citations, no related-work, no method minutiae.
- Present tense, active, "We show / We find".

### Introduction
- **CARS / funnel:** establish territory → indicate the gap ("but existing methods fail to…") → occupy it (what we do + principal findings). Widom's 5 questions: what's the problem / why interesting / why hard / why unsolved / key approach+results.
- **Nail contributions to the mast:** a bulleted, *refutable*, specific contributions list, each forward-referenced to its section. The contributions list drives the whole paper — the body must substantiate every claim. A clear technical contribution should be visible by ~page 3.
- **Lead with a concrete example ("molehills not mountains"), no throat-clearing** ("X has long been important [1,2,3]…" is banned). Front-load the payoff; no suspense. Replace the "rest of this paper is organized…" roadmap with forward references woven into the intro.

### Section budget for ~8 pages (relative emphasis, not literal)
Title/Abstract/Intro carry the most readers; "details" carry the fewest. Keep in main text: problem + motivating example, the core idea explained *intuitively*, headline result(s), the single most decisive ablation, enough setup to be reproducible in principle. Push to appendix: full hyperparameters, proofs, extra ablations/robustness, dataset-construction minutiae, implementation specifics.

### Sentence-level register
- **Active voice, first person, owned claims** ("We propose/show/find"); subject–verb–object; concrete nouns; no nominalizations ("use" not "utilize").
- **Confidence comes from quantified evidence, not adjectives** — cut "striking", "very significant", "novel". Hedge only where you *should*: limitations and claims beyond your evidence. Never hedge a measured result; never over-claim an untested generalization.
- **Intuition first, formalism second.** Convey the idea so a reader gets it, *then* add the math. Avoid the jargon wall ("Consider a bifurcated semi-lattice…") that signals rigor but sends readers to sleep. Precise technical vocabulary ≠ jargon overload; define each term once before use.
- Conciseness: kill "it should be noted that", "in other words" (say it once, right), in-section repetition, filler. Short sentences. "Every word must count."
- Topic-sentence-led, one-idea paragraphs; explicit transitions for coherence; consistent terminology and notation (don't elegantly vary the word for one concept).

### Coherence — the single through-line
- **One "ping":** one sharp central idea, stated explicitly ("The main idea of this paper is…"). If you have many ideas, write many papers. A reviewer must finish able to state the one contribution.
- **Tell the whiteboard story:** problem → why open → my idea → it works (evidence) → how it compares. No significant interruptions in the main text (those → appendix).
- Use forward references purposefully; frequent "as we saw / recall from §2" backward references usually mean things are in the wrong order.

### Finance / AI×finance register (when the domain applies)
- Lead with **economic significance**, not just statistical: "a one-SD increase in X is associated with a Y% change, ≈ N% of the mean." Report standard errors; in large panels everything is "significant" — magnitude is what matters.
- **Caution on causality:** associational/evidential verbs ("is associated with", "consistent with") unless identification supports causation.
- **Multiple-testing discipline:** for a new factor/strategy, expect the t>3.0 bar (Harvey–Liu–Zhu), correct for multiple tests, pre-specify, and report true out-of-sample / walk-forward, **net of costs** (Sharpe, drawdown, turnover). Frame robustness as "the opposite of data mining."
- AI×finance bridge: describe the ML method with full rigor, then frame every empirical claim with finance caution — time-series-aware (purged/embargoed) validation, overfitting controls, deflated Sharpe, economic (not just R²) significance.

---

## Part 2 — The short-version protocol (venue-targeted)

The short version is a **distillation re-architected around the one core message — not a truncation** of the main draft. Naive deletion produces the broken, fragmented version the main draft's essence doesn't survive. It is built **for a specific target conference/journal** (chosen via `research-venue-selection`), so its limit, template, and disclosure rules come from that venue — confirm them before you start cutting.

### Page budget
Driven by the **target venue's limit** (page/column count, what counts toward it, whether references/appendix are excluded) — get this from `research-venue-selection`, don't assume. The common top-CS default is **≤ 8 pages of main text excluding appendix**, but journals and other venues differ widely. Regardless of the number, the main text must be **self-contained**: reviewers may ignore the appendix, so every headline claim must be stated, motivated, and at least summarized-with-evidence within the limit.

### What to EMPHASIZE
- The **main idea(s) and core competence** — the contribution and *why it works*, explained intuitively.
- The **headline results** and the **single most decisive ablation** (the one isolating why the method works).
- The clean contributions list and the through-line connecting problem → idea → evidence.

### What to OMIT (move to appendix or drop)
- **Drop** (process noise, not evidence): debug history, minor implementation trivia, intermediate direction changes, and the travelogue of failed attempts. Keep the primary design facts needed to judge the result — independent sample size, seed/run count, split, effect and uncertainty method, and multiplicity rule — in the main text.
- **Relocate to appendix** (substantiating detail) with a one-line stub remaining in main text: full hyperparameters, proofs, secondary ablations, robustness sweeps, dataset minutiae.

### Good distillation vs broken truncation
1. **Re-derive the core message first**, then build the short paper around it (start from the "ping", not the long draft's section list).
2. **Necessity test:** "nothing before the main result that a reader doesn't need to understand the main result." Everything that survives earns its place against the headline claim.
3. **Re-write the joints, don't just delete bodies.** When a subsection is cut, rewrite the surrounding topic sentences and transitions so the narrative still flows. Fragmented = orphaned references + lost topic sentences.
4. **Move, don't drop, evidence:** relocate detail to the appendix but keep the *claim* (with a summary) in main text.
5. **Re-sync the abstract + contributions list with the trimmed body** — they must not promise what the short body no longer delivers.
6. Detection (signs of broken truncation): a reviewer can't name the one contribution; dangling references to cut sections; method shown without its motivating intuition; a results table whose explanatory ablation was cut; inconsistent terminology from stitched fragments.

### Language for the short version
Elevate the register: **confident and technically precise**, denser than the long draft — but **intuition-first so big ideas don't confuse**. Confidence via quantified claims, not adjectives. Tighter sentences, higher information density, but never the jargon wall. The short version should read as more authoritative *and* more readable, because it carries only the load-bearing ideas.

### Intentional vagueness for IP protection (the public/arXiv version) — mask the RECIPE, never the EVIDENCE
This rule governs whatever you post **publicly** — primarily the main arXiv draft (and any short version posted openly). A public preprint may legitimately withhold *implementation specifics* to protect property — major labs do this (the GPT-4 report explicitly withholds architecture/data/training detail while reporting capabilities and evals). The rule:

| Safe to keep vague / abstract | Must stay concrete (or credibility collapses) |
|---|---|
| Exact hyperparameters & final values (give ranges/intuition) | The **core idea/mechanism** — enough for an expert to *critique* it; it cannot hide behind "proprietary" |
| Proprietary/licensed data sources, scraping & mixture recipes | **Datasets named/described**; evaluation setup at a level that supports the claim; leakage ruled out |
| Engineering tricks, internal tooling, serving infra | **Honest, complete results**: baselines, variance/seeds-in-aggregate, the key ablation, negatives |
| Exact proprietary feature formulas (give category/intuition) | **No look-ahead/leakage**; in finance, the **overfitting/OOS controls** (true walk-forward, multiple-testing/deflated metrics, # trials) — these may **never** be hidden |
| Exact micro-architecture sizes | The high-level structure + the novel component |

**The line:** a skeptical expert reading only the short paper must still be able to (a) understand the idea well enough to critique it, and (b) judge whether the evidence supports the claim. Abstract the *how-built*; keep the *what-it-does-and-how-well* verifiable.

**Backfire warnings (state these, don't pretend vagueness is free):**
- Hiding the *evidence* (not just the recipe) reads as **"marketing, not science"** and gets discounted — most harshly in finance, where impressive backtests are nearly free to fabricate (Bailey/López de Prado).
- Without ablations you can't rebut the "the gain was just tuning/data/scale" prior (Lipton–Steinhardt's "failure to identify sources of gains").
- Unfalsifiable claims get auto-discounted (extraordinary claims need extraordinary evidence) — vagueness *lowers* evidence while *raising* claim strength, the worst combination.
- A thin v1 is **permanent and date-stamped**; and preprinting near a double-blind deadline risks de-anonymization. Decide consciously.
- **Finance hard rule:** you may withhold the strategy recipe, but withholding the recipe **and** the overfitting controls is fatal to credibility.
