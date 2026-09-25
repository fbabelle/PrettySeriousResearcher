---
name: research-mock-review
description: Pre-submission gate — an adversarial multi-model panel of referees AND desk-triage editors scores the draft on the target venue's rubric vs a numeric bar and returns ranked weaknesses + drafted rebuttals. Never auto-decides accept/reject. Use before submitting, and always after a desk reject.
---

# Research mock-review — the pre-submission reviewer gate

Simulate the review the paper is about to face, so the agent surfaces the weaknesses a real reviewer would raise **before** submission — and hands the user a ranked, pre-critiqued decision instead of an open-ended "please review this." This is the single biggest lever for reducing the user's review burden: the diagnosis is done *for* them; they confirm and choose.

## The autonomy inversion (read first)

The strong autonomous-science systems (AI-Scientist's ensemble reviewer, Agent Laboratory's reviewer, Zochi, Agents4Science's LLM panel, ScientistTwo's review-rebuttal loop and meta-reviewer) prove the machinery works — but most of them **auto-decide accept/reject**. We **invert that**: the panel **scores, ranks, and drafts**; the **user stays the chooser**. This skill never emits an accept/reject verdict, never gates submission by itself, and never edits the paper — it produces a packet the user acts on. Auto-deciding is the opposite of the design philosophy.

## When it fires

- **Phase-4 exit (primary):** a full pass on the finished draft, as part of the exit criteria.
- **Phase-1 dry-run (lightweight):** a single-reviewer pass on the skeleton to **fix the target bar** early — what score must this venue's rubric reach, and which dimensions matter most — so every later phase optimizes toward it. Uses the venue profile from `research-venue-selection`.
- **Run `research-writing`'s machine-writing-tell scan (`scripts/ai_style_scan.py`) before the panel**, and de-style if any FIX band is exceeded, so referees and editor personas react to the science rather than to the style; note the before/after densities in the packet.
- **On request / before any resubmission — and mandatorily after a desk reject.** A desk reject (rejected without external review) returns **no feedback at all**; two in a row, with not one referee comment between them, means the paper has never actually been reviewed (earned 2026-09). This panel is then the only source of review signal, and the *editor* pass below is the part that matters, because the paper is dying at triage, not in review.

## The panel: driven via coding-agent CLIs, not API keys

The panel is realized by **driving installed coding-agent CLIs/SDKs as subprocess reviewers** — e.g. `claude -p "<review prompt>"`, `codex exec "<review prompt>"`, `gemini -p "<review prompt>"` — each producing an independent review captured from stdout. This is deliberate:

- **No API keys, no secrets.** Each CLI owns its own auth; this skill never asks for, stores, or logs a key (keeps the `install_skills.py` secrets-lint clean and the set portable).
- **Detect billing before launch.** A CLI may be subscription-covered, credit-limited, metered, or API-backed. Confirm the basis for every panel member; book subscription-covered use to its plan and explicit metered charges as coding-agent actuals. Keep panel runtime separate from experiment spend.
- **Reviewer family != writer family.** Assign each review to a **different family than the one that wrote the draft** to kill the known self-preference / sycophancy bias. Detect which CLIs are on PATH; use the diverse set.
- **Check the quota before launch, and have the fallback ready.** A subscription CLI can be exhausted for the day (codex: "You've hit your usage limit ... try again at <time>", after a heavy audit day), and the review then fails in seconds with an empty output file; test with a one-line call first, record the reset time, and if the cross-family reviewer is out run the same-family personas now (fresh-context subagents, discounted as below) and schedule the cross-family pass for the reset time rather than waiting a day (earned 2026-09-18).
- **A same-family panel is a rehearsal, never the gate.** On the same draft the cross-family panel scored one point lower on the evidence criterion and raised three defects the same-family panel had not seen (a proposer that holds information about the future breaks the guarantee's hypothesis; one term naming two different objects; a ladder that is a package comparison, not an ablation). Fix what the same-family panel finds, then run the cross-family pass and expect a second round of fixes before calling the packet done (earned 2026-09-19).
- **Graceful degradation.** If only one family is available, run multiple **personas/roles at varied temperature** instead — but then treat agreement with suspicion and **discount** the panel's confidence (a same-family panel is an echo chamber, not independent evidence).
- **Hold one reviewer out of the revision loop.** A reviewer whose critiques steer the revisions stops being an evaluator: the draft is optimized against it. ScientistTwo (arXiv:2609.19644, Table 5) revised against one AI reviewer for two rounds, and that reviewer's acceptance rate rose 46.9 % → 79.6 % → 93.9 %, while a held-out reviewer never used for revision went 49.0 % → 73.5 % → 69.4 % — the second round bought score on the in-loop reviewer and lost it on the held-out one. Before the first revision round, designate one panel member (preferably another family, fresh context, same rubric) as **held-out**: its reviews are never shown to the writer, and only its score is reported as distance-to-bar after a revision. Stop revising when the held-out score stops rising, even if the in-loop reviewers still have complaints; a real referee is a held-out reviewer.

## Two kinds of panel member: referees and editors

Referees and editors fail a paper for different reasons, and the second is far more common for long benchmark papers from unaffiliated authors. Every journal run therefore includes both:

- **Referees** (full read, ~1,000–1,600 words each): score the venue rubric, rank weaknesses pinned to §/Table/Figure, ask questions, and state what would move the recommendation up one level. Journal scale: Reject / Major revision / Minor revision / Accept.
- **Desk-triage editors** (one per candidate venue, 15-minute persona): decide **send to review vs reject without review**, give a probability that a typical handling editor would send it out, the three decisive reasons, a first-impression checklist (title states a result? main finding within three abstract sentences? contributions on page 1? length vs the journal's median? reads as finance / AI-systems / benchmark / software paper — and does that match the venue?; does the prose carry machine-writing tells — spaced em dashes in most paragraphs, semicolon chains, arrows in sentences, "delve/underscores/notably" — that make it look generated and unreviewed?), the changes that would flip the decision, and cover-letter advice. A paper can score "Major revision" with every referee and still never reach them.

**Multi-venue mode.** When the fallback chain is undecided, run the editor persona once per candidate venue on the *same* draft: the resulting triage-survival probabilities become a column in the `research-venue-selection` plan, so venue priority is set by evidence rather than by rank alone.

**Runner.** `.claude/skills/research-mock-review/scripts/mock_review_panel.py` (shipped with this skill) drives the panel. The project describes its candidate venues and panel members in a JSON config (`--dump-config` writes the generic default to start from; members = referee × venue + editor × venue, each on a named CLI); `codex exec --ephemeral -s read-only -o <file>` gets the manuscript on stdin, and `claude -p` (optionally `--claude-model <pinned>`) is the second family. Reviews land in `docs/review/mock_<date>/<member>.md` under the working directory unless `--outdir` says otherwise; the packet aggregates them. Gotchas: **a multi-paragraph argv prompt reaches Codex truncated at its first blank line** (found 2026-09-17: the personas' rubric and output-format paragraphs never arrived; the runner now stages the brief inside stdin ahead of the manuscript and passes a one-line pointer as the argv prompt; verify in the `.log` that the `user` block carries the whole brief); an old `claude` CLI rejects the 1M-context model it auto-selects for a long stdin (only `claude update` fixes it — a pinned `--model` is not enough); on Windows resolve the npm shim with `shutil.which`; Codex at xhigh effort ignores a 1–5 score template and writes editorial prose, so read the stated recommendation and the ranked concerns rather than expecting a score table; Codex members web-check cited papers and model cards — treat those findings as leads and re-verify each against the primary source before acting.

## The protocol

1. **Load the venue rubric.** From the `research-venue-selection` venue profile: the review dimensions, the numeric scale, the acceptance bar, and which dimensions are decisive for this venue. For journals, the realistic first-submission bar is **"Major revision" from the referees *and* ≥60% send-to-review from the editor persona**; below the second, fix the first page before touching the science.
2. **Run the panel.** Each reviewer scores every rubric sub-dimension **grounded in the venue rubric and in retrieved prior work** (not vibes), plus an overall score on the venue's scale, and writes free-text strengths/weaknesses like a real review.
3. **Aggregate to a *relative* signal — never an oracle.** Report **distance-to-bar** and the **cross-reviewer disagreement spread**, not an absolute "it will be accepted." Do **not** claim a calibrated go/no-go: with n=1 paper there is no human-agreement ceiling to calibrate against (the published calibration numbers came from scoring *pools* of papers vs labeled human reviews — not available here). The honest output is "here is where the panel lands relative to the bar, and here is where reviewers disagree."
4. **Cross-reviewer disagreement = escalate to the user.** A dimension where the (genuinely diverse) panel splits is exactly the judgment to hand up, flagged, rather than average away.
5. **Ranked weaknesses.** Order by severity × likelihood-a-reviewer-raises-it. Rank **triage killers** (what the editor persona said would cause a desk reject) above referee weaknesses — they are cheaper to fix and are what actually ends submissions. Tag each **fixable-now** (do it before submission) vs **preempt-in-Limitations** (name it honestly in the paper to defuse it). **Pin every weakness to evidence** — the exact section/table/figure/claims-ledger row (or run id) it concerns — so the fix is mechanical, not a re-hunt through the draft.
6. **Drafted rebuttal per weakness — and name what would answer it.** A concrete response the user can adopt or edit — so rebuttal prep is done before the reviews even land. Tag each weakness with the cheapest thing that actually answers it: **text** (a clarifying edit), **existing evidence** (a pointer to a table, appendix or claims-ledger row), **new experiment**, or **limitation** (concede it). For every *new experiment* weakness, draft the experiment rather than a promise: the cells, the protocol it reuses, the estimated cost and wall-clock (`research-experiments` throttle math), and whether it fits the remaining budget — the user picks which to run, and they then go through the budget gate like any other run. An evidence weakness answered with prose is the weak answer: ScientistTwo's rebuttal agent answered critiques by running supplementary experiments, and its first such round raised even the held-out reviewer's acceptance from 49.0 % to 73.5 % (arXiv:2609.19644, Table 5). Result: the packet lists the experiments worth running before submission, not only the arguments.
7. **Hypothesis-closure check.** Verify every Phase-1 research question/hypothesis is actually answered (confirmed/refuted) in the draft and that each abstract claim maps to a reported result. An unclosed claim is a top reviewer kill.

## The one pre-submission packet

Bundle into a single artifact under `docs/review/` so the user reviews **one** surface, not four:

- the panel's score-vs-bar + disagreement map,
- the ranked weaknesses + drafted rebuttals + hypothesis-closure table,
- the **`research-references`** citation audit (clean/UNVERIFIABLE),
- the **`research-visuals`** figure audit,
- the **`research-provenance`** results reconciliation (every number resolves) and its **integrity audit** (headline tables re-executed from a clean checkout, specification compliance, method-code alignment).

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
- **research-submission** — on the user's "submit", takes the packet forward; the drafted rebuttals become its response bank when real reviews arrive. On a **desk reject** it routes back here (editor pass) because there are no reviews to fold.
