---
name: research-submission
description: Post-packet tail — execute the submission (portal checklist, anonymization, supplement, arXiv, artifact release), then the decision branches; evidence-mapped rebuttals, revise-and-resubmit, camera-ready. Use when submitting or when reviews arrive.
---

# Research submission — from approved packet to published paper

The `research-mock-review` packet ends with the user's submit decision — this skill owns everything **after** it: executing the submission, the review cycle, camera-ready, and release. Production papers spend real effort here (multi-edition builds, supplements, response passes); an unmanaged tail loses an accepted-quality paper to a missed form, a broken anonymization, or a sloppy rebuttal.

## Ground rules

- **Everything outward-facing is user-confirmed before it leaves.** The agent stages, verifies, and drafts; the user uploads, clicks, and sends. A submission, an arXiv post, and a rebuttal are all irreversible publications — the same autonomy inversion as `research-mock-review`.
- **Every portal fact is re-verified against the venue's current pages** (forms, field limits, deadlines change every cycle) — the recency discipline of `research-venue-selection`, never recalled.

## Step 1 — Execute the submission

- **Rerun the audits on the exact artifact being submitted** — not the working draft: `research-provenance` (all RESOLVED), `research-references` (no UNVERIFIABLE), `research-visuals` (fonts/vector/Type-3), and — if multiple editions exist — a **version-consistency check** that shared numbers and claims match across them.
- **Walk the venue checklist literally:** page limit (incl./excl. references — venues differ), official template, required sections (ethics/broader impact, reproducibility checklist, AI-use disclosure per the venue's policy), and for double-blind an **anonymization sweep**: author names, acknowledgements, funding, repo/dataset links, self-revealing citation phrasing ("we showed [12]" → "[12] showed"), and **PDF metadata** (author fields survive compilation — check them).
- **Package the supplement separately** when the venue splits main paper from supplementary (appendix overflow, extra ablations, code zip) — each side self-contained, cross-references stated as "see supplementary §X".
- **Artifact / code release:** double-blind review → an anonymized mirror (e.g. an anonymous-repo service) with an install + one-command-reproduces-the-headline-table README; acceptance → public repo + archival DOI (e.g. Zenodo). License stated; data availability consistent with the licenses recorded at experiment time (`docs/local-env.md`; finance data per `research-finance-rigor`).
- **Stage the portal fields** (OpenReview / CMT / EasyChair): draft every form field — title, abstract (portal field limits differ from the paper's abstract), keywords, COI/conflicts — into `docs/submission/<venue>-form.md` for the user to paste and confirm.
- **arXiv** (when the Phase-1 arXiv-vs-double-blind reconciliation says post): category, license selection, and the **processor-matched, preview-verified LaTeX source** from `research-writing`'s submission build (arXiv recompiles the source — the PDF alone is not a submission). Mind the announcement schedule if timing/priority matters.
- **Record it:** submission date + venue + edition tag in the changelog; the fee as a `publication` cost row (`research-tracking`); the decision ETA into `state.json.target_submission_date` context.

## Step 2 — The decision (ranked-options handshake)

When the decision arrives, hand the user a pre-analyzed branch choice, per the orchestrator's gate pattern:

- **Accept / minor revision** → Step 4 (camera-ready), with the minor points mapped like a lite Step 3.
- **Major revision / revise-and-resubmit** → Step 3, plus a feasibility check of the required work against the resubmission window (`research-experiments` throttle math for any new runs).
- **Reject** → fold the reviews into the draft **first** (real reviews are the highest-value input the paper will ever get — log each point into the claims ledger / weakness list so the next submission is stronger), then route down the `research-venue-selection` fallback chain, re-verifying the next target's deadline. Never resubmit unchanged.

## Step 3 — Rebuttal / response protocol

1. **Parse every reviewer point into an addressable row:** `R#.n | type | response | evidence`, where type ∈ *misunderstanding* / *evidence-already-exists* / *new-work-needed* / *valid-limitation*.
2. **Evidence-first, never assertion:** each response cites a claims-ledger row, a table/figure, or a new run. A *misunderstanding* gets a polite pointer **plus a clarifying edit in the paper** — fix the text that allowed the misreading, don't just win the argument.
3. **Start from the mock-review rebuttal bank.** The panel pre-drafted responses to predicted weaknesses; reuse what hit, and score the prediction quality while at it (it calibrates the next mock review).
4. **Promise only what fits the window.** A new experiment enters the response only if it can actually complete before the response deadline; otherwise concede honestly and scope it as future work. An unkept rebuttal promise is worse than a concession.
5. **Tone:** thank, concede real points explicitly, correct factual errors with evidence, number every response to match the review. Draft → user approves → user sends.

## Step 4 — Camera-ready & release

- Apply the camera-ready deltas: **de-anonymize** (names, acks, funding, links restored), the venue's rights/copyright form, template differences (page allowance changes, reference style), and any reviewer-required items from the decision letter.
- **Rerun the three audits + render verification on the final PDF** — camera-ready edits are where a stale figure or broken reference sneaks back in.
- Post-acceptance closure: arXiv updated with the venue metadata (journal-ref/DOI when assigned); code/artifact flipped public and archived; README / architecture / changelog reflect the final state; acceptance and any remaining fees recorded in tracking. The paper is done when the *public record* is consistent — venue copy, arXiv copy, and repo all telling the same story.

## Cross-references

- **research-paper** — routes here after the user's submit decision at the Phase-4 gate; the tail is calendar-gated by the venue, not effort-gated.
- **research-writing** — owns the submission *build* (packaging, processor matching, preview/log verification, multi-edition assertions); this skill executes the process around that artifact.
- **research-mock-review** — its packet is the input; its drafted rebuttals seed Step 3.
- **research-venue-selection** — supplies the venue's forms/policies and the fallback chain on reject; fees flow to `research-tracking`.
- **research-provenance / research-references / research-visuals** — audits rerun on the exact submitted artifact and again at camera-ready.
- **research-experiments** — feasibility math for rebuttal-window experiments.
- **research-reflection** — the reject branch's reframe pass; optional while waiting for the decision.
