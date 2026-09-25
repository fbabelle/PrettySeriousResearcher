"""Run an adversarial mock-review panel over a manuscript by driving coding-agent CLIs as referees and
desk-triage editors.

Purpose: the `research-mock-review` pre-submission gate. Each panel member is an independent
non-interactive CLI call (codex exec / claude -p) with the full manuscript on stdin and a persona
brief; its review lands as one markdown file. Two kinds of member:
  * referee - a full journal-style review with 1-5 scores on a 7-dimension rubric + recommendation;
  * editor  - a 15-minute desk-triage pass ("send to review or reject without review?"). A desk reject
              returns no feedback, so this is the only place to obtain it before submitting.
The script never decides accept/reject; it produces the raw reviews the pre-submission packet aggregates.

The panel (candidate venues + members) is the project's own JSON config; --dump-config prints the
generic default (DEFAULT_PANEL) as a starting point:
  {"venues":  {"<key>": "<one-paragraph description of the venue and its readers>"},
   "members": {"<id>": {"cli": "codex" | "claude", "role": "referee" | "editor", "venue": "<key>",
                        "persona": "<referee persona; not used for editors>"}}}

Inputs : --draft         manuscript markdown (required unless --dump-config)
         --config        panel JSON (default: DEFAULT_PANEL)
         --outdir        where reviews go (default: docs/review/mock_<YYYYMMDD>/ under the working directory)
         --only          comma-separated member ids to (re)run (default: every member without a review)
         --claude-model  pin a model for `claude -p` (default: the CLI's own choice)
Outputs: <outdir>/<member>.md (review), <member>.stdin.md (brief + manuscript exactly as sent),
         <member>.log / <member>.err (CLI output), run.log
Needs  : `codex` on PATH (model/effort from ~/.codex/config.toml); `claude` on PATH for claude members.

Usage : python mock_review_panel.py --dump-config > docs/review/panel.json      # then edit venues/personas
        python mock_review_panel.py --draft drafts/<paper>.md --config docs/review/panel.json
        python mock_review_panel.py --draft drafts/<paper>.md --config docs/review/panel.json --only E1_applied_ai_editor
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

CODEX = shutil.which("codex") or "codex"
CLAUDE = shutil.which("claude") or "claude"
CLIS = ("codex", "claude")
ROLES = ("referee", "editor")

DEFAULT_PANEL = {
    "venues": {
        "ml_journal": (
            "a general machine-learning journal: the claims must be supported by clear, correct evidence, and the "
            "audience is ML researchers interested in methods, benchmarks and evaluation methodology."
        ),
        "finance_journal": (
            "a finance journal for data science in investment management. Readers are quantitative portfolio "
            "managers, asset-management researchers and finance academics. It favours economically meaningful, "
            "practically usable results net of costs and accessible exposition over ML machinery; heavy "
            "engineering detail belongs in an appendix or online supplement."
        ),
        "applied_ai_journal": (
            "an applied-AI journal that publishes intelligent systems with demonstrated application value. It "
            "expects a clearly delineated system contribution, rigorous comparison against sensible baselines, and "
            "evidence of practical significance; its editors reject a large share without review for weak fit, "
            "incremental novelty, or unclear presentation."
        ),
    },
    "members": {
        "R1_finance_quant": {
            "cli": "codex", "role": "referee", "venue": "finance_journal",
            "persona": "a senior quantitative portfolio manager turned academic referee; you care about economic "
                       "significance net of costs, overfitting and look-ahead control, whether the results would "
                       "change how a practitioner acts, and whether the paper is too long or too engineering-heavy "
                       "for this journal.",
        },
        "R2_applied_ai": {
            "cli": "codex", "role": "referee", "venue": "applied_ai_journal",
            "persona": "an applied-AI / intelligent-systems referee; you care about whether the system contribution "
                       "is clearly delineated from prior work, whether the experimental comparison (baselines, "
                       "ablations, statistical tests) is rigorous, and whether practical value is demonstrated "
                       "rather than asserted.",
        },
        "R3_ml_methodology": {
            "cli": "codex", "role": "referee", "venue": "ml_journal",
            "persona": "an evaluation-methodology specialist; you attack the construct validity of the metrics, "
                       "judge circularity and self-preference wherever a model scores outputs, seed counts and "
                       "multiple-comparison control, and whether a benchmark is a measurement instrument or a "
                       "leaderboard in disguise.",
        },
        "R4_claude_repro": {
            "cli": "claude", "role": "referee", "venue": "ml_journal",
            "persona": "a reproducibility- and statistics-minded referee; you check that every headline number in "
                       "the abstract resolves to a table or figure, that the appendices actually let someone rerun "
                       "the experiments, and that the limitations section names what the evidence cannot support.",
        },
        "E1_applied_ai_editor": {"cli": "codex", "role": "editor", "venue": "applied_ai_journal"},
        "E2_finance_editor": {"cli": "codex", "role": "editor", "venue": "finance_journal"},
    },
}

REFEREE = """You are an anonymous external referee for {venue}
The complete manuscript (markdown; figures are omitted but their captions and every table remain) is in the <stdin> block. Persona: {persona}

Review it as a demanding, fair, expert referee who reads the whole paper. Ground every criticism in the manuscript — pin each point to the section, table, or figure it concerns and quote a short phrase where useful. Do not re-summarize the paper beyond three sentences. Length: 1,000–1,600 words. Output plain markdown with EXACTLY these sections:

## Summary
Three sentences: what the paper claims, what evidence it offers, what its main contribution type is (method / system / benchmark / empirical finding).

## Recommendation
One of: Reject / Major revision / Minor revision / Accept — for THIS journal. Then one sentence: "As handling editor I would (send it to review | reject without review) because …".

## Scores (1–5; 5 = best)
- D1 Fit to this journal's scope and audience:
- D2 Novelty of contribution over cited and uncited prior work:
- D3 Technical soundness (design, statistics, judge validity, leakage control):
- D4 Strength of empirical validation (sample sizes, seeds, robustness, live evidence):
- D5 Clarity, organization, and appropriateness of length for this journal:
- D6 Significance to this journal's readers:
- D7 Reproducibility (artifacts, parameters, registry):
- Confidence (1–5):

## Main weaknesses (ranked, most damaging first)
Numbered. For each: location (§/Table/Figure), one-paragraph critique, severity (major/minor), and whether it is fixable by rewriting alone or needs new experiments.

## Strengths
Bullets, concrete.

## Questions for the authors
Numbered, answerable.

## What would move my recommendation up one level
At most five concrete, checkable requests.
"""

EDITOR = """You are the handling editor (an associate editor) of {venue}
It is triage day: forty new submissions, fifteen minutes for this one. You must decide whether to send it to external referees or reject it without review. The complete manuscript is in the <stdin> block. Read the title, abstract, introduction, contribution list, section headings and the conclusion carefully; skim the rest the way a busy editor does (tables of results, length, figure count, reference list, author signal). Be candid about the heuristics editors actually use — fit, length, whether the main result is visible early, whether the novelty claim survives a glance at the related-work table, presentation quality, and whether a referee could review it in a reasonable time.

Output plain markdown with EXACTLY these sections:

## Decision
"Send to review" or "Reject without review", plus your probability (0–100%) that a typical handling editor at this journal would send it out.

## The three decisive reasons
Numbered, one or two sentences each, in order of weight.

## First-impression checklist
One line each, with a yes/no and a short justification:
- Title conveys a result or only a system name?
- Abstract states the main finding within its first three sentences?
- Introduction reaches the contribution list within the first page?
- Length relative to this journal's typical paper (state your estimate of both)?
- Reads primarily as a finance paper, an AI-systems paper, a benchmark/methodology paper, or a software paper — and does that match this journal?
- Related-work table makes the novelty case in one glance?
- Does the prose carry machine-writing tells (spaced em dashes in most paragraphs, semicolon chains, arrows in sentences, "delve/underscores/notably") that make it look generated and unreviewed?
- Any red flags (language, unsupported claims, missing baselines, self-citation, anonymity leaks, preprint status)?

## What would flip the decision
At most five concrete changes (e.g. "cut to N pages by moving §X to a supplement", "retitle to state the finding", "lead the abstract with the main result"), most effective first.

## Cover-letter advice
Three to five sentences on what a cover letter to this journal's editor should say so that the paper survives triage.
"""

# GOTCHA (found 2026-09-17): a multi-paragraph argv prompt reaches Codex truncated at its first blank line,
# so the brief travels inside stdin ahead of the manuscript and argv carries only this pointer.
POINTER = "Follow the INSTRUCTIONS block at the top of the stdin text exactly, applied to the MANUSCRIPT block that follows it."


def validate_panel(panel: dict) -> dict:
    """Return `panel` unchanged if it is well formed; raise ValueError naming the first defect otherwise."""
    venues, members = panel.get("venues"), panel.get("members")
    if not isinstance(venues, dict) or not venues:
        raise ValueError("panel needs a non-empty 'venues' object")
    if not isinstance(members, dict) or not members:
        raise ValueError("panel needs a non-empty 'members' object")
    for mid, m in members.items():
        if m.get("cli") not in CLIS:
            raise ValueError(f"member {mid}: cli must be one of {CLIS}")
        if m.get("role") not in ROLES:
            raise ValueError(f"member {mid}: role must be one of {ROLES}")
        if m.get("venue") not in venues:
            raise ValueError(f"member {mid}: venue {m.get('venue')!r} is not in 'venues'")
        if m["role"] == "referee" and not m.get("persona"):
            raise ValueError(f"member {mid}: a referee needs a persona")
    return panel


def load_panel(path: str | None) -> dict:
    if not path:
        return validate_panel(DEFAULT_PANEL)
    return validate_panel(json.loads(Path(path).read_text(encoding="utf-8")))


def build_prompt(panel: dict, member: str) -> str:
    m = panel["members"][member]
    template = REFEREE if m["role"] == "referee" else EDITOR
    return template.format(venue=panel["venues"][m["venue"]], persona=m.get("persona", ""))


def build_command(cli: str, out: Path, claude_model: str | None = None) -> list[str]:
    if cli == "codex":
        return [CODEX, "exec", "--ephemeral", "-s", "read-only", "-o", str(out), POINTER]
    cmd = [CLAUDE, "-p", POINTER, "--output-format", "text"]
    if claude_model:
        # an old claude CLI can reject the long-context model it auto-picks for a long stdin; `claude update`
        # is the real fix, a pinned model is the stopgap
        cmd += ["--model", claude_model]
    return cmd


def pending_members(panel: dict, outdir: Path, only: str = "") -> list[str]:
    """Members to run: the --only list if given, else every member whose review is missing or empty."""
    if only:
        chosen = [m.strip() for m in only.split(",") if m.strip()]
        unknown = [m for m in chosen if m not in panel["members"]]
        if unknown:
            raise ValueError(f"unknown member ids: {unknown}")
        return chosen
    return [m for m in panel["members"]
            if not (outdir / f"{m}.md").exists() or (outdir / f"{m}.md").stat().st_size == 0]


def launch(panel: dict, member: str, draft: Path, outdir: Path, claude_model: str | None) -> subprocess.Popen:
    cli = panel["members"][member]["cli"]
    out = outdir / f"{member}.md"
    staged = outdir / f"{member}.stdin.md"
    staged.write_text("=== INSTRUCTIONS ===\n" + build_prompt(panel, member) + "\n\n=== MANUSCRIPT ===\n"
                      + draft.read_text(encoding="utf-8"), encoding="utf-8")
    # codex writes the review with -o and chatter to stdout; claude -p writes the review to stdout
    stdout_target = open(out if cli == "claude" else outdir / f"{member}.log", "w", encoding="utf-8")
    return subprocess.Popen(
        build_command(cli, out, claude_model),
        stdin=open(staged, encoding="utf-8"),
        stdout=stdout_target,
        stderr=open(outdir / f"{member}.err", "w", encoding="utf-8"),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a mock-review panel of coding-agent CLIs over a manuscript.")
    ap.add_argument("--draft")
    ap.add_argument("--config")
    ap.add_argument("--outdir", default=str(Path("docs") / "review" / f"mock_{date.today():%Y%m%d}"))
    ap.add_argument("--only", default="")
    ap.add_argument("--claude-model")
    ap.add_argument("--dump-config", action="store_true", help="print the default panel JSON and exit")
    args = ap.parse_args(argv)

    if args.dump_config:
        print(json.dumps(DEFAULT_PANEL, indent=2, ensure_ascii=False))
        return 0
    if not args.draft:
        ap.error("--draft is required")
    panel = load_panel(args.config)
    draft, outdir = Path(args.draft), Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    members = pending_members(panel, outdir, args.only)
    if not members:
        print("nothing to run — every member already has a review")
        return 0
    runnable = []
    for m in members:
        if panel["members"][m]["cli"] == "claude" and not shutil.which("claude"):
            print(f"skip {m}: claude CLI not on PATH")
        else:
            runnable.append(m)

    log = open(outdir / "run.log", "a", encoding="utf-8")
    t0 = time.time()
    running = {m: launch(panel, m, draft, outdir, args.claude_model) for m in runnable}
    msg = f"[{date.today()}] draft={draft.name} ({len(draft.read_text(encoding='utf-8').split())} words) members={runnable}"
    print(msg)
    log.write(msg + "\n")
    while running:
        for m, p in list(running.items()):
            if p.poll() is not None:
                out = outdir / f"{m}.md"
                ok = out.exists() and out.stat().st_size > 200
                msg = f"[{time.time() - t0:5.0f}s] done {m} exit={p.returncode} {'OK' if ok else 'NO OUTPUT'}"
                print(msg, flush=True)
                log.write(msg + "\n")
                log.flush()
                del running[m]
        time.sleep(10)
    print(f"all done in {time.time() - t0:.0f}s")
    log.write(f"all done in {time.time() - t0:.0f}s\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
