---
name: research-topic-selection
description: Phase 1 (~30%) — run the two-direction interview, do a prior-art / novelty-gap scan, score topics, and produce a paper skeleton with research questions and hypotheses. Use at a paper's start or when reframing the topic (AI/Finance).
---

# Phase 1 — Topic research, selection & skeleton

The most leveraged phase: a well-chosen, well-scoped topic with a defensible gap is worth more than any later cleverness. Output of this phase is a **confirmed topic + direction**, a **novelty/gap claim**, and a **paper skeleton**.

## Step 1 — The two-direction interview (hard stop; do not skip)

Before any investigation, confirm scope **with the user**. These answers shape everything downstream — never assume them:

- **Domain & sub-area** (e.g. LLM agents for financial QA; portfolio optimization; time-series forecasting; market-microstructure RL; risk/factor models).
- **Target problem(s)** — the specific pain or open question.
- **Expected outcome** — a new method/system, or an analysis/understanding result?
- **Improve vs challenge** — patch/extend existing systems, or test/break a prevailing thesis?
- **Direction (a) vs (b):**
  - **(a) Algorithm/technical** — push the field: new architecture, mechanism, or thesis (think *Attention Is All You Need*, ResNet, MoE). Demands deep, comprehensive investigation before any claim. Higher risk, higher novelty.
  - **(b) Experimental/analytical** — survey, benchmark, replication, ablation/variation study, limitation analysis, or parameter refinement of existing systems. Lower invention, high rigor and interpretation.
- **Venue & length target** (sets the bar and the skeleton): NeurIPS/ICML/ICLR/AAAI/ACL; or finance venues — *Journal of Finance*, *RFS*, *JFE*, arXiv **q-fin**, SSRN; workshops vs full track. **Fire `research-venue-selection` early** to turn this into a *venue profile* (rubric, acceptance bar, section/length template, disclosure/anonymity rules, deadline windows) that becomes a **scored input** to topic choice below — the topic is picked partly *for* venue fit, not retrofitted to a venue later (venue-as-input).

Record the answers as the project charter (top of `architecture.md`). The orchestrator will not advance past this without them.

## Step 2 — Broad prior-art & novelty-gap investigation (breadth)

Use the host agent's current web-search and page-fetch tools for the heavy search; here you frame and synthesize it. The question this phase answers is **"is the topic worth it?"** — not yet "can these specific algorithms solve it" (that depth analysis is Phase 2's job; see `research-algo-design`).

Map the field:
- **What's been done** — the canonical works and the current SOTA for the target problem.
- **What's saturated or over-exploited** vs **underexplored** — where adding another increment yields little, vs a genuine open seam.
- **The gap** — a crisp, defensible statement of what's missing and why it matters. For direction (a), the gap is a capability/thesis; for (b), it's an unanswered empirical/interpretive question or an untested boundary.

**AI & Finance specifics to check:**
- **Sources:** arXiv (cs.LG, cs.CL, q-fin.*), SSRN, Google Scholar, OpenReview (read the reviews, not just papers), papers-with-code for SOTA + leaderboards.
- **Data feasibility up front** (finance bites here): licensing and look-ahead/survivorship bias for CRSP/Compustat/WRDS, Bloomberg/Refinitiv terms, free tiers (FRED, Yahoo, SEC EDGAR, Polygon/IEX), point-in-time vs restated data. A topic that needs data you can't license is a dead end — surface it now. **Tag a finance-leaning topic for `research-finance-rigor`**, which owns the full data-licensing/point-in-time/survivorship checkpoint from here through writing.
- **Reproducibility & leakage red flags** in the prior work — finance ML is rife with subtle look-ahead leakage and unrealistic backtests; a credible gap is often "prior results don't survive a leakage-clean / cost-aware setup."
- **Lane velocity (measure it, don't assume it).** Count the lane's recent publication cadence (papers/month on the exact sub-topic). In a hot lane (≈1+/month), integration-shaped gaps close in months: prefer mechanism-shaped claims that survive being scooped, adopt an **arXiv-first timestamp policy** (preprint at first solid result), and **re-verify the gap days before locking the topic** — a gap-closing preprint can appear between the scan and the decision. Record the scan's **freeze date** in the scan itself; every later design gate re-audits "since <freeze date>" by lane with a claim-status table (see `research-reflection`).
- **Verify before you cite.** Any prior-art work you'll cite (here or in related-work) must pass **`research-references`** — resolve a real link and confirm it actually says what you attribute to it. Don't let a plausible-but-unverified paper into the gap argument; a hallucinated citation here propagates into the whole framing.

## Step 3 — Multi-angle lateral scan + tournament ranking

Don't score a handful of framings serially on gut feel — evaluate a **wider candidate pool from many independent angles in parallel**, then rank. This is the "more lateral evaluation in topic formulation, exploration, and competitive-intelligence" the skill set is built around.

1. **Generate a candidate pool** (aim ~6–10 framings), then run **one bounded, goal-tagged probe per candidate across a FIXED angle set**, in parallel (use bounded parallel search probes when the host supports them; reserve a strong model for synthesis):
   - **Novelty** — how big and defensible is the gap?
   - **Competitors / prior-art** — who else is here; build a **feature-axis matrix** of the closest systems (what each does vs doesn't).
   - **Feasibility** — data licensing/access, compute, and *user-interaction time* within the budget envelope.
   - **Venue-fit** — does it match the early venue profile's scope, bar, and norms?
   - **Impact** — who cares, and how much?
   - **Failure-modes** — how could it fail to produce a result?
2. **Force a structured card per candidate.** Each candidate is a fixed card that must name **the specific limitation of a NAMED SOTA method it removes** (not a vague "gap"), plus its row in the competitor feature-matrix. A card that can't name the concrete limitation it beats isn't a contribution yet.
3. **Rank by a cheap pairwise pass.** Run a **single, breadth-capped pairwise / win-ratio comparison** over the cards into a ranked, rationale-bearing slate — *not* a many-round Elo tournament (statistically noisy at this scale and it burns the metered budget the time model tracks).
4. **De-dup for diversity.** Ensure the shortlist spans **distinct clusters**, not near-duplicates of one idea.
5. **Present the ranked slate; the user chooses** — and can **inject their own framing on equal footing** (it runs through the same card + ranking). This is the topic-slate hard stop.

**Narrow contamination guard (corrected).** When judging novelty, check that the *specific claimed-novel contribution* isn't already in the prior art or plausibly memorized from pretraining — **do not** restrict the whole prior-art corpus to post-cutoff work (that would exclude almost all real prior art and break the scan). The guard is a targeted check on the novel claim, not a corpus-wide filter.

## Step 4 — Skeleton + research questions

Produce the paper skeleton and the testable claims:
- **Research-brief "north star"** — a compressed problem → idea → evidence-plan (a few lines) that every later phase references and the end-deliverable rubric optimizes toward. Keep it at the top of `architecture.md`.
- **Research questions / hypotheses** stated so an experiment can confirm or refute each — these are what `research-mock-review`'s hypothesis-closure check verifies got answered.
- **Section outline** matched to the venue (typical ML: Intro / Related / Method / Experiments / Ablations / Limitations / Conclusion; survey/benchmark layouts differ — pick the right template).
- **Success criteria** — what result would make this a paper, and what the honest negative result would be.
- For direction (b), draft the **evaluation protocol** early (datasets, metrics, baselines) since that *is* the contribution.

Write the skeleton as the first draft under `drafts/` (see `research-repo-hygiene` for versioning) and mirror the charter + outline into `architecture.md`.

## Exit criteria (Phase 1 → 2)

Confirmed topic + direction, a defensible novelty/gap claim, a feasibility check that clears data/compute/interaction-time, an **early venue profile** consumed as a scoring input, a **research-brief north star**, and a skeleton with research questions. Then the orchestrator advances to `research-algo-design`.

## Cross-references

- **research-paper** — orchestrator; runs the hard-stop interview and the topic-slate confirmation through this skill and advances on the exit criteria.
- **Host web-search/page-fetch tools** — resolve current primary sources for the parallel multi-angle probes; record URLs and access dates.
- **research-venue-selection** — fired early here to emit the venue profile that becomes the venue-fit scoring angle (venue-as-input).
- **research-references** — verify any prior-art citation before it enters the gap argument or related-work; its literature pass doubles as the novelty scan.
- **research-finance-rigor** — a finance-leaning topic is tagged here; it owns the data-licensing/point-in-time/survivorship feasibility from Phase 1 on.
- **research-mock-review** — a lightweight Phase-1 dry-run against the venue profile fixes the acceptance bar the whole paper aims at.
- **research-algo-design** — Phase 2; does the *depth* per-candidate technical evaluation and the solvability gate that this phase's breadth scan sets up.
- **research-tracking** — logs this phase's effort against the 30% target (user-interaction hours).
