---
name: research-paper
description: Orchestrate an AI/Finance research paper end-to-end across four phases (topic, design, experiments, writing) with session clock, budget gate, and reflection checkpoints. Use to start or resume 'the paper', or ask 'where are we / what's next'.
---

# Research-paper orchestrator

This is the entry point and state machine for building a research paper. It is deliberately thin: it figures out **where we are**, opens the **session clock**, routes to the right **phase craft skill**, enforces a few **hard-stop gates**, and reports **effort + cost**. The actual work lives in the phase and cross-cutting skills it invokes.

Optional run focus: `$ARGUMENTS` (e.g. a phase name, a topic, or "resume").

## Lifecycle (effort weights are planning targets, not quotas)

| Phase | Skill | Weight |
|---|---|---|
| 1. Topic selection + skeleton | `research-topic-selection` | 30% |
| 2. Algorithm / solution design + impl | `research-algo-design` | 20% |
| 3. Experiments + ablations | `research-experiments` | 30% |
| 4. Writing (sections, figures, refs, appendix) | `research-writing` | 20% |

Total effort budget ≈ 120 **agent-active hours**, where "hours" means the **user's interaction time with the coding agent** — framing options, confirming at gates, steering — **not** human research labor and **not** the agent's autonomous background runtime (that's a separate wall-clock line). Because the research and writing are automated, the calendar cycle collapses; what this budget tracks is *time-in-the-loop*. See `research-tracking` for how the two clocks are measured and kept apart.

After Phase 4, the **submission tail** (`research-submission`: execute the submission, rebuttals, revise-and-resubmit, camera-ready, release) runs outside the four-phase effort split — it is **calendar-gated by the venue**, not effort-gated, and every outward-facing step in it is user-confirmed.

## On every engagement (do this first)

1. **First run?** If `docs/tracking/state.json` has a null first `phase_windows[].start` and the repo lacks the scaffold (`docs/`, `README.md`, `architecture.md`, `.gitignore`, `memory.md`), bootstrap it — create the layout described in `research-repo-hygiene` and set the first window's `start` to now. Then begin Phase 1.
2. **Open the session clock.** Set/refresh `docs/tracking/.session` (`start`, `last_heartbeat`, `phase`). The authoritative time/token accounting is derived from transcripts by `research-tracking`; `.session` just marks the open session.
3. **Read state.** `current_phase` and the gate flags from `state.json` tell you where we are and what's allowed next. If `docs/HANDOFF.md` exists, read it **before** `architecture.md`: it is the rolling handoff (in-flight runs, decisions only the user can make, next steps, environment pitfalls), rewritten at every milestone and before any context reset — a compaction summary is not a substitute (earned: a mid-battery context reset resumed cleanly from it). Before repeating any "pending user action" from the handoff, **re-run its acceptance test** (a credential probe, a tier check, a file's existence) — the user may have done it since; a stale pending item asked twice costs trust (earned: a data-vendor top-up listed as pending had been completed days earlier).
4. **Recall user patterns.** Read root `memory.md` (untracked) for the user's working habits; apply them unless they contradict a project skill (skills win on methodology; memory wins on the user's explicit stated choices — see `research-repo-hygiene`).
5. **Report status.** Run `research-tracking` and surface the compact effort+cost line, then state the current phase and the immediate next step.

**Background research agents (resilience discipline).** Long-running research subagents must be told, in their initial prompt, that **their final message IS the deliverable — never defer, never promise a later synthesis**; an agent that ends with "I'll compile the results next" has produced nothing. Agents can also die mid-flight (session limits, stalls): on a failure notification, resume the *same* agent with an explicit finish-and-deliver instruction rather than respawning (its context survives), and verify every parallel agent actually delivered before synthesizing — a silently missing member skews the synthesis. Per-agent web-search budgets are finite (on the order of a couple hundred calls): split a literature audit **by lane across parallel agents** rather than one giant sweep, require each to mark unverified facts (✱) and close with an explicit could-not-verify list, and have it write its report to a project file *as well as* returning it.

## Routing & auto-advance

Auto-advance through the phases — when a phase's exit criteria are met, close its window, append the next, update `current_phase`, and invoke the next phase skill — **except** at the hard-stop checkpoints below, where you stop and get the user. Everything else proceeds without asking.

**How a gate works — the ranked-options handshake (not a self-cleared checklist).** At every hard stop the agent does the diagnosis *first*, then hands the user a decision — never an open-ended "please review this." Each gate: (1) present a **ranked, pre-critiqued set of options** — the recommendation with its rationale, the runners-up with their tradeoffs; (2) **echo a one-line verification of what proceeding will spend** (metered budget / background runtime); (3) proceed only on explicit confirm. Use **two-tier triage** to keep this cheap in the user's time (the resource the effort clock tracks): the agent scores/ranks the *full* option set itself and escalates **only the shortlist + genuinely borderline / high cross-model-disagreement items**. A gate is a confirmation on an agent-produced artifact — never "go author a template, run a baseline, or hunt for problems yourself."

**Hard-stop checkpoints (always pause for the user):**

- **The two-direction disambiguation interview** (start of Phase 1). Owned by `research-topic-selection`: confirm domain, target problems, expected outcomes, improve-vs-challenge, new-system-vs-survey, and direction **(a)** algorithm-heavy/novel vs **(b)** experimental/analytical (survey, benchmark, variation). Do not pick the topic direction for the user. **Fire `research-venue-selection` early here** to emit a venue profile (rubric, acceptance bar, template, disclosure/anonymity, deadlines) that becomes an *input* to topic scoring — the topic is chosen partly for venue fit, not retrofitted to a venue later.
- **The topic slate** (end of Phase 1). Present the ranked, multi-angle candidate slate (`research-topic-selection`), let the user choose or inject their own, and confirm the resulting research-brief "north star" every later phase references.
- **The budget-finalization gate** (entry to Phase 3). Entry into `experiments` is **blocked** while `cost.json.status != "finalized"`. When Phase 2 completes (`gates.algo_design_complete: true`), invoke `research-tracking`'s budget playbook, present lean/balanced/aggressive scenarios, get a USD cap from the user, finalize, then proceed.
- **The pre-submission packet** (Phase-4 exit). Fire `research-mock-review`; present its one packet (score-vs-bar, ranked weaknesses + drafted rebuttals, bundled citation/visual/provenance audits) and the single submit-or-revise decision. Never auto-decide. On "submit", route to **`research-submission`** — its outward-facing steps (portal upload, arXiv post, rebuttal send, camera-ready) are each user-confirmed too.
- **Reflection confirmations** (see below). Propose; act only once confirmed.

**The null / negative-result branch.** A fully-automated pipeline that must *always* emit a positive paper is structurally pushed toward over-claiming — the very failure this gate discipline guards against. If a method does not beat its baselines, do **not** force a win: hand the user a ranked choice — (a) reframe as an analysis / limitation / negative-result paper (often a legitimate contribution), (b) retarget a venue that publishes such results, (c) loop back via `research-reflection` to revise the approach, or (d) stop. An honest null result reported well beats a fabricated positive one.

## Gates & exit criteria

- **Phase 1 → 2:** a confirmed topic+direction, a defensible novelty/gap claim (breadth **multi-angle** prior-art + competitive scan), an **early venue profile** consumed as a scoring input, a compressed **research-brief "north star,"** and a paper skeleton with research questions/hypotheses. Finance-leaning topics are tagged for `research-finance-rigor`.
- **Phase 2 → 3:** a chosen solution implemented with tests, candidate approaches identified for ablations, **and** the per-candidate **solvability gate** passed (at least one approach can plausibly solve the framed problem). On gate failure, do **not** advance — fire `research-reflection` to revisit the framing. Set `gates.algo_design_complete: true`, then run the **budget gate**.
- **Phase 3 → 4:** pre-flight smoke test passed (go/no-go recorded), the planned ablation matrix run (or its descoping logged), results captured, a first **`research-provenance` reconciliation** at results-capture (every headline number traces to a `runs/` artifact), and — for finance-leaning topics — the **`research-finance-rigor` statistical battery** passed (leakage-clean splits, multiple-testing correction, after-cost metrics). If the results are null/negative, take the **null-result branch** above rather than forcing a positive narrative.
- **Phase 4 → done:** the **main draft** (md + LaTeX + PDF, arXiv-grade render) complete with figures/tables, references, and appendix; **all figures/tables pass the `research-visuals` audit** (consistent fonts, vector, colourblind-safe, no baked-in chrome), **every citation has passed the `research-references` audit** (no unverifiable/hallucinated references), and **every reported number passes the `research-provenance` reconciliation** (all RESOLVED, no fabricated/placeholder values); the **`research-mock-review` pre-submission packet** produced, with its ranked weaknesses either fixed or preempted in Limitations and **hypothesis-closure** confirmed (every Phase-1 research question answered; abstract claims map to results); an **AI-involvement disclosure** appendix present; a **venue-targeted short version** if a target is selected; tests still passing; changelog and README/architecture current.

After any code is written in Phases 2–3, invoke `research-code-review` before considering that step done.

**Venue selection (runs twice — as an input, then on the deadline).** Fire **`research-venue-selection`** in **two modes**: (1) **early, in Phase 1**, to emit a *venue profile* (rubric, acceptance bar, template, disclosure/anonymity rules, deadline windows) that feeds topic scoring, the end-deliverable target, and the `research-mock-review` bar — venue-fit is an input to *what to work on*, not a late retrofit; and (2) **late, as the estimated finishing date comes into view** (`research-tracking`, typically late Phase 3 / entering Phase 4), to lock the deadline-feasible target while it's still catchable. The chosen venue drives the short version's requirements (`research-writing`) and its fee is recorded as a `publication` cost line. If the venue is double-blind or has a preprint policy, reconcile that against the arXiv-first default *early* (see `research-venue-selection`). Re-run if the timeline slips.

## Reflection cadence (periodic self-check)

At each phase boundary, and roughly every ~15 agent-active hours within a long phase, **offer** a self-reflection via a targeted question — e.g. *"While the experiments run, want me to revisit and pressure-test the algorithm design and confirm it's still the optimal approach?"* If the user confirms, hand off to `research-reflection`. It's legitimate to conclude the current approach is already optimal — do not force a change (avoid tilted, change-for-its-own-sake behavior).

## Committing & plan backups

Work is committed by **feature**, not by hours. When the user changes subject, that's the cue to commit the previous chunk (see `research-repo-hygiene` for branch/push/PR rules and the no-co-author-footer convention). On any significant plan, back it up timestamped to `docs/plans/` and **re-run `research-tracking`** so the effort+cost line is reported with the update.

## Cross-references

- **research-topic-selection / research-algo-design / research-experiments / research-writing** — the four phase craft skills this routes to.
- **research-tracking** — effort+cost ledgers, the report line, and the budget-gate playbook.
- **research-code-review** — the design-judgment + test gate invoked after code in Phases 2–3.
- **research-references** — the anti-hallucination citation gate; required for the Phase-4 exit.
- **research-provenance** — the results-integrity gate; every reported number resolves to a `runs/` artifact. Required for the Phase-4 exit; first pass at results-capture.
- **research-finance-rigor** — fires for finance-leaning topics; enforces statistical honesty + data-licensing provenance across design/experiments/writing.
- **research-visuals** — builds + audits every figure/table; required for the Phase-4 exit.
- **research-mock-review** — the pre-submission reviewer-panel gate (Phase-4 exit + a Phase-1 bar-setting dry-run); bundles the citation/visual/provenance audits into one packet.
- **research-submission** — the post-packet tail: executes the submission, then rebuttals / revise-and-resubmit / camera-ready / release; calendar-gated, every outward step user-confirmed.
- **research-venue-selection** — runs twice: early (Phase 1) as a venue-profile *input*, and late (Phase 3/4) to lock the deadline-feasible target the short version is built for.
- **research-reflection** — the self-check protocol fired at boundaries / on the solvability-gate failure; shares the multi-CLI adversarial-panel mechanism with `research-mock-review`.
- **research-repo-hygiene** — scaffold layout, commit/push/PR rules, draft rotation, `memory.md` policy.
