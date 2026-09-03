---
name: research-tracking
description: Track and report effort (agent-active hours + tokens) and cost (USD), and run the budget-finalization playbook. Use when reporting time/budget, updating a plan (re-report cost), at the budget gate, or when asked about hours, tokens, or spend.
---

# Research tracking — effort & cost

This skill keeps an honest, auditable record of two things across the life of a paper: **effort** (agent-active hours + tokens) and **cost** (USD). Cost has two lineages that must not be conflated:

- **Project overhead (reported, NOT gated)** — coding-agent billing and publication/submission fees. First identify the actual coding plan: record flat plans in `coding_agent.agents[]`; record metered coding bills as `actuals` rows with `category: "coding_agent"`. Never infer billing from transcript tokens. Publication fees use `category: "publication"`.
- **Variable spend (gated by the budget cap)** — experiment/system **LLM API** cost (the metered cost of running the method, from `runs/usage.jsonl`), **local compute**, and **data providers**.

It also runs the **budget-finalization playbook** that gates entry into experiments (on the variable spend).

## Keep time measures distinct

Keep measured clocks distinct. **Agent-active effort** is derived from compatible transcript events and excludes idle gaps over one hour; it is not a measurement of the user's attention. **User-interaction time** must be measured explicitly when it matters. **Background runtime** covers unattended experiments and review panels. Report each available measure separately, label estimates, and use calendar/venue deadlines for delivery forecasts.

Exact file schemas, the session-boundary algorithm, and the cost formula live in [references/ledger-formats.md](references/ledger-formats.md). Read that before editing any ledger by hand. This file is the *when* and *how-to-decide*.

## Core principle: derive, don't fabricate

`track.py` parses **Claude Code JSONL only**. On another host, use a schema adapter or record measured effort manually; do not pass an incompatible transcript and call the output measured. Transcript tokens are an effort signal and are priced only when they map to an actual metered bill. Flag every estimate and missing source.

```
python .claude/skills/research-tracking/scripts/track.py            # refresh + print report line
python .claude/skills/research-tracking/scripts/track.py --json     # machine summary
```

`track.py` splits compatible Claude Code events into agent-active sessions, sums tokens by model, prices experiment usage from `runs/usage.jsonl`, and reports configured coding-plan or metered actuals. It is idempotent. Without compatible transcripts, effort auto-parsing is unavailable; record measured effort manually or add an explicit adapter. Cost still computes from usage, actuals, and configured plans.

## When to run it

- **Every plan update.** Whenever a timestamped plan is written to `docs/plans/`, run `track.py` and surface the compact report line. Effort and cost reporting share this trigger so they never drift.
- **On phase transitions.** Before advancing, run it and compare per-phase agent-active hours to the 30/20/30/20 split of `effort_target_hours`. If a phase exceeded its weight, emit a **non-blocking** overrun warning (e.g. "topic-selection used 38% of the 120h budget vs a 30% target") — a heads-up, not a halt.
- **When the user asks** about time, tokens, or money.

## The compact report line

Always report cost and effort together, in one line, so the user sees the whole picture:

```
Spent $X of $Y cap (Z%) | exp-llm $a / compute $b / data $c | coding $d (sub, N mo) | effort: H active-hrs, T tokens
```

`$X` and the cap are **variable spend only** (exp-llm + compute + data). The coding fields report flat-plan estimates plus explicit metered coding actuals outside that experiment cap. When the budget is still provisional, `$Y cap` reads `UNSET (provisional)` — that itself is a signal the budget gate hasn't been cleared yet.

## Phase weights are soft targets

The 30/20/30/20 split (topic / algo / experiments / writing) is a **planning target**, not a quota. Overruns produce a warning and a short note on *why* (e.g. "deep prior-art scan ran long — justified, the novelty gap needed nailing down"), not a stop. Under-runs are fine and unremarked. Never reshape the research to hit the numbers.

## Coding-agent billing (detect, then record)

Do not assume a CLI is flat-rate or zero-marginal-cost. Confirm whether each installed agent is subscription-covered, credit-limited, usage-metered, or API-backed, and record the billable basis.

Before running review/reflection panels, detect the billing basis of every CLI. Subscription-covered runs stay in the configured plan line; metered coding-agent charges are recorded as explicit `actuals` with `category: "coding_agent"`. Metered experiment/system calls still log to `runs/usage.jsonl` and remain subject to the experiment cap.

- **Ask for or verify the actual plan — don't guess it.** For flat plans, populate `cost.json.coding_agent.agents[]` and use `share_pct` when appropriate. For metered plans, record billed amounts as coding-agent actuals.
- **Expense = Σ(fee × share) × months_active**, where `months_active` is the count of distinct calendar months with agent activity (auto-derived from the effort clock). Set `months_active_override` if you'd rather fix it by hand.
- **Coding overhead is reported outside the experiment cap.** Both subscription estimates and explicit metered coding actuals appear in the grand total; the separate experiment cap still governs method-running API, compute, and data spend.

## The budget-finalization playbook (the gate before experiments)

`cost.json.status` starts `provisional`. The orchestrator **blocks entry to the experiments phase** until it is `finalized`. The cap governs **variable spend** (experiment LLM API + compute + data); coding-agent plan estimates and metered coding actuals are tracked separately and are not part of this experiment gate. When the gate is hit (Phase 2 done, `algo_design_complete: true`), run this playbook — do **not** assume the user's budget appetite:

1. **Gather the cost drivers.** From `research-algo-design` (the chosen approach and its candidate ablations) and the `research-experiments` pre-flight smoke test (measured I/O token sizes, latency, failure/retry rates, local compute profile), estimate the spend of a full run.
2. **Present 2–3 scenarios — lean / balanced / aggressive — with explicit efficiency-vs-cost tradeoffs.** Span all three categories the "both significantly" cost model implies:
   - **LLM:** model tiering (Haiku/Sonnet for bulk, Opus for the hard cases), **prompt caching** (cache-read is ~10% of input — huge for repeated context), the **Batch API** (50% off, async), and sampling/ablation count (fewer seeds/items = cheaper, wider CIs).
   - **Local compute:** run scope, precision, parallelism vs RAM/thermal limits, how many ablation cells.
   - **Data:** free tiers vs paid overages, one-off pulls vs subscriptions.
   For each scenario give a rough USD total and what it buys/costs in statistical power and wall-clock.
3. **Recommend one, but let the user set the cap.** State your recommendation and why; the number is theirs to choose.
4. **Finalize.** Set `cost.json` `status: "finalized"`, `finalized_at`, `budget.total_cap`, and `budget.by_category` (the `llm_api`/`compute`/`data` variable caps — not coding); flip `state.json.gates.budget_status`. Re-report the cost line. Re-finalization later is allowed but must be explicit and logged (append a dated note in `cost.json`; never silently overwrite a cap).

## Finishing-date estimate (feeds venue selection)

This skill also surfaces the **estimated finishing date** — kept in `state.json.estimated_finish_date` (and `target_submission_date` once a venue is chosen), echoed in the `--json` output. Because the work is automated, **do not project it from human-labor calendar velocity.** Estimate from what actually remains: the **number of remaining confirm-loops** (user-interaction hours still ahead), the **background runtime** those loops kick off (experiment wall-clock, panel runs), and any **binding venue deadline**. It's a judgement, not a hard computation. `research-venue-selection` runs **twice** off this: **early in Phase 1** it emits the venue profile (an input to topic choice — no finish date needed yet), and **as the finish date comes into view** (late Phase 3 / Phase 4) it locks the deadline-feasible target while upcoming deadlines are still catchable. Publication fees it surfaces come back here as a `publication` cost line.

**Budget-forcing terminal rule.** As the variable-spend cap (or a hard venue deadline) is neared, do **not** stall or silently truncate — force the **best committable draft** from what exists: take the null-result branch if the results don't support the headline claim, descope the ablation matrix with the descope logged, and hand the user a ranked "submit-now vs extend-budget" choice. Running out of budget mid-run with nothing submittable is the failure to avoid.

## Keeping the rate-card honest

Experiment LLM cost is only as good as `cost.json.rate_card` — and the rate-card now prices **`runs/usage.jsonl`** (the experiment harness's per-call usage), not the coding transcript. It is dated (`as_of`); when pricing might have changed or a model appears as `unpriced`, refresh it from the provider's current official pricing documentation — do not fill prices from memory. Enter local-compute, data-provider, and metered coding-agent bills as dated `actuals` rows; configure flat coding plans under `coding_agent`. No transcript can determine the user's billing contract. **Prefer the provider's billed cost per call** (ask the API to include it in `usage`) over rate-card × tokens, keep both in the row, and **reconcile the ledger total against the provider's own usage figure for the key at every batch gate** — the key's figure, not an account-wide total that mixes other projects' keys. A catalogue price that doubled between verification and the run went unnoticed until a reconciliation was demanded; a gap is closed with a dated, labelled adjustment row that explains itself, never by re-pricing history in place.

## Cross-references

- **research-paper** — the orchestrator; runs this on plan updates and phase transitions, and enforces the budget gate.
- **research-experiments** — supplies the pre-flight smoke-test measurements that turn a budget guess into an estimate.
- **research-repo-hygiene** — defines the `docs/plans/` plan-backup trigger this skill rides on.
- **research-venue-selection** — consumes the estimated finishing date; records the chosen venue's fee as a `publication` cost line.
- **research-mock-review / research-reflection** — their CLI panel billing is detected per plan and recorded as subscription-covered or metered coding overhead.
- **Provider official pricing documentation** — authoritative source for each dated rate-card entry; record the source URL and verification date.
