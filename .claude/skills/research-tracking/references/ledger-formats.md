# Ledger formats & session-accounting spec

This is the data-model reference for `research-tracking`. The SKILL.md points here; read this when you need exact field meanings, the session-boundary algorithm, or the cost formula.

All files live under `<project-root>/docs/tracking/`. `effort.jsonl`, `state.json`, and `cost.json` are committed; `.session` is gitignored.

## The clock: agent-active time

"Effort" time is **agent-active time**, not human wall-clock. The rule (from the user's working agreement): counting starts when the agent is engaged and **stops after >1h of inactivity**; the previous session's end is only knowable from the next session's start.

`scripts/track.py` implements this by reading the harness transcript JSONL for this project, sorting every timestamped record, and splitting into **sessions** wherever the gap between consecutive records exceeds `IDLE_GAP_SECONDS` (3600). A session's `active_hours = last_ts - first_ts` within that session, so any idle gap >1h is excluded and the previous session's end is fixed at its last pre-gap record — exactly the "derived from the next session" rule, computed retroactively.

This means the ledger is **derived, not hand-maintained**: re-running `track.py` rebuilds `effort.jsonl` from the immutable transcripts (idempotent — no duplicate rows on re-run). Do not hand-edit `effort.jsonl`.

## `.session` (untracked scratch)

`{ "start": "<iso>", "last_heartbeat": "<iso>", "phase": "<phase>" }`

Optional aid for the *currently open* session. The orchestrator may write it on engagement and bump `last_heartbeat` at major steps so an in-progress session is visible before `track.py` next runs. It is **not** the source of truth (the transcript is) and is gitignored because it is volatile and machine-local. If transcript parsing works, `.session` can be ignored entirely.

## `state.json` (committed)

Drives phase attribution and the gates.

| field | meaning |
|---|---|
| `current_phase` | one of `topic-selection`/`algo-design`/`experiments`/`writing` |
| `effort_target_hours` | total budget for the 30/20/30/20 soft-target check (default 120) |
| `phase_weights` | the 0.30/0.20/0.30/0.20 split |
| `phase_windows` | ordered `[{phase, start, end}]`; a session at time *t* belongs to the window with `start <= t < (end or +inf)` |
| `gates.algo_design_complete` | set `true` when Phase 2 finishes; precondition for the budget gate |
| `gates.budget_status` | mirror of `cost.json.status`; `provisional` → blocks Phase 3 entry |
| `estimated_finish_date` | ISO date (nullable) — projected/judged finish; when it comes into view it triggers `research-venue-selection` to find venues whose deadlines are still catchable |
| `target_submission_date` | ISO date (nullable) — the deadline being aimed at once a target venue is chosen |

**Advancing a phase:** set the current window's `end` to now, append `{phase: <next>, start: now, end: null}`, and update `current_phase`. Set the first window's `start` on first engagement.

## `effort.jsonl` (committed, derived)

One JSON object per closed session, regenerated each run:

```json
{
  "session_id": "2026-06-22T08:00:40Z",
  "phase": "topic-selection",
  "start": "2026-06-22T08:00:40Z",
  "end": "2026-06-22T08:46:54Z",
  "end_basis": "inferred_next_start | provisional_open",
  "active_hours": 0.77,
  "tokens": {"in": ..., "out": ..., "cw5": ..., "cw1": ..., "cr": ..., "total": ..., "source": "harness_transcript", "confidence": "measured"},
  "web": {"search": 0, "fetch": 0},
  "models": ["claude-opus-4-8"]
}
```

`cw5`/`cw1` = 5-minute / 1-hour cache-write tokens; `cr` = cache-read tokens. These transcript tokens are an *effort* signal; price them only when they map to an actual metered bill. Flat plans belong under `coding_agent` and metered coding bills under `actuals`. The last row may carry `end_basis: "provisional_open"` — it is the still-running session and its end will be finalized on the next engagement.

## `cost.json` (committed)

```json
{
  "schema_version": 2,
  "status": "provisional | finalized",
  "finalized_at": null,
  "currency": "USD",
  "coding_agent": {
    "agents": [ {"name": "Claude Code (Max)", "usd_per_month": 200, "share_pct": 100} ],
    "months_active_override": null
  },
  "budget": {"total_cap": null, "by_category": {"llm_api": null, "compute": null, "data": null}},
  "rate_card": { "as_of": "<date>", "llm": { "<model>": {"in","out","cache_write_5m","cache_write_1h","cache_read"} }, "web_search_per_1k": {...}, "compute": {...}, "data": {...} },
  "actuals": [ {"ts","category":"compute|data|publication","item","usd","period","phase"} ]
}
```

Cost splits into two lineages — keep them apart. **Grand total = variable + coding + publication; the cap/gate governs the variable part only.**

- **Coding-agent billing (reported, NOT gated).** Detect the actual plan. Record flat plans in `coding_agent.agents[]` with monthly fee and optional project share. Record explicit metered bills in `actuals` with `category: "coding_agent"`. Transcript tokens never establish a billing contract. Both coding lines appear in the grand total outside the experiment cap.
- **Publication / submission fees (FIXED, reported, NOT gated).** The venue's APC or submission fee (from `research-venue-selection`). Entered as an `actuals` row with `category: "publication"`. Reported as its own line in the grand total but **outside** the experiments cap — it's a post-experiment, end-stage cost, not a variable run decision (same treatment as the coding subscription).
- **Experiment/system LLM API (VARIABLE, gated).** The metered cost of *running the method* — computed by `track.py` from `runs/usage.jsonl` (per-call usage logged by the experiment harness) × `rate_card.llm[model]`. Keep the rate-card current from each provider's official pricing documentation and record the verification date. A usage row may carry an explicit `usd` (trusted verbatim); otherwise it is priced from its tokens.
- **Compute and data (VARIABLE, gated).** Entered by hand as `actuals` rows (category `compute`/`data`) — local-machine amortization/electricity and provider subscriptions that no log can know.
- **The budget cap & gate govern VARIABLE spend only** (experiment LLM API + compute + data). `status` starts `provisional`; the orchestrator blocks entry to the `experiments` phase until `status == "finalized"`. Finalizing sets `finalized_at`, `total_cap`, and `by_category`, and flips `state.json.gates.budget_status`. Re-finalization is allowed but must be an explicit, logged action (append a note; don't silently overwrite).

## `runs/usage.jsonl` (experiment usage — the metered LLM cost source)

The experiment harness (see `research-experiments`) appends one JSON object per API call. `track.py` reads `runs/usage.jsonl` and any `runs/**/usage*.jsonl`. Tolerant of field aliases:

```json
{"ts": "<iso>", "model": "claude-sonnet-4-6", "in": 1200, "out": 800, "cr": 5000, "phase": "experiments"}
{"ts": "<iso>", "model": "gpt-...", "usd": 0.0123, "phase": "experiments"}
```

`in`/`out`/`cw5`/`cw1`/`cr` (aliases: `input_tokens`/`output_tokens`/`cache_write_5m`/`cache_write_1h`/`cache_read`, plus `cache_creation.ephemeral_*`). A row with explicit `usd` is summed as-is (use this for non-Anthropic providers not in the rate-card); otherwise the tokens are priced from the rate-card.

## Cost formula (experiment LLM, per model)

```
usd = ( in*in_rate + out*out_rate
      + cw5*cache_write_5m + cw1*cache_write_1h + cr*cache_read ) / 1_000_000
```

Applied to the per-model token sums from `runs/usage.jsonl` (NOT the coding transcript). Unknown model → contributes 0 with a printed warning (tokens are still counted; only the dollar figure is withheld). Local-model inference has no API token cost — its cost is the `compute` actuals.

## Running it

```
python <project-root>/.claude/skills/research-tracking/scripts/track.py [--json]
```

Default: refreshes `effort.jsonl` + regenerates `effort.md`/`cost.md`, prints the compact report line. `--json` emits a machine summary. Fallback: if no transcript dir is found, it prints a `/cost`-paste instruction and still regenerates `cost.md` from manual actuals. The transcript dir is auto-located across `$CLAUDE_CONFIG_DIR`, `~/.claude`, and any sibling home's `.claude` (handles split-home setups on Linux, macOS, and Windows). The project path is encoded into a single directory name by replacing each separator with `-`; a Windows drive letter is lowercased and its `:` becomes a `-` (`C:\Projects\MyPaper` → `c--Projects-MyPaper`). If that encoding ever yields something other than a bare name, discovery returns "not found" and takes the `/cost` fallback rather than guessing at a directory.
