#!/usr/bin/env python3
"""Tests for research-tracking/scripts/track.py — transcript-directory discovery
(portable across OSes) and the cost-model split between the coding-agent
subscription (fixed, not gated) and metered experiment LLM spend.

Run: python tests/test_track.py        (stdlib unittest; no third-party deps)
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACK_PY = os.path.join(REPO, ".claude", "skills", "research-tracking", "scripts", "track.py")


def _load_track():
    spec = importlib.util.spec_from_file_location("track", TRACK_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


track = _load_track()

RATE = {"llm": {"claude-opus-4-8": {"in": 5.0, "out": 25.0,
                                    "cache_write_5m": 6.25, "cache_write_1h": 10.0,
                                    "cache_read": 0.5}}}


def _sess(start_iso):
    # minimal session shape used by months_active (needs only "start" epoch)
    return {"start": track.parse_ts(start_iso)}


class EncodeCwd(unittest.TestCase):
    """The encoding must be host-independent: a Windows path encodes the same way
    whether these tests run on Windows or POSIX."""

    def test_posix_path(self):
        self.assertEqual(track.encode_cwd("/home/x/papers/alpha"), "-home-x-papers-alpha")

    def test_windows_path_lowercases_drive_and_drops_colon(self):
        self.assertEqual(track.encode_cwd(r"C:\Papers\Alpha"), "c--Papers-Alpha")

    def test_result_is_always_a_bare_directory_name(self):
        for path in ("/home/x/proj", r"C:\Projects\proj", r"D:/mixed/sep\proj"):
            enc = track.encode_cwd(path)
            self.assertFalse(os.path.isabs(enc), path)
            self.assertNotIn("/", enc)
            self.assertNotIn("\\", enc)


class FindTranscriptDir(unittest.TestCase):
    def test_override_must_exist(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(track.find_transcript_dir(d, d), d)
            self.assertIsNone(track.find_transcript_dir(d, os.path.join(d, "nope")))

    def test_finds_encoded_dir_under_config_root(self):
        with tempfile.TemporaryDirectory() as d:
            proj = os.path.join(d, "proj")
            os.makedirs(proj)
            cfg = os.path.join(d, "cfg")
            tdir = os.path.join(cfg, "projects", track.encode_cwd(os.path.abspath(proj)))
            os.makedirs(tdir)
            open(os.path.join(tdir, "session.jsonl"), "w").close()
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": cfg}):
                self.assertEqual(track.find_transcript_dir(proj, None), tdir)

    def test_never_resolves_to_the_project_root(self):
        """Regression: on Windows the encoded name stayed an absolute path, so
        os.path.join(config, 'projects', enc) discarded the prefix and returned
        the repo itself. Its docs/tracking/effort.jsonl satisfied the *.jsonl
        guard, and track.py reported 0 hours / 0 tokens as if measured instead
        of printing the /cost fallback."""
        with tempfile.TemporaryDirectory() as d:
            proj = os.path.join(d, "proj")
            os.makedirs(os.path.join(proj, "docs", "tracking"))
            open(os.path.join(proj, "docs", "tracking", "effort.jsonl"), "w").close()
            cfg = os.path.join(d, "cfg")
            os.makedirs(cfg)
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": cfg}):
                self.assertIsNone(track.find_transcript_dir(proj, None))


class MonthsActive(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(track.months_active([], None), 0.0)

    def test_distinct_calendar_months(self):
        s = [_sess("2026-06-10T00:00:00Z"), _sess("2026-06-28T00:00:00Z"),
             _sess("2026-07-02T00:00:00Z")]
        self.assertEqual(track.months_active(s, None), 2.0)  # Jun + Jul

    def test_override_wins(self):
        s = [_sess("2026-06-10T00:00:00Z")]
        self.assertEqual(track.months_active(s, 3), 3.0)


class CodingExpense(unittest.TestCase):
    def test_unconfigured(self):
        usd, configured = track.coding_expense({"agents": [{"name": None, "usd_per_month": None}]}, 5)
        self.assertEqual(usd, 0.0)
        self.assertFalse(configured)

    def test_single_agent(self):
        usd, configured = track.coding_expense(
            {"agents": [{"name": "Claude Code", "usd_per_month": 200, "share_pct": 100}]}, 2)
        self.assertEqual(usd, 400.0)
        self.assertTrue(configured)

    def test_share_and_multi(self):
        cfg = {"agents": [{"usd_per_month": 200, "share_pct": 100},
                          {"usd_per_month": 20, "share_pct": 50}]}
        usd, configured = track.coding_expense(cfg, 1)  # 200 + 10 = 210
        self.assertEqual(usd, 210.0)
        self.assertTrue(configured)


class ExperimentCost(unittest.TestCase):
    def test_usd_override_trusted(self):
        rows = [{"model": "x", "tok": {"in": 0, "out": 0, "cw5": 0, "cw1": 0, "cr": 0}, "usd": 1.23}]
        usd, toks, warns = track.experiment_cost(rows, RATE)
        self.assertEqual(usd, 1.23)
        self.assertEqual(warns, [])

    def test_priced_from_rate_card(self):
        # 1M in @5 + 1M out @25 = $30
        rows = [{"model": "claude-opus-4-8",
                 "tok": {"in": 1_000_000, "out": 1_000_000, "cw5": 0, "cw1": 0, "cr": 0},
                 "usd": None}]
        usd, toks, warns = track.experiment_cost(rows, RATE)
        self.assertAlmostEqual(usd, 30.0, places=4)
        self.assertEqual(toks, 2_000_000)

    def test_unknown_model_warns_zero(self):
        rows = [{"model": "mystery", "tok": {"in": 1000, "out": 0, "cw5": 0, "cw1": 0, "cr": 0}, "usd": None}]
        usd, toks, warns = track.experiment_cost(rows, RATE)
        self.assertEqual(usd, 0.0)
        self.assertTrue(any("unpriced" in w for w in warns))


class LoadUsageAliases(unittest.TestCase):
    def test_field_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            runs = os.path.join(d, "runs")
            os.makedirs(runs)
            with open(os.path.join(runs, "usage.jsonl"), "w") as fh:
                fh.write(json.dumps({"model": "m", "input_tokens": 10, "output_tokens": 5}) + "\n")
                fh.write(json.dumps({"model": "m", "in": 1, "out": 2, "cache_read": 7}) + "\n")
            rows = track.load_experiment_usage(d)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["tok"]["in"], 10)
        self.assertEqual(rows[0]["tok"]["out"], 5)
        self.assertEqual(rows[1]["tok"]["cr"], 7)


class IntegrationCapExcludesCoding(unittest.TestCase):
    """End-to-end: coding plan/metered overhead must not enter the experiment cap."""

    def test_json_split(self):
        with tempfile.TemporaryDirectory() as d:
            tdir = os.path.join(d, "docs", "tracking")
            os.makedirs(tdir)
            cost = {
                "status": "finalized",
                "coding_agent": {
                    "agents": [{"name": "Claude Code", "usd_per_month": 100, "share_pct": 100}],
                    "months_active_override": 2,
                },
                "budget": {"total_cap": 50, "by_category": {"llm_api": 50, "compute": 0, "data": 0}},
                "rate_card": RATE,
                "actuals": [{"category": "data", "usd": 10},
                            {"category": "coding_agent", "usd": 7},
                            {"category": "publication", "usd": 30}],
            }
            with open(os.path.join(tdir, "cost.json"), "w") as fh:
                json.dump(cost, fh)
            with open(os.path.join(tdir, "state.json"), "w") as fh:
                json.dump({"phase_windows": []}, fh)
            runs = os.path.join(d, "runs")
            os.makedirs(runs)
            with open(os.path.join(runs, "usage.jsonl"), "w") as fh:
                fh.write(json.dumps({"model": "claude-opus-4-8",
                                     "in": 1_000_000, "out": 0}) + "\n")  # $5

            out = subprocess.check_output(
                [sys.executable, TRACK_PY, "--project-root", d, "--json",
                 "--transcript-dir", os.path.join(d, "nonexistent")],
                stderr=subprocess.DEVNULL).decode()
            res = json.loads(out)

        self.assertAlmostEqual(res["exp_llm_usd"], 5.0, places=2)
        self.assertAlmostEqual(res["data_usd"], 10.0, places=2)
        self.assertAlmostEqual(res["variable_usd"], 15.0, places=2)   # 5 + 10; NO coding, NO publication
        self.assertAlmostEqual(res["coding_usd"], 200.0, places=2)    # 100 × 2 months
        self.assertAlmostEqual(res["coding_metered_usd"], 7.0, places=2)
        self.assertAlmostEqual(res["publication_usd"], 30.0, places=2)
        self.assertAlmostEqual(res["grand_usd"], 252.0, places=2)
        self.assertEqual(res["cap"], 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
