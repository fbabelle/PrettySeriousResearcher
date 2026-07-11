---
name: research-mock-review
description: Pre-submission gate — an adversarial multi-model reviewer panel scores the draft on the target venue's rubric vs a numeric bar and returns ranked weaknesses + drafted rebuttals. Never auto-decides accept/reject. Use before submitting.
---

# Research mock-review — the pre-submission reviewer gate

Simulate the review the paper is about to face, so the agent surfaces the weaknesses a real reviewer would raise **before** submission — and hands the user a ranked, pre-critiqued decision instead of an open-ended "please review this." This is the single biggest lever for reducing the user's review burden: the diagnosis is done *for* them; they confirm and choose.

## The autonomy inversion (read first)

The strong autonomous-science systems (AI-Scientist's ensemble reviewer, Agent Laboratory's reviewer, Zochi, Agents4Science's LLM panel) prove the machinery works — but most of them **auto-decide accept/reject**. We **invert that**: the panel **scores, ranks, and drafts**; the **user stays the chooser**. This skill never emits an accept/reject verdict, never gates submission by itself, and never edits the paper — it produces a packet the user acts on. Auto-deciding is the opposite of the design philosophy.

## When it fires

- **Phase-4 exit (primary):** a full pass on the finished draft, as part of the exit criteria.
- **Phase-1 dry-run (lightweight):** a single-reviewer pass on the skeleton to **fix the target bar** early — what score must this venue's rubric reach, and which dimensions matter most — so every later phase optimizes toward it. Uses the venue profile from `research-venue-selection`.
- **On request / before any resubmission.**

## The panel: driven via coding-agent CLIs, not API keys

The panel is realized by **driving installed coding-agent CLIs/SDKs as subprocess reviewers** — e.g. `claude -p "<review prompt>"`, `codex exec "<review prompt>"`, `gemini -p "<review prompt>"` — each producing an independent review captured from stdout. This is deliberate:

- **No API keys, no secrets.** Each CLI owns its own auth; this skill never asks for, stores, or logs a key (keeps the `install_skills.py` secrets-lint clean and the set portable).
- **Detect billing before launch.** A CLI may be subscription-covered, credit-limited, metered, or API-backed. Confirm the basis for every panel member; book subscription-covered use to its plan and explicit metered charges as coding-agent actuals. Keep panel runtime separate from experiment spend.
- **Reviewer family != writer family.** Assign each review to a **different family than the one that wrote the draft** to kill the known self-preference / sycophancy bias. Detect which CLIs are on PATH; use the diverse set.
- **Graceful degradation.** If only one family is available, run multiple **personas/roles at varied temperature** instead — but then treat agreement with suspicion and **discount** the panel's confidence (a same-family panel is an echo chamber, not independent evidence).

## The protocol

1. **Load the venue rubric.** From the `research-venue-selection` venue profile: the review dimensions, the numeric scale, the acceptance bar, and which dimensions are decisive for this venue.
2. **Run the panel.** Each reviewer scores every rubric sub-dimension **grounded in the venue rubric and in retrieved prior work** (not vibes), plus an overall score on the venue's scale, and writes free-text strengths/weaknesses like a real review.
3. **Aggregate to a *relative* signal — never an oracle.** Report **distance-to-bar** and the **cross-reviewer disagreement spread**, not an absolute "it will be accepted." Do **not** claim a calibrated go/no-go: with n=1 paper there is no human-agreement ceiling to calibrate against (the published calibration numbers came from scoring *pools* of papers vs labeled human reviews — not available here). The honest output is "here is where the panel lands relative to the bar, and here is where reviewers disagree."
4. **Cross-reviewer disagreement = escalate to the user.** A dimension where the (genuinely diverse) panel splits is exactly the judgment to hand up, flagged, rather than average away.
5. **Ranked weaknesses.** Order by severity × likelihood-a-reviewer-raises-it. Tag each **fixable-now** (do it before submission) vs **preempt-in-Limitations** (name it honestly in the paper to defuse it). **Pin every weakness to evidence** — the exact section/table/figure/claims-ledger row (or run id) it concerns — so the fix is mechanical, not a re-hunt through the draft.
6. **Drafted rebuttal per weakness.** A concrete response the user can adopt or edit — so rebuttal prep is done before the reviews even land.
7. **Hypothesis-closure check.** Verify every Phase-1 research question/hypothesis is actually answered (confirmed/refuted) in the draft and that each abstract claim maps to a reported result. An unclosed claim is a top reviewer kill.

## The one pre-submission packet

Bundle into a single artifact under `docs/review/` so the user reviews **one** surface, not four:

- the panel's score-vs-bar + disagreement map,
- the ranked weaknesses + drafted rebuttals + hypothesis-closure table,
- the **`research-references`** citation audit (clean/UNVERIFIABLE),
- the **`research-visuals`** figure audit,
- the **`research-provenance`** results reconciliation (every number resolves).

Then a 2–4 sentence recommendation and the **single decision** to make next. Only the actionable items (must-fix, unresolved, disagreements) surface — the user never re-derives them from the draft.

## Not a substitute for reflection

`research-reflection` is the broad adversarial self-check on topic/design/implementation with **no numeric venue bar**; this skill is the **venue-calibrated, draft-level** review gate. Keep both: reflection asks "is this the right work?"; mock-review asks "will this draft clear *this venue's* bar, and what will reviewers attack?"

## Cross-references

- **research-paper** — orchestrator; fires this at the Phase-4 exit (and the Phase-1 dry-run) and stops for the user on the packet.
- **research-venue-selection** — supplies the venue rubric + numeric bar this panel scores against.
- **research-references / research-visuals / research-provenance** — their audits are bundled into the one packet.
- **research-reflection** — the broader, non-venue-calibrated self-check; shares the anti-tilt principle and the multi-CLI panel mechanism.
- **research-tracking** — records panel runtime and the verified per-CLI billing basis; never assumes zero marginal cost.
- **research-writing** — consumes the ranked weaknesses + rebuttals to revise the draft.
- **research-submission** — on the user's "submit", takes the packet forward; the drafted rebuttals become its response bank when real reviews arrive.
