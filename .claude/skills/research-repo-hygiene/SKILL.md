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
- **Python env** → managed by **`uv`**; committed `pyproject.toml` + `uv.lock`, Python **3.12** by default (`.python-version` + `requires-python>=3.12`); run code via `uv run` (`.venv/` gitignored). Skill-set utilities like `track.py` are stdlib-only and run under plain `python3`. (full rules in the reference)
- **memory.md** → untracked; rolling user summary on top + dated specifics below; skills win on *methodology*, memory wins on the user's *explicit choices* (full priority rule in the reference).
- **Source vs install — don't self-edit the skills** → this skill set is authored/maintained in its **source project** and installed **read-only** into paper projects. While building a *paper*, do not edit the skill files (`.claude/skills/**`) — that diverges from source and the next reinstall will clobber/conflict; fix the skill **upstream** in the source project and reinstall instead. (Authoring the skills themselves is a source-project task, documented there, not part of paper work.)

## Cross-references

- **research-paper** — orchestrator; bootstraps this layout on first run and follows the commit/plan rules.
- **research-tracking** — owns `docs/tracking/`; its report rides on the `docs/plans/` backup trigger defined here.
- **research-writing** — applies the `drafts/` versioning/rotation rules.
- **research-code-review** — enforces the test discipline named here.
