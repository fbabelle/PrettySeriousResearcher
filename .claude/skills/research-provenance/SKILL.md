---
name: research-provenance
description: Results-integrity gate — every number, table, and figure in the draft must trace to a run artifact in runs/; surfaces only unresolved/placeholder values. The results sibling of the citation gate. Use at results-capture and before submission.
---

# Research provenance — the results-integrity gate

LLM-authored papers invent plausible-looking **numbers** the same way they invent citations: a Sharpe of 2.1 that never came out of a run, a table cell nudged to look better, a figure regenerated from stale data. This skill makes that impossible to ship by **forcing every reported result to resolve to a logged run artifact before it can enter the draft** — the exact discipline `research-references` applies to citations, applied to results. In AI+Finance, fabricated/overfit numbers are the #1 failure mode, so this is a first-class gate, not a nicety.

## The rule

*A number, table cell, or figure that cannot be traced to a logged artifact in `runs/` does not go in the paper.* Every reported value must resolve to a run keyed by config-hash → metric (the instrumented output `research-experiments` writes). Placeholders, hand-typed values, and hand-edited figures are defects, not results.

**No artefact, no number — and an auditor's prose is not an artefact.** A statistic that a human or a subagent computed ad hoc while checking the draft must be written by a script into a run report before it enters the text; otherwise the draft inherits whatever the auditor happened to look at. The specific way this fails: a campaign-level or book-level statistic is quoted from the one seed the auditor opened, and the draft says "the book" where the artefact says "seed 0". A campaign statistic is always the multi-seed value with its seed range, and the check scripts that produce it live in the repo (earned 2026-09-15: several headline numbers traced only to an audit's prose; four check scripts had to be written to create the artefacts they should have come from).

## When it fires

- **At results-capture (Phase 3)** — as `research-experiments` persists outputs, reconcile each headline number to its producing run so provenance is captured while the run context is fresh.
- **At the Phase-4 exit** — a full sweep of the draft: every table cell, every in-text statistic, every figure traces back, or it is flagged.
- Its output is a **required input to the `research-mock-review` packet**.

## The protocol

1. **Enumerate every reported quantity** in the draft (abstract stats, table cells, figure data, in-text numbers) — **including direction words**. A sentence that states a direction ("ahead/behind", "above/below", "narrows/widens") carries a sign that must be re-derived from the artefact table at writing time and again at the sweep; a check that matches numbers only will pass a sentence whose direction is inverted (earned 2026-09-15: one such sentence survived several provenance passes with every number in it correct). Significance annotations are numbers too: a "significant in k of n" or a Holm count is re-read from the *current* report after every re-run or re-booking; the recurring failure is a count carried over from an earlier report whose correction family was smaller (earned 2026-09-16: the current artefact had none where the prose said three).
2. **Resolve each to an artifact** — the `runs/` record (config-hash, seed, metric) that produced it. Regenerate figures from `runs/` via the `research-visuals` figures-as-code pipeline so a figure *is* its artifact, not a pasted bitmap.
3. **Assign a verdict:** RESOLVED (traces cleanly), STALE (artifact exists but predates the current config — rerun), or **UNRESOLVED** (no artifact / placeholder / hand-edited → **must fix or remove**).
4. **Surface only the exceptions.** Emit a reconciliation table, but only STALE/UNRESOLVED rows need the user's attention — so the user never hunts the whole draft for a fabricated number (that diagnosis is done for them).

## Output: the reconciliation table

```
| Reported value | Where (section/table/fig) | Resolving artifact (run id / config-hash) | Verdict |
|---|---|---|---|
| Sharpe 2.26 | §7.3, Table 5 | runs/2026-06-30/a3f9c1…/scorecard.csv | RESOLVED |
| accuracy 0.84 | Fig. 3 | runs/2026-06-12/77b2e0… (config changed 06-28) | STALE — rerun |
| "3× faster" | Abstract | (no artifact) | UNRESOLVED — fix or remove |
```

## The claims ledger (the running form of the gate)

Don't wait for the Phase-4 sweep — maintain a **claims ledger** (`docs/claims-ledger.md`) from the moment results start landing. One row per quantitative or comparative claim in the draft:

```
ID | § | Claim (one line) | Evidence (file/table/fig + cell) | n / seeds | Caveat | Status
```

A measured result the owner decides *not* to put in the paper keeps its row with the status **internal check, not a paper item** — the evidence stays reproducible and the decision stays visible, and nobody re-litigates it next month (2026-09-12).

Rules, proven in production: **no orphan claims** (a claim without an evidence row doesn't ship) and **no orphan evidence** (a table/figure no claim uses gets cut); every row carries its sample size/seed count and the honest caveat ("live only", "benign 1-yr regime"); `Status` stays `draft` until the number is regenerated from current data and reconciled, then flips to `verified`. The Phase-4 sweep then reduces to auditing the ledger instead of rediscovering the draft, and `research-mock-review` consumes it directly.

## A constant quoted in the theory is a derived number with provenance

Thresholds and conversion factors that the method section *derives* (a break-even, a scaling constant, a calibration) are results, not definitions: they belong in the ledger with the artefact that measures them, and they must be recomputed — and the arithmetic re-done — whenever that measurement changes. Two independent failures in one line of this project: the theory carried the superseded estimate of a conversion rate long after a better measurement existed, *and* the formula that turned it into per-family thresholds had a wrong coefficient, so every quoted threshold was too low and nobody noticed because the numbers were internally consistent with each other. The check that catches both is to re-derive the constant from the measurement it summarises by a second route (here: break-even = IC x cost / gross, read straight off the cost curve) and require the two to agree to a stated tolerance (2026-09-14).

## A design change silently re-aims the existing reports

When the construction under measurement changes (a shared schedule becomes per-unit, a pooled book becomes per-unit books), walk every derived series and ask *what days / units does this actually sample now*. A per-family attribution that recorded returns on rebalance days was interpretable while every unit rebalanced together; once each unit had its own calendar the same code sampled only that family's formation days and every number turned negative — a reading that would have gone into the paper as a finding. The signature is a table that suddenly disagrees with a quantity you trust (here the ledger, accrued every held day). Suppress or re-derive the affected section, say in the report why, and prefer the series with the denominator you can state in one sentence (2026-09-13).

## Make provenance executable where you can

The strongest form of this gate is an **assertion, not a review**: the scripts that turn `runs/` artifacts into tables and chart data must `assert` that the derived values reproduce the published numbers within tolerance (see `research-visuals` principle 5 and its figure-studio `prep_data` pattern). A failed assert means draft and data diverged — fix the divergence, never the assert. What's asserted mechanically never reaches the reconciliation table as an exception.

## Cross-references

- **research-experiments** — writes the instrumented `runs/` outputs (config-hash → metrics) this gate resolves against.
- **research-visuals** — regenerates figures from `runs/` so a figure *is* its artifact; its prep scripts assert chart data against published tables.
- **research-writing** — the Phase-4 exit requires a clean sweep (no UNRESOLVED rows).
- **research-mock-review** — bundles the reconciliation/ledger output into the pre-submission packet.
- **research-references** — the citation sibling: the same resolve-or-remove discipline applied to sources.
- **research-finance-rigor** — owns whether a resolved number is *statistically honest*; this gate only proves it's *real*.
