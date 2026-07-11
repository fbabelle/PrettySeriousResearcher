---
name: research-provenance
description: Results-integrity gate — every number, table, and figure in the draft must trace to a run artifact in runs/; surfaces only unresolved/placeholder values. The results sibling of the citation gate. Use at results-capture and before submission.
---

# Research provenance — the results-integrity gate

LLM-authored papers invent plausible-looking **numbers** the same way they invent citations: a Sharpe of 2.1 that never came out of a run, a table cell nudged to look better, a figure regenerated from stale data. This skill makes that impossible to ship by **forcing every reported result to resolve to a logged run artifact before it can enter the draft** — the exact discipline `research-references` applies to citations, applied to results. In AI+Finance, fabricated/overfit numbers are the #1 failure mode, so this is a first-class gate, not a nicety.

## The rule

*A number, table cell, or figure that cannot be traced to a logged artifact in `runs/` does not go in the paper.* Every reported value must resolve to a run keyed by config-hash → metric (the instrumented output `research-experiments` writes). Placeholders, hand-typed values, and hand-edited figures are defects, not results.

## When it fires

- **At results-capture (Phase 3)** — as `research-experiments` persists outputs, reconcile each headline number to its producing run so provenance is captured while the run context is fresh.
- **At the Phase-4 exit** — a full sweep of the draft: every table cell, every in-text statistic, every figure traces back, or it is flagged.
- Its output is a **required input to the `research-mock-review` packet**.

## The protocol

1. **Enumerate every reported quantity** in the draft (abstract stats, table cells, figure data, in-text numbers).
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

Rules, proven in production: **no orphan claims** (a claim without an evidence row doesn't ship) and **no orphan evidence** (a table/figure no claim uses gets cut); every row carries its sample size/seed count and the honest caveat ("live only", "benign 1-yr regime"); `Status` stays `draft` until the number is regenerated from current data and reconciled, then flips to `verified`. The Phase-4 sweep then reduces to auditing the ledger instead of rediscovering the draft, and `research-mock-review` consumes it directly.

## Make provenance executable where you can

The strongest form of this gate is an **assertion, not a review**: the scripts that turn `runs/` artifacts into tables and chart data must `assert` that the derived values reproduce the published numbers within tolerance (see `research-visuals` principle 5 and its figure-studio `prep_data` pattern). A failed assert means draft and data diverged — fix the divergence, never the assert. What's asserted mechanically never reaches the reconciliation table as an exception.

## Cross-references

- **research-experiments** — writes the instrumented `runs/` outputs (config-hash → metrics) this gate resolves against.
- **research-visuals** — regenerates figures from `runs/` so a figure *is* its artifact; its prep scripts assert chart data against published tables.
- **research-writing** — the Phase-4 exit requires a clean sweep (no UNRESOLVED rows).
- **research-mock-review** — bundles the reconciliation/ledger output into the pre-submission packet.
- **research-references** — the citation sibling: the same resolve-or-remove discipline applied to sources.
- **research-finance-rigor** — owns whether a resolved number is *statistically honest*; this gate only proves it's *real*.
