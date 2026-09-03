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
- **Limitations & assumptions** — where it breaks; what it silently assumes about the data/market. **Extract the assumption fine print from primary sources** (exact dependence/independence conditions, calibration requirements, what the theorems actually cover) — method-level assumptions routinely decide the whole stack choice, and secondary summaries omit them.
- **Maturity** — is it rare/underexplored (novelty upside, more risk) or over-exploited (well-understood, lower novelty)?
- **The named-SOTA limitation it removes** — each candidate must name the *specific* limitation of a *named* SOTA method it beats (carried from the Phase-1 candidate card), plus a **co-primary efficiency/robustness metric** (compute, latency, turnover, drawdown) alongside the headline number — not "it's novel" in the abstract.

Use the host agent's current web-search and page-fetch tools for prior-art lookups on specific methods. This evaluation also defines the **baselines** the experiments will measure against — capture them now.

## Step 2 — The solvability gate (hard checkpoint)

Before building, answer plainly: **can at least one candidate plausibly solve the framed problem within our data/compute/budget envelope?**

Present the verdict as an **advisor-style ranked modification report the user confirms**, not a pass/fail the agent self-clears: per candidate, its **strengths/weaknesses**, **prioritized next steps** to make it work, and an explicit **feasible / unfeasible** classification — so the user chooses which approach to build from a pre-critiqued slate (the same confirm surface the orchestrator gates rely on), rather than auditing raw analysis.

- **Pass** → pick the approach (and the variants worth keeping as ablations) and build — but **spike the riskiest assumption first**: before full implementation, run a 1–2 session spike that measures the make-or-break quantity at *realistic* problem scale/SNR (not toy settings). A spike that fails is a success of the process — it converts an invisible risk into a design lesson (often publishable as such) at minimal cost, and the fallback switches while the harness is still shared. Theory-valid machinery can still be practically broken by a tuning choice; only empirical behavior at real scale settles it.
- **Fail** (no candidate classifies feasible) → do **not** push forward into expensive implementation/experiments. Hand back to **`research-reflection`** to revisit the framing or topic with the user. A clean "this framing isn't solvable as posed" now saves the 30% experiments budget later.

## Step 3 — Design the chosen approach

- Specify the method precisely enough to implement and to write up: inputs/outputs, the core mechanism, complexity, and the exact comparison to baselines.
- **Propose multiple approaches as first-class design artifacts** — the chosen one plus the variants that become the ablation matrix (Phase 3). Each variant should isolate one design decision so an ablation can attribute the effect. Keep a menu of **mutation/evolution operators** (swap a component, relax an assumption, change the objective, tier the model) to generate variants systematically rather than ad hoc.
- **Math ↔ code fidelity map (design-time anti-hallucination).** For any method with equations, maintain a bidirectional mapping from each equation/quantity to the code that implements it, and back. This extends the anti-hallucination discipline from "does the citation exist" (`research-references`) to "does our implementation actually match the math it claims" — checked in `research-code-review`.
- **State expected operating scale, derived from the method's own math.** A design isn't complete when the mechanisms are specified: back-of-envelope the system's operating point (candidate-universe size, expected throughput/acceptance rates, steady-state stock via Little's law, latency floors) from the design's own quantities, and label the results as pre-registered design estimates the experiments will validate. This surfaces internal inconsistencies early and preempts the reviewer/user question "so how much does it actually produce, how fast?".
- **Headline "opportunities" are measured against the *feasible* oracle.** A proposal that quotes its upside as (oracle − current) must use an oracle that respects the implementation's own constraints (caps, bounds, safety margins); an unconstrained optimum can be unplayable, and the true headroom may be an order of magnitude smaller than the quoted one. If a constraint is relaxed to create headroom, every baseline gets the same relaxed action space. **Corollary — a binding constraint erases the capability:** when the optimum exceeds the cap for *every* policy (perfect, noisy and overconfident alike), all policies act identically through that channel and no skill is measurable there; retire the claim and look for channels where the constraint does not bind (behaviour under the null, held-out tasks, what is *submitted* rather than how fast it clears).
- **Fetch the exact rule before coding a sequential / multiple-testing procedure.** Abstracts never carry the rejection rule; read the definition (threshold, weights, index conventions, finality of decisions, dependence and filtration conditions) from the paper's full text, cite it in the fidelity map, and reproduce one worked example as a unit test. Two rules from the same family can differ in a single index and diverge completely in behaviour.
- **When a planned capability dies, run a constraint-scored capability scan before proposing replacements.** Score each candidate 0–3 on: non-enumerable (its output is not a choice among designer-defined options), measurable by the paper's own frozen evaluator without touching it, a strong non-AI baseline at matched budget, not crowded on a *dated* audit, affordable inside the remaining effort, and thesis-fit; adopt only candidates ≥ 2 on every axis, and record the killed ones with reasons so they are not re-proposed.
- **Scope exclusions carry reasons and revival paths.** For every dimension deliberately left out (data types, frequencies, asset classes, model families), record the specific blocking reason (ideally with the quantified cost of inclusion) and the condition under which it re-enters. Unstated cuts read as arbitrary; costed cuts read as design.
- **AI & Finance design cautions:**
  - **No look-ahead / leakage** — features must be point-in-time; split train/val/test by *time*, never randomly, for any temporal/financial target.
  - **Costs & constraints** — if it's a trading/portfolio method, bake in transaction costs, slippage, position/turnover limits; an alpha that dies under realistic costs isn't a result.
  - **Right baselines** — include the honest simple ones (buy-and-hold, equal-weight, linear/ARIMA, last-value, a tuned non-neural model). Beating only a weak baseline is a classic reviewer kill.
  - **Determinism & seeds** — fix and record seeds; plan to report variance across seeds, not a single lucky run.

## Step 4 — Implement with tests

- Build in `src/`; experiments harness in `experiments/`; tests in `tests/`. Ship unit/regression tests **with** the code — they are part of the repo and must pass after major changes (see `research-repo-hygiene`).
- This is where the Python project is born: initialize **`uv`** (`uv init`, `uv python pin 3.12`), commit `pyproject.toml` + `uv.lock`, add deps with `uv add`, and run via `uv run` — see `research-repo-hygiene` for the full convention.
- For LLM-based methods, the design must anticipate the experiments-phase realities (token limits sized to real I/O lengths, reasoning-model latency, rate limits) — note expected I/O sizes now so `research-experiments` can calibrate and `research-tracking` can cost it.
- **Prompts are first-class artifacts, not filler.** A generic system prompt makes the agent decorative and any controller comparison uninterpretable — the model cannot reason about a mechanism it was never told about. Each role's prompt carries the actual mechanics, real magnitudes, what the role may not touch, the true economics of its actions, and worked good/bad examples; it is versioned, hashed into every ledger row (an edit is a visible experimental change), and guarded by a **lint** that fails short, generic, placeholder-ridden, example-free or magnitude-free prompts. Each role also declares an output **contract** (schema + semantic validator + a fallback that itself passes the validator) because roles emit different shapes — an allocation, an expression, a diagnosis, code, a plan.
- After writing code, **invoke `research-code-review`** (4-step design judgment + test discipline) before calling the step done.

## Step 5 — Emit cost drivers & hit the budget gate

At phase completion, set `state.json.gates.algo_design_complete: true` and hand the cost drivers (chosen approach, ablation count, expected per-call token sizes, local vs API execution) to **`research-tracking`** so the orchestrator can run the **budget-finalization playbook** before experiments begin. Do not enter Phase 3 until the budget is finalized.

## Exit criteria (Phase 2 → 3)

Chosen approach implemented and tested; baselines defined; ablation variants identified; solvability gate passed; code reviewed; budget gate cleared. Then the orchestrator advances to `research-experiments`.

## Regret and value metrics — transparent economy first

When an experiment needs to price decisions (regret vs an oracle, after-cost value of an intervention) but the phenomenon lives outside the simulation engine (e.g. data faults the market simulator does not model), do not bolt it into the engine first: write a **transparent economic model** — a stated constants table (lags, costs, return horizons) mapping true state × action → value over a horizon — whose oracle is the argmax by construction and is unit-tested, and get common random numbers by showing the *identical* episode to every arm. The engine-embedded, branched-rollout version is a later upgrade for the headline experiment, recorded as an amendment in the design doc rather than a silent substitution (earned: probe-environment build, 2026-09-01).

## Cross-references

- **research-paper** — orchestrator; enforces the solvability gate (loop-back to reflection on failure) and the budget gate.
- **research-topic-selection** — Phase 1; its breadth gap claim is what this phase tests for depth/solvability.
- **research-experiments** — Phase 3; consumes the chosen approach, baselines, and ablation variants.
- **research-code-review** — invoked after any code here; checks the math↔code fidelity map.
- **research-finance-rigor** — for finance-leaning methods, bakes in point-in-time features, temporal splits, and the cost model at design time.
- **research-reflection** — the loop-back target if the solvability gate fails.
- **research-tracking** — runs the budget playbook this phase triggers.
- **Host web-search/page-fetch tools** — prior-art lookups for specific candidate methods, with primary-source verification.
