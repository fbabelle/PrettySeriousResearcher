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

## Two extra checks when the code is LLM-heavy

- **Math ↔ code fidelity.** If the method has equations (from `research-algo-design`), verify the implementation actually matches them — each equation/quantity maps to the code that computes it, and no silent divergence. A method that's written up as one thing and coded as another is an anti-hallucination failure, not just a bug.
- **LLM-as-judge calibration.** If the code builds a *grader/scorer* (an LLM judging outputs, a backtest scorer, an eval rubric), it cannot be trusted uncalibrated. Validate it against a held-out human/ground-truth baseline and report its agreement **relative to a human–human (or ground-truth) ceiling** before any result leans on it. Flag honestly when no such baseline exists (common for a single paper) — then the judge is a *signal*, not a *verdict*, and downstream claims must say so.

## Test discipline (ships with the gate)

- **Tests ship with the code.** New code and core designs come with unit/regression tests in `tests/`; they are tracked and committed (per the user's working agreement).
- **Tests pass after major changes.** After any significant change, run the suite; it must be green before the step is considered done. Report failures with the actual output — never claim green you didn't see.
- **Research-specific tests worth having:** a leakage check (assert no future information in features), determinism (same seed → same result), a metric sanity test (known input → known metric), and a small end-to-end smoke of the experiment harness.

## Delegate the mechanical pass

For line-level bug-finding (off-by-one, null/None, resource leaks, error handling, edge cases), invoke the built-in **`/code-review`** skill on the diff and fold its findings in. Reserve this skill's prose for the four judgment questions and the validity/test concerns `/code-review` doesn't cover.

## Output

A short verdict: the four points, the test status (ran / passed / failures), the mechanical findings (from `/code-review`), and a clear **ship / fix-first** call. If fixing first, list the must-fix items distinct from the nice-to-haves.

## Cross-references

- **research-algo-design / research-experiments** — invoke this after writing method or harness/run code.
- **/code-review** (built-in) — delegated mechanical bug-finding on the diff.
- **research-reflection** — shares the anti-tilt principle: don't force findings; "already good" is a valid result.
- **research-repo-hygiene** — the commit/test conventions this gate enforces.
