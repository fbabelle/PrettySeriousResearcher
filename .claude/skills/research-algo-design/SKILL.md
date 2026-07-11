---
name: research-algo-design
description: Phase 2 (~20%) — evaluate candidate algorithms (efficiency, limits, maturity), pass a solvability gate, then design/implement the choice with tests, seeding ablation variants. Use when building the method once the topic is set (AI/Finance).
---

# Phase 2 — Algorithm / solution design & implementation

Turn the Phase-1 gap into a concrete, implemented method. The deliverable is a **chosen approach implemented with tests**, a set of **candidate variants** for later ablations, and a passed **solvability gate**.

## Step 1 — Per-candidate technical evaluation (depth)

Phase 1 asked "is the topic worth it?" (breadth). Phase 2 asks **"can *these specific* approaches solve the framed problem, and which is best?"** For each candidate approach (aim for 2–4), evaluate:

- **Effectiveness** — does the mechanism plausibly close the gap? On what evidence (prior results, theory, a quick spike)?
- **Efficiency** — compute/memory/latency cost; does it fit the local-execution envelope (see `research-experiments`)?
- **Limitations & assumptions** — where it breaks; what it silently assumes about the data/market.
- **Maturity** — is it rare/underexplored (novelty upside, more risk) or over-exploited (well-understood, lower novelty)?
- **The named-SOTA limitation it removes** — each candidate must name the *specific* limitation of a *named* SOTA method it beats (carried from the Phase-1 candidate card), plus a **co-primary efficiency/robustness metric** (compute, latency, turnover, drawdown) alongside the headline number — not "it's novel" in the abstract.

Use the host agent's current web-search and page-fetch tools for prior-art lookups on specific methods. This evaluation also defines the **baselines** the experiments will measure against — capture them now.

## Step 2 — The solvability gate (hard checkpoint)

Before building, answer plainly: **can at least one candidate plausibly solve the framed problem within our data/compute/budget envelope?**

Present the verdict as an **advisor-style ranked modification report the user confirms**, not a pass/fail the agent self-clears: per candidate, its **strengths/weaknesses**, **prioritized next steps** to make it work, and an explicit **feasible / unfeasible** classification — so the user chooses which approach to build from a pre-critiqued slate (the same confirm surface the orchestrator gates rely on), rather than auditing raw analysis.

- **Pass** → pick the approach (and the variants worth keeping as ablations) and build.
- **Fail** (no candidate classifies feasible) → do **not** push forward into expensive implementation/experiments. Hand back to **`research-reflection`** to revisit the framing or topic with the user. A clean "this framing isn't solvable as posed" now saves the 30% experiments budget later.

## Step 3 — Design the chosen approach

- Specify the method precisely enough to implement and to write up: inputs/outputs, the core mechanism, complexity, and the exact comparison to baselines.
- **Propose multiple approaches as first-class design artifacts** — the chosen one plus the variants that become the ablation matrix (Phase 3). Each variant should isolate one design decision so an ablation can attribute the effect. Keep a menu of **mutation/evolution operators** (swap a component, relax an assumption, change the objective, tier the model) to generate variants systematically rather than ad hoc.
- **Math ↔ code fidelity map (design-time anti-hallucination).** For any method with equations, maintain a bidirectional mapping from each equation/quantity to the code that implements it, and back. This extends the anti-hallucination discipline from "does the citation exist" (`research-references`) to "does our implementation actually match the math it claims" — checked in `research-code-review`.
- **AI & Finance design cautions:**
  - **No look-ahead / leakage** — features must be point-in-time; split train/val/test by *time*, never randomly, for any temporal/financial target.
  - **Costs & constraints** — if it's a trading/portfolio method, bake in transaction costs, slippage, position/turnover limits; an alpha that dies under realistic costs isn't a result.
  - **Right baselines** — include the honest simple ones (buy-and-hold, equal-weight, linear/ARIMA, last-value, a tuned non-neural model). Beating only a weak baseline is a classic reviewer kill.
  - **Determinism & seeds** — fix and record seeds; plan to report variance across seeds, not a single lucky run.

## Step 4 — Implement with tests

- Build in `src/`; experiments harness in `experiments/`; tests in `tests/`. Ship unit/regression tests **with** the code — they are part of the repo and must pass after major changes (see `research-repo-hygiene`).
- This is where the Python project is born: initialize **`uv`** (`uv init`, `uv python pin 3.12`), commit `pyproject.toml` + `uv.lock`, add deps with `uv add`, and run via `uv run` — see `research-repo-hygiene` for the full convention.
- For LLM-based methods, the design must anticipate the experiments-phase realities (token limits sized to real I/O lengths, reasoning-model latency, rate limits) — note expected I/O sizes now so `research-experiments` can calibrate and `research-tracking` can cost it.
- After writing code, **invoke `research-code-review`** (4-step design judgment + test discipline) before calling the step done.

## Step 5 — Emit cost drivers & hit the budget gate

At phase completion, set `state.json.gates.algo_design_complete: true` and hand the cost drivers (chosen approach, ablation count, expected per-call token sizes, local vs API execution) to **`research-tracking`** so the orchestrator can run the **budget-finalization playbook** before experiments begin. Do not enter Phase 3 until the budget is finalized.

## Exit criteria (Phase 2 → 3)

Chosen approach implemented and tested; baselines defined; ablation variants identified; solvability gate passed; code reviewed; budget gate cleared. Then the orchestrator advances to `research-experiments`.

## Cross-references

- **research-paper** — orchestrator; enforces the solvability gate (loop-back to reflection on failure) and the budget gate.
- **research-topic-selection** — Phase 1; its breadth gap claim is what this phase tests for depth/solvability.
- **research-experiments** — Phase 3; consumes the chosen approach, baselines, and ablation variants.
- **research-code-review** — invoked after any code here; checks the math↔code fidelity map.
- **research-finance-rigor** — for finance-leaning methods, bakes in point-in-time features, temporal splits, and the cost model at design time.
- **research-reflection** — the loop-back target if the solvability gate fails.
- **research-tracking** — runs the budget playbook this phase triggers.
- **Host web-search/page-fetch tools** — prior-art lookups for specific candidate methods, with primary-source verification.
