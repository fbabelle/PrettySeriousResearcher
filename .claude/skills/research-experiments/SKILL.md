---
name: research-experiments
description: Phase 3 (~30%) — smoke-test paid services, design the ablation matrix, probe local/supplier rate limits, build throttled+resumable run plans, track token/cost accounting. Use when planning or running experiments/ablations (AI/Finance, local).
---

# Phase 3 — Experiments & ablations

Where the claims get tested and 30% of effort (and most variable cost) lands. The deliverable is **evidence**: a clean ablation matrix, honest baselines, and results that survive scrutiny — produced on local hardware under real rate limits and a finalized budget. Apply the full [experimental-rigor protocol](references/experimental-rigor.md) before the full run and again during reporting.

## Step 1 — Pre-flight smoke tests = boundary calibration (do this BEFORE any full run)

A smoke test here is **not** "does it run once" — it **discovers the operating envelope and proves robustness**, especially for **cost-triggered services (LLM APIs, data-vendor APIs)**. Run it small and cheap, then read off:

- **Boundary discovery per service.** Measure the real **input/output token-length distribution** for the actual call scenarios — set `max_tokens` from measurement, not a guess. Distinguish **reasoning models** (much larger output budgets, longer/variable latency — verify against the provider's current official model/API documentation) from standard ones. Record per-call **latency** and timeout tolerances for the specific models/providers in this project.
- **Meaningfulness checks.** Confirm function-calling / prompt framings return *useful, parseable* data on the large majority of calls. Measure and drive down **parse-failure** and **excessive-retry** rates; fix schemas/framings until results are reliable. A run that mostly retries or returns garbage is wasted budget.
- **Config robustness.** Validate configs across the scenario spread — long vs short inputs, rate-limit bursts, partial failures, empty/degenerate responses — with sane backoff and retry caps.
- **Outputs feed two consumers.** The measured I/O sizes + latencies + failure rates refine (a) the **throttled/resumable run plan** below and (b) the **cost estimate** that `research-tracking` uses for the **budget-finalization gate**. Record a **go/no-go summary** before the full run is authorized.

## Step 2 — Probe the local environment & supplier limits

Experiments run on the **user's local machine** — plan around its limits, don't assume a cluster. Probe once and write the findings to `docs/local-env.md` — a **project** doc, not a skill file; the installed skills stay read-only (see `research-repo-hygiene`). Record:

- **Hardware:** CPU cores, RAM, GPU/VRAM (or none), free disk. **Detect the host OS first** (Linux / macOS / Windows) — never assume it; commands, paths, and GPU tooling all differ.
- **Rate limits & quotas:** query the supplier docs for each API in play (LLM provider TPM/RPM tiers, data-vendor request caps, batch windows). Record the actual ceilings.
- **Throughput math:** from per-call latency × concurrency-under-limit, estimate wall-clock for the full matrix. If it's days, that's a planning input, not a surprise.

**Two guardrails on the autonomous runner (adopt from the research-agent harnesses):**
- **Anti-leakage read-only sandbox.** The agent must not be able to tune to the test set, edit the evaluation script, or introduce look-ahead: hold the **datasets *and* the eval/grader script read-only**, run under a non-privileged user, and freeze leakage-resistant splits: by time for temporal targets, or by entity/group when repeated entities could cross partitions. A run that can touch its own grader is a leakage waiting to happen (the #1 finance-ML failure). For finance, `research-finance-rigor` owns the point-in-time/survivorship side of this.
- **Capability containment.** The agent **never self-provisions paid compute, scrapes new data, or signs up for a new paid service without explicit user confirm** — those are budget/legal decisions, not run decisions. Surface them as a gate, don't act on them autonomously.

## Step 3 — Design the ablation matrix

Turn the Phase-2 candidate variants into a matrix where **each cell isolates one design decision** so its effect is attributable. Include:
- The chosen method, the baselines (incl. honest simple ones), and one-factor-at-a-time variants.
- **Anchor to an established public benchmark** with one comparable headline metric vs *named* baselines (for finance QA: FinQA/ConvFinQA/TAT-QA; for trading/portfolio use `research-finance-rigor`'s leakage-safe infra), plus a **co-primary efficiency/robustness metric** (turnover, capacity, transaction cost, drawdown, latency) — not the headline number alone. Beating only a bespoke metric or a weak baseline is a classic reviewer kill.
- **Prospective analysis plan** — state the estimand, unit of analysis, primary/secondary endpoints, independent sample size, inclusion/exclusion and stopping rules, and a power/precision justification before inspecting final test results.
- **Seeds/repeats** for variance — justify the count and report effect sizes with confidence/credible intervals, not a single run or p-values alone.
- **Dependence and multiplicity plan** — predefine the comparison family; use paired or dependence-aware intervals/tests and one correction matched to the inferential goal. For finance, prefer true out-of-sample/walk-forward evaluation and report Sharpe/drawdown/turnover **after costs**.
- **Evaluation disclosure** — for LLMs record exact model snapshot/date, complete prompts/tool schemas/decoding, contamination checks, judge calibration/blinding, and repeated sampling; for human evaluation record consent/ethics determination, compensation, instructions, rater assignment, and agreement.
- A descope plan: if the budget/time can't cover the full matrix, which cells are dropped — and **log the descope** (no silent truncation).

## Step 4 — Throttled, resumable, instrumented runs

Local + rate-limited means runs must survive interruption and respect ceilings:
- **Reproducible env:** run every experiment under **`uv`** (`uv run python …`) against the committed `uv.lock` / Python 3.12, so a result can be reproduced exactly on another machine or after a gap — see `research-repo-hygiene`.
- **Resumable:** checkpoint after each cell/batch; idempotent re-runs (skip completed work via a manifest/cache keyed by config hash). A killed run resumes, it doesn't restart.
- **Throttled:** concurrency capped to the measured rate limit; exponential backoff on 429/5xx; for LLM bulk work consider the **Batch API** (50% cheaper, async) and **prompt caching** (cache-read ≈ 10% of input) — both are budget levers from `research-tracking`.
- **Instrumented:** every API call logs its `usage` (input/output/cache tokens, optional explicit `usd`, `model`, `phase`) to `runs/usage.jsonl` — this is the **source `research-tracking` prices for the experiment LLM API cost** (the metered, gated spend), distinct from the coding-agent subscription and the transcript-derived effort numbers. Local-model runs log compute-hours instead (cost ≈ electricity/amortization, entered into `cost.json`).
- **Bounded self-debug, not open tree search.** When a run errors, allow a **capped repair loop** (a fixed max-debug-depth, then abandon the cell and log it) and keep a **scored best-program/best-config buffer** that seeds the ablation variants — the useful, bounded pieces of the experiment-search engines. Do **not** run a full best-first agentic tree search over the config space: for AI+Finance the binding constraint is data licensing / leakage / cost-realism, not a huge hyperparameter search, and the extra unattended autonomy works against the confirm-surface the gates provide.
- **Campaign hardening (each earned in a real multi-week campaign):** a **credit/quota watchdog** — check remaining supplier credits/quota before and during long campaigns, don't discover exhaustion mid-run; **back up the official result stores before any destructive rerun or migration** (a one-command backup script, run before, not after); **re-execution at the smallest unit** — support re-running a *single* cell/round in place (with the repaired code, same config hash) so one bad record doesn't force a campaign restart.
- **Dataset/API licensing check (any domain, not just finance):** before a dataset or data API enters the matrix, record that its license/ToS permits research use and whether results/excerpts can be redistributed (into `docs/local-env.md` alongside the rate limits). Finance-facing data additionally goes through `research-finance-rigor`'s licensing/point-in-time checkpoint.
- After writing harness/run code, **invoke `research-code-review`**.

## Step 5 — Capture results honestly

Persist raw outputs, and generate the derived tables/figures through **`research-visuals`** (figures-as-code from `runs/`: vector, shared style, no baked-in titles/captions) so they're publication-ready and auditable, not throwaway PNGs. Report negative and null results plainly (the orchestrator's null-result branch is a legitimate outcome, not a failure). If a result looks too good, suspect **leakage** first (the #1 finance-ML failure) — re-verify the temporal split and point-in-time features before believing it. Run the first **`research-provenance` reconciliation here** while the run context is fresh: every headline number must key back to a `runs/` artifact; for finance topics, the number must also clear the **`research-finance-rigor`** statistical battery (deflated Sharpe / PBO / multiple-testing / after-cost). Traceable *and* honest.

## Exit criteria (Phase 3 → 4)

Pre-flight go/no-go and timestamped analysis plan recorded; the planned matrix run (or its descope logged); independent sample size and all attempted conditions disclosed; results reported with effect sizes, justified uncertainty, multiplicity control, and after-cost metrics where relevant; LLM/human evaluation disclosures complete; leakage and contamination checks passed. Then the orchestrator advances to `research-writing`.

## Cross-references

- **research-paper** — orchestrator; will not enter this phase until the budget is finalized.
- **research-algo-design** — supplies the chosen method, baselines, and ablation variants; its expected I/O sizes seed the smoke test.
- **research-tracking** — the smoke-test measurements feed its budget gate; `runs/usage.jsonl` is the priced source for its experiment LLM API cost line (separate from coding-agent subscription and transcript effort).
- **research-code-review** — invoked after harness/run code.
- **research-provenance** — reconciles every reported number to a `runs/` artifact; its first pass runs here at results-capture.
- **research-finance-rigor** — for finance topics, owns the anti-leakage point-in-time/survivorship controls and the statistical-honesty battery on every run.
- **research-visuals** — turns run outputs into publication-quality, vector, audited figures/tables.
- **Provider official documentation** — current model limits, streaming, batch, caching, rate limits, and pricing for the run plan; record the URL and verification date.
