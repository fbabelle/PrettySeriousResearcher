# Authoring SKILL.md (limits & best practices)

Reference for writing/maintaining the skills in `.claude/skills/`. **This is a skill-source-project doc — it lives outside `.claude/skills/` on purpose, so `install_skills.py` does not ship it into paper projects.** Authoring/maintaining skills happens here in the source project (`PrettySeriousResearcher`); a paper project that merely *uses* the installed skills must never edit them — that diverges from source, so improve upstream and reinstall. The **official docs are the source of truth** — this file records the numbers that bite and the project's own rule, then links out. Limits change (see the version history below), so verify against the links rather than trusting a copied number.

## Official docs (read these first)

- **Claude Code skills** — frontmatter, invocation control, the skill-listing budget: https://code.claude.com/docs/en/skills
- **Skill authoring best practices** — descriptions, progressive disclosure, the authoring loop: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- **Agent Skills overview** — structure + the validated field limits: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- **Claude.ai custom skills (upload)** — the stricter 200-char surface: https://claude.com/docs/skills/how-to
- **Claude Code settings** — `skillListingMaxDescChars`, `skillListingBudgetFraction`: https://code.claude.com/docs/en/settings
- **Agent Skills open standard** (cross-tool): https://agentskills.io

## Field limits by surface (verify against the links)

| Field | Surface | Limit | On exceed |
|---|---|---|---|
| `name` | all | **64 chars**; lowercase/digits/hyphens; must match the directory name; no XML tags; no reserved words (`anthropic`, `claude`) | rejected |
| `description` | Agent Skills spec / API / platform | **1,024 chars** (non-empty, no XML tags) | rejected at validation |
| `description` | **claude.ai** upload | **200 chars** | rejected on upload |
| `description` | **Claude Code** (current) | per-desc `skillListingMaxDescChars` **1,536**, then total `skillListingBudgetFraction` **1%** of the context window | over 1,536 → that desc trimmed; total over budget → lowest-priority skills' descriptions dropped whole (by recency/frequency), not truncated |
| `description` | Claude Code (historical, ~v2.1.86) | **250 chars** per desc | silently truncated; **superseded** by the 1,536+budget scheme ~v2.1.129 |

**Why the confusion exists:** "200" is real but is the *claude.ai upload* limit; "1,024" is the *spec/API* limit; Claude Code uses a *budget* model with a 1,536 per-desc cap; and a transient 250-char cap existed for a few versions. There is no single universal number — it depends on where the skill runs.

## Project rule (what we actually do here)

- **`description` ≤ 250 characters.** This survives every Claude Code regime (including the old 250-char cap), sits far under the 1,024 spec max, and roughly halves the standing context cost of the always-loaded skill listing. (If a skill will ever be uploaded to claude.ai, trim it to **≤ 200**.)
- **Front-load the trigger.** Lead with what the skill does, then a concrete *"Use when …"* clause — the keywords Claude routes on must come early, because trimming/budget pressure eats the tail first.
- **Third person, no first/second person.** "Verify each citation …", not "I can verify …" / "You can use this to …". The description is injected into the system prompt; mixed point-of-view hurts discovery.
- **Keep orchestration out of the description.** "Invoked by X / delegates to Y / owns file Z" is internal wiring, not a discovery trigger — put it in the SKILL.md body's **Cross-references** section, not the frontmatter.
- **Body:** keep SKILL.md under ~500 lines; push detail into `references/*.md` one level deep; consistent terminology; no time-sensitive phrasing (link, don't hardcode, things that drift).

## Verify before committing a skill

```bash
# longest description, in characters (target <= 250)
for f in .claude/skills/*/SKILL.md; do
  d=$(awk '/^---$/{n++;next} n==1 && sub(/^description: /,""){print;exit}' "$f")
  printf '%4d  %s\n' "$(printf '%s' "$d" | wc -m)" "$(dirname "$f" | xargs basename)"
done | sort -rn
```

`/doctor` (in Claude Code) reports which descriptions are being shortened or dropped under the live budget. `python install_skills.py --check-only` lints the set for absolute paths / secrets before it can be shared.
