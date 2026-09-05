---
name: research-reflection
description: Periodic self-check — pressure-test the topic, design, or implementation against alternatives via adversarial search, then propose an optimization or conclude it's optimal. Use at phase boundaries, ~every 15 active hrs, or before submission.
---

# Research self-reflection

A guardrailed protocol for periodically challenging the work, so the paper doesn't lock in an early-but-suboptimal decision. It is **invoked, not automatic** — the orchestrator offers it; this skill runs once the user confirms (or when the algo-design solvability gate fails and a reframe is forced).

## The anti-tilt principle (read first)

The goal is a *correct* answer about whether to change course — **not** to manufacture changes. It is fully legitimate, and often the right outcome, to conclude **"the current approach is already optimal; no change."** Do not force constructiveness; reflexive change-for-its-own-sake introduces tilted behavior and churn. Reflect honestly, recommend honestly.

## When it fires

- At each **phase boundary** (a natural checkpoint).
- Roughly every **~15 agent-active hours** within a long phase.
- **On a surprising event, not only on cadence** — a strong prior-art hit that threatens novelty, a competitor that appears dead/alive, a failed or too-good-to-be-true result. These are the moments a scoped reflection pays off most.
- On an **algo-design solvability-gate failure** (revisit the framing/topic before spending the experiments budget).
- **At the end of each run batch (a stage)**, as a *path re-evaluation* against the pre-registered hypotheses: an inventory of every run with its artefact pointer and one-line verdict; a reading per hypothesis (supported / bounded / pending); a settings table that says what each interval and level means; the loopholes and analysis gaps found; and a re-ordered path that runs the cheapest framing-deciding experiment before the most expensive block. Written for the owner in the project's teaching register (every number pointed to its artefact and to where it was derived), filed under `docs/reflections/`, and mirrored in a claims ledger so writing never starts from memory.
- **Before submission** — a fresh adversarial read of the whole argument.

The orchestrator opens it with a **targeted question**, e.g. *"While the experiments run, want me to revisit and pressure-test the algorithm design and confirm it's still the optimal approach?"* Act only once the user confirms the scope.

## The protocol

1. **Draft a revision plan.** State exactly what's being re-examined (topic / design / implementation / a specific module) and the criteria for "better." Keep it scoped — one target per pass.
2. **Broad adversarial search — via a diverse panel.** Use the host agent's current web-search and page-fetch tools to look *outward*: has the field moved? Is there a stronger baseline, a known failure mode of this approach, a simpler method that would do as well, a critique of the assumptions? Search to *challenge* the current choice, not to confirm it. When more than one coding-agent CLI is available (`claude`, `codex`, `gemini`), run the challenge as a **multi-family panel** — the same CLI-driven, reviewer-≠-author mechanism as `research-mock-review`; first determine whether each CLI invocation is subscription-covered or metered and log it accordingly — so the critique isn't a single model agreeing with itself. **Cross-family disagreement is itself the signal to escalate to the user**, not to average away. **Cross-family CONVERGENCE is equally informative in the other direction**: when independent model families propose the *same* alternative unprompted, treat that as the strongest available change signal.
   - *CLI practicalities (Windows-earned):* pass long prompts via **stdin** (`Get-Content -Raw file | codex exec -`) — npm `.ps1` shims re-split multi-line arguments; a CLI whose default model returns "requires a newer version" needs a CLI upgrade, and explicit `-m` model picks can be rejected per account type. Verify each panel member actually completed — a member that dies mid-run (session limits) silently shrinks the panel.
   - *Dated re-audit, by lane.* A prior-art scan has a freeze date and a shelf life of weeks in a hot lane. At every later design gate — and before any flagship claim is committed — re-audit **"since <freeze date>"**, split across parallel probes by lane (domain lane / method lane / theory lane / evaluation+venue lane), each scoring every hit **0–3 against the paper's *named* claims**, and maintain a **claim-status table** (open / contested / absorbed). "First X" claims are the most perishable — expect them to die first and prefer conjunctive, narrowed wording that survives a single scooping paper.
   - *Label vs plan.* When the families disagree only on **framing/label** while converging on the experiment plan, escalate just the label — with an **option-value argument** (which framing can be downgraded later at zero waste, which must be designed in from the start). If the user delegates the call, decide once, with **falsifiable fallback conditions** written into the verdict — not a re-survey.
3. **Apply the AI-critic reliability map.** Auto-resolve the checks the agent is *reliable* at (internal consistency, number/citation grounding, assumption decomposition, obvious failure modes) and only **escalate to the user the judgments AI is provably weak at** — novelty, significance, "is this worth doing." This is what keeps reflection from either rubber-stamping or dumping raw doubt on the user. **Panel output is evidence to verify, not a verdict:** before acting, run an author verification pass on every decision-critical claim — internal facts against the repo's own artifacts (run results, derivations: a panel can surface a violation the spike verdict never wrote down), external references by fetching the primary page — and record it as a verification table in the verdict.
4. **Compare honestly.** Put the current approach against the strongest alternative the search surfaced, on the criteria from step 1 (effectiveness, cost, risk, novelty, validity). Show the comparison, not a conclusion-first rationalization.
5. **Decide and recommend.**
   - **Optimization found** → propose the concrete change, its expected benefit, its cost (including the rework and effort/budget hit via `research-tracking`), and a recommendation. Get the user's go before large rework. **Label every proposed change with its driver** (venue-mechanics / statistical-validity / competitiveness / data-feasibility) — users legitimately ask "is this forced by the venue or by the analysis?", and an attribution table answers it before it's asked.
   - **Already optimal** → say so plainly, with the evidence that the alternatives are weaker or not worth the switch. This is a successful reflection, not a failed one.
6. **Record it — including what was rejected.** Note the reflection and its outcome in `docs/changelogs.md` (and back the plan to `docs/plans/` if it leads to rework) so the decision trail is auditable. **Reversals are recorded, never overwritten:** when a later spike or run contradicts one of the reflection's recommendations, annotate the original change row as "reversed by evidence" with the run pointer and leave the original text struck through — those rows are the audit trail's most valuable entries, and the same recommendation must not resurface in a later pass. **Carry a rejected-approach memory forward** (the topics/designs/venues already killed and why) so later passes don't re-propose an idea that was already ruled out — churn the anti-tilt principle is meant to prevent.

## When a result looks odd (to you or the user)

Re-investigate with **instruments that fail differently**, not with more repetitions of the same method: a manipulation check that the treatment is live, a harder yardstick that can bend, and a truth-free second opinion (e.g. a blind pairwise judge from another model family). Then report where the methods agree and disagree and what each one *cannot* see. Agreement across instruments is what turns a suspicious conclusion into a finding; disagreement names the next experiment. Earned: an effort study that looked "too flat" survived a ladder and a blind judge and sharpened into a model-specific statement instead of being re-run with more seeds.

## Scope discipline

Reflect on **one** target per invocation. A reflection that tries to re-litigate the whole paper at once produces noise; a scoped pass produces a decision. If multiple things deserve review, queue them and run separate passes. The multi-family panel and reliability map above are *how a single scoped pass searches* — **not** a license to run a standing battery before every decision (that would add exactly the review burden the design avoids).

## Cross-references

- **research-paper** — orchestrator; fires this at boundaries / cadence and on solvability-gate failure.
- **Host web-search/page-fetch tools** — current outward evidence for the adversarial search in step 2.
- **research-mock-review** — shares the CLI-driven multi-family panel mechanism; that skill is the venue-calibrated draft review, this is the broader "is this the right work?" self-check.
- **research-tracking** — costs any proposed rework so the recommendation includes the effort/budget impact.
- **research-venue-selection** — among the things worth re-evaluating (is the target venue still the best fit × rank × timing?), especially if the timeline slips.
- **research-code-review** — shares the anti-tilt principle for code-level judgment.
