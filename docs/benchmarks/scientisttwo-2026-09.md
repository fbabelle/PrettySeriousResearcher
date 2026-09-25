# ScientistTwo vs this skill set (benchmarking pass, 2026-09-25)

Source-project doc (not shipped by `install_skills.py`). Records which mechanisms of
ScientistTwo were folded into the skills, which were not, and why, so later passes do not
re-litigate them.

**Source.** J. Nam, J. Yoon, Y. Pan, Y. Wang, R. Meng, P. Ranganathan, T. Pfister,
"ScientistTwo: Pioneering the Human Knowledge Frontier with Autonomous AI",
arXiv:2609.19644v1 (2026-09-17), Google Cloud AI Research + University of Waterloo.
Project page: https://scientist-two.github.io/. Integrity audit from ScientistOne
(Meng et al., arXiv:2605.26340). Facts below were read from the arXiv HTML on 2026-09-25.

## What it is

A multi-agent pipeline that takes an ML problem and a human SOTA paper and returns a paper
plus codebase with no human in the loop: limitation extraction → seed ideas ranked by
novelty → subset-first screening (Bad / Good / Engineer, capped engineering) → idea
evolution mixed with untried seeds → selector → ablation planner/critic → drafter →
review-rebuttal loop (score ≥ 8 or N_peer rounds) → meta-review (Accept / Refine).
Every loop has a named cap (N_seed, N_0, N_eng, K, S, N_p, N_abl, N_peer, N_meta);
zero successes after K rounds ends the run.

## Evidence worth keeping

| Finding | Number | Where |
|---|---|---|
| Beats the human SOTA it started from | 86 of 107 problems (80.4 %), mean relative gain 25.2 % | abstract, Tables 2 and 4 |
| In-loop reviewer (ScholarPeer) acceptance over rebuttal rounds 0/1/2 | 46.9 → 79.6 → 93.9 % | Table 5 |
| Held-out reviewer (Stanford Agentic Reviewer), same rounds | 49.0 → 73.5 → 69.4 % | Table 5 |
| Integrity failures without repair agents (of 50 papers) | 11 method-code misaligned, 1 spec violation, 19/1,840 bad references | Table 7 |
| Human experts, ScientistTwo vs accepted human papers (3 = parity) | overall 3.0; method soundness and rigor 2.9 (humans ahead); baselines/benchmarks 3.5 | Table 10 |
| Cost and time per problem | ≈ $3,800, 2.5 days on average; idea refinement dominates | §4.3, Fig. 11 |
| Where the best ideas come from | mostly the early refinement rounds | Fig. 10 |
| Statistical reporting of gains | no seed variance, intervals or significance tests in the paper | whole text |

## Mapping

| ScientistTwo mechanism | Decision | Where it landed |
|---|---|---|
| Limitation Extractor + Verifier loop | **Adopted** as a limitation inventory with a sufficiency pass by another family, capped at 2–3 rounds | `research-topic-selection` Step 3.0 |
| Seed ideas ranked by novelty; evolved ideas mixed with untried seeds | **Adopted** as the reserve pool drawn on at loop-backs | `research-topic-selection` Step 3.4 |
| Baseline reproduced on a subset before any idea is tested | **Adopted**: compare with the reproduced number; the reproduction gap is a finding | `research-algo-design` Step 4 |
| Subset-first screening, Bad / Good / Engineer, capped engineering, stop rule | **Adapted**: development slice only, rule and caps stated before the loop, every candidate logged as a trial, zero survivors → null-result branch | `research-algo-design` Step 2 |
| Result Comparison Agent (replace only if strictly better; else discard) | **Adopted** as keep-the-incumbent, with downstream re-runs and trial counting | `research-experiments` Step 3 |
| Rebuttal agent runs supplementary experiments | **Adapted**: the packet drafts costed experiment plans; the user picks; runs pass the budget gate | `research-mock-review` protocol step 6 |
| In-distribution vs held-out reviewer | **Adopted, and turned into a rule**: one reviewer never steers revisions; only its score is reported after a revision; stop when it stops rising | `research-mock-review` panel section |
| CoE integrity audit (score, spec, references, method-code) | **Adopted** as the Phase-4 integrity audit; references stay with `research-references` | `research-provenance`; wired into `research-paper`, `research-mock-review`, `research-code-review` |
| Trial accounting for idea search | **Added** (absent in ScientistTwo) | `research-finance-rigor` multiple-testing bullet |
| Meta-review Agent decides Accept / Refine | **Not adopted.** The user stays the chooser (autonomy inversion, 2026-07-08 decision). | — |
| Revise until the reviewer scores ≥ 8 | **Not adopted.** A target score on an in-loop reviewer is what Table 5 shows being gamed; the held-out reviewer rule replaces it. | — |
| Unbounded idea evolution on the reported benchmark | **Not adopted.** Screening stays on development data with stated caps; the 2026-07-08 non-adoption of full tree search stands. | — |
| Proprietary-model, ≈ $3,800 fully autonomous runs | **Not adopted as a default.** Useful as a budget-gate reference point for an "aggressive" scenario. | — |

## Where this set remains ahead

ScientistTwo's own human study puts it behind human authors only on method soundness and
rigor, and it reports gains without seed variance or significance tests. The set's
experimental-rigor protocol, finance-rigor battery and provenance gate cover exactly that
gap; the adoptions above add its strengths (screening discipline, experiment-backed
rebuttals, integrity audit) without giving up the user's decisions or the trial count.
