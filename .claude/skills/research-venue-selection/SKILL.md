---
name: research-venue-selection
description: Find, rank, and time conferences/journals to submit to — by topic/domain fit, rank, deadline feasibility vs the estimated finish date, and prep/fees. Use when planning submission, picking a target venue, or as a finish date comes into view.
---

# Research venue selection

A paper isn't done in a vacuum — it's done *for a venue*, on that venue's deadline, in that venue's format. This skill finds **where to submit**: the conferences/journals that fit the work, ranked, ordered by deadline feasibility, with the prep and cost each one demands. It runs **twice** in the cycle: **early (Phase 1)** to emit a *venue profile* that shapes *what to work on*, and **late (Phase 3/4)** to lock the deadline-feasible target the short version is built for. Picking a target early lets the topic be chosen for venue fit and lets `research-writing` build the short version to the right requirements — not a one-off at the very end.

Use the host agent's current web-search and page-fetch tools for current venue research. **Deadlines, fees, and even venues change every cycle** — every date/fee is a claim to verify against the official current-year CFP, never recalled from memory (the recency discipline shared with `research-references`).

## When to run

- **Early, at Phase-1 start (venue-as-input mode).** Emit a **venue profile** — a shortlist of 2–4 candidate venues + their *shared* norms (rubric dimensions, acceptance bar, section/length template, disclosure/anonymity rules, deadline windows), partly derived by **mining the venues' recent accepted papers as exemplars**. `research-topic-selection` consumes this as a scored **venue-fit** angle, the end-deliverable rubric and the `research-mock-review` bar calibrate to it, and the skeleton is shaped by its norms. No finish date is needed yet — this run is about *fit and bar*, not deadline feasibility.
- **Late, triggered by the estimated finishing date** (from `research-tracking`): once the projected finish is far enough ahead that upcoming deadlines are still catchable — typically late Phase 3 / entering Phase 4 — **lock the deadline-feasible target**. Too late and you miss the cycle.
- **Re-run when the timeline shifts** (finish date slips, a deadline passes) or at phase boundaries — deadlines are time-sensitive, so a plan goes stale.
- **When the user asks** "where can we submit this?" / "what's the deadline?"

## arXiv-first vs double-blind (reconcile early)

The skill set's default is an **arXiv-first main draft** (`research-writing`). That can collide with a target venue that is **double-blind** or has a **preprint policy** — posting to arXiv first may break anonymity or violate dual-submission rules. Surface this conflict **in the early venue profile** as an explicit user decision (arXiv-now-and-pick-a-preprint-friendly-venue, vs hold-the-preprint-for-a-double-blind-target), so the early venue push doesn't silently undermine the arXiv-first writing default. Record the resolution in the venue profile.

## The four axes (score every candidate on these)

1. **Topic & domain fit.** Map the paper's *contribution type* to the venues that publish it: an AI **method** paper, a **benchmark/survey**, an **AI×finance** bridge, and an **empirical finance** study go to different places. A finance-leaning ML paper has *two* tracks (ML conferences **and** finance journals) — name both; they have very different norms, lengths, and timelines.
2. **Rank & prestige (use the field's standard, not vibes).** CS: **CORE** (A*/A/B), **CCF** (A/B/C), Google Scholar **h5-index**, acceptance rate. Finance/econ: **ABS/AJG** (4*/4/3), **FT50**, impact factor, the "top-3" (JF/JFE/RFS) convention. Always state the ranking *source and year*.
3. **Timeline, order & priority.** Order candidates by **submission deadline vs the estimated finishing date** and **review-period length**; set a **priority chain** — aim highest fit×rank first, with realistic fallbacks down the chain. A venue whose deadline can't be met this cycle isn't dropped — log it with its *next* cycle. Conferences are deadline-driven (miss it, wait a year); journals are rolling (submit anytime, longer reviews) — weigh accordingly.
4. **Preparation & cost.** Per candidate: **prerequisites** (page/column limit, template/`.cls`, anonymization for double-blind, artifact/ethics/reproducibility checklist, **the venue's LLM/AI-use policy** — disclosure requirements and what AI authorship it permits, now a per-venue variable — dual-submission/preprint policy vs an arXiv post), **fees** (submission fee / APC — **record into cost tracking**), **review-period length** (to project the decision date), and **both deadlines** (soft = abstract/registration, hard = full paper).

See [references/venue-landscape.md](references/venue-landscape.md) for the ranking systems, the AI / finance / AI×finance venue map, preprint-vs-double-blind cautions, and typical fee ranges.

## Output: the venue plan (`docs/venues.md`)

A ranked table the user can act on, plus a short recommendation:

```
| Venue | Type (conf/journal) | Fit | Rank (source, yr) | Soft deadline | Hard deadline | Review period | Fee (→cost) | Key prereqs | Priority |
```

Then a 2–4 sentence narrative: the recommended **primary target** and the **fallback chain**, and the **single binding deadline to act on next**. Stamp an `as_of` date and the CFP links the rows came from. Keep it current — re-verify before relying on a row.

## Cost integration (fees are part of total cost)

A submission fee / APC is a real project expense. When a venue is chosen (or to compare candidates), record its fee in `cost.json.actuals` with **`category: "publication"`**; `research-tracking` reports it as a **separate fixed line** in the grand total — **outside** the experiments budget cap, like the coding-agent subscription (it's a post-experiment, end-stage cost, not a variable run decision). Surface candidate fees in the plan so cost is part of the choice, not a surprise at submission.

## Cross-references

- **research-paper** — orchestrator; fires this **early** (Phase 1, venue profile) and **late** (Phase 3/4, deadline lock), and records the chosen target so writing aims at it.
- **research-topic-selection** — consumes the early venue profile as a scored **venue-fit** angle; the topic is chosen partly for venue fit (venue-as-input).
- **research-mock-review** — scores the draft against the venue rubric + numeric bar this skill's profile supplies.
- **research-tracking** — supplies the **estimated finishing date** that triggers the late run; records the **publication fee** as a `publication` cost line.
- **research-writing** — builds the **short version** to the venue + rules this skill confirms (limit, template, format/syntax, disclosure); the main draft stays the arXiv version (subject to the arXiv-vs-double-blind reconciliation above).
- **research-reflection** — re-evaluate the venue choice at boundaries or if the timeline slips (is the target still the best fit×rank×timing?).
- **Host web-search/page-fetch tools** — current CFPs, rankings, deadlines, and fees; prefer official venue sources and verify every cycle.
