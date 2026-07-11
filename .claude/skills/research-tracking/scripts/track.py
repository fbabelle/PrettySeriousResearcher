#!/usr/bin/env python3
"""track.py — effort & cost ledger for the research-paper skill system.

Two distinct lineages, deliberately kept apart:

  EFFORT  — agent-active hours + tokens parsed from Claude Code transcript JSONL.
            Other hosts require a compatible transcript adapter or manual effort rows.
            Transcript tokens are not priced unless they correspond to an actual
            metered bill; billing basis comes from the user's plan, never an assumption.

  COST    — actual USD spend, in two parts:
            * VARIABLE (gated by the budget cap): experiment/system LLM API spend
              (metered from runs/usage.jsonl × rate-card) + compute + data actuals.
            * PROJECT OVERHEAD (reported, NOT gated): coding-agent subscription
              estimates plus explicit metered coding-agent actuals, and publication fees.

This script *derives* the ledgers every run (idempotent — safe to re-run; never
duplicates rows).

What it produces (under <project-root>/docs/tracking/):
  effort.jsonl   one row per agent-active session  (regenerated each run)
  effort.md      human-readable per-phase + total summary
  cost.md        spend by category vs budget, plus the compact report line

What it reads:
  - transcript JSONL for this project (auto-located) — EFFORT only (hours+tokens)
  - runs/usage.jsonl — per-call usage from EXPERIMENT/system API calls; the metered
    LLM cost of running the method (priced via cost.json.rate_card)
  - state.json   phase windows, gate flags, effort target/weights
  - cost.json    rate-card, coding-agent subscription, compute/data actuals, budget cap

Agent-active time rule (user requirement): counting starts when the agent is
engaged and STOPS after >1h of inactivity. We implement this by sorting every
timestamped transcript record and splitting into sessions wherever the gap
between consecutive records exceeds IDLE_GAP_SECONDS. A session's active time is
(last_ts - first_ts) within that session, so idle gaps >1h are excluded and the
*previous* session's end is naturally fixed by the *next* session's first event.

Stdlib only. No third-party deps. Python 3.9+.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

IDLE_GAP_SECONDS = 3600  # >1h inactivity ends a session (user rule)
PHASES = ("topic-selection", "algo-design", "experiments", "writing")


# --------------------------------------------------------------------------- #
# Locating the harness transcripts (portable across split-home setups and OSes)
# --------------------------------------------------------------------------- #
_DRIVE_RE = re.compile(r"^([A-Za-z]):")


def encode_cwd(path: str) -> str:
    """Encode a project path the way the harness names its transcript directory:
    every path separator becomes '-'. A Windows drive letter is lowercased and
    its ':' becomes a '-' too. The result is a single directory NAME.

      POSIX:   /home/x/papers/alpha   -> -home-x-papers-alpha
      Windows: C:\\Projects\\MyPaper  -> c--Projects-MyPaper

    Done with a regex rather than os.path.splitdrive so the encoding is
    identical on every host (a Windows path must encode the same way when
    this is exercised from a POSIX machine, e.g. in tests).
    """
    path = _DRIVE_RE.sub(lambda m: m.group(1).lower() + "-", path, count=1)
    return path.replace("\\", "-").replace("/", "-")


def find_transcript_dir(project_root: str, override: str | None) -> str | None:
    """Locate <config-dir>/projects/<encoded-cwd>. The harness config dir is not
    always under $HOME (e.g. config under one home while the project cwd is
    under a different home/user), so we probe several candidate roots."""
    if override:
        return override if os.path.isdir(override) else None

    enc = encode_cwd(os.path.abspath(project_root))
    # A well-formed encoding is a bare directory name. If a separator survives,
    # the os.path.join below would resolve somewhere real instead (an absolute
    # `enc` silently discards the prefix), and any directory holding a stray
    # *.jsonl would be mistaken for the transcript dir — reporting zero effort
    # as if it were measured. Fail loud (-> the /cost fallback) instead.
    if not enc or os.path.isabs(enc) or "/" in enc or "\\" in enc or os.sep in enc:
        return None

    home = os.path.expanduser("~")
    candidate_roots: list[str] = []
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        candidate_roots.append(os.environ["CLAUDE_CONFIG_DIR"])
    candidate_roots.append(os.path.join(home, ".claude"))
    # split-home / multi-user fallback: siblings of this user's home directory.
    # Covers /home/*, /Users/*, and C:\Users\* without hardcoding any of them.
    candidate_roots += sorted(glob.glob(os.path.join(os.path.dirname(home), "*", ".claude")))

    seen = set()
    for root in candidate_roots:
        if root in seen:
            continue
        seen.add(root)
        cand = os.path.join(root, "projects", enc)
        if os.path.isdir(cand) and glob.glob(os.path.join(cand, "**/*.jsonl"), recursive=True):
            return cand
    return None


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def parse_ts(ts: str) -> float | None:
    """ISO-8601 (with trailing 'Z') -> epoch seconds."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


def load_events(transcript_dir: str) -> list[dict]:
    """Read every *.jsonl (recursively — includes sub-agent transcripts so
    sub-agent tokens count toward total effort). Returns a list of events:
      {ts, is_assistant, model, tok:{in,out,cw5,cw1,cr}, web_search, web_fetch}
    Malformed lines are skipped (transcripts can contain partial writes)."""
    events: list[dict] = []
    files = sorted(glob.glob(os.path.join(transcript_dir, "**/*.jsonl"), recursive=True))
    for fp in files:
        try:
            fh = open(fp, "r", encoding="utf-8")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = parse_ts(rec.get("timestamp"))
                if ts is None:
                    continue
                ev = {"ts": ts, "is_assistant": False, "model": None,
                      "tok": None, "web_search": 0, "web_fetch": 0}
                if rec.get("type") == "assistant":
                    msg = rec.get("message") or {}
                    usage = msg.get("usage") or {}
                    ev["is_assistant"] = True
                    ev["model"] = msg.get("model")
                    cc = usage.get("cache_creation") or {}
                    ev["tok"] = {
                        "in": usage.get("input_tokens", 0) or 0,
                        "out": usage.get("output_tokens", 0) or 0,
                        # split ephemeral cache writes when the breakdown exists,
                        # else fall back to lumping all into the 5m bucket.
                        "cw5": cc.get("ephemeral_5m_input_tokens",
                                      usage.get("cache_creation_input_tokens", 0)) or 0,
                        "cw1": cc.get("ephemeral_1h_input_tokens", 0) or 0,
                        "cr": usage.get("cache_read_input_tokens", 0) or 0,
                    }
                    stu = usage.get("server_tool_use") or {}
                    ev["web_search"] = stu.get("web_search_requests", 0) or 0
                    ev["web_fetch"] = stu.get("web_fetch_requests", 0) or 0
                events.append(ev)
    events.sort(key=lambda e: e["ts"])
    return events


# --------------------------------------------------------------------------- #
# Sessionization (the agent-active clock)
# --------------------------------------------------------------------------- #
def sessionize(events: list[dict]) -> list[dict]:
    """Split sorted events into sessions on gaps > IDLE_GAP_SECONDS.
    Each session: {start, end, active_hours, tok totals, web counts}."""
    sessions: list[dict] = []
    cur: dict | None = None
    for ev in events:
        if cur is None or (ev["ts"] - cur["last_ts"]) > IDLE_GAP_SECONDS:
            cur = {"start": ev["ts"], "last_ts": ev["ts"],
                   "tok": {"in": 0, "out": 0, "cw5": 0, "cw1": 0, "cr": 0},
                   "by_model": {}, "web_search": 0, "web_fetch": 0}
            sessions.append(cur)
        cur["last_ts"] = ev["ts"]
        if ev["is_assistant"] and ev["tok"]:
            for k in cur["tok"]:
                cur["tok"][k] += ev["tok"][k]
            m = ev["model"] or "unknown"
            bm = cur["by_model"].setdefault(
                m, {"in": 0, "out": 0, "cw5": 0, "cw1": 0, "cr": 0})
            for k in bm:
                bm[k] += ev["tok"][k]
            cur["web_search"] += ev["web_search"]
            cur["web_fetch"] += ev["web_fetch"]
    for s in sessions:
        s["end"] = s.pop("last_ts")
        s["active_hours"] = round((s["end"] - s["start"]) / 3600.0, 4)
    return sessions


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# Phase attribution + LLM pricing
# --------------------------------------------------------------------------- #
def phase_for(ts: float, windows: list[dict]) -> str:
    """Return the phase whose window contains ts (start <= ts < end|inf)."""
    chosen = "unphased"
    for w in windows:
        start = parse_ts(w.get("start"))
        end = parse_ts(w.get("end")) if w.get("end") else None
        if start is not None and start <= ts and (end is None or ts < end):
            chosen = w.get("phase", "unphased")
    return chosen


def llm_cost(by_model: dict, rate_card: dict) -> tuple[float, list[str]]:
    """Cost in USD from token totals * dated rate-card (USD per MTok).
    Used to price EXPERIMENT/system API calls (runs/usage.jsonl) — NOT coding-agent
    transcript tokens, whose billing basis cannot be inferred from the transcript.
    Returns (cost, warnings). Unknown models contribute 0 + a warning."""
    llm_rates = (rate_card or {}).get("llm") or {}
    cost = 0.0
    warns: list[str] = []
    for model, tok in by_model.items():
        r = llm_rates.get(model)
        if not r:
            warns.append(f"unpriced model '{model}' "
                         f"({tok['in']+tok['out']+tok['cw5']+tok['cw1']+tok['cr']} tok)")
            continue
        cost += (tok["in"] * r.get("in", 0)
                 + tok["out"] * r.get("out", 0)
                 + tok["cw5"] * r.get("cache_write_5m", r.get("in", 0) * 1.25)
                 + tok["cw1"] * r.get("cache_write_1h", r.get("in", 0) * 2.0)
                 + tok["cr"] * r.get("cache_read", r.get("in", 0) * 0.1)) / 1_000_000.0
    return round(cost, 4), warns


# --------------------------------------------------------------------------- #
# Experiment/system LLM spend (metered) — runs/usage.jsonl
# --------------------------------------------------------------------------- #
def load_experiment_usage(root: str) -> list[dict]:
    """Read per-call usage logged by the experiment harness to runs/usage.jsonl
    (and any runs/**/usage*.jsonl). Tolerant of field aliases. Each returned row:
      {model, tok:{in,out,cw5,cw1,cr}, usd (optional explicit cost), phase (optional)}
    A row may carry an explicit `usd` (trusted as-is); otherwise it is priced from
    the rate-card by its tokens."""
    paths: set[str] = set()
    direct = os.path.join(root, "runs", "usage.jsonl")
    if os.path.isfile(direct):
        paths.add(direct)
    for p in glob.glob(os.path.join(root, "runs", "**", "usage*.jsonl"), recursive=True):
        paths.add(p)

    rows: list[dict] = []
    for fp in sorted(paths):
        try:
            fh = open(fp, "r", encoding="utf-8")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cc = rec.get("cache_creation") or {}
                tok = {
                    "in": rec.get("in", rec.get("input_tokens", 0)) or 0,
                    "out": rec.get("out", rec.get("output_tokens", 0)) or 0,
                    "cw5": (rec.get("cw5", rec.get("cache_write_5m",
                            cc.get("ephemeral_5m_input_tokens",
                                   rec.get("cache_creation_input_tokens", 0))))) or 0,
                    "cw1": (rec.get("cw1", rec.get("cache_write_1h",
                            cc.get("ephemeral_1h_input_tokens", 0)))) or 0,
                    "cr": (rec.get("cr", rec.get("cache_read",
                           rec.get("cache_read_input_tokens", 0)))) or 0,
                }
                rows.append({
                    "model": rec.get("model") or "unknown",
                    "tok": tok,
                    "usd": rec.get("usd"),
                    "phase": rec.get("phase"),
                })
    return rows


def experiment_cost(rows: list[dict], rate_card: dict) -> tuple[float, int, list[str]]:
    """Total experiment/system LLM spend. Rows with an explicit `usd` are summed
    verbatim; the rest are priced per-model from the rate-card. Returns
    (usd, total_tokens, warnings)."""
    by_model: dict[str, dict] = {}
    override = 0.0
    tok_total = 0
    for r in rows:
        tok_total += total_tok(r["tok"])
        if r.get("usd") is not None:
            try:
                override += float(r["usd"])
            except (TypeError, ValueError):
                pass
        else:
            bm = by_model.setdefault(r["model"], {"in": 0, "out": 0, "cw5": 0, "cw1": 0, "cr": 0})
            for k in bm:
                bm[k] += r["tok"][k]
    calc, warns = llm_cost(by_model, rate_card)
    return round(override + calc, 4), tok_total, warns


# --------------------------------------------------------------------------- #
# Coding-agent subscription (fixed, reported, NOT gated)
# --------------------------------------------------------------------------- #
def months_active(sessions: list[dict], override) -> float:
    """Number of distinct calendar months in which the project saw agent activity
    (the unit a monthly subscription is billed in). `override` (cost.json
    coding_agent.months_active_override) wins when set."""
    if override is not None:
        try:
            return float(override)
        except (TypeError, ValueError):
            pass
    months = {iso(s["start"])[:7] for s in sessions}  # 'YYYY-MM' with activity
    return float(len(months))


def coding_expense(coding_cfg: dict, months: float) -> tuple[float, bool]:
    """Estimated coding-agent expense = sum(monthly fee × share) × active months.
    Returns (usd, configured?) — `configured` is False when no agent has a fee set,
    which the report surfaces as a prompt to enter it."""
    cfg = coding_cfg or {}
    per_month = 0.0
    configured = False
    for a in cfg.get("agents", []) or []:
        fee = a.get("usd_per_month")
        if fee in (None, 0, 0.0):
            continue
        configured = True
        try:
            share = float(a.get("share_pct", 100)) / 100.0
        except (TypeError, ValueError):
            share = 1.0
        try:
            per_month += float(fee) * share
        except (TypeError, ValueError):
            continue
    return round(per_month * months, 2), configured


# --------------------------------------------------------------------------- #
# IO helpers
# --------------------------------------------------------------------------- #
def read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def total_tok(tok: dict) -> int:
    return tok["in"] + tok["out"] + tok["cw5"] + tok["cw1"] + tok["cr"]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate research effort/cost ledgers.")
    ap.add_argument("--project-root", default=os.getcwd(),
                    help="repo root holding docs/tracking (default: cwd)")
    ap.add_argument("--transcript-dir", default=None,
                    help="Claude Code transcript directory override; other schemas require an adapter")
    ap.add_argument("--json", action="store_true", help="emit machine summary to stdout")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    tdir = os.path.join(root, "docs", "tracking")
    os.makedirs(tdir, exist_ok=True)

    state = read_json(os.path.join(tdir, "state.json"), {})
    cost_cfg = read_json(os.path.join(tdir, "cost.json"), {})
    rate_card = cost_cfg.get("rate_card", {})
    coding_cfg = cost_cfg.get("coding_agent", {})
    windows = state.get("phase_windows", [])
    target_hours = state.get("effort_target_hours", 120)
    weights = state.get("phase_weights",
                        {"topic-selection": .30, "algo-design": .20,
                         "experiments": .30, "writing": .20})

    transcript_dir = find_transcript_dir(root, args.transcript_dir)
    if not transcript_dir:
        # Fallback path: transcripts unreadable -> effort auto-parse off, but cost
        # (experiment usage + actuals + coding subscription) still computes.
        msg = ("[track.py] No compatible Claude Code transcript dir found.\n"
               "  Effort auto-parse is unavailable for this host/schema.\n"
               "  FALLBACK: record measured effort manually, or pass --transcript-dir\n"
               "  only for compatible Claude Code JSONL. Cost still computes below.")
        print(msg, file=sys.stderr)
        sessions = []
    else:
        sessions = sessionize(load_events(transcript_dir))

    # ---- per-session EFFORT rows + per-phase aggregation ------------------- #
    # NOTE: no inferred per-session dollar cost — the transcript does not encode
    # the billing contract. Effort remains hours+tokens; billed actuals are separate.
    per_phase: dict[str, dict] = {}
    rows: list[dict] = []
    now = max((s["end"] for s in sessions), default=None)
    for i, s in enumerate(sessions):
        ph = phase_for(s["start"], windows)
        is_open = (i == len(sessions) - 1) and now is not None and (now - s["end"] < IDLE_GAP_SECONDS)
        row = {
            "session_id": iso(s["start"]),
            "phase": ph,
            "start": iso(s["start"]),
            "end": iso(s["end"]),
            "end_basis": "provisional_open" if is_open else "inferred_next_start",
            "active_hours": s["active_hours"],
            "tokens": {**s["tok"], "total": total_tok(s["tok"]),
                       "source": "harness_transcript", "confidence": "measured"},
            "web": {"search": s["web_search"], "fetch": s["web_fetch"]},
            "models": sorted(s["by_model"].keys()),
        }
        rows.append(row)
        agg = per_phase.setdefault(ph, {"active_hours": 0.0, "tokens": 0, "sessions": 0})
        agg["active_hours"] += s["active_hours"]
        agg["tokens"] += total_tok(s["tok"])
        agg["sessions"] += 1

    # ---- write effort.jsonl (regenerated, idempotent) ---------------------- #
    with open(os.path.join(tdir, "effort.jsonl"), "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    # ---- effort totals ----------------------------------------------------- #
    tot_hours = round(sum(p["active_hours"] for p in per_phase.values()), 2)
    tot_tokens = sum(p["tokens"] for p in per_phase.values())

    # ---- COSTS ------------------------------------------------------------- #
    # Variable (gated by the cap): experiment/system LLM API + compute + data.
    usage_rows = load_experiment_usage(root)
    exp_llm, exp_tokens, exp_warns = experiment_cost(usage_rows, rate_card)
    compute_actual = round(sum(a.get("usd", 0) for a in cost_cfg.get("actuals", [])
                               if a.get("category") == "compute"), 2)
    data_actual = round(sum(a.get("usd", 0) for a in cost_cfg.get("actuals", [])
                            if a.get("category") == "data"), 2)
    variable_total = round(exp_llm + compute_actual + data_actual, 2)

    # Project overhead (reported, NOT gated): coding plan, metered coding actuals, publication.
    mo = months_active(sessions, coding_cfg.get("months_active_override"))
    coding, coding_configured = coding_expense(coding_cfg, mo)
    coding_metered = round(sum(a.get("usd", 0) for a in cost_cfg.get("actuals", [])
                                 if a.get("category") == "coding_agent"), 2)
    publication = round(sum(a.get("usd", 0) for a in cost_cfg.get("actuals", [])
                            if a.get("category") == "publication"), 2)

    grand = round(variable_total + coding + coding_metered + publication, 2)
    cap = (cost_cfg.get("budget") or {}).get("total_cap")
    finalized = cost_cfg.get("status") == "finalized"
    # Finishing-date estimate — triggers research-venue-selection; surfaced, not computed here.
    est_finish = state.get("estimated_finish_date")
    target_submission = state.get("target_submission_date")

    # ---- effort.md --------------------------------------------------------- #
    em = ["# Effort ledger (auto-generated by track.py — do not edit by hand)\n",
          f"_Generated: {iso(now) if now else 'n/a'} · source: harness transcripts · "
          f"agent-active clock (idle >1h excluded) · tokens are an effort signal, not a cost_\n",
          "| Phase | Target % | Active hrs | Target hrs | Status | Tokens | Sessions |",
          "|---|---|---|---|---|---|---|"]
    for ph in PHASES + ("unphased",):
        p = per_phase.get(ph)
        if not p and ph == "unphased":
            continue
        p = p or {"active_hours": 0, "tokens": 0, "sessions": 0}
        w = weights.get(ph, 0)
        tgt = round(target_hours * w, 1)
        over = (w > 0 and p["active_hours"] > tgt)
        status = "OVER ⚠" if over else "ok"
        if ph == "unphased":
            status = "—"
        em.append(f"| {ph} | {int(w*100)}% | {round(p['active_hours'],2)} | "
                  f"{tgt if w else '—'} | {status} | {p['tokens']:,} | {p['sessions']} |")
    em.append(f"| **TOTAL** | 100% | **{tot_hours}** | {target_hours} | | "
              f"**{tot_tokens:,}** | {len(rows)} |\n")
    if rows and rows[-1]["end_basis"] == "provisional_open":
        em.append(f"\n> Last session ({rows[-1]['session_id']}) is **in progress "
                  f"(provisional)** — its end is finalized on the next engagement.\n")
    with open(os.path.join(tdir, "effort.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(em))

    # ---- cost.md ----------------------------------------------------------- #
    # The experiment cap governs method-running variable spend; coding overhead is separate.
    pct = f"{round(100*variable_total/cap)}%" if cap else "n/a"
    cap_s = f"${cap:,.2f}" if cap else "UNSET (provisional)"
    report = (f"Spent ${variable_total:,.2f} of {cap_s} ({pct}) | "
              f"exp-llm ${exp_llm:,.2f} / compute ${compute_actual:,.2f} / data ${data_actual:,.2f} | "
              f"coding-plan ${coding:,.2f} + coding-metered ${coding_metered:,.2f} + "
              f"pub ${publication:,.2f} (outside cap) | "
              f"effort: {tot_hours} active-hrs, {tot_tokens:,} tokens")
    cm = ["# Cost ledger (auto-generated by track.py — do not edit by hand)\n",
          f"_Generated: {iso(now) if now else 'n/a'} · budget status: "
          f"**{'FINALIZED' if finalized else 'PROVISIONAL'}**_\n",
          "## Compact report line\n", f"`{report}`\n",
          "## By category", "| Category | Spend USD | Basis |", "|---|---|---|",
          f"| Experiment LLM API | {exp_llm:,.2f} | runs/usage.jsonl × rate-card |",
          f"| Compute | {compute_actual:,.2f} | manual actuals (cost.json) |",
          f"| Data providers | {data_actual:,.2f} | manual actuals (cost.json) |",
          f"| **Variable subtotal (vs cap)** | **{variable_total:,.2f}** | gated by the budget cap |",
          f"| Coding agent (subscription) | {coding:,.2f} | "
          f"$/mo × {mo:g} active months — fixed, **outside** the cap |",
          f"| Coding agent (metered actuals) | {coding_metered:,.2f} | explicit billed amounts; **outside** the experiment cap |",
          f"| Publication / submission fees | {publication:,.2f} | venue APC/submission (research-venue-selection) — fixed, **outside** the cap |",
          f"| **Grand total (all-in)** | **{grand:,.2f}** | variable + coding plan/metered + publication |\n"]
    notes: list[str] = []
    if not usage_rows:
        notes.append("no `runs/usage.jsonl` yet — experiment LLM cost is $0 until the "
                     "experiment harness logs per-call usage.")
    if not coding_configured:
        notes.append("coding-agent subscription not set — enter your monthly fee(s) in "
                     "`cost.json.coding_agent.agents[].usd_per_month` (research-tracking prompts for this).")
    if not rate_card.get("llm"):
        notes.append("`rate_card.llm` is empty — experiment LLM cost stays $0 until you "
                     "populate per-model rates from the provider's current official pricing documentation.")
    for w in exp_warns:
        notes.append(f"experiment usage: {w}")
    for n in notes:
        cm.append(f"\n> ⚠ {n}\n")
    with open(os.path.join(tdir, "cost.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(cm))

    # ---- stdout ------------------------------------------------------------ #
    if args.json:
        print(json.dumps({
            "total_active_hours": tot_hours, "total_tokens": tot_tokens,
            "experiment_tokens": exp_tokens,
            "exp_llm_usd": exp_llm, "compute_usd": compute_actual,
            "data_usd": data_actual, "variable_usd": variable_total,
            "coding_usd": coding, "coding_metered_usd": coding_metered,
            "months_active": mo, "coding_configured": coding_configured,
            "publication_usd": publication,
            "grand_usd": grand, "cap": cap, "finalized": finalized,
            "estimated_finish_date": est_finish, "target_submission_date": target_submission,
            "sessions": len(rows), "per_phase": per_phase,
        }, indent=2))
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
