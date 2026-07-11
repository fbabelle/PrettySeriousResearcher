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
- **Before submission** — a fresh adversarial read of the whole argument.

The orchestrator opens it with a **targeted question**, e.g. *"While the experiments run, want me to revisit and pressure-test the algorithm design and confirm it's still the optimal approach?"* Act only once the user confirms the scope.

## The protocol

1. **Draft a revision plan.** State exactly what's being re-examined (topic / design / implementation / a specific module) and the criteria for "better." Keep it scoped — one target per pass.
2. **Broad adversarial search — via a diverse panel.** Use the host agent's current web-search and page-fetch tools to look *outward*: has the field moved? Is there a stronger baseline, a known failure mode of this approach, a simpler method that would do as well, a critique of the assumptions? Search to *challenge* the current choice, not to confirm it. When more than one coding-agent CLI is available (`claude`, `codex`, `gemini`), run the challenge as a **multi-family panel** — the same CLI-driven, reviewer-≠-author mechanism as `research-mock-review`; first determine whether each CLI invocation is subscription-covered or metered and log it accordingly — so the critique isn't a single model agreeing with itself. **Cross-family disagreement is itself the signal to escalate to the user**, not to average away.
3. **Apply the AI-critic reliability map.** Auto-resolve the checks the agent is *reliable* at (internal consistency, number/citation grounding, assumption decomposition, obvious failure modes) and only **escalate to the user the judgments AI is provably weak at** — novelty, significance, "is this worth doing." This is what keeps reflection from either rubber-stamping or dumping raw doubt on the user.
4. **Compare honestly.** Put the current approach against the strongest alternative the search surfaced, on the criteria from step 1 (effectiveness, cost, risk, novelty, validity). Show the comparison, not a conclusion-first rationalization.
5. **Decide and recommend.**
   - **Optimization found** → propose the concrete change, its expected benefit, its cost (including the rework and effort/budget hit via `research-tracking`), and a recommendation. Get the user's go before large rework.
   - **Already optimal** → say so plainly, with the evidence that the alternatives are weaker or not worth the switch. This is a successful reflection, not a failed one.
6. **Record it — including what was rejected.** Note the reflection and its outcome in `docs/changelogs.md` (and back the plan to `docs/plans/` if it leads to rework) so the decision trail is auditable. **Carry a rejected-approach memory forward** (the topics/designs/venues already killed and why) so later passes don't re-propose an idea that was already ruled out — churn the anti-tilt principle is meant to prevent.

## Scope discipline

Reflect on **one** target per invocation. A reflection that tries to re-litigate the whole paper at once produces noise; a scoped pass produces a decision. If multiple things deserve review, queue them and run separate passes. The multi-family panel and reliability map above are *how a single scoped pass searches* — **not** a license to run a standing battery before every decision (that would add exactly the review burden the design avoids).

## Cross-references

- **research-paper** — orchestrator; fires this at boundaries / cadence and on solvability-gate failure.
- **Host web-search/page-fetch tools** — current outward evidence for the adversarial search in step 2.
- **research-mock-review** — shares the CLI-driven multi-family panel mechanism; that skill is the venue-calibrated draft review, this is the broader "is this the right work?" self-check.
- **research-tracking** — costs any proposed rework so the recommendation includes the effort/budget impact.
- **research-venue-selection** — among the things worth re-evaluating (is the target venue still the best fit × rank × timing?), especially if the timeline slips.
- **research-code-review** — shares the anti-tilt principle for code-level judgment.
