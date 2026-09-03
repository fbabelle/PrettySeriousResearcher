"""Contracts for the research-skill-evolution hook and its scaffold wiring.

- the hook script counts prompts under the project root it discovers (walk-up from the
  skill's scripts/ dir, or $CLAUDE_PROJECT_DIR), stays silent before the interval, emits
  additionalContext at the interval, and honours the PreCompact usage flag;
- install_skills.scaffold() registers the hook in .claude/settings.json for the Claude
  target only, merging into an existing file idempotently, and git-ignores the state file.

Run: uv run pytest tests/test_skill_evolution_hook.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import install_skills  # noqa: E402

HOOK_SRC = ROOT / ".claude" / "skills" / "research-skill-evolution" / "scripts" / "skill_update_trigger.py"


def _fire(hook: Path, event: str, cwd: Path, extra_env: dict | None = None) -> str:
    env = {**os.environ, "SKILL_EVOLUTION_INTERVAL": "3"}
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.update(extra_env or {})
    r = subprocess.run([sys.executable, str(hook)], input=json.dumps({"hook_event_name": event}),
                       capture_output=True, text=True, env=env, cwd=str(cwd))
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


class HookScript(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-evo-"))
        self.proj = self.tmp / "proj"
        scripts = self.proj / ".claude" / "skills" / "research-skill-evolution" / "scripts"
        scripts.mkdir(parents=True)
        self.hook = scripts / HOOK_SRC.name
        shutil.copy(HOOK_SRC, self.hook)
        self.state = self.proj / "docs" / "tracking" / ".skill-evolution-state.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_counts_under_discovered_root_and_triggers_at_interval(self):
        self.assertEqual(_fire(self.hook, "UserPromptSubmit", self.tmp), "")
        self.assertEqual(_fire(self.hook, "UserPromptSubmit", self.tmp), "")
        self.assertEqual(json.loads(self.state.read_text(encoding="utf-8"))["round_count"], 2)
        out = json.loads(_fire(self.hook, "UserPromptSubmit", self.tmp))
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("research-skill-evolution", ctx)
        self.assertIn("3 user rounds", ctx)

    def test_precompact_flag_triggers_next_prompt(self):
        _fire(self.hook, "UserPromptSubmit", self.tmp)
        self.assertEqual(_fire(self.hook, "PreCompact", self.tmp), "")
        self.assertTrue(json.loads(self.state.read_text(encoding="utf-8"))["pending_usage_trigger"])
        self.assertIn("PreCompact fired", _fire(self.hook, "UserPromptSubmit", self.tmp))

    def test_claude_project_dir_overrides_discovery(self):
        other = self.tmp / "other"
        other.mkdir()
        _fire(self.hook, "UserPromptSubmit", self.tmp, {"CLAUDE_PROJECT_DIR": str(other)})
        self.assertTrue((other / "docs" / "tracking" / ".skill-evolution-state.json").exists())
        self.assertFalse(self.state.exists())


class ScaffoldWiring(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-evo-scaffold-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def _hook_commands(settings: dict) -> dict:
        return {ev: [h["command"] for e in entries for h in e["hooks"]]
                for ev, entries in settings["hooks"].items()}

    def test_claude_scaffold_registers_hook_and_ignores_state(self):
        install_skills.scaffold(self.tmp, force=False, target="claude", tracking_command="python track.py")
        settings = json.loads((self.tmp / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmds = self._hook_commands(settings)
        for ev in ("UserPromptSubmit", "PreCompact"):
            self.assertEqual(cmds[ev], [install_skills.HOOK_COMMAND])
        self.assertIn("docs/tracking/.skill-evolution-state.json",
                      (self.tmp / ".gitignore").read_text(encoding="utf-8"))
        self.assertTrue((self.tmp / "docs" / "tracking" / "skill-evolution-log.md").exists())
        self.assertIn("research-skill-evolution", (self.tmp / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_scaffold_merges_into_existing_settings_idempotently(self):
        cdir = self.tmp / ".claude"
        cdir.mkdir()
        existing = {"permissions": {"allow": ["Bash(ls:*)"]},
                    "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}}
        (cdir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")
        install_skills.scaffold(self.tmp, force=False, target="claude", tracking_command="x")
        install_skills.scaffold(self.tmp, force=False, target="claude", tracking_command="x")
        settings = json.loads((cdir / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["permissions"], existing["permissions"])
        cmds = self._hook_commands(settings)
        self.assertEqual(cmds["UserPromptSubmit"], ["echo hi", install_skills.HOOK_COMMAND])
        self.assertEqual(cmds["PreCompact"], [install_skills.HOOK_COMMAND])

    def test_invalid_settings_json_is_left_untouched(self):
        cdir = self.tmp / ".claude"
        cdir.mkdir()
        (cdir / "settings.json").write_text("{not json", encoding="utf-8")
        install_skills.scaffold(self.tmp, force=False, target="claude", tracking_command="x")
        self.assertEqual((cdir / "settings.json").read_text(encoding="utf-8"), "{not json")

    def test_non_claude_scaffold_writes_no_settings(self):
        install_skills.scaffold(self.tmp, force=False, target="codex", tracking_command="x")
        self.assertFalse((self.tmp / ".claude").exists())
        self.assertIn("docs/tracking/.skill-evolution-state.json",
                      (self.tmp / ".gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
