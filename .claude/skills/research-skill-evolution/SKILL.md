---
name: research-skill-evolution
description: Incremental self-improvement of the research skill set: review only the increment since the last pass, distill methodology lessons, apply targeted logged skill edits. Use when the skill-evolution hook fires or the user asks to update the skills.
---

# Research skill evolution (incremental)

Keeps the research skills practically sharp by folding what actually happened — decisions,
failures, workarounds, user feedback — back into the skill files. **Incremental by
design**: each pass examines only what changed since the previous pass, so cost stays
bounded and lessons are captured while fresh.

## Trigger & state

Fired by this skill's own hook script, `scripts/skill_update_trigger.py`, registered in
`.claude/settings.json` on the `UserPromptSubmit` and `PreCompact` events (the installer's
`--with-scaffold` writes or merges that registration; the script's docstring carries the
snippet for a manual setup): every 10 user prompts since the last update, or on the first
prompt after PreCompact (context nearly exhausted). Hooks are a Claude Code feature — on
other hosts, invoke this skill by hand at the same cadence. State:
`docs/tracking/.skill-evolution-state.json` (git-ignored) — `round_count`,
`last_update_round`, `last_update_commit`, `last_update_time`, `pending_usage_trigger`.

## The incremental procedure

1. **Define the increment.** Read the state file.
   - *Documents*: `git log --oneline <last_update_commit>..HEAD` and
     `git diff --stat <last_update_commit>..HEAD -- docs/ drafts/ src/ experiments/ tests/ architecture.md`
     plus `git status --short` for uncommitted changes. If `last_update_commit` is null,
     treat the whole history as the increment (first run).
   - *Conversation*: everything in the current context since round `last_update_round`
     (the in-context conversation IS the conversation increment — cross-session history
     is already reflected in the committed documents, so no transcript archaeology).
2. **Distill lessons — filter hard.** A lesson qualifies only if it is (a) *general
   methodology* (would help the NEXT paper/project, not just this one), and (b) *earned*
   (came from something that actually happened: a failure, a reversal, a verified
   surprise, explicit user feedback on process). Route everything else:
   - user-specific preferences → root `memory.md`, NOT skills;
   - project-specific facts → `architecture.md`/changelog, NOT skills;
   - one-off trivia → nowhere.
3. **Map lessons to skills.** For each lesson name the ONE skill file (occasionally two)
   whose future reader would act differently. Prefer **small targeted edits** (a
   sentence, a bullet, a caveat in an existing section) over new sections; never bloat a
   skill with narrative. If a lesson fits no existing skill and is big enough, propose a
   new skill to the user rather than silently creating one.
4. **Apply the edits.** Edit the skill files directly. Keep each skill's voice and
   structure; additions must read as if originally written there.
5. **Log the pass.** Append to `docs/tracking/skill-evolution-log.md`: date, trigger
   (rounds/usage), increment summary (commits covered, conversation span), lessons
   applied (skill → one-line change), lessons REJECTED and why (prevents re-litigating
   the same candidates every pass — the anti-churn memory).
6. **Reset state.** Write the state file: `last_update_round = round_count`,
   `last_update_commit = HEAD` (after committing the skill edits),
   `pending_usage_trigger = false`, `last_update_time = now`.
7. **Commit** the skill edits + log as one feature commit ("Skill evolution: <n> lessons
   from <span>").
8. **Sync upstream.** If the skill set has a source project, open a PR there with the
   diffed skill files (its contract tests and secrets/abs-path lint must pass; strip any
   project-specific residue first). Unsynced evolution edits are clobbered by the next
   reinstall.

## Guardrails

- **Anti-tilt (shared with research-reflection):** "no qualifying lessons in this
  increment" is a legitimate outcome — log it and reset the counter; do not manufacture
  edits to justify the pass.
- **Don't rewrite, accrete.** Wholesale skill rewrites are user-approved changes, not
  evolution passes. If a skill seems structurally wrong, propose it in the log and ask.
- **Skills stay general.** The moment an edit mentions this paper's specifics (a
  particular estimator, a particular index or dataset, a particular venue's date),
  reconsider — the general form of the lesson is what belongs ("verify track-level
  desk-reject rules", not "venue X rejected us").
- **Bounded cost.** One pass ≈ one focused turn. If the increment is huge (e.g. first
  run), cap at the ~5–8 highest-value lessons and note the cut in the log.

## Cross-references

- **research-reflection** — sibling mechanism: reflection challenges the *research*;
  this skill evolves the *process*. Reflection outcomes are prime lesson sources.
- **research-repo-hygiene** — commit conventions for the evolution commits.
- **memory.md (root)** — destination for user-specific patterns rejected in step 2.
