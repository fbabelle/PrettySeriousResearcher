---
name: research-code-review
description: Code-review gate for research code (Phases 2–3) — a 4-step design review (solves / pattern-fit / tradeoffs / validity) plus test discipline (tests ship and pass). Use after writing or changing an algorithm, harness, or run code, or on a PR.
---

# Research code-review gate

A correctness-and-judgment gate that runs **after any code is written or changed** in Phases 2–3, and when reviewing a PR. It has two halves: the **4-step design judgment** (this skill's core) and **test discipline**. Mechanical bug-hunting is delegated to the built-in `/code-review` skill so this one stays focused on judgment.

## The 4-step review (apply in order, every time)

1. **What is the change trying to solve?** State the goal in one sentence. If you can't, the change is unclear — stop and clarify before reviewing further. Tie it back to the research question or the experiment it serves.
2. **Conflict & pattern-fit.** Does it conflict with the existing design/decisions? Does it follow the surrounding code's patterns, naming, and conventions (match the repo's house style, not a new personal one)? Flag silent contradictions with earlier choices.
3. **Tradeoffs — benefit vs shortcoming.** What does it buy, and at what cost (complexity, speed, memory, coupling, statistical validity)? Is the tradeoff worth it for a research artifact, or is it premature optimization / over-engineering? Name the shortcoming explicitly even when recommending the change.
4. **Legibility & validity.** Is it readable and correct? For research code specifically: does it preserve **experimental validity** — no data leakage, correct train/val/test temporal split, fixed/recorded seeds, metrics computed as claimed, results reproducible from the committed code?

Write the review as those four points, not a vibe. It's legitimate to conclude "no change needed" — don't manufacture findings (see `research-reflection` on avoiding tilted, change-for-its-own-sake behavior).

## Extra checks for statistical machinery

- **Guarantee ≠ power.** Code implementing a statistical guarantee (error control, calibration, coverage) can be theoretically valid yet practically broken by a tuning choice — the guarantee still "holds" while the procedure alarms constantly or never. Verify **empirical behavior at realistic problem scale** (false-alarm rate, power/delay, on inputs matching real SNR), not just the math↔code map. A validity test suite should include an empirical check of the guarantee's *usefulness*, not only its *correctness*.
- **Guarantee ≠ usability for multi-stream / rank-threshold rules.** A multiplicity procedure (BH-style rank thresholds, family-wise combinations) can carry a correct bound and still be unusable when the per-stream statistic has a null *plateau* that sits above the lower-rank thresholds — an all-healthy library then gets declared en bloc while the (loose) bound is satisfied. Before adopting any combined rule, simulate it on an all-null population at realistic scale and pin the failure mode as a regression test if you reject it; the per-stream rule with a union bound is often the honest default.
- **Every null cell against its nominal bound.** A spike or validity verdict must tabulate each null-hypothesis condition (every dependence / noise / regime variant) against the guarantee's nominal level — not summarise "holds empirically." Any cell above the bound is a validity violation that becomes a **prioritized open ADR** before any downstream claim builds on the machinery; stored results routinely contain a violation the verdict prose never surfaced.

- **Test every statistical helper on a degenerate input.** A Holm routine that returns adjusted p-values was consumed as booleans and reported "10 of 10 contrasts significant" with p = 1.0 (earned 2026-09-05; caught before the number reached a document). Every report that calls a p-value / multiplicity / interval helper gets a test with all-zero differences (p = 1 must not reject) and one with a large effect (must reject); read the helper's return type before consuming it.

## Environment audit — review the ruler, not only the code that runs it

An agent evaluation environment can push the agent into the "wrong" answer by construction, and a result measured with such a ruler is not evidence about the agent. Before a powered run, and again whenever a result surprises, read the environment end to end (prompts, world generators, scoring economy, every arm's inputs) against this list: (1) **told vs shown** — everything the agent is told must be consistent with what it is shown (an "alarm" implies a visible break in the monitored quantity; an alarm block must report the quantity the alarm is on); (2) **rulebook vs held-out signature** — if the prompt's rules map a held-out condition's visible signature to the wrong label, that is either the intended difficulty (then say so) or a defect; (3) **dominance** — find the constant that dominates the score and give it a sensitivity row; (4) **information asymmetry across arms** — a baseline fed true outcomes or feedback the agent arms never get is an oracle-fed baseline and must be labelled; (5) **public vs instrument** — if the decisive numbers are visible to every arm, the instrument's value is interpretation, and the estimate is conservative; (6) contamination lint, common random numbers, cross-process determinism, sandbox well-formedness. Write the audit as a dated document; defects become labelled amendments (registered results stay the headline, the corrected ruler runs as a robustness check), properties become disclosures (earned: an alarm shown beside a healthy IC and a single constant worth seven of another explained a whole family-level 'failure', 2026-09-04).

## Two extra checks when the code is LLM-heavy

- **Math ↔ code fidelity.** If the method has equations (from `research-algo-design`), verify the implementation actually matches them — each equation/quantity maps to the code that computes it, and no silent divergence. A method that's written up as one thing and coded as another is an anti-hallucination failure, not just a bug.
- **Robustness fixes are experimental changes.** A stability fix that reduces a model's capability (disabling reasoning to cure empty output, shrinking context to avoid overflow, lowering temperature to tame parsing) silently changes the treatment: if the agent then loses to its baseline, the result is uninterpretable. Review every such fix as a design change — is the capability a *treatment* or a *nuisance* for this paper? — pin it per role, log it per call, and prefer budgeting the capability over removing it. Earned: reasoning was switched off to fix a runtime symptom and had to be reverted by the user.
- **LLM-as-judge calibration.** If the code builds a *grader/scorer* (an LLM judging outputs, a backtest scorer, an eval rubric), it cannot be trusted uncalibrated. Validate it against a held-out human/ground-truth baseline and report its agreement **relative to a human–human (or ground-truth) ceiling** before any result leans on it. Flag honestly when no such baseline exists (common for a single paper) — then the judge is a *signal*, not a *verdict*, and downstream claims must say so. Score definitions must also respect the contract's own semantics: if the prompt caps `confidence` at 0.5 on an abstain, a Brier score over abstentions punishes correct behaviour — exclude them (earned in the first effort sweep).

## Test discipline (ships with the gate)

- **Tests ship with the code.** New code and core designs come with unit/regression tests in `tests/`; they are tracked and committed (per the user's working agreement).
- **Tests pass after major changes.** After any significant change, run the suite; it must be green before the step is considered done. Report failures with the actual output — never claim green you didn't see.
- **Research-specific tests worth having:** a leakage check (assert no future information in features), determinism — **across processes with different hash seeds, compared on the whole decision/prompt sequence, not on end metrics** (set iteration order leaked into an agent's action order while the final metrics still matched; sort every iteration over a set that reaches a decision, a log, or a prompt), a metric sanity test (known input → known metric), and a small end-to-end smoke of the experiment harness.

## Delegate the mechanical pass

For line-level bug-finding (off-by-one, null/None, resource leaks, error handling, edge cases), invoke the built-in **`/code-review`** skill on the diff and fold its findings in. Reserve this skill's prose for the four judgment questions and the validity/test concerns `/code-review` doesn't cover. If no reviewable diff exists yet (pre-first-commit), do the mechanical pass inline file-by-file and note the deviation in the review record.

## Output

A short verdict: the four points, the test status (ran / passed / failures), the mechanical findings (from `/code-review`), and a clear **ship / fix-first** call. If fixing first, list the must-fix items distinct from the nice-to-haves.

## Cross-references

- **research-algo-design / research-experiments** — invoke this after writing method or harness/run code.
- **/code-review** (built-in) — delegated mechanical bug-finding on the diff.
- **research-reflection** — shares the anti-tilt principle: don't force findings; "already good" is a valid result.
- **research-repo-hygiene** — the commit/test conventions this gate enforces.
