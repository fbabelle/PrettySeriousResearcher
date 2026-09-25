#!/usr/bin/env python3
"""Tests for the research-writing drafting tools: reader_audit.py (blind-reader audit: reference block, summary
line, drift rows, argument parsing), translate_draft.py (structural guard, terms slot), plain_prose.py (length band
guard) and emph_scan.py (emphasis audit). No CLI is launched.

Run: python tests/test_writing_tools.py        (stdlib unittest; no third-party deps)
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, ".claude", "skills", "research-writing", "scripts")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


reader = _load("reader_audit")
td = _load("translate_draft")
plain = _load("plain_prose")
emph = _load("emph_scan")


class ReaderAudit(unittest.TestCase):
    def test_files_after_stops_at_the_next_option(self):
        argv = ["audit", "--files", "a.md", "b.md", "--parallel", "4", "--context"]
        self.assertEqual(reader.files_after(argv), ["a.md", "b.md"])
        self.assertEqual(reader.files_after(["audit"]), [])

    def test_audit_needs_draft_files(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(AssertionError):
            reader.stage_audit([], Path(d), 1, "high", None, False)

    def test_reader_persona_fills_the_brief(self):
        self.assertIn("{READER}", reader.AUDIT_BRIEF)
        brief = reader.AUDIT_BRIEF.replace("{READER}", "a statistician new to finance")
        self.assertTrue(brief.startswith("You are a statistician new to finance."))
        self.assertNotIn("sequential statistics", reader.AUDIT_BRIEF)

    def test_reference_block_collects_the_named_appendices(self):
        chunks = [("01-intro", "intro"), ("08-app-glossary", "terms"), ("09-app-proofs", "proofs")]
        self.assertEqual(reader.reference_text(chunks, "app-glossary,app-proofs"), "terms\n\nproofs")
        self.assertEqual(reader.reference_text(chunks, None), "")

    def test_summary_line_counts_jumps_and_chains(self):
        rows = [("s", {"clarity": 5, "link": "first", "point_position": "first sentence"}),
                ("s", {"clarity": 2, "link": "jump", "running_account": True, "point_position": "late"})]
        res = {"s": {"section": {"chain": "holds"}}, "t": {"section": {"chain": "detours"}}}
        line = reader.summary_line(res, rows)
        self.assertIn("mean 3.50", line)
        self.assertIn("jumps: 1 of 2", line)
        self.assertIn("chain holds: 1 of 2 sections", line)

    def test_drift_lists_long_paragraphs_whose_point_drifts(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            (work / "in").mkdir()
            (work / "out").mkdir()
            long_p = "[P01] " + "word " * 120
            short_p = "[P02] " + "word " * 20
            steady = "[P03] " + "word " * 120
            (work / "in" / "01-x.md").write_text("\n\n".join([long_p, short_p, steady]), encoding="utf-8")
            reply = {"paragraphs": [
                {"id": "P01", "running_account": True, "n_points": 2, "point_position": "first sentence", "clarity": 3},
                {"id": "P02", "running_account": True, "n_points": 5, "point_position": "late", "clarity": 2},
                {"id": "P03", "running_account": False, "n_points": 1, "point_position": "first sentence", "clarity": 5}]}
            (work / "out" / "01-x.json").write_text(json.dumps(reply), encoding="utf-8")
            rows = reader.drift_rows(work)
        self.assertEqual([r[2] for r in rows], ["P01"])   # long and drifting; P02 too short, P03 steady


class TranslateGuard(unittest.TestCase):
    EN = "## Results\n\nThe gain is 0.37 over 20 seeds [@smith2021], see Table 2.\n\n: Main results {#tbl:main}\n"

    def test_faithful_translation_passes(self):
        zh = "## Results\n\n增益为 0.37，基于 20 个种子 [@smith2021]，见 Table 2。\n\n: 主要结果 {#tbl:main}\n"
        bad, warn = td.guard(self.EN, zh)
        self.assertEqual(bad, [])

    def test_lost_number_and_lost_caption_marker_are_rejected(self):
        zh = "## Results\n\n增益为 0.38，基于 20 个种子 [@smith2021]，见 Table 2。\n\n主要结果 {#tbl:main}\n"
        bad, _ = td.guard(self.EN, zh)
        self.assertTrue(any("protected tokens" in b for b in bad))
        self.assertTrue(any("table-caption markers" in b for b in bad))

    def test_number_words_rendered_as_digits_only_warn(self):
        en = "## A\n\nWe ran twenty groups of five seeds each over the whole sample period here.\n"
        zh = "## A\n\n我们在整个样本期间运行了 20 组，每组 5 个种子。\n"
        bad, warn = td.guard(en, zh)
        self.assertEqual(bad, [])
        self.assertTrue(warn)

    def test_terms_slot(self):
        self.assertIn("arm, sleeve, and any established term", td.with_terms(td.BRIEF, ["arm", "sleeve"]))
        self.assertIn("unchanged: any established term", td.with_terms(td.BRIEF, []))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "terms.txt"
            p.write_text("# terms\narm\n\nsleeve\n", encoding="utf-8")
            self.assertEqual(td.load_terms(str(p)), ["arm", "sleeve"])


class PlainProseGuard(unittest.TestCase):
    OLD = "## A\n\nThe estimate, which we computed over the whole sample, holds; it is small.\n\nSecond paragraph stays.\n"

    def test_shorter_faithful_reply_passes(self):
        new = "## A\n\nWe computed the estimate over the whole sample. It holds. It is small.\n\nSecond paragraph stays.\n"
        self.assertEqual(plain.guard_plain(self.OLD, new), [])

    def test_merged_paragraphs_and_longer_reply_are_rejected(self):
        merged = "## A\n\nThe estimate holds and is small. Second paragraph stays.\n"
        self.assertTrue(any("paragraph count" in r for r in plain.guard_plain(self.OLD, merged)))
        longer = self.OLD.replace("it is small", "it is small, as a long list of further words that nobody asked for shows")
        self.assertTrue(any("longer" in r for r in plain.guard_plain(self.OLD, longer)))

    def test_terms_reach_the_brief(self):
        self.assertIn("exactly: arm, and every defined term", td.with_terms(plain.BRIEF, ["arm"]))


class EmphasisScan(unittest.TestCase):
    def test_reitalicised_term_and_mixed_treatment_are_reported(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "draft.md"
            p.write_text("# T\n\nAn *e-value* is defined here.\n\nLater the *e-value* again, and **e-value** in bold.\n\n"
                         "| *table* | cell |\n", encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(emph.main([str(p)]), 0)
            out = buf.getvalue()
        self.assertIn("2x  *e-value*", out)
        self.assertIn("both bold and italic", out)
        self.assertNotIn("*table*", out)

    def test_no_arguments_prints_usage(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(emph.main([]), 2)


if __name__ == "__main__":
    unittest.main()
