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

- **No leakage / correct splits** — for temporal or market targets, split by **time** and use walk-forward/out-of-sample evaluation; for non-temporal finance QA or document tasks, use entity/document/group-disjoint splits when repeated entities could leak. Random row splits are acceptable only when independence is defensible. **The paper carries a fixed-before-data ledger:** one paragraph in the design section that sorts every input into fixed in advance and never tuned / walk-forward by construction / in sample (a market constant, a construction chosen after a first pass, overlapping start years), then says whether there is a held-out period beyond the walk-forward and how many markets; an owner's "is this all in sample?" is answered by that ledger, not by a limitations sentence (earned 2026-09-18).
- **Multiple-testing and selection correction** — define the family and estimand first, then choose the appropriate control. Deflated Sharpe/PBO address strategy-selection overfit; White's Reality Check or Hansen's SPA compare data-mined rules; FWER/FDR procedures address hypothesis families. They are not interchangeable. Report all relevant trials and never present best-of-N unadjusted.
- **After-cost, co-primary metrics** — report **turnover, transaction costs, slippage, capacity, and drawdown** alongside (not after) the headline Sharpe/return. An alpha that dies under realistic costs is not a result.
- **Dependence-aware uncertainty** — report effect sizes with intervals across independent seeds/periods and use block bootstrap, HAC, cluster, or another design-appropriate method for serial/cross-sectional dependence; never treat rows or overlapping windows as independent.

## 2b) Ground truth does not exist on real data — define the realised label and say so

A synthetic study labels candidates true/false by construction; real data cannot. Replace the label with a *realised*, ex-post, referee-independent rule fixed before the run (e.g. mean post-submission edge over the remaining horizon ≥ the economic threshold, minimum window stated), disclose that late candidates carry short windows, and make the after-cost book statistic — not the label — the primary real-data metric. Re-derive the economic threshold from measured turnover, cost and return-per-unit-signal rather than copying a synthetic value, and if the registered value survives the check, keep it and publish the check (earned 2026-09-05: break-even IC ranged 0.004–0.03 across families; the registered δ stayed, disclosed as above break-even for three families and below for one).

## 2c) A controlled factor library ships its coverage table

When the paper's object is the *process* around factors (a referee, a controller, an agent) and the library is deliberately parametric, the first question after the real-data result is "is it all technical indicators, and are the families really different?" Answer it before it is asked, with measurements on the real panel: for every family the taxonomy category it covers (momentum, value, size, profitability, investment, growth, volatility, frictions), the grid size, the mean IC and its s.d., the share of specs above the economic threshold, the WITHIN-family correlation of the signal streams against the BETWEEN-family correlation (earned: 0.70–0.98 within vs 0.00 between — each family is one idea with parameter noise, which is what "family" should mean and must be said), signal coverage, turnover and break-even IC. Include fundamentals aligned on ANNOUNCEMENT dates (not period ends), with a staleness cap; state that factor discovery is not the contribution and that the library is controlled so the comparison is reproducible.

**One economic threshold across classes with 10x turnover differences penalises slow signals.** A cost-based threshold derived for a fast class (reversal, turnover ≈ 0.4/day) is 5x the break-even of a slow class (fundamentals, ≈ 0.06/day). Do not answer with a slower scoring clock — evidence per year (IC/sd · √obs) falls with the horizon for every class measured — answer with a per-class break-even table and a threshold slice (free baselines at two thresholds and two holding periods), and disclose that a realised label defined through the threshold relabels as it re-admits.

## 2d) Execution and prediction windows follow the trading calendar

**A factor's prediction horizon is part of its identity, and every instrument must use it.** A library that mixes 1--5-day reversal with 1--3-month momentum and fundamentals cannot be certified with one daily statistic, priced with one break-even threshold, and traded on one monthly calendar: each choice silently re-labels every factor as a one-horizon factor, and the three choices need not even agree with each other. The remedy is NOT to re-score the certificate per family (erratum 2026-09-12: the owner rejected it — non-overlapping windows at a family's horizon divide the anytime-valid sample by the horizon and make the standard non-uniform inside a library). Keep three layers apart: **certification** (one statistic at the library's declared horizon, one threshold, the finest-grained sample the machinery supports), **persistence** (the measured decay curve of the certified ranking, not certified), **execution** (each sleeve's holding period calibrated point in time from its own curve and turnover, with the right to *shelve* a certified factor whose best estimate does not pay). A slow-factor family is a scope statement — another library with its own declared horizon and threshold — and the sample-size boundary of what is certifiable is stated, not hidden.

Rebalance on the calendar a desk uses (daily; first open of the ISO week; first open of the month) and measure forecast horizons over those same windows — from the close before one rebalance day to the close before the next. A fixed count of 5 or 21 trading days drifts away from real execution points over years, and fundamentals arrive on the calendar (reporting deadlines; staleness caps in calendar days). Report evidence per year (IC/sd · √windows) per calendar rather than mean IC alone: slow signals gain IC per window and lose windows (earned 2026-09-07).

## 2d') A statistic converts to money at an average rate — measure it on the construction that trades it

**Before a statistic becomes an objective, check how it scales with its aggregation window.** A correlation against an h-day *average* return (the practitioner's "IC at horizon h") rises ≈ √h by noise averaging even when the per-day predictive power is flat or falling, so it ranks every holding period toward the longest and cannot choose one; the per-day curve (or the measured net return per frequency, from daily returns) can. Ten minutes of measurement on the actual panel settles it and the owner may then drop the familiar statistic from the paper (2026-09-12).

Any threshold derived as "cost / (return per unit statistic)" needs that conversion rate measured on the very book construction the paper trades (quintile sleeve, rank-weighted, ...), as **mean return / mean statistic**, and the regression of daily return on the daily statistic inspected for its intercept. A slope from daily data is dominated by high-dispersion days that carry large |statistic| and can overstate the average conversion three-fold (a −10 bp/day intercept is the signature); a break-even built on it is silently too lenient, and if it was shown to an agent it is a disclosure. "Certified" is a statement about the statistic; whether the factor pays its own trading is answered by the cost-vs-decay curve per family, per holding period, with cost charged on |Δw| only (2026-09-12).

## 2e) Multi-factor books aggregate positions, not signals

Averaging rank signals across styles and sorting once builds a composite that is nobody's factor: where styles disagree on a stock the signal cancels and the stock drops out, and each style's edge is diluted before it can be measured — weighting the signals by IC does not change that. Build each factor's own long/short book (its style intact), add the books with equal notional per factor, re-normalise at every rebalance (the factor count changes), and let disagreements net at the position level; record per-family sleeve returns so attribution is possible. Add the ex-ante controls a desk would use — a turnover cap per rebalance and an index beta hedge from rolling betas — and report beta measured, not assumed (owner correction 2026-09-07).

- **A certification statistic and a book must share a horizon, and a Sharpe ordering needs counterfactual books before it gets a mechanism.** A referee that certifies factors by daily IC and a book that trades monthly disagree about which factors are valuable: the daily statistic favours fast signals a monthly book cannot harvest and rejects slow ones it can; uncertified zero-edge factors can even hedge the certified ones. Before naming the reason a strict gate's book under-Sharpes a loose one, re-book the recorded holdings through the same accounting as (i) an equal-count random subset of the loose book (breadth), (ii) the strict gate's own factors at the loose gate's timing (earliness), (iii) the loose book minus one family at a time (composition / hedging), and read the calendar-window IC per family at the book's rebalance clock. Earned 2026-09-11: the first reading was "Sharpe rewards breadth"; the equal-count subset matched the full book exactly and the mechanism was horizon mismatch plus cross-family hedging. Score the referee at the book's holding horizon, and never let a portfolio Sharpe stand in for certification quality in either direction. Build every comparator under the treatment's own execution constraints: an "equal-breadth" random subset re-drawn at each rebalance under a turnover cap blends many draws and is far broader than its nominal size (rejected 2026-09-11); draw it once and hold it, and record mean positions per day so breadth matching is checked, not assumed.

## 3) Leakage-safe backtest infrastructure (don't reinvent it)

Prefer maintained execution/evaluation frameworks over a hand-rolled backtest when they fit: **qlib**, **FinRL / FinRL-Meta**, **backtrader**, **vectorbt**. These are engines, not leakage guarantees; audit data vintages, universe construction, splits, execution timing, costs, and defaults for every framework. For QA/reasoning-style finance-LLM work, anchor to public benchmarks — **FinQA, ConvFinQA, TAT-QA** — with a named-baseline comparison, not a bespoke metric.

## Cross-references

- **research-topic-selection** — tags a topic as finance-leaning and runs the data-feasibility part of this gate during the prior-art scan.
- **research-algo-design** — bakes the controls in at design time; its baselines include the honest simple ones (buy-and-hold, equal-weight).
- **research-experiments** — enforces the anti-leakage read-only sandbox and the statistical battery on runs.
- **research-provenance** — the traceability sibling; a finance number must be both provenance-resolved and rigor-honest.
- **research-writing** — reports after-cost/OOS metrics and the data-provenance statement in the appendix.
- **research-paper** — orchestrator; fires this gate whenever the topic is finance-leaning.
