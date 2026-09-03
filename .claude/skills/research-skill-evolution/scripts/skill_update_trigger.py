"""Skill-evolution trigger hook (UserPromptSubmit + PreCompact) for Claude Code.

Purpose: fire the research-skill-evolution procedure (a) every INTERVAL user prompts since
the last skill update, or (b) on the first prompt after an auto-compaction warning fired
(PreCompact = context/usage nearly exhausted, the "10% left" proxy).

Input:  hook JSON on stdin (hook_event_name distinguishes the two events).
Output: on UserPromptSubmit when triggered — JSON with hookSpecificOutput.additionalContext
        instructing the agent to invoke the research-skill-evolution skill. Otherwise silent.
State:  <project>/docs/tracking/.skill-evolution-state.json (git-ignored)
        {round_count, last_update_round, last_update_commit, last_update_time,
         pending_usage_trigger}
Project root: $CLAUDE_PROJECT_DIR when set (Claude Code exports it to hooks); otherwise the
        nearest ancestor of this file that contains a `.claude/` directory — so the script
        works both from `.claude/skills/research-skill-evolution/scripts/` (installed layout)
        and from a project-level `.claude/hooks/` copy.
Config: SKILL_EVOLUTION_INTERVAL env var overrides the 10-prompt cadence (tests use it).

Register in .claude/settings.json (install_skills.py --with-scaffold writes/merges this):
    {"hooks": {
      "UserPromptSubmit": [{"hooks": [{"type": "command", "timeout": 15,
        "command": "python .claude/skills/research-skill-evolution/scripts/skill_update_trigger.py"}]}],
      "PreCompact":       [{"hooks": [{"type": "command", "timeout": 15,
        "command": "python .claude/skills/research-skill-evolution/scripts/skill_update_trigger.py"}]}]}}

Usage (manual test):
    echo '{"hook_event_name":"UserPromptSubmit"}' | python .claude/skills/research-skill-evolution/scripts/skill_update_trigger.py
"""

import json
import os
import sys
from pathlib import Path

INTERVAL = int(os.environ.get("SKILL_EVOLUTION_INTERVAL", "10"))

DEFAULT_STATE = {
    "round_count": 0,
    "last_update_round": 0,
    "last_update_commit": None,
    "last_update_time": None,
    "pending_usage_trigger": False,
}


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".claude").is_dir():
            return parent
    return here.parents[4] if len(here.parents) > 4 else here.parent


def state_path() -> Path:
    return project_root() / "docs" / "tracking" / ".skill-evolution-state.json"


def load_state() -> dict:
    try:
        state = json.loads(state_path().read_text(encoding="utf-8"))
        return {**DEFAULT_STATE, **state}
    except Exception:
        return dict(DEFAULT_STATE)


def save_state(state: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    event = payload.get("hook_event_name", "")
    state = load_state()

    if event == "PreCompact":
        state["pending_usage_trigger"] = True
        save_state(state)
        return

    # UserPromptSubmit (default path)
    state["round_count"] += 1
    rounds_since = state["round_count"] - state["last_update_round"]
    triggered = rounds_since >= INTERVAL or state["pending_usage_trigger"]
    save_state(state)

    if triggered:
        reason = (
            f"{rounds_since} user rounds since the last skill update"
            if rounds_since >= INTERVAL
            else "context/usage nearly exhausted (PreCompact fired)"
        )
        context = (
            f"[skill-evolution hook] Trigger: {reason}. After completing the user's "
            "current request in this turn, invoke the `research-skill-evolution` skill: "
            "review ONLY the increment since the last update (conversation since round "
            f"{state['last_update_round']}, plus `git diff {state['last_update_commit'] or '<initial>'}..HEAD` "
            "and uncommitted changes for docs/drafts/src/architecture.md), distill "
            "methodology lessons, apply targeted edits to .claude/skills/, log to "
            "docs/tracking/skill-evolution-log.md, and reset the state file. If the "
            "current turn is itself heavy, it is acceptable to run the update at the "
            "start of the NEXT turn instead - but do not skip it twice."
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }))


if __name__ == "__main__":
    main()
