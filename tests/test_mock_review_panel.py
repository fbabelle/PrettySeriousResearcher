#!/usr/bin/env python3
"""Tests for research-mock-review/scripts/mock_review_panel.py — panel config validation, prompt and
command construction, and member selection. No CLI is launched.

Run: python tests/test_mock_review_panel.py        (stdlib unittest; no third-party deps)
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL_PY = os.path.join(REPO, ".claude", "skills", "research-mock-review", "scripts", "mock_review_panel.py")


def _load():
    spec = importlib.util.spec_from_file_location("mock_review_panel", PANEL_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


panel_mod = _load()


class PanelConfig(unittest.TestCase):
    def test_default_panel_is_valid_and_has_both_roles(self):
        panel = panel_mod.load_panel(None)
        roles = {m["role"] for m in panel["members"].values()}
        self.assertEqual(roles, {"referee", "editor"})

    def test_default_panel_names_no_real_venue(self):
        text = json.dumps(panel_mod.DEFAULT_PANEL)
        for name in ("TMLR", "Expert Systems", "Journal of Financial Data Science", "Financial Innovation"):
            self.assertNotIn(name, text)

    def test_invalid_panels_are_rejected(self):
        base = copy.deepcopy(panel_mod.DEFAULT_PANEL)
        bad_venue = copy.deepcopy(base)
        bad_venue["members"]["R1_finance_quant"]["venue"] = "nowhere"
        no_persona = copy.deepcopy(base)
        del no_persona["members"]["R1_finance_quant"]["persona"]
        bad_cli = copy.deepcopy(base)
        bad_cli["members"]["R1_finance_quant"]["cli"] = "gpt"
        for panel in (bad_venue, no_persona, bad_cli, {"venues": {}, "members": {}}):
            with self.assertRaises(ValueError):
                panel_mod.validate_panel(panel)

    def test_config_file_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "panel.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(panel_mod.main(["--dump-config"]), 0)
            p.write_text(buf.getvalue(), encoding="utf-8")
            self.assertEqual(panel_mod.load_panel(str(p)), panel_mod.DEFAULT_PANEL)


class PromptsAndCommands(unittest.TestCase):
    def setUp(self):
        self.panel = panel_mod.load_panel(None)

    def test_referee_prompt_carries_venue_persona_and_rubric(self):
        prompt = panel_mod.build_prompt(self.panel, "R1_finance_quant")
        self.assertIn(self.panel["venues"]["finance_journal"], prompt)
        self.assertIn("quantitative portfolio manager", prompt)
        self.assertIn("## Scores (1–5; 5 = best)", prompt)

    def test_editor_prompt_is_a_triage_brief(self):
        prompt = panel_mod.build_prompt(self.panel, "E2_finance_editor")
        self.assertIn("reject it without review", prompt)
        self.assertIn("machine-writing tells", prompt)

    def test_codex_command_writes_review_with_o_and_passes_one_line_pointer(self):
        cmd = panel_mod.build_command("codex", Path("out.md"))
        self.assertIn("-o", cmd)
        self.assertEqual(cmd[-1], panel_mod.POINTER)
        self.assertNotIn("\n", cmd[-1])

    def test_claude_model_pin_is_optional(self):
        self.assertNotIn("--model", panel_mod.build_command("claude", Path("o.md")))
        cmd = panel_mod.build_command("claude", Path("o.md"), "some-model")
        self.assertEqual(cmd[cmd.index("--model") + 1], "some-model")


class MemberSelection(unittest.TestCase):
    def test_only_members_without_a_non_empty_review_run(self):
        panel = panel_mod.load_panel(None)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "R1_finance_quant.md").write_text("a review", encoding="utf-8")
            (out / "R2_applied_ai.md").write_text("", encoding="utf-8")
            todo = panel_mod.pending_members(panel, out)
            self.assertNotIn("R1_finance_quant", todo)
            self.assertIn("R2_applied_ai", todo)
            self.assertEqual(panel_mod.pending_members(panel, out, "R1_finance_quant"), ["R1_finance_quant"])
            with self.assertRaises(ValueError):
                panel_mod.pending_members(panel, out, "R9_nobody")


if __name__ == "__main__":
    unittest.main()
