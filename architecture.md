# Architecture

Design, workflow, and project charter for the research-paper workspace.

## Project charter (filled in during Phase 1)

> Set by `research-topic-selection` from the two-direction interview. Until a paper is started, this is a template.

- **Domain / sub-area:** _TBD_
- **Target problem(s):** _TBD_
- **Direction:** _(a) algorithm/technical — push the field  |  (b) experimental/analytical — survey/benchmark/variation_ — _TBD_
- **Improve vs challenge:** _TBD_
- **Expected outcome:** _new method/system | analysis/understanding_ — _TBD_
- **Target venue / length:** _TBD_
- **Success criteria:** _what result makes this a paper; what the honest negative result is_ — _TBD_

## System design — the skill orchestration

The `research-paper` orchestrator is a thin state machine. On each engagement it reads `docs/tracking/state.json`, opens the session clock, routes to the current phase's craft skill, enforces the hard-stop gates, and reports effort+cost.

```
research-paper (orchestrator: routing, session clock, ranked-options gates, null-result branch, status)
├── Phase 1  research-topic-selection   ──(web search/fetch, research-venue-selection[early venue profile], research-references)
├── Phase 2  research-algo-design        ──(research-code-review, web search/fetch)                            ──► BUDGET GATE
├── Phase 3  research-experiments        ──(research-code-review, research-provenance, research-finance-rigor)  ◄── (blocked until budget finalized)
└── Phase 4  research-writing            ──(research-references, research-provenance, research-visuals)
                                          ──► research-mock-review packet + clean citation/visual/provenance audits required to finish
                                          ──► on "submit": research-submission (portal execution, rebuttals, camera-ready, release — calendar-gated tail)
cross-cutting: research-tracking (effort+cost ledgers, two time clocks, budget playbook)
               research-code-review (4-step judgment + tests + math↔code & judge-calibration checks)
               research-references (anti-hallucination citation gate + running evidence ledger; Phase-1 novelty scan)
               research-provenance (results-integrity gate: every number/figure → a runs/ artifact)
               research-finance-rigor (statistical honesty + data-licensing gate; finance-leaning topics only)
               research-visuals (publication-quality figures/tables + two-phase VLM audit; Phases 3–4)
               research-venue-selection (early venue profile → a topic-selection input; late deadline lock)
               research-mock-review (pre-submission reviewer panel via coding-agent CLIs; ranked weaknesses + rebuttals)
               research-submission (post-packet tail: submission execution, evidence-mapped responses, camera-ready, release)
               research-reflection (periodic multi-CLI adversarial self-check; loop-back target)
               research-repo-hygiene (standing conventions)
```

### Hard-stop checkpoints (each a ranked-options → confirm handshake, not a self-cleared checklist)
1. **Two-direction interview + early venue profile** (start of Phase 1) — confirm scope; the venue becomes a topic input (venue-as-input).
2. **Topic slate** (end of Phase 1) — the ranked, multi-angle candidate slate; the user chooses or injects their own framing.
3. **Budget-finalization gate** (entry to Phase 3) — `cost.json.status` must be `finalized` first.
4. **Pre-submission packet** (Phase-4 exit) — `research-mock-review` score-vs-bar + ranked weaknesses + drafted rebuttals + bundled citation/visual/provenance audits; the user decides submit-or-revise. Never auto-decided.
5. **Reflection confirmations** — propose, act on confirmation.

At every gate the agent does the diagnosis first and presents a pre-ranked, pre-critiqued artifact with a one-line spend echo; two-tier triage escalates only the shortlist + genuine cross-model disagreements — so the gates *reduce* the user's review time (the resource the effort clock tracks) rather than multiplying touchpoints.

### Null / negative-result branch
If a method doesn't beat its baselines, the orchestrator does **not** force a positive paper — it offers a ranked choice (reframe as analysis/limitation/negative-result, retarget a venue, loop back via `research-reflection`, or stop). A fully-automated pipeline that must always emit a win is structurally pushed toward the over-claiming the gates guard against.

### Solvability gate (Phase 2)
If no candidate approach can plausibly solve the framed problem, the orchestrator does **not** advance — it fires `research-reflection` to revisit the framing rather than spend the experiments budget. The verdict is presented as an advisor-style ranked modification report (feasible/unfeasible per candidate), not a self-cleared pass/fail.

### Deferred / future work (intentional non-adoptions)

Recorded so the decision trail is explicit — these were evaluated against the open-source field and deliberately **not** built, to keep the set a tight state machine:

- **Cross-run / cross-paper memory** (an AgentRxiv-style shared preprint/results store, or a SciAgents-style concept knowledge graph). Measured gains exist across *many* runs, but it's infra-heavy and yields nothing for a single paper. **Revisit trigger:** once ~2–3 papers exist to compound across. Until then, `research-references`' single-paper in-context evidence ledger covers the need.
- **Full best-first agentic experiment tree search** (AI-Scientist-v2). We take only the bounded pieces (capped self-debug + best-config buffer); a full search fights the confirm surface and doesn't fit the data/leakage/cost-bound AI×finance regime.
- **A shared finance-data auto-loader.** Data acquisition stays a deliberate per-paper step under `research-finance-rigor`'s licensing/point-in-time/survivorship checkpoint, not a one-line public-hub load.

Other deliberate non-adoptions (auto-accept/reject decisioning, manual-labor checkpoints, open-ended clarifying questions, majority-vote citations, uncalibrated LLM-judges, compute-heavy Elo, pricing subscription tokens as spend) are recorded in the maintainers' internal changelog.

## Effort & cost accounting

`.claude/skills/research-tracking/scripts/track.py` parses compatible Claude Code JSONL, segments agent-active sessions (idle >1h excluded), sums per-model tokens, and regenerates `effort.md` / `cost.md`. Other agents require an adapter or manual effort rows. Transcript activity is not user-attention time and transcript tokens do not determine billing. Cost detects the real coding plan: flat plans and explicit metered coding actuals are reported outside the experiment cap; the cap governs method-running LLM API, compute, and data spend. Background runtime and explicitly measured user-interaction time remain separate. See `.claude/skills/research-tracking/references/ledger-formats.md` for the full data model.

## Portability & import

The skill set is authored to be shared: no hardcoded project paths, no identifying data. Three distribution channels share one source of truth (`.claude/skills/`):

1. **Claude Code plugin** — the repo self-hosts a single-plugin marketplace (`.claude-plugin/marketplace.json` + `plugin.json`, whose `"skills"` field points at `.claude/skills/`, so no restructuring). Users: `/plugin marketplace add fbabelle/PrettySeriousResearcher` → `/plugin install`. Zero Python; versioned by commit SHA (no `version` field, per plugin docs, so users update per commit).
2. **`uvx` console script** — `pyproject.toml` packages `install_skills.py` as the `research-skills` entry point (hatchling; the wheel force-includes `.claude/skills` and the two tracking templates under `install_skills_data/`, and the script falls back to that layout when the repo layout is absent). `uvx --from git+<repo> research-skills --target <tool> --dest <proj>` works on Windows/macOS/Linux with only uv installed (it auto-provisions Python ≥3.10).
3. **Clone + stdlib script** — `python install_skills.py` (`--target claude|cursor|codex|agents|…`), translating to the target's skills location (`SKILL.md` is a cross-tool standard) or to `.cursor/rules/*.mdc` (lossy) / a neutral `bundle`.

Every channel **lints** the skill set for absolute paths and secrets before any copy and refuses on a hit (`--check-only` runs the lint alone). `--with-scaffold` lays down reset tracking templates and stubs but never copies run data (`effort.jsonl`/`effort.md`/`cost.md`) or `settings.local.json`. CI (`.github/workflows/ci.yml`) proves the whole surface on a Linux/macOS/Windows matrix: unit tests, the lint, a copy-mode install smoke, a wheel-mode (`uvx --from .`) install smoke, and plugin-manifest validation. See the README for usage.

## Workflow conventions

See `.claude/skills/research-repo-hygiene/references/conventions.md` — directory layout, plan backups, changelog, draft rotation, commit/push/PR rules, test discipline, and the `memory.md` policy.

**Source vs install.** This repo (`PrettySeriousResearcher`) is the **skill-source project**: the skills here are the deliverable. `install_skills.py` copies `.claude/skills/` into *paper* projects, where they are used **read-only** — a paper project should not track or edit its installed skills (it ignores `.claude/`), and updates flow one way: improve a skill here, then reinstall. Because of this, guidance for **authoring the skills themselves** (the `name`/`description` limits per surface, the ≤250-char rule, SKILL.md best practices, with official-doc links) lives at the source-project level in [`docs/skill-authoring.md`](docs/skill-authoring.md) — deliberately **outside** `.claude/skills/` so it is never shipped into a paper build.
