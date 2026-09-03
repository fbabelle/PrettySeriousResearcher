---
name: research-finance-rigor
description: Finance gate — enforce statistical honesty (deflated Sharpe, PBO, multiple-testing, walk-forward, after-cost) and data licensing/point-in-time/survivorship provenance; names leakage-safe backtest infra. Use for any finance-facing topic.
---

# Research finance-rigor — the AI×finance validity gate

Finance ML is where credible-looking results quietly die: a backtest that leaks future information, a Sharpe inflated by trying 200 configs and reporting the best, an alpha that evaporates under transaction costs, a dataset with survivorship bias. This gate enforces the two things a finance reviewer (and reality) will check — **the data is clean and licensed**, and **the numbers are statistically honest** — so a finance-leaning paper doesn't get desk-rejected or, worse, published wrong.

## When it fires

Only for **finance/market-facing topics** (equity/factor/portfolio/trading/forecasting/microstructure/risk). `research-topic-selection` tags the topic as finance-leaning; this gate then has three touchpoints:

- **Design-time (`research-algo-design`)** — bake the controls into the method before building (point-in-time features, temporal splits, cost model).
- **Run-time (`research-experiments`)** — enforce the anti-leakage sandbox and the statistical battery on every run.
- **Reporting (`research-writing` / `research-provenance`)** — every headline metric is reported after-cost, out-of-sample, and multiple-testing-aware.

## 1) Data licensing & provenance checkpoint (owned here)

Data is the binding constraint in AI×finance, so confirm it **up front** (a dead-end topic is one that needs data you can't license):

- **Licensing & access** — CRSP/Compustat/WRDS, Bloomberg/Refinitiv terms vs free tiers (FRED, Yahoo, SEC EDGAR, Polygon/IEX). Record what's licensed and what's not.
- **Point-in-time, not restated** — features must reflect what was knowable at the time; restated fundamentals are look-ahead.
- **Survivorship & selection** — delisted/dead names must be in the universe; a survivors-only backtest is biased upward.
- **Provenance trail** — record vendor, snapshot date, and point-in-time handling so results are checkable (feeds the appendix reproducibility statement).
- **Ready-made bundles are not data** — a framework's downloadable market bundle must be checked for currency, provenance and status (crawler source, end date, "disabled" notices, open issues on adjustments) before it enters the pipeline; several end years before the evaluation window. Price the vendor tiers from their own pages (points/tier thresholds, per-interface minimums, call caps, ToS on redistribution) — the tier that unlocks adjustment factors, delisted lists and index weights is usually cheap, the free tier usually isn't enough.
- **Point-in-time index membership is the hard requirement** — no free source gives it directly. Triangulate: a snapshot-by-date API looped daily/weekly, the index provider's official announcements for effective dates, and vendor monthly weights, merged into a `(code, start, end)` interval table; smoke-test that delisted names keep their price history; use a *fixed-anchor* price adjustment (a vendor's forward-adjusted series anchored on a later date is look-ahead).

This is the **positive replacement** for the one-line public-dataset auto-loaders the ML autonomous-science systems use — finance data rarely lives on a public hub and never loads leakage-safe by default.

## 2) Statistical-honesty battery

A result must survive all of these before it's believed or reported:

- **No leakage / correct splits** — for temporal or market targets, split by **time** and use walk-forward/out-of-sample evaluation; for non-temporal finance QA or document tasks, use entity/document/group-disjoint splits when repeated entities could leak. Random row splits are acceptable only when independence is defensible.
- **Multiple-testing and selection correction** — define the family and estimand first, then choose the appropriate control. Deflated Sharpe/PBO address strategy-selection overfit; White's Reality Check or Hansen's SPA compare data-mined rules; FWER/FDR procedures address hypothesis families. They are not interchangeable. Report all relevant trials and never present best-of-N unadjusted.
- **After-cost, co-primary metrics** — report **turnover, transaction costs, slippage, capacity, and drawdown** alongside (not after) the headline Sharpe/return. An alpha that dies under realistic costs is not a result.
- **Dependence-aware uncertainty** — report effect sizes with intervals across independent seeds/periods and use block bootstrap, HAC, cluster, or another design-appropriate method for serial/cross-sectional dependence; never treat rows or overlapping windows as independent.

## 3) Leakage-safe backtest infrastructure (don't reinvent it)

Prefer maintained execution/evaluation frameworks over a hand-rolled backtest when they fit: **qlib**, **FinRL / FinRL-Meta**, **backtrader**, **vectorbt**. These are engines, not leakage guarantees; audit data vintages, universe construction, splits, execution timing, costs, and defaults for every framework. For QA/reasoning-style finance-LLM work, anchor to public benchmarks — **FinQA, ConvFinQA, TAT-QA** — with a named-baseline comparison, not a bespoke metric.

## Cross-references

- **research-topic-selection** — tags a topic as finance-leaning and runs the data-feasibility part of this gate during the prior-art scan.
- **research-algo-design** — bakes the controls in at design time; its baselines include the honest simple ones (buy-and-hold, equal-weight).
- **research-experiments** — enforces the anti-leakage read-only sandbox and the statistical battery on runs.
- **research-provenance** — the traceability sibling; a finance number must be both provenance-resolved and rigor-honest.
- **research-writing** — reports after-cost/OOS metrics and the data-provenance statement in the appendix.
- **research-paper** — orchestrator; fires this gate whenever the topic is finance-leaning.
