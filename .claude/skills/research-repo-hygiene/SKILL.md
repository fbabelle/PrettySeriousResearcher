---
name: research-repo-hygiene
description: Standing conventions for a research-paper project — layout, docs backups, changelog, drafts rotation, README/architecture upkeep, commit/PR rules, tests, memory.md policy. Consult when committing, scaffolding, or unsure of a convention.
---

# Research repo hygiene

The standing rules every phase follows for repo structure and process. This is a **reference** skill — consulted, not run. The full spec (layout, every rule, the `.gitignore`) is in [references/conventions.md](references/conventions.md); read it when scaffolding the repo or when a convention is in question. The essentials:

## Layout (what goes where)

`docs/plans/` (timestamped plan backups) · `docs/changelogs.md` (append-only change log) · `docs/tracking/` (effort/cost ledgers) · `docs/local-env.md` (probed host + supplier limits) · `docs/claims-ledger.md` (claim→evidence rows) · `docs/venue-profile.md` (early venue-as-input profile) · `docs/venues.md` (late deadline-feasible venue plan) · `docs/review/` (pre-submission `research-mock-review` packets) · `docs/submission/` (staged portal forms + response drafts) · `drafts/` (versioned paper drafts) · `src/` `experiments/` `runs/` `tests/` (code, lazy per phase) · root `README.md` (quickstart) · `architecture.md` (design + project charter) · `memory.md` (untracked user patterns). Cross-cutting infra is scaffolded up front; code dirs and the venue/review artifacts are created lazily when their phase arrives.

## The rules that bite most often

- **Plans** → back up to `docs/plans/plan-YYYYMMDD-HHMMSS.md` before executing; that backup also triggers a `research-tracking` effort+cost report.
- **Changelog** → every change gets a dated what+why entry in `docs/changelogs.md`.
- **Drafts** → `vNN-title.md`; **start a new draft when an effort chunk exceeds ~5 agent-active hours**; periodically move superseded drafts to the gitignored `drafts/_archive/`.
- **README/architecture** → updated less often, but kept accurate; `architecture.md` also holds the Phase-1 project charter.
- **Commits** → by **feature, not hours**; **commit when the user changes subject**; **auto-push**; **PR to main only on explicit request**; **no co-author/generated-by footer**. Use a `research/<paper-slug>/<feature>` branch in the monorepo, never the shared default branch directly.
- **Tests** → ship with all new code, tracked and committed, and **must pass after major changes** (enforced by `research-code-review`).
- **A commit's diff must contain what its message claims** → after a scripted or anchored patch, check the target line is actually in `git diff` before committing (earned: a patch whose anchor silently failed produced a commit carrying the fix's message but not its code; the follow-up commit had to say so). Gate commits on the test runner's **exit code**, never on a parsed log line — an unwritable log path once produced a false "suite red" and an unverified state.
- **Python env** → managed by **`uv`**; committed `pyproject.toml` + `uv.lock`, Python **3.12** by default (`.python-version` + `requires-python>=3.12`); run code via `uv run` (`.venv/` gitignored). Skill-set utilities like `track.py` are stdlib-only and run under plain `python3`. Note: **`uv init` creates a git repo automatically** when none exists — check `.git` before running `git init` yourself. (full rules in the reference)
- **memory.md** → untracked; rolling user summary on top + dated specifics below; skills win on *methodology*, memory wins on the user's *explicit choices* (full priority rule in the reference).
- **Secrets** → the moment a secrets file (`.env`, token files) appears in the tree, run `git check-ignore -v` on it — the scaffold's `.gitignore` may predate it (earned: a `.env` holding an API key sat un-ignored). Never commit it; non-secret selection lines may live beside the secret only once the file is confirmed ignored, and the decision they encode is recorded in a tracked doc. When *probing* a credential (does this token unlock tier X?), read it in code and print only masked results — a value echoed by `grep`/`cat` lands in the session transcript, and any secret that reached a transcript is rotated, not hoped about.
- **ADR changes ripple** → when a decision record changes a mechanism, grep every doc (both languages, diagrams, symbol tables) for the *old narrative* and fix it in the same commit — a superseded sentence surviving in three places is an internal contradiction a reviewer will find (the global-impact rule: find every consumer before changing shared logic).
- **Compiled expository artefacts are docs** → a PDF built from a `.tex` (lecture notes, tutorials) drifts silently when only the markdown moves; list such artefacts in the project rules, rebuild them in the **same commit** as the ADR that changes the theory or architecture, and git-ignore the build by-products (`.aux/.log/.out/.toc`), never the PDF (earned: notes were three architecture versions behind until the user asked).
- **Source vs install — skill edits go through the evolution channel** → this skill set is authored/maintained in its **source project** and installed into paper projects. Ad-hoc mid-task edits to `.claude/skills/**` are still prohibited; the **sanctioned path** is `research-skill-evolution` (user-configured, hook-triggered): incremental, logged (`docs/tracking/skill-evolution-log.md`), committed passes. If a source project exists, **sync evolution edits upstream** after each pass — otherwise the next reinstall clobbers them.

- **Never delete committed run artefacts to re-run them.** Re-run beside them into new directories, verify identity against the committed originals file by file (a receipt: N/N byte-identical), and let the owner decide whether the new set replaces the old — a delete-and-rerun script was rightly blocked (2026-09-10).
- **Never patch source through a shell heredoc.** Escape sequences (`\\n`) and quotes are re-interpreted by the shell and by the interpreter, and the failure is silent until a syntax error surfaces in an unrelated test (earned twice on 2026-09-07: an f-string split across four lines). Write the patch as a script file with the editor tool, run it, and assert each anchor occurs exactly once before replacing.

## Cross-references

- **research-paper** — orchestrator; bootstraps this layout on first run and follows the commit/plan rules.
- **research-tracking** — owns `docs/tracking/`; its report rides on the `docs/plans/` backup trigger defined here.
- **research-writing** — applies the `drafts/` versioning/rotation rules.
- **research-code-review** — enforces the test discipline named here.
